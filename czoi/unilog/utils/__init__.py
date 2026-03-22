from .visitors import PrettyPrinter, SubstitutionVisitor

class UniLangSyntaxError(Exception):
    def __init__(self, message, line=None, column=None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(message)

__all__ = ['PrettyPrinter', 'SubstitutionVisitor', 'UniLangSyntaxError']
