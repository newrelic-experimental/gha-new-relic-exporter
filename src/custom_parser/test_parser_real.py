import unittest
import json
from src.custom_parser import parse_attributes


class TestParseAttributesRealData(unittest.TestCase):
    def setUp(self):
        # Example GitHub Actions job run response (simplified)
        self.github_job_run = {
            "id": 123456,
            "name": "build",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2025-08-27T12:00:00Z",
            "started_at": "2025-08-27T12:01:00Z",
            "completed_at": "2025-08-27T12:10:00Z",
            "steps": [
                {
                    "name": "checkout",
                    "status": "completed",
                    "conclusion": "success",
                    "number": 1,
                    "started_at": "2025-08-27T12:01:10Z",
                    "completed_at": "2025-08-27T12:01:20Z",
                },
                {
                    "name": "build",
                    "status": "completed",
                    "conclusion": "failure",
                    "number": 2,
                    "started_at": "2025-08-27T12:01:30Z",
                    "completed_at": "2025-08-27T12:09:00Z",
                },
            ],
        }
        self.cancelled_job_run = {
            "id": 654321,
            "name": "test",
            "status": "completed",
            "conclusion": "cancelled",
            "created_at": "2025-08-27T13:00:00Z",
            "started_at": None,
            "completed_at": "2025-08-27T13:05:00Z",
            "steps": [],
        }

    def test_successful_job_run(self):
        result = parse_attributes(self.github_job_run, [], None)
        self.assertIn("created_at", result)
        self.assertIn("created_at_ms", result)
        self.assertIn("started_at", result)
        self.assertIn("started_at_ms", result)
        self.assertIn("completed_at", result)
        self.assertIn("completed_at_ms", result)
        self.assertIn("steps.name", result)
        self.assertIn("steps.status", result)
        self.assertIn("steps.conclusion", result)
        self.assertIn("steps.number", result)
        self.assertIn("steps.started_at", result)
        self.assertIn("steps.started_at_ms", result)
        self.assertIn("steps.completed_at", result)
        self.assertIn("steps.completed_at_ms", result)
        self.assertEqual(result["conclusion"], "success")

    def test_cancelled_job_run(self):
        result = parse_attributes(self.cancelled_job_run, [], None)
        self.assertIn("created_at", result)
        self.assertIn("created_at_ms", result)
        self.assertIn("completed_at", result)
        self.assertIn("completed_at_ms", result)
        self.assertIn("conclusion", result)
        self.assertEqual(result["conclusion"], "cancelled")

        # started_at is set to created_at for cancelled jobs
        self.assertIn("started_at", result)
        self.assertEqual(result["started_at"], result["created_at"])
        self.assertIn("started_at_ms", result)
        self.assertEqual(result["started_at_ms"], result["created_at_ms"])

    def test_missing_fields(self):
        minimal = {"id": 1, "conclusion": "skipped"}
        result = parse_attributes(minimal, [], None)
        self.assertIn("conclusion", result)
        self.assertEqual(result["conclusion"], "skipped")
        self.assertNotIn("created_at_ms", result)
        self.assertNotIn("started_at_ms", result)

    def test_step_failure(self):
        # Check that step failure is parsed
        result = parse_attributes(self.github_job_run, [], None)
        self.assertIn("steps.conclusion", result)
        self.assertEqual(result["steps.conclusion"], "failure")


if __name__ == "__main__":
    unittest.main()
