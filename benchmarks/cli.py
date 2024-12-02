import argparse
import sys
from pathlib import Path
from typing import Dict

from pydantic_core import ValidationError

from benchmarks.core.config import ConfigParser, ExperimentBuilder
from benchmarks.core.experiments.experiments import Experiment
from benchmarks.deluge.config import DelugeExperimentConfig

config_parser = ConfigParser()
config_parser.register(DelugeExperimentConfig)


def cmd_list(experiments: Dict[str, ExperimentBuilder[Experiment]], _):
    """
    Lists the experiments available in CONFIG.
    """
    print(f'Available experiments are:')
    for experiment in experiments.keys():
        print(f'  - {experiment}')


def cmd_run(experiments: Dict[str, ExperimentBuilder[Experiment]], args):
    """
    Runs the experiment with name EXPERIMENT.
    """
    if args.experiment not in experiments:
        print(f'Experiment {args.experiment} not found.')
        sys.exit(-1)
    experiments[args.experiment].build().run()


def _parse_config(config: Path) -> Dict[str, ExperimentBuilder[Experiment]]:
    if not config.exists():
        print(f'Config file {config} does not exist.')
        sys.exit(-1)

    with config.open(encoding='utf-8') as infile:
        try:
            return config_parser.parse(infile)
        except ValidationError as e:
            print(f'There were errors parsing the config file.')
            for error in e.errors():
                print(f' - {error["loc"]}: {error["msg"]} {error["input"]}')
            sys.exit(-1)


def _init_logging():
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path, help="Path to the experiment configuration file.")

    commands = parser.add_subparsers(required=True)
    list_cmd = commands.add_parser('list', help='Lists available experiments.')
    list_cmd.set_defaults(func=cmd_list)

    run_cmd = commands.add_parser('run')
    run_cmd.add_argument('experiment', type=str, help='Name of the experiment to run.')
    run_cmd.set_defaults(func=cmd_run)

    args = parser.parse_args()

    _init_logging()

    args.func(_parse_config(args.config), args)


if __name__ == '__main__':
    main()
