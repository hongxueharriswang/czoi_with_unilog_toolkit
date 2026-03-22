from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Any, Union

class Formula(ABC):
    @abstractmethod
    def accept(self, visitor): pass

class Term(ABC):
    pass

class Variable(Term):
    def __init__(self, name: str):
        self.name = name

class Constant(Term):
    def __init__(self, value: Any):
        self.value = value

class Function(Term):
    def __init__(self, name: str, args: List[Term]):
        self.name = name
        self.args = args

# Atomic formulas
class Atom(Formula):
    def __init__(self, name: str, args: List[Term]):
        self.name = name
        self.args = args

    def accept(self, visitor):
        return visitor.visit_atom(self)

class AndFormula(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right

    def accept(self, visitor):
        return visitor.visit_and(self)

class OrFormula(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right

    def accept(self, visitor):
        return visitor.visit_or(self)

class ImpliesFormula(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right

    def accept(self, visitor):
        return visitor.visit_implies(self)

class IffFormula(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right

    def accept(self, visitor):
        return visitor.visit_iff(self)

class NotFormula(Formula):
    def __init__(self, sub: Formula):
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_not(self)

class ForallFormula(Formula):
    def __init__(self, var: str, sort: str, body: Formula):
        self.var = var
        self.sort = sort
        self.body = body

    def accept(self, visitor):
        return visitor.visit_forall(self)

class ExistsFormula(Formula):
    def __init__(self, var: str, sort: str, body: Formula):
        self.var = var
        self.sort = sort
        self.body = body

    def accept(self, visitor):
        return visitor.visit_exists(self)

# Modal
class BoxModal(Formula):
    def __init__(self, modality: str, agent: Optional[str], sub: Formula):
        self.modality = modality
        self.agent = agent
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_box(self)

class DiamondModal(Formula):
    def __init__(self, modality: str, agent: Optional[str], sub: Formula):
        self.modality = modality
        self.agent = agent
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_diamond(self)

# Epistemic shortcuts
class KFormula(BoxModal):
    def __init__(self, agent: str, sub: Formula):
        super().__init__('K', agent, sub)

class BFormula(BoxModal):
    def __init__(self, agent: str, sub: Formula):
        super().__init__('B', agent, sub)

# Deontic
class OFormula(BoxModal):
    def __init__(self, sub: Formula):
        super().__init__('O', None, sub)

class PFormula(DiamondModal):
    def __init__(self, sub: Formula):
        super().__init__('P', None, sub)

class FModal(BoxModal):
    def __init__(self, sub: Formula):
        super().__init__('F', None, sub)

# Temporal
class GFormula(Formula):
    def __init__(self, sub: Formula, bound: Optional[Tuple[float, float]] = None):
        self.sub = sub
        self.bound = bound

    def accept(self, visitor):
        return visitor.visit_G(self)

class FFormula(Formula):
    def __init__(self, sub: Formula, bound: Optional[Tuple[float, float]] = None):
        self.sub = sub
        self.bound = bound

    def accept(self, visitor):
        return visitor.visit_F(self)

class XFormula(Formula):
    def __init__(self, sub: Formula):
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_X(self)

class UntilFormula(Formula):
    def __init__(self, left: Formula, right: Formula, bound: Optional[Tuple[float, float]] = None):
        self.left = left
        self.right = right
        self.bound = bound

    def accept(self, visitor):
        return visitor.visit_until(self)

class ReleaseFormula(Formula):
    def __init__(self, left: Formula, right: Formula, bound: Optional[Tuple[float, float]] = None):
        self.left = left
        self.right = right
        self.bound = bound

    def accept(self, visitor):
        return visitor.visit_release(self)

class AFormula(Formula):
    def __init__(self, sub: Formula):
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_A(self)

class EFormula(Formula):
    def __init__(self, sub: Formula):
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_E(self)

# Dynamic
class Action:
    pass

class AtomicAction(Action):
    def __init__(self, name: str):
        self.name = name

class SequenceAction(Action):
    def __init__(self, left: Action, right: Action):
        self.left = left
        self.right = right

class ChoiceAction(Action):
    def __init__(self, left: Action, right: Action):
        self.left = left
        self.right = right

class StarAction(Action):
    def __init__(self, action: Action):
        self.action = action

class TestAction(Action):
    def __init__(self, condition: Formula):
        self.condition = condition

class BoxAction(Formula):
    def __init__(self, action: Action, sub: Formula):
        self.action = action
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_box_action(self)

class DiamondAction(Formula):
    def __init__(self, action: Action, sub: Formula):
        self.action = action
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_diamond_action(self)

# Probabilistic
class ProbGeq(Formula):
    def __init__(self, threshold: float, sub: Formula):
        self.threshold = threshold
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_prob_geq(self)

class ProbLeq(Formula):
    def __init__(self, threshold: float, sub: Formula):
        self.threshold = threshold
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_prob_leq(self)

class ProbEq(Formula):
    def __init__(self, threshold: float, sub: Formula):
        self.threshold = threshold
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_prob_eq(self)

class ExpectedValue(Formula):
    def __init__(self, term: Term):
        self.term = term

    def accept(self, visitor):
        return visitor.visit_expected(self)

# Fuzzy
class FuzzyAnd(Formula):
    def __init__(self, left: Formula, right: Formula, norm: str):
        self.left = left
        self.right = right
        self.norm = norm

    def accept(self, visitor):
        return visitor.visit_fuzzy_and(self)

class FuzzyOr(Formula):
    def __init__(self, left: Formula, right: Formula, norm: str):
        self.left = left
        self.right = right
        self.norm = norm

    def accept(self, visitor):
        return visitor.visit_fuzzy_or(self)

class FuzzyNot(Formula):
    def __init__(self, sub: Formula, norm: str):
        self.sub = sub
        self.norm = norm

    def accept(self, visitor):
        return visitor.visit_fuzzy_not(self)

class GradedTruth(Formula):
    def __init__(self, threshold: float, sub: Formula):
        self.threshold = threshold
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_graded(self)

# Non-monotonic
class DefaultImplies(Formula):
    def __init__(self, antecedent: Formula, consequent: Formula):
        self.antecedent = antecedent
        self.consequent = consequent

    def accept(self, visitor):
        return visitor.visit_default(self)

class Preference(Formula):
    def __init__(self, left: Formula, right: Formula):
        self.left = left
        self.right = right

    def accept(self, visitor):
        return visitor.visit_preference(self)

class Optimal(Formula):
    def __init__(self, sub: Formula):
        self.sub = sub

    def accept(self, visitor):
        return visitor.visit_optimal(self)

# Description Logic
class Concept(ABC):
    pass

class AtomicConcept(Concept):
    def __init__(self, name: str):
        self.name = name

class AndConcept(Concept):
    def __init__(self, concepts: List[Concept]):
        self.concepts = concepts

class OrConcept(Concept):
    def __init__(self, concepts: List[Concept]):
        self.concepts = concepts

class NotConcept(Concept):
    def __init__(self, concept: Concept):
        self.concept = concept

class SomeConcept(Concept):
    def __init__(self, role: str, concept: Concept):
        self.role = role
        self.concept = concept

class AllConcept(Concept):
    def __init__(self, role: str, concept: Concept):
        self.role = role
        self.concept = concept

class AtLeastConcept(Concept):
    def __init__(self, n: int, role: str, concept: Concept):
        self.n = n
        self.role = role
        self.concept = concept

class AtMostConcept(Concept):
    def __init__(self, n: int, role: str, concept: Concept):
        self.n = n
        self.role = role
        self.concept = concept

class ConceptApplication(Formula):
    def __init__(self, concept: Concept, term: Term):
        self.concept = concept
        self.term = term

    def accept(self, visitor):
        return visitor.visit_concept_application(self)
