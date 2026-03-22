import pytest

@pytest.fixture
def simple_system():
    from czoi.core import System, Zone, Role, User, Application
    sys = System()
    root = Zone('Root')
    sys.add_zone(root)
    role_admin = Role('Admin', root)
    role_user = Role('User', root)
    sys.add_role(role_admin)
    sys.add_role(role_user)
    alice = User('alice', 'alice@example.com')
    bob = User('bob', 'bob@example.com')
    sys.add_user(alice)
    sys.add_user(bob)
    app = Application('Docs', owning_zone=root)
    read = app.add_operation('read')
    write = app.add_operation('write')
    sys.add_application(app)
    return {
        'system': sys,
        'root': root,
        'roles': {'admin': role_admin, 'user': role_user},
        'users': {'alice': alice, 'bob': bob},
        'ops': {'read': read, 'write': write},
        'app': app,
    }