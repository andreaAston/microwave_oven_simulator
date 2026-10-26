"""Python API and simulation state machine for the microwave web app."""

from __future__ import annotations

import math
import time
from typing import Any

from flask import Flask, jsonify, render_template, request

MAX_COOKING_SECONDS = 359_999
ALLOWED_TIME_BUTTONS = {1, 10, 30, 60, 300, 600, 3600}
FAULTS = {"none", "Turntable fault", "Emitter fault"}
OPERATIONAL_STATES = {"CHECKING", "COOK"}
VALID_STATES = {
    "WAITING",
    "HALF_POWER",
    "FULL_POWER",
    "SET_TIME",
    "ENABLED",
    "DISABLED",
    "CHECKING",
    "COOK",
    "ALARM",
    "DONE",
}
STATUS_LABELS = {
    "WAITING": "",
    "HALF_POWER": "Half power",
    "FULL_POWER": "Full power",
    "SET_TIME": "Set time",
    "DISABLED": "Not ready",
    "ENABLED": "Ready to cook",
    "CHECKING": "Checking...",
    "COOK": "Cooking",
    "DONE": "Cooking complete",
}
TIME_FIELDS = (
    "message_expires_at",
    "last_countdown_at",
    "set_time_expires_at",
    "done_expires_at",
    "alarm_expires_at",
)

app = Flask(__name__)


def new_state() -> dict[str, Any]:
    """Return the initial state for a new browser session."""
    return {
        "state": "WAITING",
        "door_closed": True,
        "power_watts": 600,
        "remaining_seconds": 0,
        "message": "",
        "message_expires_at": 0,
        "last_countdown_at": 0,
        "set_time_expires_at": 0,
        "done_expires_at": 0,
        "alarm_expires_at": 0,
        "alarm_message": "",
    }


def normalize_state(value: Any) -> dict[str, Any]:
    """Validate and copy the state sent by the browser."""
    if value is None:
        return new_state()
    if not isinstance(value, dict):
        raise ValueError("Simulator state must be an object.")

    state = new_state()
    name = value.get("state", state["state"])
    if not isinstance(name, str) or name not in VALID_STATES:
        raise ValueError("Simulator state name is invalid.")
    state["state"] = name

    door_closed = value.get("door_closed", True)
    if not isinstance(door_closed, bool):
        raise ValueError("Door state must be true or false.")
    state["door_closed"] = door_closed

    power_watts = value.get("power_watts", 600)
    if type(power_watts) is not int or power_watts not in {300, 600}:
        raise ValueError("Power must be 300 or 600 watts.")
    state["power_watts"] = power_watts

    remaining_seconds = value.get("remaining_seconds", 0)
    if (
        type(remaining_seconds) is not int
        or not 0 <= remaining_seconds <= MAX_COOKING_SECONDS
    ):
        raise ValueError("Remaining time must be between 0 and 359999 seconds.")
    state["remaining_seconds"] = remaining_seconds

    message = value.get("message", "")
    alarm_message = value.get("alarm_message", "")
    if not isinstance(message, str) or len(message) > 200:
        raise ValueError("Message must be a string of at most 200 characters.")
    if not isinstance(alarm_message, str) or len(alarm_message) > 200:
        raise ValueError("Alarm message must be a string of at most 200 characters.")
    state["message"] = message
    state["alarm_message"] = alarm_message

    for field in TIME_FIELDS:
        timestamp = value.get(field, 0)
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
        ):
            raise ValueError(f"{field} must be a finite number.")
        state[field] = timestamp

    return state


def show_message(state: dict[str, Any], text: str, now: float) -> None:
    state["message"] = text
    state["message_expires_at"] = now + 2.5


def reset_to_waiting(state: dict[str, Any]) -> None:
    state["remaining_seconds"] = 0
    state["state"] = "WAITING"
    state["last_countdown_at"] = 0


