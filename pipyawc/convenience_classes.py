from typing import List, Callable
from argparse import ArgumentParser, _SubParsersAction
from abc import abstractmethod

class ArgumentWrapper:
    def __init__(self, kwargs):
        self.kwargs = kwargs
    
    @abstractmethod
    def add_to(self, parser: ArgumentParser) -> None:
        raise NotImplementedError("Implement this method.")


class Argument(ArgumentWrapper):
    def __init__(self, flags: List[str], kwargs: dict):
        self.flags = flags
        self.kwargs = kwargs
    
    def add_to(self, parser: ArgumentParser) -> None:
        parser.add_argument(*self.flags, **self.kwargs)


class ExclusiveArgGroup(ArgumentWrapper):
    def __init__(self, args: List[Argument]):
        self.args = args

    def add_to(self, parser: ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group()

        for arg in self.args:
            group.add_argument(*arg.flags, **arg.kwargs)


class Subcommand(ArgumentWrapper):
    def __init__(self, func: Callable, name, argsets: List[ArgumentWrapper],
                 kwargs: dict):
        self.func = func
        self.name = name
        self.argsets = argsets
        self.kwargs = kwargs

    def add_to(self, subparsers: _SubParsersAction) -> None:
        subparser = subparsers.add_parser(self.name, **self.kwargs)

        for argset in self.argsets:
            argset.add_to(subparser)

        subparser.set_defaults(func=self.func)
        
        return subparser