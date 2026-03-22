"""
Simulation of a hospital triage system with a sepsis predictor daemon.
"""

import random
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Application, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

# Setup CZOA system
system = System()
root = Zone("Hospital")
er = Zone("EmergencyRoom", parent=root)
icu = Zone("ICU", parent=root)

# Roles
nurse = Role("Nurse", er)
doctor = Role("Attending", er)
icu_nurse = Role("ICUNurse", icu)
icu_doctor = Role("ICUDoctor", icu)

# Assign base permissions
view_patient = Operation("view_patient", app=None)
admit = Operation("admit", app=None)
nurse.grant_permission(view_patient)
doctor.grant_permission(view_patient)
doctor.grant_permission(admit)

# Users
alice = User("alice", zone_role_assignments={er.id: [(nurse, 1.0)]})
bob = User("bob", zone_role_assignments={er.id: [(doctor, 1.0)]})
system.add_user(alice)
system.add_user(bob)

engine = SimpleEngine(system)

# Simulation
class HospitalSimulation(SimulationEngine):
    def step(self):
        # Simulate a new patient every 5 minutes on average
        if random.random() < 1/300:   # 5 minutes = 300 seconds
            patient = f"P{random.randint(1000,9999)}"
            self.log_event("patient_arrival", {"patient": patient})

            # Nurse triage
            if engine.decide(alice, view_patient, er):
                self.log_event("triage", {"patient": patient, "role": "nurse"})

                # Simulate sepsis risk (0.1 probability)
                if random.random() < 0.1:
                    self.log_event("sepsis_alert", {"patient": patient})

                    # Doctor can admit to ICU
                    if engine.decide(bob, admit, er):
                        self.log_event("admit_to_icu", {"patient": patient})
                    else:
                        self.log_event("admit_denied", {"patient": patient})
            else:
                self.log_event("triage_denied", {"patient": patient})

# Run
sim = HospitalSimulation(system, engine, start_time=datetime(2026,1,1,8,0,0))
sim.run(duration=timedelta(hours=24))
print(sim.analyze())