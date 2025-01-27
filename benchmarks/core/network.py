from abc import abstractmethod, ABC

from typing_extensions import Generic, TypeVar

TNetworkHandle = TypeVar("TNetworkHandle")
TInitialMetadata = TypeVar("TInitialMetadata")


class DownloadHandle(ABC):
    """A :class:`DownloadHandle` is a reference to an ongoing download operation."""

    @property
    @abstractmethod
    def node(self) -> "Node":
        """The node that initiated the download."""
        pass

    @abstractmethod
    def await_for_completion(self, timeout: float = 0) -> bool:
        """Blocks the current thread until either the download completes or a timeout expires.

        :param timeout: Timeout in seconds.
        :return: True if the download completed within the timeout, False otherwise."""
        pass


class Node(ABC, Generic[TNetworkHandle, TInitialMetadata]):
    """A :class:`Node` represents a peer within a file sharing network."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A network-wide name for this node."""
        pass

    @abstractmethod
    def genseed(
        self,
        size: int,
        seed: int,
        meta: TInitialMetadata,
    ) -> TNetworkHandle:
        """
        Generates a random file of given size and makes the current node a seeder for it. Identical seeds,
        metadata, and sizes should result in identical network handles.

        :param size: The size of the file to be seeded.
        :param seed: The seed for the random number generator producing the file.
        :param meta: Additional, client-specific metadata relevant to the seeding process. For torrents,
            this could be the name of the torrent.

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

    @abstractmethod
    def remove(self, handle: TNetworkHandle) -> bool:
        """Removes the file associated with the handle from this node. For seeders, this means the node will stop
        seeding it. For leechers, it will stop downloading it. In both cases, the file will be removed from the node's
        storage.

        :return: True if the file exists and was successfully removed, False if the file didn't exit.
        """
        pass
