import yaml

from .email_receiver import EmailReceiver


def email_receiver_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    vals = loader.construct_mapping(node)
    kwargs = {str(k): v for k, v in vals.items()}
    return EmailReceiver(**kwargs)
