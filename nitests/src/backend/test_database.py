import unittest
import pytest
import os


from narraint.config import BACKEND_CONFIG, GIT_ROOT_DIR
from narraint.backend.database import Session
from narraint.tools import proj_rel_path


class TestSession(unittest.TestCase):

    @pytest.mark.order1
    def test_sqlite_creation(self):
        session = Session.get()
        self.assertIsNotNone(session)
        self.assertEqual(BACKEND_CONFIG,
                         os.path.join(GIT_ROOT_DIR, "nitests/config/jsonfiles/backend.json"))

    def test_sqlite_ins_sel(self):
        session = Session.get()
        session.execute("INSERT INTO tagger VALUES ('foo', 'bar')")
        result = session.execute("SELECT * FROM tagger")
        for row in result:
            self.assertTrue(row['name'] == 'foo' and row['version'] == 'bar')
        self.assertTrue(os.path.isfile(proj_rel_path("nitests/tmp/sqlite.db")))


if __name__ == '__main__':
    unittest.main()
