import shutil
from abc import abstractmethod, ABC
from pathlib import Path
from typing import Sequence

from typing_extensions import Generic, TypeVar, Union

TNetworkHandle = TypeVar('TNetworkHandle')
TInitialMetadata = TypeVar('TInitialMetadata')


class Node(ABC, Generic[TNetworkHandle, TInitialMetadata]):
    """A :class:`Node` represents a peer within a :class:`FileSharingNetwork`."""

    @abstractmethod
    def seed(
            self,
            file: Path,
            handle: Union[TInitialMetadata, TNetworkHandle],
    ) -> TNetworkHandle:
        """
        Makes the current :class:`Node` a seeder for the specified file.

        :param file: local path to the file to seed.
        :param handle: file sharing requires some initial set of information when a file is first uploaded into the
            network, and that will typically then result into a compact representation such as a CID or a Torrent file,
            which other nodes can then use to identify the file and its metadata within the network. This method can
            take both such initial metadata (TInitialMetadata) or the subsequent network handle (TNetworkHandle) if
            it exists.
        """
        pass

    @abstractmethod
    def leech(self, handle: TNetworkHandle):
        """Makes the current node a leecher for the provided handle."""
        pass


class FileSharingNetwork(Generic[TNetworkHandle, TInitialMetadata], ABC):
    """A :class:`FileSharingNetwork` is a set of :class:`Node`s that share
    an interest in a given file."""

    @property
    @abstractmethod
    def nodes(self) -> Sequence[Node[TNetworkHandle, TInitialMetadata]]:
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
