import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from narraint.backend.models import Base
from narraint.config import BACKEND_CONFIG


class Session:
    _instance = None

    def __init__(self):
        if not self._instance:
            with open(BACKEND_CONFIG) as f:
                self.config = json.load(f)
            self.engine = create_engine(self.get_conn_uri())
            session_cls = sessionmaker(bind=self.engine)
            self.session = session_cls()
            Base.metadata.create_all(self.engine)
        else:
            raise ValueError("Instance already exists: Use get()")

    def get_conn_uri(self):
        return "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
            user=self.config["POSTGRES_USER"],
            password=self.config["POSTGRES_PW"],
            host=self.config["POSTGRES_HOST"],
            port=self.config["POSTGRES_PORT"],
            db=self.config["POSTGRES_DB"],
        )

    @classmethod
    def get(cls):
        if not cls._instance:
            cls._instance = Session()
        return cls._instance.session
