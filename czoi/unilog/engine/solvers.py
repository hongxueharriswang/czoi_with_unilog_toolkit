from abc import ABC, abstractmethod
from ..ast import *
from .model import Model, World

class Solver(ABC):
    @abstractmethod
    def supports(self, formula: Formula) -> bool:
        pass

    @abstractmethod
    def evaluate(self, formula: Formula, model: Model,
                 world: World, assignment: dict) -> any:
        pass

class ClassicalSolver(Solver):
    def supports(self, formula):
        return isinstance(formula, (Atom, AndFormula, OrFormula, NotFormula,
                                    ImpliesFormula, IffFormula,
                                    ForallFormula, ExistsFormula))

    def evaluate(self, formula, model, world, assignment):
        if isinstance(formula, Atom):
            args = [model.interpret(arg, assignment) for arg in formula.args]
            return model.valuation(world, formula.name, tuple(args))
        if isinstance(formula, AndFormula):
            return (self.evaluate(formula.left, model, world, assignment) and
                    self.evaluate(formula.right, model, world, assignment))
        if isinstance(formula, OrFormula):
            return (self.evaluate(formula.left, model, world, assignment) or
                    self.evaluate(formula.right, model, world, assignment))
        if isinstance(formula, NotFormula):
            return not self.evaluate(formula.sub, model, world, assignment)
        if isinstance(formula, ImpliesFormula):
            return (not self.evaluate(formula.left, model, world, assignment) or
                    self.evaluate(formula.right, model, world, assignment))
        if isinstance(formula, IffFormula):
            left = self.evaluate(formula.left, model, world, assignment)
            right = self.evaluate(formula.right, model, world, assignment)
            return left == right
        if isinstance(formula, ForallFormula):
            # Simplified: assume finite domain
            for d in model.domain():
                new_assign = dict(assignment)
                new_assign[formula.var] = d
                if not self.evaluate(formula.body, model, world, new_assign):
                    return False
            return True
        if isinstance(formula, ExistsFormula):
            for d in model.domain():
                new_assign = dict(assignment)
                new_assign[formula.var] = d
                if self.evaluate(formula.body, model, world, new_assign):
                    return True
            return False
        raise NotImplementedError

class ModalSolver(Solver):
    def supports(self, formula):
        return isinstance(formula, (BoxModal, DiamondModal, KFormula, BFormula, OFormula, PFormula, FModal))

    def evaluate(self, formula, model, world, assignment):
        if isinstance(formula, (BoxModal, KFormula, BFormula, OFormula, FModal)):
            accessible = model.accessibility(world, formula.modality, getattr(formula, 'agent', None))
            return all(self.evaluate(formula.sub, model, w, assignment) for w in accessible)
        if isinstance(formula, (DiamondModal, PFormula)):
            accessible = model.accessibility(world, formula.modality, getattr(formula, 'agent', None))
            return any(self.evaluate(formula.sub, model, w, assignment) for w in accessible)
        raise NotImplementedError

class TemporalSolver(Solver):
    def supports(self, formula):
        return isinstance(formula, (GFormula, FFormula, XFormula, UntilFormula, ReleaseFormula, AFormula, EFormula))

    def evaluate(self, formula, model, world, assignment):
        # Simplified: assume linear time and single path
        # In a real implementation, would use model checking
        # Here we just return True/False based on simple rules
        if isinstance(formula, GFormula):
            # Not enough info; return True for now
            return True
        if isinstance(formula, FFormula):
            return True
        if isinstance(formula, XFormula):
            return True
        # ... etc.
        raise NotImplementedError

class FuzzySolver(Solver):
    def supports(self, formula):
        return isinstance(formula, (FuzzyAnd, FuzzyOr, FuzzyNot, GradedTruth))

    def evaluate(self, formula, model, world, assignment):
        def truth(val):
            return float(val) if isinstance(val, (int, float)) else (1.0 if val else 0.0)

        if isinstance(formula, FuzzyAnd):
            left = truth(self.evaluate(formula.left, model, world, assignment))
            right = truth(self.evaluate(formula.right, model, world, assignment))
            if formula.norm == 'G':
                return min(left, right)
            elif formula.norm == 'L':
                return max(0.0, left + right - 1.0)
            elif formula.norm == 'P':
                return left * right
            else:
                raise ValueError(f"Unknown t-norm {formula.norm}")
        if isinstance(formula, FuzzyOr):
            left = truth(self.evaluate(formula.left, model, world, assignment))
            right = truth(self.evaluate(formula.right, model, world, assignment))
            if formula.norm == 'G':
                return max(left, right)
            elif formula.norm == 'L':
                return min(1.0, left + right)
            elif formula.norm == 'P':
                return left + right - left * right
        if isinstance(formula, FuzzyNot):
            sub = truth(self.evaluate(formula.sub, model, world, assignment))
            if formula.norm in ('G', 'L', 'P'):
                return 1.0 - sub
        if isinstance(formula, GradedTruth):
            sub = truth(self.evaluate(formula.sub, model, world, assignment))
            return sub >= formula.threshold
        raise NotImplementedError
