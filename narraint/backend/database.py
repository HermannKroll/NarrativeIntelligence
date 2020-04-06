import json
import os
import warnings
from os import environ

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import exc
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from narraint.backend.models import Base
from narraint.config import BACKEND_CONFIG


def add_engine_pidguard(engine):
    """Add multiprocessing guards.

    Forces a connection to be reconnected if it is detected
    as having been shared to a sub-process.

    """

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        connection_record.info['pid'] = os.getpid()

    @event.listens_for(engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        pid = os.getpid()
        if connection_record.info['pid'] != pid:
            # substitute log.debug() or similar here as desired
            warnings.warn(
                "Parent process %(orig)s forked (%(newproc)s) with an open "
                "database connection, "
                "which is being discarded and recreated." %
                {"newproc": pid, "orig": connection_record.info['pid']})
            connection_record.connection = connection_proxy.connection = None
            raise exc.DisconnectionError(
                "Connection record belongs to pid %s, "
                "attempting to check out in pid %s" %
                (connection_record.info['pid'], pid)
            )


class Session:
    _instance = None

    def _load_config(self):
        with open(BACKEND_CONFIG) as f:
            config = json.load(f)
        self.config = dict(
            POSTGRES_USER=environ.get("NI_POSTGRES_USER", config["POSTGRES_USER"]),
            POSTGRES_PW=environ.get("NI_POSTGRES_PW", config["POSTGRES_PW"]),
            POSTGRES_HOST=environ.get("NI_POSTGRES_HOST", config["POSTGRES_HOST"]),
            POSTGRES_PORT=environ.get("NI_POSTGRES_PORT", config["POSTGRES_PORT"]),
            POSTGRES_DB=environ.get("NI_POSTGRES_DB", config["POSTGRES_DB"]),
        )

    def __init__(self):
        if not self._instance:
            self._load_config()
            self.engine = create_engine(self.get_conn_uri())
            add_engine_pidguard(self.engine)
            session_cls = sessionmaker(bind=self.engine) # python black magic: equip self with additional functions
            self.session = scoped_session(session_cls)  # session_cls()
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

    @classmethod
    def lock_tables(cls, *tables):
        for table in tables:
            cls.get().execute(f"LOCK TABLE {table} IN EXCLUSIVE MODE")
