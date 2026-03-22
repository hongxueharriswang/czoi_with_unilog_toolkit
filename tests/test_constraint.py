from czoi.constraint import Constraint, ConstraintType


def test_python_expression_constraint():
    c = Constraint(
        name='must_be_admin',
        type=ConstraintType.ACCESS,
        target={'resource': 'docs'},
        condition='user_is_admin and request == "read"',
    )
    assert c.evaluate({'user_is_admin': True, 'request': 'read'}) is True
    assert c.evaluate({'user_is_admin': False, 'request': 'read'}) is False


def test_unilang_constraint_true_when_flag():
    c = Constraint(
        name='flag_true',
        type=ConstraintType.TRIGGER,
        target={},
        condition='flag(x)',
    )
    assert c.evaluate({'flag': True}) is True
    assert c.evaluate({'flag': False}) is False