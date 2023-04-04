from sqlalchemy.orm.scoping import ScopedSession

from narraint.backend.models import Extended
from narraint.config import BACKEND_CONFIG
from kgextractiontoolbox.backend.database import Session


class SessionExtended(Session):
    is_sqlite = False
    is_postgres = False
    _instance_extended = None

    @classmethod
    def get(cls, connection_config: str = BACKEND_CONFIG, declarative_base=Extended,
            force_create=False) -> ScopedSession:
        if not SessionExtended._instance_extended:
            SessionExtended._instance_extended = Session.get(connection_config, declarative_base, force_create=True)
            SessionExtended.is_postgres = cls._instance.is_postgres
            SessionExtended.is_sqlite = cls._instance.is_sqlite
        return SessionExtended._instance_extended
