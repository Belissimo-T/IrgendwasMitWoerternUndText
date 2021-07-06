import hashlib
import msgpack
import os

from context_logger.context_logger import log, log_decorator

PATH = "cache"


def get_hash(obj):
    data = obj if isinstance(obj, bytes) else msgpack.dumps(obj)
    return hashlib.sha256(data).hexdigest()


def get_path(hash_: str):
    return os.path.join(PATH, hash_)


@log_decorator("Looking in the cache 👀")
def get(obj):
    path = get_path(get_hash(obj))

    if os.path.exists(path):
        with open(path, "rb") as f:
            log("found! ✅")
            return f.read()

    log("not found 😐")
    return None


@log_decorator("Saving to cache 💾")
def save(content: bytes, hash_obj):
    path = get_path(get_hash(hash_obj))

    with open(path, "wb") as f:
        f.write(content)
