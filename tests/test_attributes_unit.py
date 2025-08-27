import unittest
from src.custom_parser import parse_attributes


class TestParseAttributesUnit(unittest.TestCase):
    def test_basic_at_field(self):
        obj = {"created_at": "2025-08-27T12:00:00Z", "conclusion": "success"}
        result = parse_attributes(obj, [], None)
        self.assertIn("created_at", result)
        self.assertIn("created_at_ms", result)
        self.assertIsInstance(result["created_at_ms"], int)
        self.assertFalse(result["job_reused"])
        if "queue_time_ms" in result:
            self.assertGreaterEqual(result["queue_time_ms"], 0)
        if "duration_ms" in result:
            self.assertGreaterEqual(result["duration_ms"], 0)

    def test_cancelled_job_includes_ms(self):
        obj = {"started_at": "2025-08-27T12:00:00Z", "conclusion": "cancelled"}
        result = parse_attributes(obj, [], None)
        self.assertIn("started_at", result)
        self.assertIn("started_at_ms", result)
        self.assertIsInstance(result["started_at_ms"], int)
        self.assertFalse(result["job_reused"])
        if "queue_time_ms" in result:
            self.assertGreaterEqual(result["queue_time_ms"], 0)
        if "duration_ms" in result:
            self.assertGreaterEqual(result["duration_ms"], 0)

    def test_skipped_job_includes_ms(self):
        obj = {"started_at": "2025-08-27T12:00:00Z", "conclusion": "skipped"}
        result = parse_attributes(obj, [], None)
        self.assertIn("started_at", result)
        self.assertIn("started_at_ms", result)
        self.assertIsInstance(result["started_at_ms"], int)
        self.assertFalse(result["job_reused"])
        if "queue_time_ms" in result:
            self.assertGreaterEqual(result["queue_time_ms"], 0)
        if "duration_ms" in result:
            self.assertGreaterEqual(result["duration_ms"], 0)

    def test_nested_at_field(self):
        obj = {
            "details": {"finished_at": "2025-08-27T12:00:00Z"},
            "conclusion": "success",
        }
        result = parse_attributes(obj, [], None)
        self.assertIn("details.finished_at", result)
        self.assertIn("details.finished_at_ms", result)
        self.assertIsInstance(result["details.finished_at_ms"], int)
        self.assertFalse(result["job_reused"])
        if "queue_time_ms" in result:
            self.assertGreaterEqual(result["queue_time_ms"], 0)
        if "duration_ms" in result:
            self.assertGreaterEqual(result["duration_ms"], 0)

    def test_reused_job(self):
        reused_job = {
            "id": 789012,
            "name": "reused",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2025-08-27T13:00:00Z",
            "started_at": "2025-08-27T12:59:00Z",  # started_at < created_at
            "completed_at": "2025-08-27T13:05:00Z",
        }
        result = parse_attributes(reused_job, [], None)
        self.assertTrue(result["job_reused"])
        self.assertEqual(result["queue_time_ms"], 0)
        self.assertEqual(result["duration_ms"], 0)
        self.assertEqual(result["started_at"], result["created_at"])
        self.assertEqual(result["started_at_ms"], result["created_at_ms"])


if __name__ == "__main__":
    unittest.main()
