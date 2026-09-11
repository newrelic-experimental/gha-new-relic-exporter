import unittest
from unittest.mock import Mock

from opentelemetry.trace import StatusCode

from src.custom_parser import record_conclusion


class TestRecordConclusion(unittest.TestCase):
    def test_failed_conclusions_set_error_status(self):
        for conclusion in ("failure", "timed_out", "startup_failure"):
            span = Mock()
            record_conclusion(span, conclusion)

            span.set_status.assert_called_once()
            status = span.set_status.call_args[0][0]
            self.assertEqual(status.status_code, StatusCode.ERROR)
            span.set_attribute.assert_called_once_with("error.type", conclusion)

    def test_non_failed_conclusions_leave_status_unset(self):
        for conclusion in ("success", "cancelled", "skipped", "neutral", "action_required", None):
            span = Mock()
            record_conclusion(span, conclusion)

            span.set_status.assert_not_called()
            span.set_attribute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
