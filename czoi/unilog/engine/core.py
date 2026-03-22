from typing import Optional, Dict, Any, Union
from ..ast import Formula
from .model import Model, World
from .solvers import ClassicalSolver, ModalSolver, FuzzySolver, TemporalSolver
from .registry import SolverRegistry

class InferenceEngine:
    _instance = None

    def __init__(self):
        self.registry = SolverRegistry()
        self._register_default_solvers()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_default_solvers(self):
        self.registry.register(ClassicalSolver())
        self.registry.register(ModalSolver())
        self.registry.register(FuzzySolver())
        self.registry.register(TemporalSolver())
        # Additional solvers can be added later

    def evaluate(self, formula: Formula, model: Model,
                 world: Optional[World] = None,
                 assignment: Optional[Dict[str, Any]] = None) -> Union[bool, float]:
        if world is None:
            worlds = list(model.worlds())
            if not worlds:
                raise ValueError("Model has no worlds")
            world = worlds[0]
        if assignment is None:
            assignment = {}
        solver = self.registry.get_solver(formula)
        return solver.evaluate(formula, model, world, assignment)
