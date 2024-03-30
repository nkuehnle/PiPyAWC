import inspect
import logging
from datetime import datetime
from pathlib import Path


class CustomLogger(logging.Logger):

    @property
    def log_directory(self) -> Path:
        log_directory = Path.home() / ".pipyawc" / "logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        return log_directory

    @property
    def log_file(self):
        mm_yyyy = datetime.now().strftime("%m-%Y")
        log_file = self.log_directory / f"{mm_yyyy}.log"
        if not log_file.exists():
            with open(log_file, "w") as _:
                pass
        return log_file

    def find_caller_info(self):
        stack = inspect.stack()
        # The first frame in the stack is this function, the second frame is the caller.
        if len(stack) > 2:
            frame = stack[2]
            module = inspect.getmodule(frame[0])
            modname = (module.__name__ if module else "__main__",)
            funcname = (frame.function,)
            return f" - {modname}.{funcname}"
        else:
            return ""

    def _log(
        self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs
    ):
        if extra is None:
            extra = {}
        extra.update({"caller": self.find_caller_info()})
        super()._log(level, msg, args, exc_info, extra, stack_info, **kwargs)


# Usage example:
logging.setLoggerClass(CustomLogger)

logger = logging.getLogger("PiPyAWC")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s%(caller)s\n%(message)s",
    datefmt="%m-%d-%y %I:%M %p",
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
