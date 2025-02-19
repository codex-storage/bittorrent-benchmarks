from time import sleep
from typing import List, Optional

from benchmarks.core.experiments.experiments import (
    ExperimentComponent,
    ExperimentEnvironment,
    Experiment,
)


class ExternalComponent(ExperimentComponent):
    @property
    def readiness_timeout(self) -> float:
        return 0.1

    def __init__(self, loops: int, wait_time: float = 0.0):
        self.loops = loops
        self.iteration = 0
        self.wait_time = wait_time

    def is_ready(self) -> bool:
        sleep(self.wait_time)
        if self.iteration < self.loops:
            self.iteration += 1
            return False

        return True


def test_should_await_until_components_are_ready():
    components = [
        ExternalComponent(5),
        ExternalComponent(3),
    ]

    environment = ExperimentEnvironment(components, polling_interval=0)
    assert environment.await_ready()

    assert components[0].iteration == 5
    assert components[1].iteration == 3


def test_should_timeout_if_component_takes_too_long():
    components = [
        ExternalComponent(5),
        ExternalComponent(3, wait_time=0.1),
    ]

    environment = ExperimentEnvironment(components, polling_interval=0)
    assert not environment.await_ready(0.09)

    # Because ExperimentEnvironment sweeps through the components, it will
    # iterate exactly once before timing out.
    assert components[0].iteration == 1
    assert components[1].iteration == 1


class ExperimentThatReliesOnComponents(Experiment):
    def __init__(self, components: List[ExperimentComponent]):
        self.components = components

    def experiment_id(self) -> Optional[str]:
        return None

    def run(self):
        assert all(component.is_ready() for component in self.components)


def test_should_bind_experiment_to_environment():
    components = [
        ExternalComponent(5),
        ExternalComponent(3),
    ]

    env = ExperimentEnvironment(components, polling_interval=0)
    experiment = ExperimentThatReliesOnComponents(components)
    bound = env.bind(experiment)

    bound.run()

    assert components[0].is_ready()
    assert components[1].is_ready()


def test_should_not_ping_more_than_ping_max_components_per_polling_round():
    components = [
        ExternalComponent(5),
        ExternalComponent(3),
        ExternalComponent(1),
    ]

    env = ExperimentEnvironment(components, ping_max=2, polling_interval=0)
    env.is_ready()

    assert len([component for component in components if component.iteration == 1]) == 2
    assert len([component for component in components if component.iteration == 0]) == 1
