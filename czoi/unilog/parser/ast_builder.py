from antlr4 import *
from .UniLangLexer import UniLangLexer
from .UniLangParser import UniLangParser as ANTLRUniLangParser
from ..ast import *
from ..utils import UniLangSyntaxError

class ASTBuilder:
    def __init__(self):
        self.parser = None

    def build(self, text: str):
        input_stream = InputStream(text)
        lexer = UniLangLexer(input_stream)
        stream = CommonTokenStream(lexer)
        self.parser = ANTLRUniLangParser(stream)
        tree = self.parser.start()
        return self.visit_start(tree)

    def visit_start(self, ctx):
        formulas = []
        for child in ctx.getChildren():
            if isinstance(child, ANTLRUniLangParser.FormulaContext):
                formulas.append(self.visit_formula(child))
        if len(formulas) == 1:
            return formulas[0]
        else:
            # Conjunction of multiple formulas
            result = formulas[0]
            for f in formulas[1:]:
                result = AndFormula(result, f)
            return result

    def visit_formula(self, ctx):
        if ctx.atom():
            return self.visit_atom(ctx.atom())
        if ctx.getChildCount() == 1 and ctx.getChild(0).getText() == 'true':
            return Atom('true', [])
        if ctx.getChildCount() == 1 and ctx.getChild(0).getText() == 'false':
            return Atom('false', [])
        if ctx.getChild(0).getText() == 'not':
            sub = self.visit_formula(ctx.formula(0))
            return NotFormula(sub)
        if ctx.getChild(1).getText() == 'and':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return AndFormula(left, right)
        if ctx.getChild(1).getText() == 'or':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return OrFormula(left, right)
        if ctx.getChild(1).getText() == '->':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return ImpliesFormula(left, right)
        if ctx.getChild(1).getText() == '<->':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return IffFormula(left, right)
        if ctx.getChild(0).getText() == 'forall':
            var = ctx.ID(0).getText()
            sort = ctx.ID(1).getText()
            body = self.visit_formula(ctx.formula(0))
            return ForallFormula(var, sort, body)
        if ctx.getChild(0).getText() == 'exists':
            var = ctx.ID(0).getText()
            sort = ctx.ID(1).getText()
            body = self.visit_formula(ctx.formula(0))
            return ExistsFormula(var, sort, body)
        # Modal
        if ctx.getChild(0).getText() == 'box':
            if ctx.ID():
                agent = ctx.ID().getText()
                sub = self.visit_formula(ctx.formula(0))
                return BoxModal('box', agent, sub)
            else:
                sub = self.visit_formula(ctx.formula(0))
                return BoxModal('box', None, sub)
        if ctx.getChild(0).getText() == 'diamond':
            if ctx.ID():
                agent = ctx.ID().getText()
                sub = self.visit_formula(ctx.formula(0))
                return DiamondModal('diamond', agent, sub)
            else:
                sub = self.visit_formula(ctx.formula(0))
                return DiamondModal('diamond', None, sub)
        if ctx.getChild(0).getText() == 'K':
            agent = ctx.ID().getText()
            sub = self.visit_formula(ctx.formula(0))
            return KFormula(agent, sub)
        if ctx.getChild(0).getText() == 'B':
            agent = ctx.ID().getText()
            sub = self.visit_formula(ctx.formula(0))
            return BFormula(agent, sub)
        if ctx.getChild(0).getText() == 'O':
            sub = self.visit_formula(ctx.formula(0))
            return OFormula(sub)
        if ctx.getChild(0).getText() == 'P':
            sub = self.visit_formula(ctx.formula(0))
            return PFormula(sub)
        if ctx.getChild(0).getText() == 'F':
            # Could be temporal or deontic; default to temporal? We'll treat as temporal F for now.
            sub = self.visit_formula(ctx.formula(0))
            return FFormula(sub)
        # Temporal
        if ctx.getChild(0).getText() == 'G':
            if ctx.getChildCount() > 2 and ctx.getChild(1).getText().startswith('['):
                # bounded
                l = float(ctx.REAL(0).getText())
                u = float(ctx.REAL(1).getText())
                sub = self.visit_formula(ctx.formula(0))
                return GFormula(sub, (l, u))
            else:
                sub = self.visit_formula(ctx.formula(0))
                return GFormula(sub)
        if ctx.getChild(0).getText() == 'F':
            if ctx.getChildCount() > 2 and ctx.getChild(1).getText().startswith('['):
                l = float(ctx.REAL(0).getText())
                u = float(ctx.REAL(1).getText())
                sub = self.visit_formula(ctx.formula(0))
                return FFormula(sub, (l, u))
            else:
                sub = self.visit_formula(ctx.formula(0))
                return FFormula(sub)
        if ctx.getChild(0).getText() == 'X':
            sub = self.visit_formula(ctx.formula(0))
            return XFormula(sub)
        if ctx.getChild(1).getText() == 'U':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            if ctx.getChildCount() > 4 and ctx.getChild(2).getText().startswith('['):
                l = float(ctx.REAL(0).getText())
                u = float(ctx.REAL(1).getText())
                return UntilFormula(left, right, (l, u))
            else:
                return UntilFormula(left, right)
        if ctx.getChild(1).getText() == 'R':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            if ctx.getChildCount() > 4 and ctx.getChild(2).getText().startswith('['):
                l = float(ctx.REAL(0).getText())
                u = float(ctx.REAL(1).getText())
                return ReleaseFormula(left, right, (l, u))
            else:
                return ReleaseFormula(left, right)
        if ctx.getChild(0).getText() == 'A':
            sub = self.visit_formula(ctx.formula(0))
            return AFormula(sub)
        if ctx.getChild(0).getText() == 'E':
            sub = self.visit_formula(ctx.formula(0))
            return EFormula(sub)
        # Dynamic
        if ctx.getChild(0).getText() == '[':
            action = self.visit_action(ctx.action())
            sub = self.visit_formula(ctx.formula(0))
            return BoxAction(action, sub)
        if ctx.getChild(0).getText() == '<':
            action = self.visit_action(ctx.action())
            sub = self.visit_formula(ctx.formula(0))
            return DiamondAction(action, sub)
        # Probabilistic
        if ctx.getChild(0).getText().startswith('P_>='):
            th = float(ctx.REAL().getText())
            sub = self.visit_formula(ctx.formula(0))
            return ProbGeq(th, sub)
        if ctx.getChild(0).getText().startswith('P_<='):
            th = float(ctx.REAL().getText())
            sub = self.visit_formula(ctx.formula(0))
            return ProbLeq(th, sub)
        if ctx.getChild(0).getText().startswith('P_='):
            th = float(ctx.REAL().getText())
            sub = self.visit_formula(ctx.formula(0))
            return ProbEq(th, sub)
        if ctx.getChild(0).getText() == 'E' and ctx.getChild(1).getText() == '[':
            term = self.visit_term(ctx.term())
            return ExpectedValue(term)
        # Fuzzy
        if ctx.getChild(1).getText() == '&G':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return FuzzyAnd(left, right, 'G')
        if ctx.getChild(1).getText() == '&L':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return FuzzyAnd(left, right, 'L')
        if ctx.getChild(1).getText() == '&P':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return FuzzyAnd(left, right, 'P')
        if ctx.getChild(1).getText() == '|G':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return FuzzyOr(left, right, 'G')
        if ctx.getChild(1).getText() == '|L':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return FuzzyOr(left, right, 'L')
        if ctx.getChild(1).getText() == '|P':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return FuzzyOr(left, right, 'P')
        if ctx.getChild(0).getText() == '~G':
            sub = self.visit_formula(ctx.formula(0))
            return FuzzyNot(sub, 'G')
        if ctx.getChild(0).getText() == '~L':
            sub = self.visit_formula(ctx.formula(0))
            return FuzzyNot(sub, 'L')
        if ctx.getChild(0).getText() == '~P':
            sub = self.visit_formula(ctx.formula(0))
            return FuzzyNot(sub, 'P')
        if ctx.getChild(0).getText().startswith('T_>='):
            th = float(ctx.REAL().getText())
            sub = self.visit_formula(ctx.formula(0))
            return GradedTruth(th, sub)
        # Non-monotonic
        if ctx.getChild(1).getText() == '=>':
            ant = self.visit_formula(ctx.formula(0))
            cons = self.visit_formula(ctx.formula(1))
            return DefaultImplies(ant, cons)
        if ctx.getChild(1).getText() == '<':
            left = self.visit_formula(ctx.formula(0))
            right = self.visit_formula(ctx.formula(1))
            return Preference(left, right)
        if ctx.getChild(0).getText() == 'Opt':
            sub = self.visit_formula(ctx.formula(0))
            return Optimal(sub)
        # Description Logic
        if ctx.concept():
            concept = self.visit_concept(ctx.concept())
            term = self.visit_term(ctx.term())
            return ConceptApplication(concept, term)
        raise NotImplementedError(f"Unsupported formula: {ctx.getText()}")

    def visit_action(self, ctx):
        if ctx.ID():
            return AtomicAction(ctx.ID().getText())
        if ctx.getChildCount() == 3 and ctx.getChild(1).getText() == ';':
            left = self.visit_action(ctx.action(0))
            right = self.visit_action(ctx.action(1))
            return SequenceAction(left, right)
        if ctx.getChildCount() == 3 and ctx.getChild(1).getText() == '|':
            left = self.visit_action(ctx.action(0))
            right = self.visit_action(ctx.action(1))
            return ChoiceAction(left, right)
        if ctx.getChildCount() == 2 and ctx.getChild(1).getText() == '*':
            sub = self.visit_action(ctx.action(0))
            return StarAction(sub)
        if ctx.getChildCount() == 2 and ctx.getChild(0).getText() == '?':
            cond = self.visit_formula(ctx.formula())
            return TestAction(cond)
        if ctx.getChildCount() == 3 and ctx.getChild(0).getText() == '(':
            return self.visit_action(ctx.action(0))
        raise NotImplementedError

    def visit_concept(self, ctx):
        if ctx.ID() and ctx.getChildCount() == 1:
            return AtomicConcept(ctx.ID().getText())
        if ctx.getChild(0).getText() == 'and':
            concepts = [self.visit_concept(c) for c in ctx.concept()]
            return AndConcept(concepts)
        if ctx.getChild(0).getText() == 'or':
            concepts = [self.visit_concept(c) for c in ctx.concept()]
            return OrConcept(concepts)
        if ctx.getChild(0).getText() == 'not':
            sub = self.visit_concept(ctx.concept(0))
            return NotConcept(sub)
        if ctx.getChild(0).getText() == 'some':
            role = ctx.ID().getText()
            sub = self.visit_concept(ctx.concept(0))
            return SomeConcept(role, sub)
        if ctx.getChild(0).getText() == 'all':
            role = ctx.ID().getText()
            sub = self.visit_concept(ctx.concept(0))
            return AllConcept(role, sub)
        if ctx.getChild(0).getText() == 'atleast':
            n = int(ctx.INT().getText())
            role = ctx.ID().getText()
            sub = self.visit_concept(ctx.concept(0))
            return AtLeastConcept(n, role, sub)
        if ctx.getChild(0).getText() == 'atmost':
            n = int(ctx.INT().getText())
            role = ctx.ID().getText()
            sub = self.visit_concept(ctx.concept(0))
            return AtMostConcept(n, role, sub)
        raise NotImplementedError

    def visit_atom(self, ctx):
        pred = ctx.ID().getText()
        args = [self.visit_term(t) for t in ctx.term()]
        return Atom(pred, args)

    def visit_term(self, ctx):
        if ctx.ID() and ctx.getChildCount() == 1:
            # Could be variable or constant; we'll treat as variable for now.
            return Variable(ctx.ID().getText())
        if ctx.getChildCount() > 1 and ctx.getChild(1).getText() == '(':
            # function application
            name = ctx.ID().getText()
            args = [self.visit_term(t) for t in ctx.term()]
            return Function(name, args)
        # Fallback
        return Constant(ctx.getText())

class UniLangParser:
    def __init__(self):
        self.builder = ASTBuilder()

    def parse_string(self, text: str):
        try:
            return self.builder.build(text)
        except Exception as e:
            raise UniLangSyntaxError(f"Parse error: {e}")

    def parse_file(self, path: str):
        with open(path, 'r') as f:
            return self.parse_string(f.read())
