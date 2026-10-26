# Microwave Oven Simulator

**RTS 521 Real-Time Systems — Assignment 2**  
Malawi University of Business and Applied Sciences (MUBAS)

| | |
|---|---|
| Student | Andrea Aston |
| Student ID | BECE/21/SS/002 |
| Lecturer | Mr M. Banda |
| Due date | 3 November 2026 |
| Live demo | `<add your deployment link here>` |
| Repository | `<add your GitHub repo link here>` |

## Overview

A browser-based microwave simulator with a Python/Flask backend. The oven state machine, timer, power selection, safety checks, and fault handling run in Python. The browser uses HTML and CSS for the interface and responsive styling, plus a small JavaScript client to send controls to the Python API, render responses, animate the oven, and play the completion sound.

The Python API is stateless: each request includes the current simulator state, and the response returns its updated state. The browser stores that state locally, so the application does not need a database or a continuously running server process. The API advances the simulation on user actions and once-per-second browser updates; it is not a continuously running 50 ms round-robin loop.

## Project files

| File or folder | Purpose |
|---|---|
| `app.py` | Flask application, API endpoint, input validation, and Python simulation state machine. |
| `templates/index.html` | Microwave and control-panel markup. |
| `static/styles.css` | Microwave appearance, animations, and responsive layout. |
| `static/script.js` | Browser API client, display updates, and optional completion sound. |
| `requirements.txt` | Python package dependencies. |
| `tests/test_app.py` | Tests for state transitions, safety behavior, and Flask routes. |
| `.gitignore` | Excludes Python environments, caches, and local environment variables. |
| `README.md` | Project documentation. |

## Run locally

Python 3.10 or newer is recommended.

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start the web app:

   ```powershell
   python app.py
   ```

4. Open <http://127.0.0.1:8000/>.

The app must be run through Flask; opening `index.html` directly will not provide the Python API.

## Use the controls

Choose a power level, set a cooking time, then press **Start**. Preset time buttons add to the current time.

| Control | Behaviour |
|---|---|
| **Half 300 W / Full 600 W** | Selects the power level. Full power is the default. |
| **1s, 10s, 30s, 1m, 5m, 10m, 1h** | Adds the selected time. For example, 1m followed by 30s sets 00:01:30. The maximum is 99:59:59. |
| **Clear Time** | Resets the remaining time to zero when the oven is not operating. |
| **Start** | Starts cooking when time is set and the door is closed. |
| **Stop** | Stops cooking and retains the remaining time. Press it again while stopped to clear the time. During the completion alert, it returns the oven to waiting. |
| **Open / Close Door** | Toggles the door. Opening it during cooking stops heating; close the door and press Start to continue with the remaining time. |
| **Test fault** | Selects a turntable or emitter fault for testing. A selected fault triggers the alarm while checking or cooking; choose `none` for normal operation. |

On narrow screens, the full panel remains beside the cavity. Start, Stop, Clear, and door controls use icons on small screens and retain accessible names.

## Safety and states

The simulator uses `WAITING`, `HALF_POWER`, `FULL_POWER`, `SET_TIME`, `ENABLED`, `DISABLED`, `CHECKING`, `COOK`, `ALARM`, and `DONE`.

- Heating is enabled only while the state is `COOK`, the door is closed, and time remains. A selected fault prevents heating and triggers the alarm.
- Opening the door during cooking stops heating and preserves the remaining time. Closing it does not automatically restart cooking; press **Start** again.
- When the timer reaches zero, the oven enters `DONE`, displays a completion message, and sounds a buzzer for five seconds before returning to `WAITING`.
- A fault selected during checking or cooking moves the oven to `ALARM`. The fault is displayed briefly before the oven becomes `DISABLED`.

## Tests

Run the Python tests with:

```powershell
python -m unittest discover -s tests -v
```

The tests cover timer progression, door interlocks, fault handling, invalid actions, and the Flask page/API routes.

## Deploy to Vercel

**Yes, this project can be deployed to Vercel as a Python web app.** Vercel supports Flask applications as Python Functions. This project uses the root `app.py` entry point and declares Flask in `requirements.txt`, which Vercel uses to detect the framework and install the dependency. No `vercel.json` or build command should be needed for this layout.

1. Push the complete project, including `app.py`, `requirements.txt`, `templates/`, and `static/`, to a Git repository.
2. Import that repository into Vercel and deploy using the detected Python framework settings.
3. Open the deployment URL and test the controls. The API is served by Vercel Functions; simulator state is held by each visitor's browser, not shared between visitors.

This is suitable for a small interactive simulator. Since browser updates call the Python Function about once per second, it is not intended for high-traffic production workloads without revisiting the polling frequency and hosting design.

See Vercel's [Python Runtime documentation](https://vercel.com/docs/functions/runtimes/python) and [Flask deployment guide](https://vercel.com/docs/frameworks/backend/flask) for current deployment details.

## Manual test checklist

1. Set 1m and then 30s. Confirm the display shows 00:01:30.
2. Press **Start**. Confirm the turntable spins and the timer counts down.
3. Open the door while cooking. Confirm heating stops and the remaining time is retained.
4. Close the door and press **Start**. Confirm cooking continues from the remaining time.
5. Run a short timer to zero. Confirm the completion message and five-second buzzer.
6. While cooking, press **Stop** once to stop with time remaining, then again to clear it.
7. Select a fault and start cooking. Confirm the fault message appears and the oven becomes disabled.
8. Resize the browser to a narrow mobile width. Confirm the cavity and controls remain side-by-side without horizontal page scrolling.

## Screenshots

Screenshots of the simulator states are saved in `docs/`:

- [Cooking Complete](docs/Cooking%20Complete.png)
- [Door Closed Cooking](docs/Door%20Closed%20Cooking.png)
- [Door Closed Waiting State](docs/Door%20Closed%20Waiting%20State.png)
- [Door Open](docs/Door%20Open.png)
- [Door Open can not start cooking](docs/Door%20Open%20can%20not%20start%20cooking.png)

## References

- Simon, D. E. (1999). *An Embedded Software Primer*. Addison-Wesley. https://www.informit.com/title/020161569X
- Sommerville, I. (2016). *Software Engineering* (10th ed.). Pearson. https://www.pearson.com/en-us/subject-catalog/p/software-engineering/P200000003258/9780137503148
