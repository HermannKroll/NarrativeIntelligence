from datetime import datetime

from sqlalchemy import inspect

from narraint.backend.database import Session
from narraint.backend.models import Document, Tag

s = Session.get()

# if not s.query(s.query(Document).filter_by(corpus="PMC", id=12345).exists()).scalar():
#     d = Document(corpus="PMC", id=12345, title="Test", abstract="Abstrac", date_inserted=datetime(2019, 11, 20))
#     s.add(d)
#     s.commit()
#
# doc = s.query(Document).get(("PMC", 12345))
#
# d = Document(corpus="PMC", id=12343, title="Test", abstract="Abstrac", date_inserted=datetime(2019, 11, 20))
# t1 = Tag(type="Disease", start=0, end=1, ent_id="D0284", ent_str="Cyproplaxatin", document=d, tagger_name="PMDTAgg",
#          tagger_version="1.2.5")
#
# s.add_all((t1, d))
# s.commit()

# kwargs = dict(id=12345, collection="PMC", title="Whacka")
# if not s.query(s.query(Document).filter_by(**kwargs).exists()).scalar():
#     d = Document(**kwargs, date_inserted=datetime.now())
#     d.abstract = "Checka"
#     s.add(d)
#     s.commit()
# else:
#     del kwargs["title"]
#     d = s.query(Document).get(kwargs)

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

#l = s.query(Document,Tag).join(Tag).all()

#for t in l:
#    print(t[0].id, t[1].id)

#print(set(x[0] for x in s.query(Document).filter_by(collection="PMC").values("id")))

#d = s.query(Document).get(("a",0))
d = s.query(s.query(Document).filter_by(id=0, collection="a").exists()).scalar()
print(d)
