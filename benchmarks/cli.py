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
def list(ctx: typer.Context):
    """
    Lists the experiments available in CONFIG.
    """
    experiments = ctx.obj
    print(f'Available experiments are:')
    for experiment in experiments.keys():
        print(f'  - {experiment}')


@app.command()
def run(ctx: typer.Context, experiment: str):
    """
    Runs the experiment with name EXPERIMENT.
    """
    experiments = ctx.obj
    if experiment not in experiments:
        print(f'Experiment {experiment} not found.')
        sys.exit(-1)
    experiments[experiment].build().run()


def _init_logging():
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@app.callback()
def main(ctx: typer.Context, config: Path):
    if ctx.resilient_parsing:
        return

    ctx.obj = _parse_config(config)
    _init_logging()


if __name__ == '__main__':
    app()
