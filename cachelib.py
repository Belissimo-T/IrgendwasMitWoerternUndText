import hashlib
import msgpack
import os

PATH = "cache"


def get_hash(obj):
    data = obj if isinstance(obj, bytes) else msgpack.dumps(obj)
    return hashlib.sha256(data).hexdigest()


def get_path(hash_: str):
    return os.path.join(PATH, hash_)


def get(obj):
    path = get_path(get_hash(obj))

    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()

    return None


def save(content: bytes, hash_obj):
    path = get_path(get_hash(hash_obj))

    with open(path, "wb") as f:
        f.write(content)
