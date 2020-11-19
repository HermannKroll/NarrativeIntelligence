import unittest
import os
import narraint.config


class TestCofigMod(unittest.TestCase):
    def test_config_mod(self):
        self.assertEqual(narraint.config.CONFIG_DIR,
                         os.path.join(narraint.config.GIT_ROOT_DIR, "nitests/config/jsonfiles"))


if __name__ == '__main__':
    unittest.main()
