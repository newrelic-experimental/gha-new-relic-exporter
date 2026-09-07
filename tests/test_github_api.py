import inspect
import unittest
from unittest.mock import patch

from src.github_api import create_github_api_client


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


if __name__ == "__main__":
    unittest.main()
