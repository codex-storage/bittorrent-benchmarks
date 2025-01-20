from fastapi import FastAPI

from benchmarks.core.config import Builder

# Agents are auxiliary containers deployed alongside a :class:`Node` which allow us to implement
# arbitrary actions, like generating files for experiments, close to the node itself.
AgentBuilder = Builder[FastAPI]