def process_action(
    value: Any,
    action: Any,
    fault: Any = "none",
    now: float | None = None,
) -> dict[str, Any]:
    """Advance the simulator for one user action or periodic browser tick."""
    state = normalize_state(value)
    current_time = time.time() if now is None else now

    if not isinstance(action, dict):
        raise ValueError("Action must be an object.")
    action_type = action.get("type", "tick")
    if not isinstance(action_type, str):
        raise ValueError("Action type must be a string.")
    if action_type not in {
        "tick",
        "add_time",
        "clear_time",
        "set_power",
        "start",
        "stop",
        "toggle_door",
    }:
        raise ValueError("Unknown simulator action.")
    if not isinstance(fault, str) or fault not in FAULTS:
        raise ValueError("Selected fault is invalid.")

    if action_type == "add_time":
        seconds = action.get("seconds")
        if type(seconds) is not int or seconds not in ALLOWED_TIME_BUTTONS:
            raise ValueError("Time must match one of the preset buttons.")
    if action_type == "set_power":
        watts = action.get("watts")
        if type(watts) is not int or watts not in {300, 600}:
            raise ValueError("Power must be 300 or 600 watts.")

    starting_state = state["state"]

    if starting_state in OPERATIONAL_STATES and fault != "none":
        state["state"] = "ALARM"
        state["alarm_message"] = fault
        state["alarm_expires_at"] = current_time + 2.5
    else:
        if starting_state == "COOK":
            elapsed = max(0, int(current_time - state["last_countdown_at"]))
            if elapsed:
                state["remaining_seconds"] = max(
                    0, state["remaining_seconds"] - elapsed
                )
                state["last_countdown_at"] += elapsed

        if (
            state["state"] == "SET_TIME"
            and current_time >= state["set_time_expires_at"]
        ):
            state["state"] = "ENABLED" if state["door_closed"] else "DISABLED"

        if action_type == "toggle_door":
            state["door_closed"] = not state["door_closed"]
            show_message(
                state,
                f"Food container door now {'closed' if state['door_closed'] else 'opened'}",
                current_time,
            )
            if not state["door_closed"]:
                if state["state"] in {"DONE", "ALARM"}:
                    reset_to_waiting(state)
                elif state["state"] in OPERATIONAL_STATES | {"ENABLED", "SET_TIME"}:
                    state["state"] = "DISABLED"
                    state["last_countdown_at"] = 0
            elif state["state"] == "DISABLED":
                state["state"] = (
                    "ENABLED" if state["remaining_seconds"] > 0 else "WAITING"
                )
        elif action_type == "stop":
            if state["state"] in OPERATIONAL_STATES:
                state["state"] = "ENABLED"
                state["last_countdown_at"] = 0
                show_message(state, "Cooking stopped", current_time)
            elif state["state"] == "DONE":
                reset_to_waiting(state)
            elif state["state"] != "ALARM" and (
                state["remaining_seconds"] > 0 or state["state"] == "DISABLED"
            ):
                reset_to_waiting(state)
                show_message(state, "Time cleared", current_time)
        elif action_type == "start":
            if state["state"] == "ENABLED" and state["remaining_seconds"] > 0:
                state["state"] = "CHECKING"
            elif state["state"] == "DISABLED":
                show_message(state, "Not ready", current_time)
            elif state["remaining_seconds"] == 0:
                show_message(state, "Set a cooking time", current_time)
        elif action_type == "clear_time":
            if state["state"] not in OPERATIONAL_STATES | {"DONE", "ALARM"}:
                reset_to_waiting(state)
                show_message(state, "Time cleared", current_time)
        elif action_type == "add_time":
            if state["state"] not in OPERATIONAL_STATES | {"DONE", "ALARM"}:
                state["remaining_seconds"] = min(
                    state["remaining_seconds"] + action["seconds"],
                    MAX_COOKING_SECONDS,
                )
                state["state"] = "SET_TIME"
                state["set_time_expires_at"] = current_time + 0.7
        elif action_type == "set_power":
            if state["state"] not in OPERATIONAL_STATES | {"DONE", "ALARM"}:
                state["power_watts"] = action["watts"]
                show_message(
                    state,
                    "Half power" if action["watts"] == 300 else "Full power",
                    current_time,
                )
                if state["remaining_seconds"] == 0:
                    state["state"] = (
                        "HALF_POWER" if action["watts"] == 300 else "FULL_POWER"
                    )

        if (
            state["state"] == "SET_TIME"
            and current_time >= state["set_time_expires_at"]
        ):
            state["state"] = "ENABLED" if state["door_closed"] else "DISABLED"

        if starting_state == "CHECKING" and state["state"] == "CHECKING":
            state["state"] = "COOK"
            state["last_countdown_at"] = current_time

        if state["state"] == "COOK" and state["remaining_seconds"] == 0:
            state["state"] = "DONE"
            state["done_expires_at"] = current_time + 5

        if state["state"] == "DONE" and current_time >= state["done_expires_at"]:
            reset_to_waiting(state)

        if state["state"] == "ALARM" and current_time >= state["alarm_expires_at"]:
            state["state"] = "DISABLED"

    return state


def present_state(state: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    """Return safe display values derived from the simulation state."""
    current_time = time.time() if now is None else now
    state_name = state["state"]
    if current_time < state["message_expires_at"]:
        message = state["message"]
    elif state_name == "ALARM":
        message = state["alarm_message"]
    else:
        message = STATUS_LABELS[state_name]

    is_heating = (
        state_name == "COOK"
        and state["door_closed"]
        and state["remaining_seconds"] > 0
    )
    status_text = (
        "COOKING"
        if is_heating
        else "DISABLED"
        if state_name in {"DISABLED", "ALARM"}
        else "DONE - BEEP"
        if state_name == "DONE"
        else "STANDING BY"
    )
    return {
        "state": state,
        "message": message,
        "status_text": status_text,
        "door_text": "DOOR CLOSED" if state["door_closed"] else "DOOR OPEN",
        "power_text": f"{'HALF' if state['power_watts'] == 300 else 'FULL'} "
        f"{state['power_watts']} W",
        "heating": is_heating,
        "lit": (
            not state["door_closed"]
            or state_name == "DISABLED"
            or state_name in {"CHECKING", "COOK", "DONE", "ALARM"}
        ),
    }


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/simulator")
def simulator():
    if not request.is_json:
        return jsonify(error="Expected a JSON request."), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object."), 400

    try:
        state = process_action(
            payload.get("state"),
            payload.get("action", {"type": "tick"}),
            payload.get("fault", "none"),
        )
    except ValueError as error:
        return jsonify(error=str(error)), 400

    return jsonify(present_state(state))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
