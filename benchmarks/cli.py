import argparse
import logging
import sys
from pathlib import Path
from typing import Dict

import uvicorn
from elasticsearch import Elasticsearch
from pydantic import IPvAnyAddress
from pydantic_core import ValidationError
from typing_extensions import TypeVar

from benchmarks.core.agent import AgentBuilder
from benchmarks.core.config import ConfigParser, Builder
from benchmarks.core.experiments.experiments import Experiment, ExperimentBuilder
from benchmarks.deluge.agent.api import DelugeAgentConfig
from benchmarks.deluge.config import DelugeExperimentConfig
from benchmarks.deluge.logging import DelugeTorrentDownload
from benchmarks.logging.logging import (
    basic_log_parser,
    LogSplitter,
    LogEntry,
    LogSplitterFormats,
)
from benchmarks.logging.sources.logstash import LogstashSource
from benchmarks.logging.sources.sources import (
    FSOutputManager,
    split_logs_in_source,
    LogSource,
)
from benchmarks.logging.sources.vector_flat_file import VectorFlatFileSource

experiment_config_parser = ConfigParser[ExperimentBuilder]()
experiment_config_parser.register(DelugeExperimentConfig)

agent_config_parser = ConfigParser[AgentBuilder]()
agent_config_parser.register(DelugeAgentConfig)

log_parser = basic_log_parser()
log_parser.register(DelugeTorrentDownload)

DECLogEntry = LogEntry.adapt(DelugeExperimentConfig)
log_parser.register(DECLogEntry)

logger = logging.getLogger(__name__)


def cmd_list_experiment(experiments: Dict[str, ExperimentBuilder[Experiment]], _):
    print("Available experiments are:")
    for experiment in experiments.keys():
        print(f"  - {experiment}")


def cmd_run_experiment(experiments: Dict[str, ExperimentBuilder[Experiment]], args):
    if args.experiment not in experiments:
        print(f"Experiment {args.experiment} not found.")
        sys.exit(-1)

    experiment = experiments[args.experiment]
    logger.info(DECLogEntry.adapt_instance(experiment))
    experiment.build().run()


def cmd_describe_experiment(args):
    if not args.type:
        print("Available experiment types are:")
        for experiment in experiment_config_parser.experiment_types.keys():
            print(f"  - {experiment}")
        return

    print(experiment_config_parser.experiment_types[args.type].schema_json(indent=2))


def cmd_parse_single_log(log: Path, output: Path):
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


def cmd_parse_log_source(source: LogSource, group_id: str, output_dir: Path):
    if not output_dir.parent.exists():
        print(f"Folder {output_dir.parent} does not exist.")
        sys.exit(-1)

    output_dir.mkdir(exist_ok=True)

    with (
        source as log_source,
        FSOutputManager(output_dir) as output_manager,
    ):
        split_logs_in_source(
            log_source,
            log_parser,
            output_manager,
            group_id,
            formats=[(DECLogEntry, LogSplitterFormats.jsonl)],
        )


def cmd_run_agent(agents: Dict[str, AgentBuilder], args):
    if args.agent not in agents:
        print(f"Agent type {args.experiment} not found.")
        sys.exit(-1)

    uvicorn.run(
        agents[args.agent].build(),
        host=str(args.host),
        port=args.port,
        reload=False,
        workers=1,
    )


T = TypeVar("T")


def _parse_config(
    config: Path, parser: ConfigParser[Builder[T]]
) -> Dict[str, Builder[T]]:
    if not config.exists():
        print(f"Config file {config} does not exist.")
        sys.exit(-1)

    with config.open(encoding="utf-8") as infile:
        try:
            return parser.parse(infile)
        except ValidationError as e:
            print("There were errors parsing the config file.")
            for error in e.errors():
                print(f' - {error["loc"]}: {error["msg"]} {error["input"]}')
            sys.exit(-1)


def _configure_source(args):
    # TODO we should probably have builders for sources as well, but for now
    #   we'll just keep it simple.
    if args.source_file:
        if not args.source_file.exists():
            print(f"Log source file {args.source_file} does not exist.")
            sys.exit(-1)
        return VectorFlatFileSource(
            app_name="codex-benchmarks", file=args.source_file.open(encoding="utf-8")
        )
    else:
        import urllib3

        urllib3.disable_warnings()

        return LogstashSource(
            Elasticsearch(args.es_url, verify_certs=False),
            structured_only=True,
        )


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
    list_cmd.set_defaults(
        func=lambda args: cmd_list_experiment(_parse_config(args.config), args)
    )

    run_cmd = experiment_commands.add_parser("run", help="Runs an experiment")
    run_cmd.add_argument("experiment", type=str, help="Name of the experiment to run.")
    run_cmd.set_defaults(
        func=lambda args: cmd_run_experiment(
            _parse_config(args.config, experiment_config_parser), args
        )
    )

    describe_cmd = commands.add_parser(
        "describe", help="Shows the JSON schema for the various experiment types."
    )
    describe_cmd.add_argument(
        "type",
        type=str,
        help="Type of the experiment to describe.",
        choices=experiment_config_parser.experiment_types.keys(),
        nargs="?",
    )

    describe_cmd.set_defaults(func=cmd_describe_experiment)

    logs_cmd = commands.add_parser("logs", help="Parse logs.")
    log_subcommands = logs_cmd.add_subparsers(required=True)

    single_log_cmd = log_subcommands.add_parser(
        "single", help="Parse a single log file."
    )
    single_log_cmd.add_argument("log", type=Path, help="Path to the log file.")
    single_log_cmd.add_argument(
        "output_dir", type=Path, help="Path to an output folder."
    )
    single_log_cmd.set_defaults(
        func=lambda args: cmd_parse_single_log(args.log, args.output_dir)
    )

    log_source_cmd = log_subcommands.add_parser(
        "source", help="Parse logs from a log source."
    )

    group = log_source_cmd.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--source-file", type=Path, help="Vector log file to parse from."
    )
    group.add_argument(
        "--es-url", type=str, help="URL to a logstash Elasticsearch instance."
    )
    log_source_cmd.add_argument(
        "output_dir", type=Path, help="Path to an output folder."
    )
    log_source_cmd.add_argument(
        "group_id", type=str, help="ID of experiment group to parse."
    )
    log_source_cmd.set_defaults(
        func=lambda args: cmd_parse_log_source(
            _configure_source(args), args.group_id, args.output_dir
        )
    )

    agent_cmd = commands.add_parser("agent", help="Starts a local agent.")
    agent_cmd.add_argument(
        "config", type=Path, help="Path to the agent configuration file."
    )
    agent_cmd.add_argument("agent", type=str, help="Name of the agent to run.")
    agent_cmd.add_argument(
        "--host",
        type=IPvAnyAddress,
        help="IP address to bind to.",
        default=IPvAnyAddress("0.0.0.0"),
    )
    agent_cmd.add_argument(
        "--port", type=int, help="Port to listen to connections.", default=9001
    )

    agent_cmd.set_defaults(
        func=lambda args: cmd_run_agent(
            _parse_config(args.config, agent_config_parser), args
        )
    )

    args = parser.parse_args()

    _init_logging()

    args.func(args)


if __name__ == "__main__":
    main()
