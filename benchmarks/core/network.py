from abc import abstractmethod, ABC
from pathlib import Path

from typing_extensions import Generic, TypeVar, List, Optional

TNode = TypeVar('TNode', bound='Node')
TFileHandle = TypeVar('TFileHandle')


class Node(ABC, Generic[TFileHandle]):
    """A :class:`Node` represents a peer within a :class:`FileSharingNetwork`."""

    @abstractmethod
    def seed(
            self,
            file: Path,
            handle: Optional[TFileHandle]
    ) -> TFileHandle:
        """
        Makes the current :class:`Node` a seeder for the specified file.

        :param file: path to the file to seed.
        :param handle: an existing network handle to this file. If none is provided, a new one
            will be generated.
        """
        pass

    def leech(self, handle: TFileHandle):
        """Makes the current node a leecher for the provided handle."""
        pass


class FileSharingNetwork(Generic[TNode], ABC):
    """A :class:`FileSharingNetwork` is a set of :class:`Node`s that share
    an interest in a given file."""

    @property
    @abstractmethod
    def nodes(self) -> List[TNode]:
        pass
