from typing import List, Dict, Type
from ..ast import Formula
from .solvers import Solver

class SolverRegistry:
    def __init__(self):
        self._solvers: List[Solver] = []

    def register(self, solver: Solver):
        self._solvers.append(solver)

    def get_solver(self, formula: Formula) -> Solver:
        for solver in self._solvers:
            if solver.supports(formula):
                return solver
        raise ValueError(f"No solver found for formula type {type(formula)}")
