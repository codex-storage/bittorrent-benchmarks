import shutil
from abc import abstractmethod, ABC
from pathlib import Path

from typing_extensions import Generic, TypeVar, Union

TNetworkHandle = TypeVar('TNetworkHandle')
TInitialMetadata = TypeVar('TInitialMetadata')


class DownloadHandle(ABC):
    """A :class:`DownloadHandle` is a reference to an ongoing download operation."""

    @abstractmethod
    def await_for_completion(self, timeout: float = 0) -> bool:
        """Blocks the current thread until either the download completes or a timeout expires.

        :param timeout: Timeout in seconds.
        :return: True if the download completed within the timeout, False otherwise."""
        pass


class Node(ABC, Generic[TNetworkHandle, TInitialMetadata]):
    """A :class:`Node` represents a peer within a file sharing network."""

    @abstractmethod
    def seed(
            self,
            file: Path,
            handle: Union[TInitialMetadata, TNetworkHandle],
    ) -> TNetworkHandle:
        """
        Makes the current :class:`Node` a seeder for the specified file.

        :param file: local path to the file to seed.
        :param handle: file sharing typically requires some initial metadata when a file is first uploaded into the
            network, and this will typically then result into a compact representation such as a manifest CID (Codex)
            or a Torrent file (Bittorrent) which other nodes can then use to identify and locate both the file and its
            metadata within the network. When doing an initial seed, this method should be called with the initial
            metadata (TInitialMetadata). Subsequent calls should use the network handle (TNetworkHandle).

        :return: The network handle (TNetworkHandle) for this file. This handle should be used for subsequent calls to
            :meth:`seed`.
        """
        pass

    @abstractmethod
    def leech(self, handle: TNetworkHandle) -> DownloadHandle:
        """Makes the current node a leecher for the provided handle.

        :param handle: a :class:`DownloadHandle`, which can be used to interact with the download process.
        """
        pass


class SharedFSNode(Node[TNetworkHandle, TInitialMetadata], ABC):
    """A `SharedFSNode` is a :class:`Node` which shares a network volume with us. This means
    we are able to upload files to it by means of simple file copies."""

    def __init__(self, volume: Path):
        self.volume = volume

    def upload(self, local: Path, name: str) -> Path:
        target_path = self.volume / name
        target_path.mkdir(parents=True, exist_ok=True)
        target = target_path / local.name
        if local.is_dir():
            shutil.copytree(local, target)
        else:
            shutil.copy(local, target)

        return target
