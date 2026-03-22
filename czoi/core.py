from __future__ import annotations
from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional, List, Dict, Set, Tuple, Any
import networkx as nx

class Zone:
    def __init__(self, name: str, parent: Optional['Zone'] = None):
        self.id: UUID = uuid4()
        self.name: str = name
        self.parent: Optional['Zone'] = parent
        self.children: List['Zone'] = []
        self.roles: List['Role'] = []
        self.applications: List['Application'] = []
        self.users: List['User'] = []
        self.created_at: datetime = datetime.utcnow()
        self.capacity: Optional[int] = None
        if parent:
            parent.add_child(self)

    def add_child(self, zone: 'Zone'):
        zone.parent = self
        self.children.append(zone)

    def get_path(self) -> List[str]:
        if self.parent:
            return self.parent.get_path() + [self.name]
        return [self.name]

    def __repr__(self):
        return f"Zone(name='{self.name}')"

class Role:
    def __init__(self, name: str, zone: Zone):
        self.id: UUID = uuid4()
        self.name: str = name
        self.zone: Zone = zone
        self.base_permissions: Set['Operation'] = set()
        self.senior_roles: List['Role'] = []
        self.junior_roles: List['Role'] = []
        self.created_at: datetime = datetime.utcnow()
        zone.roles.append(self)

    def grant_permission(self, operation: 'Operation'):
        self.base_permissions.add(operation)

    def add_senior(self, role: 'Role'):
        if role.zone != self.zone:
            raise ValueError("Senior roles must be in same zone")
        self.senior_roles.append(role)
        role.junior_roles.append(self)

    def __repr__(self):
        return f"Role(name='{self.name}', zone='{self.zone.name}')"

class User:
    def __init__(self, username: str, email: str = None):
        self.id: UUID = uuid4()
        self.username: str = username
        self.email: str = email
        self.attributes: Dict[str, Any] = {}
        self.zone_role_assignments: Dict[UUID, List[Tuple['Role', float]]] = {}

    def assign_role(self, zone: Zone, role: Role, weight: float = 1.0):
        if role.zone != zone:
            raise ValueError("Role must belong to the zone")
        if zone.id not in self.zone_role_assignments:
            self.zone_role_assignments[zone.id] = []
        self.zone_role_assignments[zone.id].append((role, weight))

    def __repr__(self):
        return f"User(username='{self.username}')"

class Application:
    def __init__(self, name: str, owning_zone: Optional[Zone] = None):
        self.id: UUID = uuid4()
        self.name: str = name
        self.owning_zone: Optional[Zone] = owning_zone
        self.operations: List['Operation'] = []

    def add_operation(self, name: str, method: str = None) -> 'Operation':
        op = Operation(name, self, method)
        self.operations.append(op)
        return op

    def __repr__(self):
        return f"Application(name='{self.name}')"

class Operation:
    def __init__(self, name: str, app: Application, method: str = None):
        self.id: UUID = uuid4()
        self.name: str = name
        self.app: Application = app
        self.method: str = method

    def __repr__(self):
        return f"Operation(name='{self.name}', app='{self.app.name}')"

class GammaMapping:
    def __init__(self, child_zone: Zone, child_role: Role,
                 parent_zone: Zone, parent_role: Role,
                 weight: float = 1.0, priority: int = 0):
        self.child_zone = child_zone
        self.child_role = child_role
        self.parent_zone = parent_zone
        self.parent_role = parent_role
        self.weight = weight
        self.priority = priority

    def __repr__(self):
        return f"GammaMapping({self.child_zone.name}.{self.child_role.name} -> {self.parent_zone.name}.{self.parent_role.name}, w={self.weight})"

class System:
    def __init__(self):
        self.zones: Set[Zone] = set()
        self.roles: Set[Role] = set()
        self.users: Set[User] = set()
        self.applications: Set[Application] = set()
        self.operations: Set[Operation] = set()
        self.gamma_mappings: List[GammaMapping] = []
        self.root_zone: Optional[Zone] = None

    def add_zone(self, zone: Zone):
        self.zones.add(zone)
        if zone.parent is None and self.root_zone is None:
            self.root_zone = zone

    def add_role(self, role: Role):
        self.roles.add(role)

    def add_user(self, user: User):
        self.users.add(user)

    def add_application(self, app: Application):
        self.applications.add(app)
        self.operations.update(app.operations)

    def add_gamma_mapping(self, mapping: GammaMapping):
        self.gamma_mappings.append(mapping)

    def get_zone(self, zone_id: UUID) -> Optional[Zone]:
        for z in self.zones:
            if z.id == zone_id:
                return z
        return None

    def get_role(self, role_id: UUID) -> Optional[Role]:
        for r in self.roles:
            if r.id == role_id:
                return r
        return None
