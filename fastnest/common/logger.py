import logging
import sys
from datetime import datetime


class _Formatter(logging.Formatter):
    COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color and sys.stdout.isatty()

    def format(self, record):
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level = record.levelname.ljust(7)
        ctx = record.name

        if self.use_color:
            c = self.COLORS.get(record.levelname, "")
            return (f"{self.DIM}{ts}{self.RESET} "
                    f"{c}{self.BOLD}{level}{self.RESET} "
                    f"{self.DIM}[{ctx}]{self.RESET} "
                    f"{record.getMessage()}")
        return f"{ts} {level} [{ctx}] {record.getMessage()}"


class Logger:
    """
    Built-in context-aware logger.

    Usage:
        logger = Logger("UsersService")
        logger.info("user created")
        logger.error("something failed", exc_info=True)
    """
    _root_configured = False

    def __init__(self, context: str = "FastNest"):
        self._logger = logging.getLogger(context)
        if not Logger._root_configured:
            self._configure_root()

    @classmethod
    def _configure_root(cls):
        root = logging.getLogger()
        if root.handlers:
            cls._root_configured = True
            return
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_Formatter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        cls._root_configured = True

    def set_level(self, level: str):
        self._logger.setLevel(level.upper())

    def debug(self, msg, *a, **kw):   self._logger.debug(msg, *a, **kw)
    def info(self, msg, *a, **kw):    self._logger.info(msg, *a, **kw)
    def warn(self, msg, *a, **kw):    self._logger.warning(msg, *a, **kw)
    def warning(self, msg, *a, **kw): self._logger.warning(msg, *a, **kw)
    def error(self, msg, *a, **kw):   self._logger.error(msg, *a, **kw)
    def critical(self, msg, *a, **kw): self._logger.critical(msg, *a, **kw)