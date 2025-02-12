import random
from itertools import islice
from typing import List, cast

from pydantic import Field
from pydantic_core import Url
from urllib3.util import parse_url

from benchmarks.codex.agent.codex_agent_client import CodexAgentClient
from benchmarks.codex.client.common import Cid
from benchmarks.codex.codex_node import CodexMeta, CodexNode
from benchmarks.core.experiments.experiments import (
    ExperimentBuilder,
    ExperimentEnvironment,
    ExperimentComponent,
)
from benchmarks.core.experiments.iterated_experiment import IteratedExperiment
from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.pydantic import SnakeCaseModel, Host
from benchmarks.core.utils.random import sample


class CodexNodeConfig(SnakeCaseModel):
    name: str
    address: Host
    disc_port: int
    api_port: int
    agent_url: Url


CodexDisseminationExperiment = IteratedExperiment[
    StaticDisseminationExperiment[Cid, CodexMeta]
]


class CodexExperimentConfig(ExperimentBuilder[CodexDisseminationExperiment]):
    experiment_set_id: str = Field(
        description="Identifies the group of experiment repetitions", default="unnamed"
    )
    seeder_sets: int = Field(
        gt=0, default=1, description="Number of distinct seeder sets to experiment with"
    )
    seeders: int = Field(gt=0, description="Number of seeders per seeder set")
    file_size: int = Field(gt=0, description="File size, in bytes")
    repetitions: int = Field(
        gt=0, description="How many experiment repetitions to run for each seeder set"
    )

    logging_cooldown: int = Field(
        gt=0,
        default=0,
        description="Time to wait after the last download completes before tearing down the experiment.",
    )

    nodes: List[CodexNodeConfig]

    def build(self) -> CodexDisseminationExperiment:
        agents = [
            CodexAgentClient(parse_url(str(node.agent_url))) for node in self.nodes
        ]

        network = [
            CodexNode(
                codex_api_url=parse_url(f"http://{str(node.address)}:{node.api_port}"),
                agent=agents[i],
            )
            for i, node in enumerate(self.nodes)
        ]

        env = ExperimentEnvironment(
            components=cast(List[ExperimentComponent], network + agents),
            ping_max=10,
            polling_interval=0.5,
        )

        def repetitions():
            for seeder_set in range(self.seeder_sets):
                seeders = list(islice(sample(len(network)), self.seeders))
                for experiment_run in range(self.repetitions):
                    yield env.bind(
                        StaticDisseminationExperiment(
                            network=network,
                            seeders=seeders,
                            file_size=self.file_size,
                            seed=random.randint(0, 2**16),
                            meta=CodexMeta(f"dataset-{seeder_set}-{experiment_run}"),
                            logging_cooldown=self.logging_cooldown,
                        )
                    )

        return IteratedExperiment(
            repetitions(), experiment_set_id=self.experiment_set_id
        )
