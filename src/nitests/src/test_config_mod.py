import unittest
import os
import narraint.config


class TestConfigMod(unittest.TestCase):
    def test_config_mod(self):
        self.assertEqual(narraint.config.BACKEND_CONFIG,
                         os.path.join(narraint.config.GIT_ROOT_DIR, "src/nitests/config/jsonfiles/backend.json"))


if __name__ == '__main__':
    unittest.main()