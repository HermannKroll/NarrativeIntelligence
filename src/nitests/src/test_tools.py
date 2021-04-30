import unittest
import narrant.tools as tl
from nitests.util import get_test_resource_filepath


class TestTools(unittest.TestCase):
    def test_read_if_path(self):
        self.assertEqual("foobar", tl.read_if_path("foobar"))
        self.assertTrue("My Hovercraft is full of eals",
                        tl.read_if_path(get_test_resource_filepath("dummy.txt")))


if __name__ == '__main__':
    unittest.main()
