import copy
import unittest
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from src.app import activities, signup_for_activity, unregister_from_activity


class ActivityCapacityTests(unittest.TestCase):
    def setUp(self):
        self.original_activities = copy.deepcopy(activities)

    def tearDown(self):
        activities.clear()
        activities.update(self.original_activities)

    def test_signup_rejects_full_activity(self):
        activity = activities["Math Club"]
        activity["participants"] = [
            f"student{index}@mergington.edu"
            for index in range(activity["max_participants"])
        ]

        with self.assertRaises(HTTPException) as context:
            signup_for_activity("Math Club", "waiting@mergington.edu")

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.detail, "Activity is full")
        self.assertNotIn("waiting@mergington.edu", activity["participants"])

    def test_signup_accepts_last_available_place(self):
        activity = activities["Math Club"]
        activity["participants"] = [
            f"student{index}@mergington.edu"
            for index in range(activity["max_participants"] - 1)
        ]

        signup_for_activity("Math Club", "last-place@mergington.edu")

        self.assertEqual(
            len(activity["participants"]), activity["max_participants"]
        )

    def test_simultaneous_signups_cannot_exceed_capacity(self):
        activity = activities["Math Club"]
        activity["max_participants"] = 1
        activity["participants"] = []

        def attempt_signup(email):
            try:
                signup_for_activity("Math Club", email)
                return 200
            except HTTPException as error:
                return error.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(
                executor.map(
                    attempt_signup,
                    ["first@mergington.edu", "second@mergington.edu"],
                )
            )

        self.assertCountEqual(statuses, [200, 409])
        self.assertEqual(len(activity["participants"]), 1)

    def test_unregistering_makes_a_place_available(self):
        activity = activities["Math Club"]
        activity["max_participants"] = 1
        activity["participants"] = ["leaving@mergington.edu"]

        unregister_from_activity("Math Club", "leaving@mergington.edu")
        signup_for_activity("Math Club", "joining@mergington.edu")

        self.assertEqual(activity["participants"], ["joining@mergington.edu"])


if __name__ == "__main__":
    unittest.main()