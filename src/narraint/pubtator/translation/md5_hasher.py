import hashlib


def get_md5_hash(file):
    m = hashlib.md5()
    if file:
        with open(file) as f:
            m.update(str.encode(f.read()))
            return m.hexdigest()


def get_md5_hash_str(str_input):
    m = hashlib.md5()
    m.update(str_input.encode())
    return m.hexdigest()