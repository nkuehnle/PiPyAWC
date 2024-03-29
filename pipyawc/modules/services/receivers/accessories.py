from dataclasses import dataclass
from typing import List


class ReceiverError(Exception):
    pass


@dataclass
class RemoteCommand:
    command: List[str]
    sender: str
