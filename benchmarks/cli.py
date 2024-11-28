import sys
from pathlib import Path

import typer
from pydantic_core import ValidationError

from benchmarks.core.config import ConfigParser
from benchmarks.deluge.config import DelugeExperimentConfig

parser = ConfigParser()
parser.register(DelugeExperimentConfig)

app = typer.Typer()


def _parse_config(config: Path):
    if not config.exists():
        print(f'Config file {config} does not exist.')
        sys.exit(-1)

    with config.open(encoding='utf-8') as infile:
        try:
            return parser.parse(infile)
        except ValidationError as e:
            print(f'There were errors parsing the config file.')
            for error in e.errors():
                print(f' - {error["loc"]}: {error["msg"]} {error["input"]}')
            sys.exit(-1)


@app.command()
def list(config: Path):
    """
    Lists the experiments available in CONFIG.
    """
    experiments = _parse_config(config)
    print(f'Available experiments in {config}:')
    for experiment in experiments.keys():
        print(f'  - {experiment}')


@app.command()
def run(config: Path, experiment: str):
    """
    Runs the experiment with name EXPERIMENT.
    """
    experiments = _parse_config(config)
    if experiment not in experiments:
        print(f'Experiment {experiment} not found in {config}.')
        sys.exit(-1)
    experiments[experiment].run()


if __name__ == '__main__':
    app()
