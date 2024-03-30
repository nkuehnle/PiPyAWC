from typing import Dict, List, Optional

import yaml
from apprise.common import NotifyType

from pipyawc.awclogger import logger

from .notifier import Notifier
from .receivers import Receiver, RemoteCommand, ReceiverError


class NotificationFailure(Exception):
    pass


class Contact(yaml.YAMLObject):
    yaml_tag = "!Contact"

    def __init__(self, name: str, address: str):
        """_summary_

        Parameters
        ----------
        name : str
            _description_
        address : str
            _description_
        """
        self.name = name
        self.address = address
        # self.notify_types = notify_types

    # def cares_about(self, notice_level: NotifyType) -> bool:
    #     """_summary_

    #     Parameters
    #     ----------
    #     notice_level : NotifyType
    #         _description_

    #     Returns
    #     -------
    #     bool
    #         _description_
    #     """
    #     return notice_level in self.notify_types


class Messenger:
    """_summary_"""

    def __init__(
        self,
        receivers: Optional[List[Receiver]] = None,
        contacts: Optional[Dict[str, Contact]] = None,
        check_delay_sec: int = 30,
    ):
        """_summary_

        Parameters
        ----------
        receivers : Optional[List[Receiver]], optional
            _description_, by default None
        contacts : Optional[Dict[str, Contact]], optional
            _description_, by default None
        check_delay_sec : int, optional
            _description_, by default 30
        """
        self.receivers = receivers if receivers is not None else []
        self.contacts = {} if contacts is None else contacts
        self.check_delay_sec = int(check_delay_sec)

    def check(self) -> List[RemoteCommand]:
        """
        Abstract method to be implemented by subclasses.
        Checks for unseen/new messages and returns them as a list of RemoteCommand
        objects.

        Returns
        -------
        List[RemoteCommand]
            List of messages, which should be valid CLI arguments
        """
        messages = []
        for receiver in self.receivers:
            try:
                new_messages = receiver.check()
                messages.extend(new_messages)
            except ReceiverError:
                pass
        return messages

    def notify(
        self,
        body: str,
        title: str,
        notify_type: NotifyType = NotifyType.INFO,
        contacts: Optional[List[str]] = None,
    ):
        """_summary_

        Parameters
        ----------
        body : str
            _description_
        title : str
            _description_
        notify_type : NotifyType, optional
            _description_, by default NotifyType.INFO
        contacts : Optional[List[str]], optional
            _description_, by default None
        """
        contacts = [] if contacts is None else contacts
        _contacts = [self.contacts[c] for c in contacts]
        # _contacts = [c for c in _contacts if c.cares_about(notify_type)]

        if contacts:
            notifier = Notifier(servers=[c.address for c in _contacts])
            status = notifier.notify(body=body, title=title, notify_type=notify_type)

        if not status:
            logger.warn("Notification delivery failed")
            raise NotificationFailure(f"Notification failed, status: {status}")
        logger.info(f"Notifications delivered to {len(contacts)}")

    def register_contact(self, contact: Contact):
        self.contacts[contact.name] = contact

    def register_receiver(self, receiver: Receiver):
        self.receivers.append(receiver)


def contact_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    vals = loader.construct_mapping(node)
    kwargs = {str(k): v for k, v in vals.items()}
    return Contact(**kwargs)
