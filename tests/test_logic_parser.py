import importlib
import pytest

antlr_modules_present = True
for mod in ("czoi.logic.parser.UniLangLexer", "czoi.logic.parser.UniLangParser"):
    try:
        importlib.import_module(mod)
    except Exception:
        antlr_modules_present = False

pytestmark = pytest.mark.skipif(not antlr_modules_present, reason="ANTLR-generated parser not present")


def test_parse_simple_formula():
    from czoi.logic.parser import UniLangParser
    parser = UniLangParser()
    f = parser.parse_string('true')
    assert f is not None