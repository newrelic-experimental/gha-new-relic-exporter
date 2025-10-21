import unittest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, "../src")
from src.custom_parser import find_log_file, find_system_log_file


class TestFindLogFile(unittest.TestCase):
    """Test the find_log_file function with various directory structures."""

    def setUp(self):
        """Create a temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_find_log_file_in_job_subdirectory(self):
        """Test finding a log file in the expected job subdirectory."""
        # Create directory structure: logs/Job Name/1_Step Name.txt
        job_dir = os.path.join(self.test_dir, "Job Name")
        os.makedirs(job_dir)
        log_file = os.path.join(job_dir, "1_Step Name.txt")
        with open(log_file, "w") as f:
            f.write("test log content")

        result = find_log_file(self.test_dir, "Job Name", 1, "Step Name")
        self.assertEqual(result, log_file)
        self.assertTrue(os.path.exists(result))

    def test_find_log_file_at_root_level(self):
        """Test finding a log file at the root level (fallback case)."""
        # Create directory structure: logs/1_Step Name.txt (no job subdirectory)
        log_file = os.path.join(self.test_dir, "1_Step Name.txt")
        with open(log_file, "w") as f:
            f.write("test log content")

        result = find_log_file(self.test_dir, "Job Name", 1, "Step Name")
        self.assertEqual(result, log_file)
        self.assertTrue(os.path.exists(result))

    def test_find_log_file_with_special_characters(self):
        """Test finding a log file when job name contains special characters (angle brackets)."""
        # This is the exact case from issue #46
        job_name = "Clone PROD > DEV branch"
        job_dir = os.path.join(self.test_dir, job_name)
        os.makedirs(job_dir)
        log_file = os.path.join(job_dir, "1_Set up job.txt")
        with open(log_file, "w") as f:
            f.write("test log content")

        result = find_log_file(self.test_dir, job_name, 1, "Set up job")
        self.assertEqual(result, log_file)
        self.assertTrue(os.path.exists(result))

    def test_find_log_file_not_found(self):
        """Test behavior when log file is not found."""
        # Create a job directory but no log file
        job_dir = os.path.join(self.test_dir, "Job Name")
        os.makedirs(job_dir)

        result = find_log_file(self.test_dir, "Job Name", 1, "Step Name")
        # Should return the primary path even if file doesn't exist
        expected = os.path.join(job_dir, "1_Step Name.txt")
        self.assertEqual(result, expected)
        self.assertFalse(os.path.exists(result))

    def test_find_log_file_recursive_search(self):
        """Test recursive search when file is in unexpected location."""
        # Create a nested directory structure with the file
        nested_dir = os.path.join(self.test_dir, "Job Name", "nested", "deep")
        os.makedirs(nested_dir)
        log_file = os.path.join(nested_dir, "1_Step Name.txt")
        with open(log_file, "w") as f:
            f.write("test log content")

        result = find_log_file(self.test_dir, "Job Name", 1, "Step Name")
        self.assertEqual(result, log_file)
        self.assertTrue(os.path.exists(result))

    def test_find_log_file_prefers_primary_location(self):
        """Test that primary location is preferred over fallback."""
        job_dir = os.path.join(self.test_dir, "Job Name")
        os.makedirs(job_dir)

        # Create log files in both locations
        primary_log = os.path.join(job_dir, "1_Step Name.txt")
        fallback_log = os.path.join(self.test_dir, "1_Step Name.txt")
        with open(primary_log, "w") as f:
            f.write("primary content")
        with open(fallback_log, "w") as f:
            f.write("fallback content")

        result = find_log_file(self.test_dir, "Job Name", 1, "Step Name")
        self.assertEqual(result, primary_log)

    def test_find_system_log_file_in_job_subdirectory(self):
        """Test finding system.txt in job subdirectory."""
        job_dir = os.path.join(self.test_dir, "Job Name")
        os.makedirs(job_dir)
        system_log = os.path.join(job_dir, "system.txt")
        with open(system_log, "w") as f:
            f.write("system log content")

        result = find_system_log_file(self.test_dir, "Job Name")
        self.assertEqual(result, system_log)
        self.assertTrue(os.path.exists(result))

    def test_find_system_log_file_at_root_level(self):
        """Test finding system.txt at root level."""
        system_log = os.path.join(self.test_dir, "system.txt")
        with open(system_log, "w") as f:
            f.write("system log content")

        result = find_system_log_file(self.test_dir, "Job Name")
        self.assertEqual(result, system_log)
        self.assertTrue(os.path.exists(result))

    def test_find_system_log_file_not_found(self):
        """Test behavior when system.txt is not found."""
        result = find_system_log_file(self.test_dir, "Job Name")
        self.assertIsNone(result)

    def test_find_system_log_file_with_special_characters(self):
        """Test finding system.txt when job name contains special characters."""
        job_name = "Clone PROD > DEV branch"
        job_dir = os.path.join(self.test_dir, job_name)
        os.makedirs(job_dir)
        system_log = os.path.join(job_dir, "system.txt")
        with open(system_log, "w") as f:
            f.write("system log content")

        result = find_system_log_file(self.test_dir, job_name)
        self.assertEqual(result, system_log)
        self.assertTrue(os.path.exists(result))


if __name__ == "__main__":
    unittest.main()
