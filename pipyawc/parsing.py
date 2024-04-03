# Built-in modules
from argparse import Namespace
from functools import wraps
from typing import List, Optional, Tuple

from pipyawc.modules import Controller, NotifyType
from pipyawc.awclogger import logger


def _process_remote(
    args: Namespace,
    controller: Controller,
    output: str = "standard",
    contacts: Optional[List[str]] = None,
):
    """[summary]

    Parameters
    ----------
    args : Namespace
        A Namespace object derived from an ArgumentParser that has already
        consumed a set arguments using ArgumentParser.parse_args()
    controller : Controller
        The active controller instance on which to act.
    output : str, optional
        How to log the results, by default 'standard'
        'remote' = uses the messenger associated with the controller object.
        'standard' = uses the default print() function
    contacts : Optional[List[str]]; optional
        A list of contact names, by default None
        required if output = 'remote'

    Raises
    ------
    ValueError
        Raised when output is set to 'remote' but no recipients are passed.
    """
    _args = vars(args)

    if _args["_helpstr_"]:
        ret = (1, _args["returns"])
    else:
        func = _args["func"]
        ret = func(_args, controller)

    if ret is not None:
        if output == "standard":
            if ret[0]:
                logger.info(f"Sucess! {ret[1]}")
            else:
                logger.warning(f"Error! {ret[1]}")
        elif output == "remote":
            if ret[0]:
                title = "Command Processed (Success)"
                notify_type = NotifyType.INFO
            else:
                title = "Command Processed (Error)"
                notify_type = NotifyType.WARNING

            if contacts is not None:
                controller.notify(
                    contacts=contacts,
                    body=ret[1],
                    title=title,
                    notify_type=notify_type,
                )
            else:
                e = "A recipient list must be passed when command parsing "
                raise ValueError(e + "output is set to notify.")


@wraps(_process_remote)
def process_remote(
    args: Namespace,
    controller: Controller,
    output: str = "standard",
    contacts: Optional[List[str]] = None,
):
    if contacts:
        try:
            _process_remote(args, controller, output, contacts)
        except Exception as e:
            if output == "remote":
                controller.notify(
                    contacts=contacts,
                    body=f"Something went wrong: {e}",
                    title="Error!",
                    notify_type=NotifyType.WARNING,
                )
                logger.error(f"Error! {e}")
            else:
                logger.error(f"Error! {e}")


def process_stardard(args: Namespace) -> Tuple[Controller, int]:
    """[summary]

    Parameters
    ----------
    args : Namespace
        [description]

    Returns
    -------
    Tuple[Controller, float]
        [description]
    """
    _args = vars(args)
    func = _args["func"]

    return func(_args)
