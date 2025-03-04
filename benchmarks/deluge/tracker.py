import socket

import requests
from requests.exceptions import ConnectionError
from urllib3.util import Url

from benchmarks.core.experiments.experiments import ExperimentComponent


class Tracker(ExperimentComponent):
    def __init__(self, announce_url: Url):
        self.announce_url = announce_url

    def is_ready(self) -> bool:
        try:
            requests.get(str(self.announce_url))
            return True
        except (ConnectionError, socket.gaierror):
            return False

    def __str__(self) -> str:
        return f"Tracker({self.announce_url})"
