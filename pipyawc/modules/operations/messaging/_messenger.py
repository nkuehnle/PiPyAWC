# Default module importsfrom typing import List
from dataclasses import dataclass
from abc import abstractmethod
from typing import List

# Third-party module imports
import yaml


class MessengerError(Exception):
    pass


@dataclass
class RemoteCommand:
    command: List[str]
    sender: str


class Messenger(yaml.YAMLObject):
    yaml_tag = "!Messenger"

    def __init__(self):
        super().__init__()

    @abstractmethod
    def check(self) -> List[RemoteCommand]:
        raise NotImplementedError("Implement this!")

    @abstractmethod
    def send(self, recipients: List[str], **kwargs):
        raise NotImplementedError("Implement this!")
