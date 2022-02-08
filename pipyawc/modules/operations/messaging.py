# Default module imports
from smtplib import SMTP_SSL, SMTPException
from email.message import EmailMessage
from tracemalloc import start
from typing import List, Dict
# Third-party module imports
try:
    from imap_tools import MailBox, AND, MailMessage
except ModuleNotFoundError as e:
    print(f"WARNING: please run pip install imap-tools")
    raise e


class Messenger:
    def __init__(self, email_address: str, password: str, smtp_domain: str,
                 imap_domain: str, smtp_port: int = 465, imap_port: int = 993,
                 contacts: Dict[str, str] = {}):
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
        smtp_port : int, optional
            SMTP server port number, by default 465
        imap_port : int, optional
            IMAP server port number, by default 993
        contacts : Dict[str, str], optional
            A dictionary of short-form contact names and corresponding email
            addresses, by default {}
        """
        self.email_address = email_address
        self.password = password
        self.smtp_domain = smtp_domain
        self.imap_domain = imap_domain
        self.smtp_port = smtp_port
        self.imap_port = imap_port
        self.contacts = contacts

    def send(self, recipients: List[str], subject: str, body: str) -> bool:
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
                if '@' in r:
                    _recipients.append(r)

        if any(_recipients):
            msg = EmailMessage()
            msg['To'] = ', '.join(_recipients)
            msg['From'] = self.email_address
            msg['Subject'] = subject
            msg.set_content(body)

            with SMTP_SSL(self.smtp_domain, self.smtp_port) as mailer:
                mailer.login(self.email_address, self.password)
                mailer.send_message(msg)

    def check(self, box: str = 'INBOX') -> List[MailMessage]:
        """A method to collect all of the unseen/new messages.

        Parameters
        ----------
        box : str, optional
            The inbox to search in, by default 'INBOX'

        Returns
        -------
        List[MailMessage]
            A list of new messages.
        """
        # Create connection and return new meessages
        mb_kwargs = {
            'host':self.imap_domain,
            'port':self.imap_port,
            'starttls':True
            }
        login_kwargs = {
            'username': self.email_address,
            'password': self.password,
            'initial_folder': box
            }
        with MailBox(**mb_kwargs).login(**login_kwargs) as mailbox:
            messages = []

            # Collect only unseen mail
            for msg in mailbox.fetch(AND(seen=False)):
                if msg.from_ in self.contacts.values():
                    messages.append(msg)

        return messages