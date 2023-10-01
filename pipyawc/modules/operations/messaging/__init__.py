from ._messenger import Messenger, RemoteCommand, MessengerError
from .email_messenger import EmailMessenger
import yaml

def messenger_constructor(loader: yaml.Loader, node: yaml.Node):
    vals = loader.construct_mapping(node)
    return Messenger(**vals)

def email_messenger_constructor(loader: yaml.Loader, node: yaml.Node):
    vals = loader.construct_mapping(node)
    return EmailMessenger(**vals)