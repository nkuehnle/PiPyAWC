from abc import abstractmethod
from typing import List

import yaml

from .accessories import RemoteCommand


class Receiver(yaml.YAMLObject):
    """
    Base class for receiving messages.

    Attributes
    ----------
    yaml_tag : str
        YAML tag for serialization. Always !Receiver
    """

    yaml_tag = "!Receiver"

    def __init__(self):
        """
        Initializes a Receiver object.
        """
        super().__init__()

    @abstractmethod
    def check(self) -> List[RemoteCommand]:
        """
        Abstract method to be implemented by subclasses.
        Checks for unseen/new messages and returns them as a list of RemoteCommand
        objects.

        Returns
        -------
        List[RemoteCommand]
            List of messages, which should be valid CLI arguments

        Raises
        ------
        NotImplementedError
            Raised if subclasses of this do not implement this method.
        """
        raise NotImplementedError("Receivers must implement a check() method!")
