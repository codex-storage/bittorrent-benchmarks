import pytest
from tenacity import wait_incrementing, stop_after_attempt, RetryError

from benchmarks.core.utils import megabytes, await_predicate
from benchmarks.deluge.deluge_node import DelugeNode, DelugeMeta, ResilientCallWrapper
from benchmarks.deluge.tracker import Tracker


def assert_is_seed(node: DelugeNode, name: str, size: int):
    def _is_seed():
        response = node.torrent_info(name=name)
        if len(response) == 0:
            return False

        assert len(response) == 1
        info = response[0]

        if not info[b"is_seed"]:
            return False

        assert info[b"name"] == name.encode(
            "utf-8"
        )  # not sure that this works for ANY name...
        assert info[b"total_size"] == size

        return True

    assert await_predicate(_is_seed, timeout=5)


@pytest.mark.integration
def test_should_seed_files(deluge_node1: DelugeNode, tracker: Tracker):
    assert not deluge_node1.torrent_info(name="dataset1")

    deluge_node1.genseed(
        size=megabytes(1),
        seed=1234,
        meta=DelugeMeta(name="dataset1", announce_url=tracker.announce_url),
    )

    assert_is_seed(deluge_node1, name="dataset1", size=megabytes(1))


@pytest.mark.integration
def test_should_download_files(
    deluge_node1: DelugeNode,
    deluge_node2: DelugeNode,
    tracker: Tracker,
):
    assert not deluge_node1.torrent_info(name="dataset1")
    assert not deluge_node2.torrent_info(name="dataset1")

    torrent = deluge_node1.genseed(
        size=megabytes(1),
        seed=1234,
        meta=DelugeMeta(name="dataset1", announce_url=tracker.announce_url),
    )
    handle = deluge_node2.leech(torrent)

    assert handle.await_for_completion(5)

    assert_is_seed(deluge_node2, name="dataset1", size=megabytes(1))


@pytest.mark.integration
def test_should_remove_files(deluge_node1: DelugeNode, tracker: Tracker):
    assert not deluge_node1.torrent_info(name="dataset1")

    torrent = deluge_node1.genseed(
        size=megabytes(1),
        seed=1234,
        meta=DelugeMeta(name="dataset1", announce_url=tracker.announce_url),
    )
    assert_is_seed(deluge_node1, name="dataset1", size=megabytes(1))

    deluge_node1.remove(torrent)
    assert not deluge_node1.torrent_info(name="dataset1")


class FlakyClient:
    def __init__(self):
        self.count = 0

    def flaky(self):
        self.count += 1
        if self.count == 1:
            raise IOError("Connection refused")
        return 1


def test_should_retry_operations_when_they_fail():
    wrapper = ResilientCallWrapper(
        FlakyClient(),
        wait_policy=wait_incrementing(start=0, increment=0),
        stop_policy=stop_after_attempt(2),
    )
    assert wrapper.flaky() == 1


def test_should_give_up_on_operations_when_stop_policy_is_met():
    wrapper = ResilientCallWrapper(
        FlakyClient(),
        wait_policy=wait_incrementing(start=0, increment=0),
        stop_policy=stop_after_attempt(1),
    )

    with pytest.raises(RetryError):
        wrapper.flaky()


class NestedFlaky:
    def __init__(self):
        self.client = FlakyClient()


def test_should_resolve_nested_objects():
    wrapper = ResilientCallWrapper(
        NestedFlaky(),
        wait_policy=wait_incrementing(start=0, increment=0),
        stop_policy=stop_after_attempt(2),
    )

    assert wrapper.client.flaky() == 1
