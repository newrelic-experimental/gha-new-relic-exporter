import unittest
from src.custom_parser import parse_attributes


class TestParseAttributes(unittest.TestCase):
    def test_basic_at_field(self):
        obj = {"created_at": "2025-08-27T12:00:00Z", "conclusion": "success"}
        result = parse_attributes(obj, [], None)
        self.assertIn("created_at", result)
        self.assertIn("created_at_ms", result)
        self.assertIsInstance(result["created_at_ms"], int)

    def test_cancelled_job_includes_ms(self):
        obj = {"started_at": "2025-08-27T12:00:00Z", "conclusion": "cancelled"}
        result = parse_attributes(obj, [], None)
        self.assertIn("started_at", result)
        self.assertIn("started_at_ms", result)
        self.assertIsInstance(result["started_at_ms"], int)

    def test_skipped_job_includes_ms(self):
        obj = {"started_at": "2025-08-27T12:00:00Z", "conclusion": "skipped"}
        result = parse_attributes(obj, [], None)
        self.assertIn("started_at", result)
        self.assertIn("started_at_ms", result)
        self.assertIsInstance(result["started_at_ms"], int)

    def test_nested_at_field(self):
        obj = {
            "details": {"finished_at": "2025-08-27T12:00:00Z"},
            "conclusion": "success",
        }
        result = parse_attributes(obj, [], None)
        self.assertIn("details.finished_at", result)
        self.assertIn("details.finished_at_ms", result)
        self.assertIsInstance(result["details.finished_at_ms"], int)


if __name__ == "__main__":
    unittest.main()
