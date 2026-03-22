from typing import Any, Dict, Set, Tuple, Optional
from ...core import System, Zone, Role, User, Application, Operation
from ..engine import Model, World
from ..ast import Term, Variable, Constant, Function

class CZOIModelAdapter(Model):
    """Adapts a CZOI System (or a specific state) to the UniLog Model interface.
    The current state is treated as a single world."""
    def __init__(self, system: System, current_state: Optional[Dict] = None):
        self.system = system
        self._world = World(id=0)
        self.state = current_state or {}

    def worlds(self) -> Set[World]:
        return {self._world}

    def valuation(self, world: World, atom: str, args: Tuple[Any, ...]) -> bool:
        # Simple lookup: if atom matches an attribute name in the state, return its truthiness.
        if atom in self.state:
            return bool(self.state[atom])
        # Could also check against system objects (e.g., inZone)
        return False

    def accessibility(self, world: World, modality: str, agent: Optional[str] = None) -> Set[World]:
        # Single-world model: no accessibility.
        return set()

    def domain(self) -> Set[Any]:
        # Return all objects in the system (users, zones, etc.)
        domain = set()
        domain.update(self.system.users)
        domain.update(self.system.zones)
        domain.update(self.system.roles)
        domain.update(self.system.applications)
        domain.update(self.system.operations)
        return domain

    def interpret(self, term: Term, assignment: Dict[str, Any]) -> Any:
        if isinstance(term, Variable):
            return assignment.get(term.name, None)
        if isinstance(term, Constant):
            return term.value
        if isinstance(term, Function):
            # Evaluate function: assume it's a method on some object? Not implemented.
            return None
        return None

    def probability(self, world: World, event: Set[World]) -> float:
        return 1.0 if world in event else 0.0

    def preference(self, world: World, w1: World, w2: World) -> bool:
        return False
