import logging
from datetime import datetime

from narraint.backend.database import SessionExtended
from narraint.backend.models import DatabaseUpdate


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info(f'Setting database update date to: {datetime.now()} ...')
    session = SessionExtended.get()
    DatabaseUpdate.update_date_to_now(session=session)
    logging.info(f'Finished - Date in DB is now: {DatabaseUpdate.get_latest_update(session)}')


if __name__ == "__main__":
    main()
