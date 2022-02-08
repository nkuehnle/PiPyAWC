#
from argparse import Namespace
import logging
from typing import List, Optional, Tuple
from functools import wraps
#
from .modules import Controller

def _process_remote(args: Namespace, controller: Controller,
                    output: str = 'print', recipients: 
                    Optional[List[str]] = None):
    """[summary]

    Parameters
    ----------
    args : Namespace
        A Namespace object derived from an ArgumentParser that has already
        consumed a set arguments using ArgumentParser.parse_args()
    controller : Controller
        The active controller instance on which to act.
    output : str, optional
        How to log the results, by default 'print'
        'email' = uses the messenger associated with the controller object.
        'print' = uses the default print() function
    recipients : Optional[List[str]]; optional
        A list of email addresses, by default None
        required if output = 'email'

    Raises
    ------
    ValueError
        Raised when output is set to 'email' but no recipients are passed.
    """
    args = vars(args)

    if args['_helpstr_']:
        ret = (1, args['returns'])
    else:
        func = args['func']
        ret = func(args, controller)

    if ret != None:
        if output == 'print':
            if ret[0]:
                print(f'Sucess! {ret[1]}')
            else:
                print(f'Error! {ret[1]}')
        elif output == 'email':
            if ret[0]:
                sub = 'Success!'
            else:
                sub = 'Error!'
                
            if recipients != None:
                controller.notify(recipients=recipients,
                                  body = ret[1],
                                  subject = sub)
            else:
                e = 'A recipient list must be passed when command parsing '
                raise ValueError(e + 'output is set to email.')

@wraps(_process_remote)
def process_remote(args: Namespace, controller: Controller,
                   output: str = 'print', recipients:
                   Optional[List[str]] = None):
    try:
        _process_remote(args, controller, output, recipients)
    except Exception as e:
        if output == 'print':
            print(f'Error! {e}')
        elif output == 'email':
            body = f'Something went wrong: {e}'
            subject = 'Error!'
            controller.notify(recipients, body, subject)        

def process_stardard(args: Namespace) -> Tuple[Controller, float]:
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
    args = vars(args)
    func = args['func']

    return func(args)