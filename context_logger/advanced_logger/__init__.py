from typing import Callable, Any
from contextvars import ContextVar


def std_log_function(message: str, prefix: str, indentation: int):
    print((f"[{prefix}] " if prefix else "") + ("  " * indentation) + message)


def log(message):
    return logger_contextvar.get().log(message)


class Logger:
    def __init__(self, prefix, log_function: Callable[[Any, Any, int], None] = std_log_function, *,
                 indentation: int = 0):
        self.log_function = log_function
        self.prefix = prefix
        self._indentation = indentation

    def log(self, message):
        self.log_function(message, self.prefix, self._indentation)

        return self

    def __enter__(self):
        if logger_contextvar.get() == self:
            self._indentation += 1
        else:
            logger_contextvar.set(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._indentation -= 1


logger_contextvar: ContextVar[Logger] = ContextVar("__advanced_logger_context_var__", default=Logger("GLOBAL"))
