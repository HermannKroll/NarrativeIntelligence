from narraint.pubtator.regex import DOCUMENT_ID


class DocumentError(Exception):
    pass


def get_document_id(fn):
    with open(fn) as f:
        line = f.readline()
    try:
        match = DOCUMENT_ID.match(line)
        return int(match.group(1))
    except AttributeError:
        raise DocumentError(f"No ID found for {fn}")
