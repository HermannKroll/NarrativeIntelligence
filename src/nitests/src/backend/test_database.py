import unittest
import pytest
import os


import narrant.config as cnf
from narraint.backend.database import SessionExtended
from narrant.backend.models import Tag, Tagger
from narrant.tools import proj_rel_path
from nitests.util import tmp_rel_path


class TestSession(unittest.TestCase):

    def test_sqlite_ins_sel(self):
        session = SessionExtended.get()
        session.execute("INSERT INTO tagger VALUES ('foo', 'bar')")
        session.query
        result = session.query(Tagger)
        for row in result:
            self.assertTrue(row.name == 'foo' and row.version == 'bar')
        self.assertTrue(os.path.isfile(tmp_rel_path("sqlite.db")))


if __name__ == '__main__':
    unittest.main()
