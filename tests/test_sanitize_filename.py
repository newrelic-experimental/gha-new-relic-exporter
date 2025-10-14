import unittest
import sys

sys.path.insert(0, "../src")
from src.custom_parser import sanitize_filename


class TestSanitizeFilename(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(sanitize_filename("simple-job"), "simple-job")
        self.assertEqual(sanitize_filename("job name"), "job name")

    def test_slash(self):
        self.assertEqual(
            sanitize_filename("Run reusable workflow/Deploy"),
            "Run reusable workflow _ Deploy",
        )

    def test_special_chars(self):
        self.assertEqual(
            sanitize_filename("job:name*with?special|chars"),
            "job_name_with_special_chars",
        )
        self.assertEqual(sanitize_filename("job\\name"), "job_name")
        # < and > are now preserved since GitHub Actions preserves them in log folder names
        self.assertEqual(sanitize_filename("job<name>"), "job<name>")
        self.assertEqual(sanitize_filename('job"name'), "job_name")

    def test_unicode(self):
        self.assertEqual(sanitize_filename("jób-nâmé"), "jób-nâmé")
        self.assertEqual(sanitize_filename("job—name"), "job—name")

    def test_strip(self):
        self.assertEqual(sanitize_filename("  job name  "), "job name")

    def test_github_actions_folder_names(self):
        # Test the exact case from the bug report
        self.assertEqual(
            sanitize_filename("Clone PROD > DEV branch"),
            "Clone PROD > DEV branch",
        )
        # Test other common GitHub Actions naming patterns
        self.assertEqual(
            sanitize_filename("Build > Test > Deploy"),
            "Build > Test > Deploy",
        )


if __name__ == "__main__":
    unittest.main()
