from contextlib import contextmanager
import logging

from benchmarks.core.experiments.experiments import Experiment
from benchmarks.logging.logging import ExperimentStage, EventBoundary

logger = logging.getLogger(__name__)


@contextmanager
def experiment_stage(experiment: Experiment, name: str):
    logger.info(
        ExperimentStage(
            name=experiment.experiment_id() or "",
            stage=name,
            type=EventBoundary.start,
        )
    )

    try:
        yield
    except Exception as exc:
        logger.info(
            ExperimentStage(
                name=experiment.experiment_id() or "",
                stage=name,
                type=EventBoundary.end,
                error=str(exc),
            )
        )
        raise

    logger.info(
        ExperimentStage(
            name=experiment.experiment_id() or "",
            stage=name,
            type=EventBoundary.end,
        )
    )
