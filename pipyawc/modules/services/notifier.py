from typing import List, Optional

from apprise import Apprise, AppriseAsset


pipyawc_asset = AppriseAsset(
    app_id="PiPyAwc v.0.9.0",
    app_desc="PiPy Automatic-Water Controller: A dynamically-configurable & automated aquarium water level controller for the Raspberry Pi using Python. Intended to run using mechanical voltage relays (i.e. Waveshare Relay Hat) and optical contact liquid sensors (i.e. from DFRobot/CQRObot)",
    app_url="https://github.com/nkuehnle/PiPyAWC",
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
