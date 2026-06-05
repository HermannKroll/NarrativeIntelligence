import argparse
import logging
from datetime import timedelta

from narraint.backend.database import SessionExtended
from narraint.backend.models import DatabaseUpdate

if "__main__" == __name__:
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    argparse = argparse.ArgumentParser()
    argparse.add_argument("output", type=str, help="File where the update date should be stored")
    argparse.add_argument("--offset", type=int, required=False, help="The number of days substracted from the DB update date")
    args = argparse.parse_args()

    logging.info("Retrieving database update date...")
    session = SessionExtended.get()
    date = DatabaseUpdate.get_latest_update(session)

    if args.offset:
        date = date - timedelta(days=args.offset)

    logging.info(f"Writing DB update date: {date} to {args.output}")
    with open(args.output, "wt") as f:
        f.write(str(date))

    logging.info("Finished.")
