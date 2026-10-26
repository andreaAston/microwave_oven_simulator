"use strict";

(() => {
  const API_URL = "/api/simulator";
  const UPDATE_INTERVAL_MS = 1000;
  const STORAGE_KEY = "microwave-simulator-state";

  const elements = {
    wrap: document.getElementById("wrap"),
    time: document.getElementById("time"),
    message: document.getElementById("msg"),
    power: document.getElementById("pw"),
    halfPower: document.getElementById("half"),
    fullPower: document.getElementById("full"),
    doorText: document.getElementById("doorTxt"),
    statusText: document.getElementById("statTxt"),
    start: document.getElementById("start"),
    strip: document.getElementById("strip"),
    fault: document.getElementById("fault"),
  };

  let simulatorState = loadSavedState();
  let requestQueue = Promise.resolve();
  let previousStateName = "";
  let audioContext;
  let alarmGain;

  function loadSavedState() {
    const savedState = localStorage.getItem(STORAGE_KEY);
    if (!savedState) {
      return null;
    }

    try {
      return JSON.parse(savedState);
    } catch (error) {
      console.warn("Saved microwave state was invalid and will be reset.", error);
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  }

  function formatTime(totalSeconds) {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return [hours, minutes, seconds]
      .map((value) => String(value).padStart(2, "0"))
      .join(":");
  }

  function render(data) {
    simulatorState = data.state;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(simulatorState));

    elements.time.textContent = formatTime(simulatorState.remaining_seconds);
    elements.message.textContent =
      data.message ||
      (simulatorState.state === "WAITING"
        ? new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : "--");
    elements.power.textContent = data.power_text;
    elements.halfPower.classList.toggle(
      "on",
      simulatorState.power_watts === 300,
    );
    elements.fullPower.classList.toggle(
      "on",
      simulatorState.power_watts === 600,
    );
    elements.doorText.textContent = data.door_text;
    elements.statusText.textContent = data.status_text;
    elements.start.classList.toggle(
      "dim",
      simulatorState.state !== "ENABLED",
    );
    elements.wrap.classList.toggle("cooking", data.heating);
    elements.wrap.classList.toggle("open", !simulatorState.door_closed);
    elements.wrap.classList.toggle("lit", data.lit);
    elements.strip.textContent = "Python simulation · updates every second";

    const isDone = simulatorState.state === "DONE";
    if (isDone && previousStateName !== "DONE") {
      startBuzzer();
    } else if (!isDone && previousStateName === "DONE") {
      stopBuzzer();
    }
    previousStateName = simulatorState.state;
  }

  function send(action = { type: "tick" }) {
    requestQueue = requestQueue.then(async () => {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: simulatorState,
          action,
          fault: elements.fault.value,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `Request failed (${response.status}).`);
      }
      render(data);
    });

    requestQueue = requestQueue.catch((error) => {
      console.error("Microwave simulator request failed.", error);
      elements.message.textContent = "SERVER ERROR — TRY AGAIN";
    });
    return requestQueue;
  }

  function startBuzzer() {
    if (alarmGain) {
      alarmGain.gain.value = 0.08;
    }
  }

  function stopBuzzer() {
    if (alarmGain) {
      alarmGain.gain.value = 0;
    }
  }

  document.addEventListener("pointerdown", () => {
    if (audioContext) {
      return;
    }

    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioContext = new AudioContextClass();
      const oscillator = audioContext.createOscillator();
      alarmGain = audioContext.createGain();
      alarmGain.gain.value = 0;
      oscillator.frequency.value = 1800;
      oscillator.connect(alarmGain);
      alarmGain.connect(audioContext.destination);
      oscillator.start();
    } catch (error) {
      console.warn("Audio is unavailable; visual completion status still works.", error);
    }
  });

  document.querySelectorAll("[data-s]").forEach((button) => {
    button.addEventListener("click", () => {
      send({ type: "add_time", seconds: Number(button.dataset.s) });
    });
  });

  elements.halfPower.addEventListener("click", () => {
    send({ type: "set_power", watts: 300 });
  });
  elements.fullPower.addEventListener("click", () => {
    send({ type: "set_power", watts: 600 });
  });
  document.getElementById("clear").addEventListener("click", () => {
    send({ type: "clear_time" });
  });
  elements.start.addEventListener("click", () => {
    send({ type: "start" });
  });
  document.getElementById("stop").addEventListener("click", () => {
    send({ type: "stop" });
  });
  document.getElementById("doorBtn").addEventListener("click", () => {
    send({ type: "toggle_door" });
  });

  send();
  window.setInterval(() => send(), UPDATE_INTERVAL_MS);
})();
