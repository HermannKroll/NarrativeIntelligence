from narraint.backend.models import Extended
from narraint.config import BACKEND_CONFIG
from narrant.backend.database import Session


class SessionExtended(Session):

    @classmethod
    def get(cls, connection_config: str = BACKEND_CONFIG, declarative_base=Extended):
        if not cls._instance:
            cls._instance = Session(connection_config, declarative_base)
        return cls._instance.session

    @classmethod
    def is_postgres(cls):
        return cls._instance.is_postgres()
