# Default module imports
from smtplib import SMTP_SSL, SMTPException
from email.message import EmailMessage
from typing import List, Dict
import shlex
import ssl
import socket

# Third-party module imports
try:
    from imap_tools import MailBox, AND, ImapToolsError
except ModuleNotFoundError as e:
    print("WARNING: please run pip install imap-tools")
    raise e
# Custom modules
from ._messenger import Messenger, RemoteCommand, MessengerError


class EmailMessenger(Messenger):
    yaml_tag = "!EmailMessenger"

    def __init__(
        self,
        email_address: str,
        password: str,
        smtp_domain: str,
        imap_domain: str,
        inbox: str = "INBOX",
        smtp_port: int = 465,
        imap_port: int = 993,
        contacts: Dict[str, str] = {},
    ):
        """[summary]

        Parameters
        ----------
        email_address : str
            The main email address for the Messenger instance to access
        password : str
            Password string. Recommended to use OAuth pass/a dedicated free
            account, i.e. GMail
        smtp_domain : str
            URL for SMTP server
        imap_domain : str
            URL for IMAP server
        inbox : str, optional
            Inbox to check for new messages, by default 'INBOX'
        smtp_port : int, optional
            SMTP server port number, by default 465
        imap_port : int, optional
            IMAP server port number, by default 993
        contacts : Dict[str, str], optional
            A dictionary of short-form contact names and corresponding email
            addresses, by default {}
        """
        super().__init__()
        self.email_address = email_address
        self.password = password
        self.smtp_domain = smtp_domain
        self.imap_domain = imap_domain
        self.inbox = inbox
        self.smtp_port = smtp_port
        self.imap_port = imap_port
        self.contacts = contacts

    def segment_text(self, body: str) -> List[str]:
        segments = []
        while len(body) > 160:
            char = 159
            found_whitespace = False

            while not (found_whitespace):
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

    def send(self, recipients: List[str], subject: str, body: str):
        segments = self.segment_text(body)
        for segment in segments:
            try:
                self._send(recipients=recipients, subject=subject, body=segment)
            except SMTPException:
                raise MessengerError()

    def _send(self, recipients: List[str], subject: str, body: str):
        """A method to send an email via SMTP to one or more recipients.

        Parameters
        ----------
        recipients : List[str]
            A list of one or more full email addresses (i.e. user@domain) to
            send to. If a single address is passed, it should still be a list.
        subject : str
            The subject of the email to send.
        body : str
            The body of the message to send.
        """
        # Create a new message
        _recipients = []
        for r in recipients:
            try:
                _recipients.append(self.contacts[r])
            except KeyError:
                if "@" in r:
                    _recipients.append(r)

        if any(_recipients):
            msg = EmailMessage()
            msg["To"] = ", ".join(_recipients)
            msg["From"] = self.email_address
            msg["Subject"] = subject
            msg.set_content(body)

            with SMTP_SSL(self.smtp_domain, self.smtp_port) as mailer:
                mailer.login(self.email_address, self.password)
                mailer.send_message(msg)

    def _check(self) -> List[RemoteCommand]:
        """A method to collect all of the unseen/new messages.

        Returns
        -------
        List[RemoteCommand]:
            A list commands.
        """
        # Create connection and return new meessages
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
        """A method to collect all of the unseen/new messages.
        Returns
        -------
        List[RemoteCommand]:
            A list commands.
        """
        try:
            commands = self._check()
            return commands
        except (ImapToolsError, socket.gaierror, ConnectionResetError) as _:
            raise MessengerError()
