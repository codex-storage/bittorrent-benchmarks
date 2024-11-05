import base64
import logging
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from time import time
from typing import List, Union, Optional, Self, Dict, Any

import pathvalidate
from deluge_client import DelugeRPCClient
from torrentool.torrent import Torrent
from urllib3.util import Url

from benchmarks.core.network import SharedFSNode, DownloadHandle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DelugeMeta:
    """:class:`DelugeMeta` represents the initial metadata required so that a :class:`DelugeNode`
    can introduce a file into the network, becoming its initial seeder."""
    name: str
    announce_url: Url


class DelugeNode(SharedFSNode[Torrent, DelugeMeta]):

    def __init__(
            self,
            name: str,
            volume: Path,
            daemon_port: int,
            daemon_address: str = 'localhost',
            daemon_username: str = 'user',
            daemon_password: str = 'password',
    ) -> None:
        if not pathvalidate.is_valid_filename(name):
            raise ValueError(f'Node name must be a valid filename (bad name: "{name}")')

        self.name = name
        self.downloads_root = volume / name / 'downloads'

        self._rpc: Optional[DelugeRPCClient] = None
        self.daemon_args = {
            'host': daemon_address,
            'port': daemon_port,
            'username': daemon_username,
            'password': daemon_password,
        }

        super().__init__(self.downloads_root)

        self._init_folders()

    def wipe_all_torrents(self):
        torrent_ids = list(self.rpc.core.get_torrents_status({}, []).keys())
        if torrent_ids:
            errors = self.rpc.core.remove_torrents(torrent_ids, remove_data=True)
            if errors:
                raise Exception(f'There were errors removing torrents: {errors}')

        # Wipe download folder to get rid of files that got uploaded but failed
        # seeding or deletes.
        shutil.rmtree(self.downloads_root)
        self._init_folders()

    def seed(
            self,
            file: Path,
            handle: Union[DelugeMeta, Torrent],
    ) -> Torrent:
        data_root = self.downloads_root / handle.name
        data_root.mkdir(parents=True, exist_ok=False)

        target = self.upload(local=file, name=handle.name)

        if isinstance(handle, DelugeMeta):
            torrent = Torrent.create_from(target.parent)
            torrent.announce_urls = handle.announce_url.url
            torrent.name = handle.name
        else:
            torrent = handle

        self.rpc.core.add_torrent_file(
            filename=f'{handle.name}.torrent',
            filedump=self._b64dump(torrent),
            options=dict(),
        )

        return torrent

    def leech(self, handle: Torrent) -> DownloadHandle:
        self.rpc.core.add_torrent_file(
            filename=f'{handle.name}.torrent',
            filedump=self._b64dump(handle),
            options=dict(),
        )

        return DelugeDownloadHandle(
            node=self,
            torrent=handle,
        )

    def torrent_info(self, name: str) -> List[Dict[bytes, Any]]:
        return list(self.rpc.core.get_torrents_status({'name': name}, []).values())

    @property
    def rpc(self) -> DelugeRPCClient:
        if self._rpc is None:
            self.connect()
        return self._rpc

    def connect(self) -> Self:
        client = DelugeRPCClient(**self.daemon_args)
        client.connect()
        self._rpc = client
        return self

    def _init_folders(self):
        self.downloads_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _b64dump(handle: Torrent) -> bytes:
        buffer = BytesIO()
        buffer.write(handle.to_string())
        return base64.b64encode(buffer.getvalue())


class DelugeDownloadHandle(DownloadHandle):

    def __init__(self, torrent: Torrent, node: DelugeNode) -> None:
        self.node = node
        self.torrent = torrent

    def await_for_completion(self, timeout: float = 0) -> bool:
        name = self.torrent.name
        current = time()
        while (time() - current) <= timeout:
            response = self.node.rpc.core.get_torrents_status({'name': name}, [])
            if len(response) > 1:
                logger.warning(f'Client has multiple torrents matching name {name}. Returning the first one.')

            status = list(response.values())[0]
            if status[b'is_finished']:
                return True

        return False
