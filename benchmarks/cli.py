import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

from pydantic_core import ValidationError

from benchmarks.core.config import ConfigParser, ExperimentBuilder
from benchmarks.core.experiments.experiments import Experiment
from benchmarks.logging.logging import (
    basic_log_parser,
    LogSplitter,
    LogEntry,
    LogSplitterFormats,
)
from benchmarks.deluge.config import DelugeExperimentConfig
from benchmarks.deluge.logging import DelugeTorrentDownload

config_parser = ConfigParser()
config_parser.register(DelugeExperimentConfig)

log_parser = basic_log_parser()
log_parser.register(DelugeTorrentDownload)

DECLogEntry = LogEntry.adapt(DelugeExperimentConfig)
log_parser.register(DECLogEntry)

logger = logging.getLogger(__name__)


def cmd_list(experiments: Dict[str, ExperimentBuilder[Experiment]], _):
    print("Available experiments are:")
    for experiment in experiments.keys():
        print(f"  - {experiment}")


def cmd_run(experiments: Dict[str, ExperimentBuilder[Experiment]], args):
    if args.experiment not in experiments:
        print(f"Experiment {args.experiment} not found.")
        sys.exit(-1)

    experiment = experiments[args.experiment]
    logger.info(DECLogEntry.adapt_instance(experiment))
    experiment.build().run()


def cmd_describe(args):
    if not args.type:
        print("Available experiment types are:")
        for experiment in config_parser.experiment_types.keys():
            print(f"  - {experiment}")
        return

    print(config_parser.experiment_types[args.type].schema_json(indent=2))


def cmd_logs(log: Path, output: Path):
    if not log.exists():
        print(f"Log file {log} does not exist.")
        sys.exit(-1)

    if not output.parent.exists():
        print(f"Folder {output.parent} does not exist.")
        sys.exit(-1)

    output.mkdir(exist_ok=True)

    def output_factory(event_type: str, format: LogSplitterFormats):
        return (output / f"{event_type}.{format.value}").open("w", encoding="utf-8")

    with (
        log.open("r", encoding="utf-8") as istream,
        LogSplitter(output_factory) as splitter,
    ):
        splitter.set_format(DECLogEntry, LogSplitterFormats.jsonl)
        splitter.split(log_parser.parse(istream))


def _parse_config(config: Path) -> Dict[str, ExperimentBuilder[Experiment]]:
    if not config.exists():
        print(f"Config file {config} does not exist.")
        sys.exit(-1)

    with config.open(encoding="utf-8") as infile:
        try:
            return config_parser.parse(infile)
        except ValidationError as e:
            print("There were errors parsing the config file.")
            for error in e.errors():
                print(f' - {error["loc"]}: {error["msg"]} {error["input"]}')
            sys.exit(-1)


def _init_logging():
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(required=True)

    experiments = commands.add_parser(
        "experiments", help="List or run experiments in config file."
    )
    experiments.add_argument(
        "config", type=Path, help="Path to the experiment configuration file."
    )
    experiment_commands = experiments.add_subparsers(required=True)

    list_cmd = experiment_commands.add_parser(
        "list", help="Lists available experiments."
    )
    list_cmd.set_defaults(func=lambda args: cmd_list(_parse_config(args.config), args))

    run_cmd = experiment_commands.add_parser("run", help="Runs an experiment")
    run_cmd.add_argument("experiment", type=str, help="Name of the experiment to run.")
    run_cmd.set_defaults(func=lambda args: cmd_run(_parse_config(args.config), args))

    describe = commands.add_parser(
        "describe", help="Shows the JSON schema for the various experiment types."
    )
    describe.add_argument(
        "type",
        type=str,
        help="Type of the experiment to describe.",
        choices=config_parser.experiment_types.keys(),
        nargs="?",
    )

    describe.set_defaults(func=cmd_describe)

    logs = commands.add_parser("logs", help="Parse logs.")
    logs.add_argument("log", type=Path, help="Path to the log file.")
    logs.add_argument("output_dir", type=Path, help="Path to an output folder.")
    logs.set_defaults(func=lambda args: cmd_logs(args.log, args.output_dir))

    args = parser.parse_args()

    _init_logging()

    args.func(args)


if __name__ == "__main__":
    main()
