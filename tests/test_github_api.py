import inspect
import unittest
from unittest.mock import MagicMock, call, patch

from src.github_api import create_github_api_client, list_all_jobs_for_workflow_run


class TestCreateGithubApiClient(unittest.TestCase):
    @patch("src.github_api.GhApi")
    def test_uses_synchronous_operations(self, gh_api):
        create_github_api_client(owner="example", repo="repository", token="token")

        gh_api.assert_called_once_with(
            owner="example",
            repo="repository",
            token="token",
            sync=True,
        )

    def test_operations_are_synchronous(self):
        api = create_github_api_client(
            owner="example",
            repo="repository",
            token="token",
        )

        self.assertFalse(
            inspect.iscoroutinefunction(api.actions.get_workflow_run.__call__)
        )


class TestListAllJobsForWorkflowRun(unittest.TestCase):
    def make_jobs(self, start, count):
        return [{"id": i, "name": f"job-{i}"} for i in range(start, start + count)]

    def test_single_partial_page_makes_one_call(self):
        api = MagicMock()
        api.actions.list_jobs_for_workflow_run.return_value = {
            "total_count": 3,
            "jobs": self.make_jobs(0, 3),
        }

        result = list_all_jobs_for_workflow_run(api, 42)

        api.actions.list_jobs_for_workflow_run.assert_called_once_with(
            42, page=1, per_page=100
        )
        self.assertEqual(result, {"total_count": 3, "jobs": self.make_jobs(0, 3)})

    def test_fetches_every_page_until_total_count(self):
        api = MagicMock()
        api.actions.list_jobs_for_workflow_run.side_effect = [
            {"total_count": 150, "jobs": self.make_jobs(0, 100)},
            {"total_count": 150, "jobs": self.make_jobs(100, 50)},
        ]

        result = list_all_jobs_for_workflow_run(api, 42)

        self.assertEqual(
            api.actions.list_jobs_for_workflow_run.call_args_list,
            [
                call(42, page=1, per_page=100),
                call(42, page=2, per_page=100),
            ],
        )
        self.assertEqual(result["jobs"], self.make_jobs(0, 150))

    def test_full_page_matching_total_count_makes_no_extra_call(self):
        api = MagicMock()
        api.actions.list_jobs_for_workflow_run.return_value = {
            "total_count": 100,
            "jobs": self.make_jobs(0, 100),
        }

        result = list_all_jobs_for_workflow_run(api, 42)

        self.assertEqual(api.actions.list_jobs_for_workflow_run.call_count, 1)
        self.assertEqual(len(result["jobs"]), 100)

    def test_empty_first_page_returns_no_jobs(self):
        api = MagicMock()
        api.actions.list_jobs_for_workflow_run.return_value = {
            "total_count": 0,
            "jobs": [],
        }

        result = list_all_jobs_for_workflow_run(api, 42)

        self.assertEqual(api.actions.list_jobs_for_workflow_run.call_count, 1)
        self.assertEqual(result, {"total_count": 0, "jobs": []})

    def test_missing_total_count_stops_on_short_page(self):
        api = MagicMock()
        api.actions.list_jobs_for_workflow_run.side_effect = [
            {"jobs": self.make_jobs(0, 100)},
            {"jobs": []},
        ]

        result = list_all_jobs_for_workflow_run(api, 42)

        self.assertEqual(api.actions.list_jobs_for_workflow_run.call_count, 2)
        self.assertIsNone(result["total_count"])
        self.assertEqual(result["jobs"], self.make_jobs(0, 100))


if __name__ == "__main__":
    unittest.main()
