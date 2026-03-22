import random
import numpy as np
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

class UniversitySimulation(SimulationEngine):
    def __init__(self, system, permission_engine, use_czoa=True):
        super().__init__(system, permission_engine)
        self.use_czoa = use_czoa
        self.registration_attempts = 0
        self.registration_success = 0
        self.grade_violations = 0

    def step(self):
        # Registration attempts during peak
        if self.current_time.hour in [9,10,11,14,15,16]:
            rate = 1200  # per second
            if random.random() < rate/3600:
                self.registration_attempts += 1
                student = next(u for u in self.system.users if any(r.name == "Student" for r in u.roles))
                if self.permission_engine.decide(student, self.register_op, self.eng_zone):
                    self.registration_success += 1
                    self.log_event("registration_success", {"student": student.id})
                else:
                    self.log_event("registration_failure", {"student": student.id})

        # Grade viewing (FERPA)
        if random.random() < 0.001:
            student = next(u for u in self.system.users if any(r.name == "Student" for r in u.roles))
            # Try to view grade of another student
            if self.permission_engine.decide(student, self.view_grade_op, self.eng_zone, context={"target_student": "other"}):
                self.grade_violations += 1
                self.log_event("ferpa_violation", {})

        # At‑risk prediction (if CZOA)
        if self.use_czoa and random.random() < 0.01:
            self.log_event("advisor_alert", {"student": "alice", "risk": "high"})

    def setup_system(self):
        uni = Zone("University")
        self.eng_zone = Zone("Engineering", parent=uni)
        student = Role("Student", self.eng_zone)
        prof = Role("Professor", self.eng_zone)
        advisor = Role("Advisor", self.eng_zone)

        self.register_op = Operation("register")
        self.view_grade_op = Operation("view_grade")
        student.grant_permission(self.register_op)
        student.grant_permission(self.view_grade_op)  # normally allowed for own grades
        prof.grant_permission(self.view_grade_op)    # professors can view

        # Create users
        for i in range(1000):
            u = User(f"student{i}", zone_role_assignments={self.eng_zone.id: [(student, 1.0)]})
            self.system.add_user(u)
        # Professors and advisors (simplified)

    def run(self, duration, step_delta=timedelta(seconds=1)):
        self.setup_system()
        super().run(duration, step_delta)

    def analyze(self):
        base = super().analyze()
        base["registration_success_rate"] = self.registration_success / max(1, self.registration_attempts)
        base["ferpa_violations"] = self.grade_violations
        return base

def run_university_comparison():
    # Baseline (no FERPA daemon, no advisor alerts)
    system = System()
    perm_engine = SimpleEngine(system)
    sim_baseline = UniversitySimulation(system, perm_engine, use_czoa=False)
    sim_baseline.run(duration=timedelta(days=3))
    base_violations = sim_baseline.analyze()["ferpa_violations"]

    # CZOA
    system = System()
    perm_engine = SimpleEngine(system)
    sim_czoa = UniversitySimulation(system, perm_engine, use_czoa=True)
    sim_czoa.run(duration=timedelta(days=3))
    czoa_violations = sim_czoa.analyze()["ferpa_violations"]

    print(f"Baseline FERPA violations: {base_violations}")
    print(f"CZOA FERPA violations: {czoa_violations}")

if __name__ == "__main__":
    run_university_comparison()