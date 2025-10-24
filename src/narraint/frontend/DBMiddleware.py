import logging

from sqlalchemy.exc import PendingRollbackError

from narraint.backend.database import SessionExtended

# This class takes requests before they get to the view component
# If some request runs into a Pending Rollback Error, the session will be rolled back and
# the request is retried with a fresh connection
class SQLAlchemyCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except PendingRollbackError:
            logging.info('Recieving rollback error: Rollback transaction...')
            session = SessionExtended.get()
            session.rollback()
            logging.info("Retrying request after rollback transaction...")
            return self.get_response(request)

