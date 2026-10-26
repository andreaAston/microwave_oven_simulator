import unittest

from app import app, new_state, present_state, process_action


class SimulatorTests(unittest.TestCase):
    def test_timer_addition_and_cooking_countdown(self):
        state = process_action(None, {"type": "add_time", "seconds": 60}, now=100)
        self.assertEqual(state["remaining_seconds"], 60)
        self.assertEqual(state["state"], "SET_TIME")

        state = process_action(state, {"type": "tick"}, now=101)
        self.assertEqual(state["state"], "ENABLED")
        state = process_action(state, {"type": "start"}, now=102)
        self.assertEqual(state["state"], "CHECKING")
        state = process_action(state, {"type": "tick"}, now=103)
        self.assertEqual(state["state"], "COOK")
        state = process_action(state, {"type": "tick"}, now=106)
        self.assertEqual(state["remaining_seconds"], 57)

    def test_start_after_time_entry_window_does_not_need_an_extra_tick(self):
        state = process_action(None, {"type": "add_time", "seconds": 60}, now=100)

        state = process_action(state, {"type": "start"}, now=101)

        self.assertEqual(state["state"], "CHECKING")

    def test_open_door_stops_heating_and_preserves_time(self):
        state = new_state()
        state.update(
            state="COOK",
            remaining_seconds=20,
            last_countdown_at=100,
        )

        state = process_action(state, {"type": "toggle_door"}, now=103)

        self.assertEqual(state["state"], "DISABLED")
        self.assertEqual(state["remaining_seconds"], 17)
        self.assertFalse(state["door_closed"])
        self.assertFalse(present_state(state, now=103)["heating"])

    def test_selected_fault_disables_heating(self):
        state = new_state()
        state.update(state="COOK", remaining_seconds=30, last_countdown_at=100)

        state = process_action(
            state,
            {"type": "tick"},
            fault="Emitter fault",
            now=101,
        )

        self.assertEqual(state["state"], "ALARM")
        self.assertFalse(present_state(state, now=101)["heating"])

    def test_invalid_actions_are_rejected(self):
        with self.assertRaises(ValueError):
            process_action(None, {"type": "add_time", "seconds": 2}, now=100)

        with self.assertRaises(ValueError):
            process_action(None, {"type": "start"}, fault="Unexpected fault", now=100)

    def test_flask_serves_page_and_simulator_api(self):
        client = app.test_client()

        page = client.get("/")
        script = client.get("/static/script.js")
        stylesheet = client.get("/static/styles.css")
        response = client.post(
            "/api/simulator",
            json={"state": None, "action": {"type": "tick"}, "fault": "none"},
        )

        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Microwave Oven Simulator", page.data)
        self.assertEqual(script.status_code, 200)
        self.assertIn(b"/api/simulator", script.data)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["state"]["state"], "WAITING")
        script.close()
        stylesheet.close()


if __name__ == "__main__":
    unittest.main()
