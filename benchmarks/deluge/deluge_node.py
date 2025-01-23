import base64
import logging
import shutil
import socket
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Self, Dict, Any

import pathvalidate
from deluge_client import DelugeRPCClient
from deluge_client.client import RemoteException
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_not_exception_type,
    after_log,
)
from tenacity.stop import stop_base
from tenacity.wait import wait_base
from torrentool.torrent import Torrent
from urllib3.util import Url

from benchmarks.core.experiments.experiments import ExperimentComponent
from benchmarks.core.network import DownloadHandle, Node
from benchmarks.core.utils import await_predicate
from benchmarks.deluge.agent.client import DelugeAgentClient

logger = logging.getLogger(__name__)

STOP_POLICY = stop_after_attempt(10)
WAIT_POLICY = wait_exponential(exp_base=2, min=4, max=16)


@dataclass(frozen=True)
class DelugeMeta:
    """:class:`DelugeMeta` represents the initial metadata required so that a :class:`DelugeNode`
    can introduce a file into the network, becoming its initial seeder."""

    name: str
    announce_url: Url


class DelugeNode(Node[Torrent, DelugeMeta], ExperimentComponent):
    def __init__(
        self,
        name: str,
        volume: Path,
        daemon_port: int,
        agent: DelugeAgentClient,
        daemon_address: str = "localhost",
        daemon_username: str = "user",
        daemon_password: str = "password",
    ) -> None:
        if not pathvalidate.is_valid_filename(name):
            raise ValueError(f'Node name must be a valid filename (bad name: "{name}")')

        self._name = name
        self.downloads_root = volume / "downloads"

        self._rpc: Optional[DelugeRPCClient] = None
        self.daemon_args = {
            "host": daemon_address,
            "port": daemon_port,
            "username": daemon_username,
            "password": daemon_password,
        }

        self.agent = agent

    @property
    def name(self) -> str:
        return self._name

    def wipe_all_torrents(self):
        torrent_ids = list(self.rpc.core.get_torrents_status({}, []).keys())
        if torrent_ids:
            errors = self.rpc.core.remove_torrents(torrent_ids, remove_data=True)
            if errors:
                raise Exception(f"There were errors removing torrents: {errors}")

        # Wipe download folder to get rid of files that got uploaded but failed
        # seeding or deletes.
        try:
            shutil.rmtree(self.downloads_root)
        except FileNotFoundError:
            # If the call to remove_torrents succeeds, this might happen. Checking
            # for existence won't protect you as the client might still delete the
            # folder after your check, so this is the only sane way to do it.
            pass

    def genseed(
        self,
        size: int,
        seed: int,
        meta: DelugeMeta,
    ) -> Torrent:
        torrent = self.agent.generate(size, seed, meta.name)
        torrent.announce_urls = [str(meta.announce_url)]

        self.rpc.core.add_torrent_file(
            filename=f"{meta.name}.torrent",
            filedump=self._b64dump(torrent),
            options=dict(),
        )

        return torrent

    def leech(self, handle: Torrent) -> DownloadHandle:
        self.rpc.core.add_torrent_file(
            filename=f"{handle.name}.torrent",
            filedump=self._b64dump(handle),
            options=dict(),
        )

        return DelugeDownloadHandle(
            node=self,
            torrent=handle,
        )

    def remove(self, handle: Torrent):
        try:
            self.rpc.core.remove_torrent(handle.info_hash, remove_data=True)
            return True
        except RemoteException as ex:
            # DelugeRPCClient creates remote exception types dynamically, so there's
            # actually no way of testing for them other than this.
            exception_type = str(ex.__class__)
            if "deluge_client.client.InvalidTorrentError" in exception_type:
                # This might happen when we retry a failed delete - maybe we got a bad response back,
                # but the node managed to delete it already.
                logger.warning(f"Torrent {handle.name} was not found on {self.name}.")
                return False
            else:
                raise ex

    def torrent_info(self, name: str) -> List[Dict[bytes, Any]]:
        return list(self.rpc.core.get_torrents_status({"name": name}, []).values())

    @property
    def rpc(self) -> DelugeRPCClient:
        if self._rpc is None:
            self.connect()
        return self._rpc

    @retry(
        stop=STOP_POLICY,
        wait=WAIT_POLICY,
        after=after_log(logger, logging.WARNING),
    )
    def connect(self) -> Self:
        return self._raw_connect()

    def _raw_connect(self):
        client = DelugeRPCClient(**self.daemon_args)
        client.connect()
        self._rpc = ResilientCallWrapper(
            client,
            wait_policy=WAIT_POLICY,
            stop_policy=STOP_POLICY,
        )
        return self

    def is_ready(self) -> bool:
        try:
            self._raw_connect()
            return True
        except (ConnectionRefusedError, socket.gaierror):
            return False

    @staticmethod
    def _b64dump(handle: Torrent) -> bytes:
        buffer = BytesIO()
        buffer.write(handle.to_string())
        return base64.b64encode(buffer.getvalue())

    def __str__(self):
        return f"DelugeNode({self.name}, {self.daemon_args['host']}:{self.daemon_args['port']})"


class ResilientCallWrapper:
    def __init__(self, node: Any, wait_policy: wait_base, stop_policy: stop_base):
        self.node = node
        self.wait_policy = wait_policy
        self.stop_policy = stop_policy

    def __call__(self, *args, **kwargs):
        @retry(
            wait=self.wait_policy,
            stop=self.stop_policy,
            retry=retry_if_not_exception_type(RemoteException),
            after=after_log(logger, logging.WARNING),
        )
        def _resilient_wrapper():
            return self.node(*args, **kwargs)

        return _resilient_wrapper()

    def __getattr__(self, item):
        return ResilientCallWrapper(
            getattr(self.node, item),
            wait_policy=self.wait_policy,
            stop_policy=self.stop_policy,
        )


class DelugeDownloadHandle(DownloadHandle):
    def __init__(self, torrent: Torrent, node: DelugeNode) -> None:
        self.node = node
        self.torrent = torrent

    def await_for_completion(self, timeout: float = 0) -> bool:
        name = self.torrent.name

        def _predicate():
            response = self.node.rpc.core.get_torrents_status({"name": name}, [])
            if len(response) > 1:
                logger.warning(
                    f"Client has multiple torrents matching name {name}. Returning the first one."
                )

            status = list(response.values())[0]
            return status[b"is_seed"]

        return await_predicate(_predicate, timeout=timeout)
