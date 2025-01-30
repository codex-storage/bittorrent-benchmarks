import pytest

from benchmarks.codex.agent import CodexAgent


@pytest.fixture
def codex_agent(codex_client_1):
    return CodexAgent(codex_client_1)


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_create_dataset(codex_agent: CodexAgent):
    cid = await codex_agent.create_dataset(size=1024, name="dataset-1", seed=1234)

    dataset = await codex_agent.client.get_manifest(cid)

    assert dataset.cid == cid
    assert dataset.datasetSize == 1024


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_same_seed_creates_same_cid(codex_agent: CodexAgent):
    cid1 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    cid2 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    cid3 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1235)

    assert cid1 == cid2
    assert cid1 != cid3
