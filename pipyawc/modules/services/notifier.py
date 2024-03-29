import tomllib
from pathlib import Path
from typing import List, Optional

from apprise import Apprise, AppriseAsset

pyproject = Path(__file__).parents[3] / "pyproject.toml"

with open(pyproject, "rb") as f:
    project_info = tomllib.load(f)["project"]


pipyawc_asset = AppriseAsset(
    app_id=f"PiPyAwc v{project_info['version']}",
    app_desc=project_info["description"],
    app_url=project_info["urls"]["Homepage"],
)


class Notifier(Apprise):
    """
    _summary_

    Parameters
    ----------
    servers : Optional[List[str]], optional
        _description_, by default None
    """

    def __init__(self, servers: Optional[List[str]] = None):
        """
        _summary_

        Parameters
        ----------
        servers : Optional[List[str]], optional
            _description_, by default None
        """
        super().__init__(servers=servers, asset=pipyawc_asset, debug=True)
