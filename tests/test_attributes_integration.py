import unittest
from src.custom_parser import parse_attributes


class TestParseAttributesIntegration(unittest.TestCase):
    def test_realistic_job(self):
        job = {
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
                    "started_at": "2025-08-27T12:01:00Z",
                    "completed_at": "2025-08-27T12:02:00Z",
                },
                {
                    "name": "build",
                    "status": "completed",
                    "conclusion": "success",
                    "started_at": "2025-08-27T12:02:00Z",
                    "completed_at": "2025-08-27T12:10:00Z",
                },
            ],
        }
        result = parse_attributes(job, [], None)
        self.assertIn("created_at_ms", result)
        self.assertIn("started_at_ms", result)
        self.assertIn("completed_at_ms", result)
        self.assertGreaterEqual(result["queue_time_ms"], 0)
        self.assertGreaterEqual(result["duration_ms"], 0)


if __name__ == "__main__":
    unittest.main()
