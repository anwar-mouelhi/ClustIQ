import logging
import sys

from colorama import Fore, Style, just_fix_windows_console
from tqdm import tqdm

just_fix_windows_console()

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

_RESET = Style.RESET_ALL
_DIM = Style.DIM

_LEVELS: dict[int, tuple[str, str]] = {
    logging.DEBUG: (Fore.LIGHTBLACK_EX, "·"),
    logging.INFO: (Fore.CYAN, "●"),
    logging.WARNING: (Fore.YELLOW, "▲"),
    logging.ERROR: (Fore.RED, "✖"),
    logging.CRITICAL: (Style.BRIGHT + Fore.RED, "✖"),
}

_formatter = logging.Formatter(datefmt="%H:%M:%S")


def _stage(logger_name: str) -> str:
    return logger_name.rsplit(".", 1)[-1]


class _ConsoleHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            color, marker = _LEVELS.get(record.levelno, (Fore.WHITE, "●"))
            timestamp = _formatter.formatTime(record, "%H:%M:%S")
            line = (
                f"{_DIM}{timestamp}{_RESET} "
                f"{color}{marker}{_RESET} "
                f"{_DIM}{_stage(record.name):<11}{_RESET} "
                f"{record.getMessage()}"
            )
            if record.exc_info:
                line += "\n" + _formatter.formatException(record.exc_info)
            tqdm.write(line, file=sys.stdout)
        except Exception:
            self.handleError(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_ConsoleHandler())
        logger.setLevel(level)
        logger.propagate = False
    return logger
