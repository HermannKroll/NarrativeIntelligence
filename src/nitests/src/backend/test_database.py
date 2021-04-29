import unittest
import pytest
import os


import narraint.config as cnf
from narraint.backend.database import Session
from narraint.tools import proj_rel_path
from nitests.util import tmp_rel_path


class TestSession(unittest.TestCase):

    @pytest.mark.order1
    def test_sqlite_creation(self):
        session = Session.get()
        self.assertIsNotNone(session)
        self.assertEqual(cnf.BACKEND_CONFIG,
                         os.path.join(cnf.GIT_ROOT_DIR, "src/nitests/config/jsonfiles/backend.json"))

    def test_sqlite_ins_sel(self):
        session = Session.get()
        session.execute("INSERT INTO tagger VALUES ('foo', 'bar')")
        result = session.execute("SELECT * FROM tagger")
        for row in result:
            self.assertTrue(row['name'] == 'foo' and row['version'] == 'bar')
        self.assertTrue(os.path.isfile(tmp_rel_path("sqlite.db")))


if __name__ == '__main__':
    unittest.main()
