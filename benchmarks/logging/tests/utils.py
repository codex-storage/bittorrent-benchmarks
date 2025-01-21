from io import StringIO

from benchmarks.logging.sources.sources import OutputManager


class InMemoryOutputManager(OutputManager):
    def __init__(self):
        self.fs = {}

    def _open(self, relative_path, mode: str, encoding: str):
        root = self.fs
        for element in relative_path.parts[:-1]:
            subtree = root.get(element)
            if subtree is None:
                subtree = {}
                root[element] = subtree
            root = subtree

        output = StringIO()
        root[relative_path.parts[-1]] = output
        return output

    def __exit__(self, exc_type, exc_value, traceback, /):
        pass
