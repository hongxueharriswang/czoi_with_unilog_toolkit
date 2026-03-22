from enum import Enum
from uuid import uuid4, UUID
from typing import Dict, List, Optional, Any, Union
from .utils import safe_eval
from .logic.parser import UniLangParser
from .logic.engine import InferenceEngine
from .logic.integration import CZOIModelAdapter
from .core import System

class ConstraintType(Enum):
    IDENTITY = "identity"
    TRIGGER = "trigger"
    GOAL = "goal"
    ACCESS = "access"

class Constraint:
    """Represents a constraint with a condition. Can be a Python expression or a UniLang formula."""
    def __init__(self, name: str, type: ConstraintType,
                 target: Dict, condition: Union[str, 'Formula'], priority: int = 0):
        self.id: UUID = uuid4()
        self.name = name
        self.type = type
        self.target = target
        self.priority = priority
        self.is_unilang = isinstance(condition, str) and condition.strip().startswith(('forall', 'exists', 'G', 'F', 'box', 'diamond', 'K', 'B', 'O', 'P', 'not', 'and', 'or', '->', '<->'))
        # Simple heuristic: if condition starts with certain keywords, treat as UniLang
        # In practice, we might have a flag or separate field.
        if self.is_unilang:
            parser = UniLangParser()
            self.formula = parser.parse_string(condition)
            self.condition_str = None
        else:
            self.condition_str = condition
            self.formula = None

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the constraint in the given context."""
        if self.formula is not None:
            # Use UniLang inference engine
            # Need a model adapter that can handle context
            # For simplicity, we create a temporary system with the context?
            # We'll assume context provides a system or enough info.
            # Here we use a basic adapter that wraps the context dict.
            from .logic.engine.model import Model, World
            class DictModel(Model):
                def __init__(self, ctx):
                    self.ctx = ctx
                    self._world = World(0)
                def worlds(self): return {self._world}
                def valuation(self, world, atom, args): return bool(self.ctx.get(atom, False))
                def accessibility(self, world, modality, agent): return set()
                def domain(self): return set()
                def interpret(self, term, assignment): return None
                def probability(self, world, event): return 0.0
                def preference(self, world, w1, w2): return False
            model = DictModel(context)
            engine = InferenceEngine.get_instance()
            return engine.evaluate(self.formula, model)
        else:
            # Use safe_eval
            return safe_eval(self.condition_str, context)

class ConstraintManager:
    def __init__(self):
        self.constraints: List[Constraint] = []

    def add(self, constraint: Constraint):
        self.constraints.append(constraint)

    def remove(self, constraint_id: UUID):
        self.constraints = [c for c in self.constraints if c.id != constraint_id]

    def get_by_type(self, type: ConstraintType) -> List[Constraint]:
        return [c for c in self.constraints if c.type == type]

    def get_for_target(self, target: Dict) -> List[Constraint]:
        # Simple key-value matching
        result = []
        for c in self.constraints:
            match = True
            for k, v in target.items():
                if k not in c.target or c.target[k] != v:
                    match = False
                    break
            if match:
                result.append(c)
        return result
