# Default module importsfrom typing import List
from dataclasses import dataclass
from abc import abstractmethod
from typing import List
# Third-party module imports
import yaml

@dataclass
class RemoteCommand:
    command: List[str]
    sender: str

class Messenger(yaml.YAMLObject):
    yaml_tag = u'!Messenger'
    def __init__(self, yaml_loader=yaml.SafeLoader):
        super().__init__()

    @abstractmethod
    def check():
        raise NotImplementedError("Implement this!")

    @abstractmethod
    def send():
        raise NotImplementedError("Implement this!")