from abc import ABC, abstractmethod
from typing import Any, Dict, Set, Tuple, Optional
from ..ast import Term

class World:
    def __init__(self, id: Any):
        self.id = id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, World) and self.id == other.id

class Model(ABC):
    @abstractmethod
    def worlds(self) -> Set[World]:
        pass

    @abstractmethod
    def valuation(self, world: World, atom: str, args: Tuple[Any, ...]) -> bool:
        pass

    @abstractmethod
    def accessibility(self, world: World, modality: str, agent: Optional[str] = None) -> Set[World]:
        pass

    @abstractmethod
    def domain(self) -> Set[Any]:
        pass

    @abstractmethod
    def interpret(self, term: Term, assignment: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def probability(self, world: World, event: Set[World]) -> float:
        pass

    @abstractmethod
    def preference(self, world: World, w1: World, w2: World) -> bool:
        pass
