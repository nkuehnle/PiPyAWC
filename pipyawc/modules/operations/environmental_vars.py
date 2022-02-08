"""
The code for this constructory was based on  an example from user dmchk on StackOverflow:
https://stackoverflow.com/questions/52412297/how-to-replace-environment-variable-value-in-yaml-file-to-be-parsed-using-python
"""
import yaml
import os
import re

def env_var_constructor(loader: yaml.Loader, node: yaml.Node):
    """A function to construct a string with environmental variables embedded.

    Parameters
    ----------
    loader : yaml.Loader
        The pyaml loader instance
    node : yaml.Node
        The node to construct

    Raises
    ------
    KeyError
        If any non-existant environmental variables are used.
    """
    value = str(node.value) # str() here for type checkers
    env_vars = re.findall(r'\$\{([^}^{]+)\}', value)
    env_vars = {v:os.getenv(v, 'NOT FOUND') for v in env_vars}
    bad_vars = [k for k,v in env_vars.items() if v == 'NOT FOUND']

    if any(bad_vars):
        err = f"Environmental variable(s) not found: {','.join(bad_vars)}"
        raise KeyError(err)
    
    value = re.sub(r'\${', r'{', value)

    return value.format(**env_vars)
