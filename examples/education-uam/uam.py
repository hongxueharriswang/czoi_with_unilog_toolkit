"""
University Academic Management System - CZOI Implementation
Demonstrates colleges, departments, FERPA constraints, student success predictor,
and simulations (registration, grading, probation monitoring).
"""

import asyncio
import random
import datetime
import numpy as np
from czoi.core import System, Zone, Role, User, Application, GammaMapping
from czoi.permission import SimpleEngine
from czoi.constraint import Constraint, ConstraintType, ConstraintManager
from czoi.neural import NeuralComponent
from czoi.daemon import Daemon
from czoi.simulation import SimulationEngine
from czoi.embedding import EmbeddingService, InMemoryVectorStore
from czoi.unilog import UniLangParser, InferenceEngine, CZOIModelAdapter

# ----------------------------------------------------------------------
# Custom Neural: Student Success Predictor (mock)
# ----------------------------------------------------------------------
class StudentSuccessPredictor(NeuralComponent):
    def __init__(self):
        self.trained = False
    def train(self, data):
        self.trained = True
    def predict(self, features):
        # Return risk probability
        return float(np.random.rand(1))
    def save(self, path): pass
    @classmethod
    def load(cls, path): return cls()

# ----------------------------------------------------------------------
class UniversitySystem:
    def __init__(self):
        self.system = System()
        self.root = Zone("University")
        self.system.add_zone(self.root)
        self._build_hierarchy()
        self._create_roles()
        self._create_applications()
        self._create_users()
        self._create_constraints()
        self._create_gamma_mappings()
        self._create_neural_components()
        self._create_daemons()
        self.permission_engine = SimpleEngine(self.system)

    # ------------------------------------------------------------------
    def _build_hierarchy(self):
        # Colleges
        self.eng = Zone("Engineering", parent=self.root)
        self.arts = Zone("Arts", parent=self.root)
        self.business = Zone("Business", parent=self.root)
        for c in [self.eng, self.arts, self.business]:
            self.system.add_zone(c)

        # Departments under Engineering
        self.cs = Zone("ComputerScience", parent=self.eng)
        self.me = Zone("MechanicalEngineering", parent=self.eng)
        self.ee = Zone("ElectricalEngineering", parent=self.eng)
        # Research labs
        self.ai_lab = Zone("AI_Lab", parent=self.eng)
        self.robotics = Zone("RoboticsLab", parent=self.eng)
        # Advising
        self.advising = Zone("Advising", parent=self.root)
        self.registrar = Zone("Registrar", parent=self.root)
        for z in [self.cs, self.me, self.ee, self.ai_lab, self.robotics, self.advising, self.registrar]:
            self.system.add_zone(z)

    def _create_roles(self):
        self.prof = Role("Professor", zone=self.eng)
        self.student = Role("Student", zone=self.eng)
        self.advisor = Role("Advisor", zone=self.advising)
        self.dean = Role("Dean", zone=self.eng)
        self.registrar_role = Role("Registrar", zone=self.registrar)
        for r in [self.prof, self.student, self.advisor, self.dean, self.registrar_role]:
            self.system.add_role(r)
        # Hierarchy
        self.dean.add_senior(self.prof)

    def _create_applications(self):
        # LMS
        lms = Application("LMS", owning_zone=self.root)
        self.view_grades = lms.add_operation("view_grades", "GET")
        self.submit_grade = lms.add_operation("submit_grade", "POST")
        self.system.add_application(lms)

        # SIS
        sis = Application("SIS", owning_zone=self.root)
        self.register = sis.add_operation("register", "POST")
        self.view_transcript = sis.add_operation("view_transcript", "GET")
        self.system.add_application(sis)

        # Advising system
        adv_app = Application("AdvisingSystem", owning_zone=self.advising)
        self.advise = adv_app.add_operation("advise_student", "POST")
        self.system.add_application(adv_app)

        # Permissions
        self.prof.grant_permission(self.submit_grade)
        self.student.grant_permission(self.view_grades)
        self.student.grant_permission(self.view_transcript)
        self.advisor.grant_permission(self.view_grades)
        self.advisor.grant_permission(self.advise)
        self.registrar_role.grant_permission(self.view_transcript)

    def _create_users(self):
        users = [
            ("smith", "Professor"), ("doe", "Student"), ("brown", "Advisor"),
            ("white", "Dean"), ("jones", "Registrar")
        ]
        for uname, rname in users:
            u = User(uname, f"{uname}@univ.edu")
            role = next(r for r in self.system.roles if r.name == rname)
            u.assign_role(self.root, role, weight=1.0)
            self.system.add_user(u)
        # Additional students
        for i in range(10):
            u = User(f"student{i}", f"student{i}@univ.edu")
            u.assign_role(self.root, self.student, weight=1.0)
            self.system.add_user(u)

    def _create_constraints(self):
        self.constraint_manager = ConstraintManager()

        # Identity: FERPA (UniLang)
        ferpa = Constraint(
            "FERPA",
            ConstraintType.IDENTITY,
            {"operations": ["view_grades", "view_transcript"]},
            "G (user = student or user.role in ['Professor','Advisor','Registrar'])"
        )
        self.constraint_manager.add(ferpa)

        # Trigger: GPA < 2.0 → probation
        probation = Constraint(
            "AcademicProbation",
            ConstraintType.TRIGGER,
            {"event": "grade_posted"},
            "gpa < 2.0"
        )
        self.constraint_manager.add(probation)

        # Access: grade entry requires instructor of record
        grade_access = Constraint(
            "GradeEntry",
            ConstraintType.ACCESS,
            {"roles": ["Professor"], "operations": ["submit_grade"]},
            "user == instructor_of_record"
        )
        self.constraint_manager.add(grade_access)

    def _create_gamma_mappings(self):
        # Professor in department can also advise with lower weight
        gm = GammaMapping(
            child_zone=self.cs,
            child_role=self.prof,
            parent_zone=self.advising,
            parent_role=self.advisor,
            weight=0.7,
            priority=1
        )
        self.system.add_gamma_mapping(gm)

    def _create_neural_components(self):
        self.success_predictor = StudentSuccessPredictor()
        dummy = np.random.randn(200, 10)
        self.success_predictor.train(dummy)

    def _create_daemons(self):
        class AcademicProgressDaemon(Daemon):
            async def check(self):
                # Check at‑risk students (mock)
                if random.random() < 0.1:
                    return ["AT_RISK_STUDENT"]
                return []
        self.progress_daemon = AcademicProgressDaemon(interval=5.0)

        class EnrollmentMonitorDaemon(Daemon):
            async def check(self):
                # Monitor course fill rates
                return []
        self.enroll_daemon = EnrollmentMonitorDaemon(interval=5.0)

    # Simulations
    def sim_registration(self, steps=100):
        class RegSim(SimulationEngine):
            def step(self, current_time):
                student = random.choice([u for u in self.system.users if any(r.name=="Student" for r in u.zone_role_assignments[self.root_zone.id])])
                op = self.system.get_operation_by_name("register")  # need helper
                zone = random.choice([z for z in self.system.zones if z.name in ["ComputerScience","MechanicalEngineering","ElectricalEngineering"]])
                has_preq = random.choice([True, False])
                context = {"student": student.username, "has_prerequisite": has_preq}
                allowed = self.permission_engine.decide(student, op, zone, context)
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": student.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "allowed": allowed,
                    "has_prerequisite": has_preq
                })
        sim = RegSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_grading(self, steps=100):
        class GradeSim(SimulationEngine):
            def step(self, current_time):
                prof = next(u for u in self.system.users if u.username == "smith")
                op = self.system.get_operation_by_name("submit_grade")
                zone = random.choice([z for z in self.system.zones if z.name in ["ComputerScience","MechanicalEngineering","ElectricalEngineering"]])
                context = {"instructor_of_record": "smith"}  # always true for smith
                allowed = self.permission_engine.decide(prof, op, zone, context)
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": prof.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "allowed": allowed
                })
        sim = GradeSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_probation_monitoring(self, steps=100):
        class ProbationSim(SimulationEngine):
            def step(self, current_time):
                advisor = next(u for u in self.system.users if u.username == "brown")
                students = [u for u in self.system.users if any(r.name=="Student" for r in u.zone_role_assignments[self.root_zone.id])]
                for s in students:
                    gpa = random.uniform(1.5,4.0)
                    if gpa < 2.0:
                        op = self.system.get_operation_by_name("advise_student")
                        zone = next(z for z in self.system.zones if z.name == "Advising")
                        context = {"student": s.username, "gpa": gpa}
                        allowed = self.permission_engine.decide(advisor, op, zone, context)
                        self.logs.append({
                            "time": current_time.isoformat(),
                            "user": advisor.username,
                            "operation": op.name,
                            "zone": zone.name,
                            "allowed": allowed,
                            "student": s.username,
                            "gpa": gpa,
                            "action": "probation_check"
                        })
        sim = ProbationSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def run_all_simulations(self):
        print("="*50)
        print("University Academic Management - Simulations")
        print("="*50)
        print("Registration:")
        res1 = self.sim_registration(50)
        print(f"  Total: {res1['total_requests']}, Allowed: {res1['allowed']}, Denied: {res1['denied']}, Allow rate: {res1['allow_rate']:.2%}")
        print("Grading:")
        res2 = self.sim_grading(50)
        print(f"  Total: {res2['total_requests']}, Allowed: {res2['allowed']}, Denied: {res2['denied']}, Allow rate: {res2['allow_rate']:.2%}")
        print("Probation monitoring:")
        res3 = self.sim_probation_monitoring(50)
        print(f"  Total events: {len(res3)}")

if __name__ == "__main__":
    uni = UniversitySystem()
    uni.run_all_simulations()