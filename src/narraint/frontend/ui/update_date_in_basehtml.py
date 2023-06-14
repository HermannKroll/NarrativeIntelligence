import argparse
import logging
import re
from datetime import datetime


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file")
    args = parser.parse_args()

    logging.info(f'Replacing date in file: {args.input}')
    with open(args.input, 'rt') as f:
        content = f.read()

    date = datetime.now()
    content = re.sub(r'Last updated \d\d.\d\d.\d\d\d\d', f"Last updated {date.day}.{date.month}.{date.year}", content)

    with open(args.input, 'wt') as f:
        f.write(content)
    logging.info('Finished')


if __name__ == "__main__":
    main()
