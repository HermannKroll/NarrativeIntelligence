import logging

from narraint.backend.database import SessionExtended


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info('Trying to create database schema / add missing tables')
    session = SessionExtended.get()
    logging.info('Finished')

if __name__ == "__main__":
    main()
