from benchmarks.core.pydantic import SnakeCaseModel
from benchmarks.logging.logging import LogEntry, ConfigToLogAdapters


class MyConfig(SnakeCaseModel):
    my_key: str
    my_value: int


class MyOtherConfig(SnakeCaseModel):
    my_other_key: str
    my_other_value: int


def test_should_adapt_pydantic_model_to_log_entry():
    adapters = ConfigToLogAdapters()

    Adapted = adapters.adapt(MyConfig)
    assert issubclass(Adapted, LogEntry)

    instance = Adapted(my_key="key", my_value=1)
    assert instance.entry_type == "my_config_log_entry"


def test_should_adapt_instance_by_type():
    adapters = ConfigToLogAdapters()

    Adapted1 = adapters.adapt(MyConfig)
    Adapted2 = adapters.adapt(MyOtherConfig)

    config1 = MyConfig(my_key="key", my_value=1)
    config2 = MyOtherConfig(my_other_key="key", my_other_value=1)

    adapted1 = adapters.adapt_instance(config1)
    adapted2 = adapters.adapt_instance(config2)

    assert isinstance(adapted1, Adapted1)
    assert isinstance(adapted2, Adapted2)
