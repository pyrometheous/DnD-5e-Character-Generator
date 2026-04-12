import tempfile
import unittest
from pathlib import Path

from scripts.validate_config_meta import validate_config_dir


class ConfigMetaValidationTests(unittest.TestCase):
    def test_repo_config_directory_passes_validation(self):
        config_dir = Path(__file__).resolve().parent.parent / 'config'
        errors, inspected = validate_config_dir(config_dir)

        self.assertGreater(inspected, 0)
        self.assertEqual(errors, [])

    def test_invalid_meta_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            (config_dir / 'broken.json').write_text(
                '{"_meta": {"version": "1.0"}, "value": 1}',
                encoding='utf-8',
            )

            errors, inspected = validate_config_dir(config_dir)

        self.assertEqual(inspected, 1)
        self.assertTrue(any("missing required key 'owner'" in error for error in errors))


if __name__ == '__main__':
    unittest.main()