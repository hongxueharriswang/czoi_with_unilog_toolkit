
"""
Simulation of student registration with grade viewing restrictions and advising alerts.
"""

import random
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Application, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

# Setup
system = System()
uni = Zone("University")
eng = Zone("Engineering", parent=uni)

student = Role("Student", eng)
prof = Role("Professor", eng)
advisor = Role("Advisor", eng)

view_grade = Operation("view_grade", app=None)
enter_grade = Operation("enter_grade", app=None)
student.grant_permission(view_grade)
prof.grant_permission(enter_grade)
advisor.grant_permission(view_grade)

alice = User("alice", zone_role_assignments={eng.id: [(student, 1.0)]})
bob = User("bob", zone_role_assignments={eng.id: [(prof, 1.0)]})
charlie = User("charlie", zone_role_assignments={eng.id: [(advisor, 1.0)]})
system.add_user(alice)
system.add_user(bob)
system.add_user(charlie)

engine = SimpleEngine(system)

class UniversitySimulation(SimulationEngine):
    def step(self):
        # Grade entry by professor
        if random.random() < 0.01:
            grade = random.choice(["A","B","C","D","F"])
            self.log_event("grade_entered", {"student": "alice", "grade": grade})

        # Student tries to view grade
        if engine.decide(alice, view_grade, eng):
            self.log_event("grade_viewed", {"student": "alice"})
        else:
            self.log_event("grade_view_denied", {})

        # Advisor checks at‑risk (simulated)
        if random.random() < 0.05:
            self.log_event("advisor_alert", {"student": "alice", "risk": "high"})

sim = UniversitySimulation(system, engine)
sim.run(duration=timedelta(hours=12))
print(sim.analyze())