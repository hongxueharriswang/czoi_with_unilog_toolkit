from czoi.core import Zone, Role, User, Application, Operation, GammaMapping, System


def test_zone_hierarchy_and_path():
    root = Zone('Root')
    dept = Zone('Dept', parent=root)
    team = Zone('Team', parent=dept)
    assert team.get_path() == ['Root', 'Dept', 'Team']


def test_role_assignment_and_permissions():
    sys = System()
    root = Zone('Root')
    sys.add_zone(root)
    role = Role('Editor', root)
    sys.add_role(role)
    app = Application('WIKI', owning_zone=root)
    op_edit = app.add_operation('edit')
    sys.add_application(app)
    role.grant_permission(op_edit)
    assert op_edit in role.base_permissions


def test_user_assign_role_weight(simple_system):
    alice = simple_system['users']['alice']
    root = simple_system['root']
    role_user = simple_system['roles']['user']
    alice.assign_role(root, role_user, weight=0.7)
    assignments = alice.zone_role_assignments[root.id]
    assert len(assignments) == 1 and assignments[0][0] is role_user and assignments[0][1] == 0.7


def test_system_collections(simple_system):
    sys = simple_system['system']
    assert sys.root_zone is not None
    assert len(sys.applications) == 1
    assert len(sys.operations) == 2