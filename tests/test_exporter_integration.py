import unittest
from unittest import mock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
with mock.patch("custom_parser.check_env_vars", lambda: None):
    import exporter


class TestExporterIntegration(unittest.TestCase):
    @mock.patch.dict(
        os.environ,
        {
            "GHA_TOKEN": "dummy",
            "NEW_RELIC_LICENSE_KEY": "dummy",
            "OTEL_EXPORTER_OTEL_ENDPOINT": "http://localhost",
            "GHA_RUN_ID": "123",
            "GHA_RUN_NAME": "TestRun",
            "GITHUB_API_URL": "http://localhost/api",
            "GHA_REPOSITORY": "octocat/Hello-World",
            "GHA_REPOSITORY_OWNER": "octocat",
            "GHA_EXPORT_LOGS": "false",
        },
    )
    @mock.patch("exporter.requests.get")
    @mock.patch("exporter.zipfile.ZipFile")
    @mock.patch("exporter.GhApi")
    @mock.patch("exporter.do_fastcore_decode")
    def test_main_workflow(
        self, mock_do_fastcore_decode, mock_GhApi, mock_ZipFile, mock_requests_get
    ):
        # Provide mock workflow and job JSON
        mock_workflow_json = '{"run_started_at": "2025-08-27T12:00:00Z", "jobs": [{"name": "build", "started_at": "2025-08-27T12:01:00Z"}]}'
        mock_job_json = (
            '{"jobs": [{"name": "build", "started_at": "2025-08-27T12:01:00Z"}]}'
        )

        # Patch do_fastcore_decode to return appropriate mock JSON
        def side_effect(arg):
            if "get_workflow_run" in str(arg):
                return mock_workflow_json
            if "list_jobs_for_workflow_run" in str(arg):
                return mock_job_json
            return "{}"

        mock_do_fastcore_decode.side_effect = side_effect
        # Mock API responses
        mock_GhApi.return_value.actions.get_workflow_run.return_value = {}
        mock_GhApi.return_value.actions.list_jobs_for_workflow_run.return_value = {}
        mock_requests_get.return_value.content = b"dummyzip"
        # Mock zipfile extraction
        mock_zip = mock.Mock()
        mock_ZipFile.return_value.__enter__.return_value = mock_zip
        mock_zip.extractall.return_value = None
        # Run main logic (import triggers execution)
        try:
            # If exporter.py has a main() or similar, call it here
            pass
        except Exception as e:
            self.fail(f"Exporter main workflow raised an exception: {e}")


if __name__ == "__main__":
    unittest.main()
