# Default module imports
import shlex
import socket
import ssl
from typing import Dict, List

from imap_tools import AND, ImapToolsError, MailBox

from pipyawc.awclogger import logger

from .accessories import ReceiverError, RemoteCommand
from .receiver import Receiver


class ImapError(ImapToolsError, socket.gaierror, ConnectionResetError):
    pass


class EmailReceiver(Receiver):
    """
    Class representing an email receiver for retrieving messages.

    Attributes
    ----------
    yaml_tag : str
        YAML tag for serialization. Always `!EmailMessenger`

    Parameters
    ----------
    email_address : str
        The main email address for the Messenger instance to access
    password : str
        Password string. Recommended to use OAuth pass/a dedicated free
        account, i.e. GMail
    imap_domain : str
        URL for IMAP server
    inbox : str, optional
        Inbox to check for new messages, by default `INBOX`
    imap_port : int, optional
        IMAP server port number, by default `993`
    contacts : Dict[str, str], optional
        A dictionary of short-form contact names and corresponding email
        addresses, by default `{}`
    """

    yaml_tag = "!EmailMessenger"

    def __init__(
        self,
        email_address: str,
        password: str,
        imap_domain: str,
        inbox: str = "INBOX",
        imap_port: int = 993,
        contacts: Dict[str, str] = {},
    ):
        """
        Initializes an EmailReceiver object.

        Parameters
        ----------
        email_address : str
            The main email address for the Messenger instance to access
        password : str
            Password string. Recommended to use OAuth pass/a dedicated free
            account, i.e. GMail
        imap_domain : str
            URL for IMAP server
        inbox : str, optional
            Inbox to check for new messages, by default `INBOX`
        imap_port : int, optional
            IMAP server port number, by default `993`
        contacts : Dict[str, str], optional
            A dictionary of short-form contact names and corresponding email
            addresses, by default `{}`
        """
        super().__init__()
        self.email_address = email_address
        self.password = password
        self.imap_domain = imap_domain
        self.inbox = inbox
        self.imap_port = imap_port
        self.contacts = contacts
        self._proced_error = False

    def segment_text(self, body: str) -> List[str]:
        """
        Segments text into chunks suitable for sending as messages.

        Parameters
        ----------
        body : str
            The text to segment.

        Returns
        -------
        List[str]
            List of segmented text.
        """
        segments = []
        while len(body) > 160:
            char = 159
            found_whitespace = False

            while not found_whitespace:
                if body[char].isspace() or body[char] == "":
                    segments.append(body[:char])
                    char_1 = char + 1
                    body = body[char_1:]
                    found_whitespace = True
                else:
                    char -= 1

        if len(body) > 0:
            segments.append(body)

        return segments

    def _check(self) -> List[RemoteCommand]:
        """
        Collects unseen/new messages.

        Returns
        -------
        List[RemoteCommand]:
            List of remote commands.
        """
        # Create connection and return new messages
        mb_kwargs = {
            "host": self.imap_domain,
            "port": self.imap_port,
            "ssl_context": ssl.SSLContext(),
        }
        login_kwargs = {
            "username": self.email_address,
            "password": self.password,
            "initial_folder": self.inbox,
        }
        with MailBox(**mb_kwargs).login(**login_kwargs) as mailbox:
            commands = []

            # Collect only unseen mail
            for msg in mailbox.fetch(AND(seen=False)):
                if msg.from_ in self.contacts.values():
                    new_cmd = RemoteCommand(shlex.split(msg.text), msg.from_)
                    commands.append(new_cmd)

        return commands

    def check(self) -> List[RemoteCommand]:
        """
        Checks for unseen/new messages and returns them as a list of RemoteCommand objects.

        Returns
        -------
        List[RemoteCommand]
            List of messages, which should be valid CLI arguments

        Raises
        ------
        ReceiverError
            If there's an IMAP error.
        """
        try:
            commands = self._check()
            if any(commands):
                logger.info(f"Received {len(commands)} new email commands.")
            self._proced_error = False
            return commands
        except ImapError as e:
            if not self._proced_error:
                logger.warn("Failed to retrieve email.", exc_info=e)
            self._proced_error = True
            raise ReceiverError(f"IMAP Error ({type(e)})")
