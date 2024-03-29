import argparse
from .arguments import (  # Abstract definition of two forms of parsers
    REMOTE_CLI,
    STANDARD_CLI,
)


class RemoteUsageError(Exception):
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string


class _HelpStrAction(argparse.Action):
    def __init__(self, option_strings, dest, default="==SUPPRESS==", help=None):
        super(_HelpStrAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
        )

    def __call__(
        self, parser: argparse.ArgumentParser, namespace, values, option_string=None
    ):
        setattr(namespace, self.dest, parser.format_help())
        setattr(namespace, "_helpstr_", True)


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, client: str = "standard", *args, **kwargs):
        self.client = client
        if self.client == "standard":
            kwargs["add_help"] = True
        elif self.client == "remote":
            kwargs["add_help"] = False
        super(ArgumentParser, self).__init__(*args, **kwargs)

        if self.client == "remote":
            self.register("action", "help_str", _HelpStrAction)
            self.add_argument(
                "-h",
                "--help",
                action="help_str",
                help="Return this help message.",
                dest="returns",
            )

        self.set_defaults(**{"_helpstr_": False})

    def error(self, message):
        """error(message: string)
        Prints a usage message incorporating the message to stderr and
        exits.
        If you override this in a subclass, it should not return -- it
        should either exit or raise an exception.
        """
        if self.client == "standard":
            super(ArgumentParser, self).error(message)
        elif self.client == "remote":
            raise RemoteUsageError(f"{self.prog}: error: {message}")


def new_parser(client: str = "standard") -> ArgumentParser:
    parser = ArgumentParser(client)

    if client == "standard":
        subcommands = STANDARD_CLI
    elif client == "remote":
        subcommands = REMOTE_CLI

    _parsers = parser.add_subparsers(title="subcommands")

    for sc in subcommands:
        sc.add_to(_parsers)

    return parser
