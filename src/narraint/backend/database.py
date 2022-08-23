from sqlalchemy.orm.scoping import ScopedSession

from narraint.backend.models import Extended
from narraint.config import BACKEND_CONFIG
from kgextractiontoolbox.backend.database import Session


class SessionExtended(Session):
    is_sqlite = False
    is_postgres = False

    @classmethod
    def get(cls, connection_config: str = BACKEND_CONFIG, declarative_base=Extended) -> ScopedSession:
        if not cls._instance:
            cls._instance = Session.get(connection_config, declarative_base)
            SessionExtended.is_postgres = cls._instance.is_postgres
            SessionExtended.is_sqlite = cls._instance.is_sqlite
        return cls._instance
