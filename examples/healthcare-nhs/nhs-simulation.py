import random
import numpy as np
from datetime import datetime, timedelta
from scipy import stats

from czoi.core import System, Zone, Role, User, Application, Operation, GammaMapping
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine
from czoi.neural import NeuralComponent
from czoi.daemons import Daemon

# ----- Mock neural components (for demonstration) -----
class MockSepsisPredictor(NeuralComponent):
    def predict(self, patient_data):
        # Simulate risk score between 0 and 1
        return np.random.random()

class MockSafetyDaemon(Daemon):
    def __init__(self, predictor, threshold=0.85):
        super().__init__(name="SafetyDaemon", interval=30)
        self.predictor = predictor
        self.threshold = threshold
    async def check(self):
        # In real simulation, would check current patients
        pass

# ----- Simulation class -----
class HealthcareSimulation(SimulationEngine):
    def __init__(self, system, permission_engine, use_czoa=True, surge=False):
        super().__init__(system, permission_engine)
        self.use_czoa = use_czoa
        self.surge = surge
        self.patient_counter = 0
        self.active_patients = []
        self.sepsis_predictor = MockSepsisPredictor() if use_czoa else None
        self.safety_daemon = MockSafetyDaemon(self.sepsis_predictor) if use_czoa else None
        self.wait_times = []

    def step(self):
        # Simulate patient arrivals: Poisson with rate depending on surge
        if self.surge and self.current_time > datetime(2026,1,1,12,0,0):
            rate = 200  # per hour
        else:
            rate = 50   # per hour
        # Convert rate to probability per second (step_delta = 1 sec)
        arrival_prob = rate / 3600
        if random.random() < arrival_prob:
            self.patient_counter += 1
            pid = self.patient_counter
            arrival_time = self.current_time
            self.active_patients.append((pid, arrival_time))
            self.log_event("patient_arrival", {"pid": pid})

        # Process patients: triage, lab, discharge (simplified)
        for i, (pid, arrival) in enumerate(self.active_patients):
            # Triage by nurse
            nurse = next(u for u in self.system.users if any(r.name == "Nurse" for r in u.roles))
            if self.permission_engine.decide(nurse, self.view_op, self.er_zone):
                # Triage successful
                self.log_event("triage_done", {"pid": pid})
                # Lab order by attending physician (may use gamma mapping if surge)
                attending = next(u for u in self.system.users if any(r.name == "Attending" for r in u.roles))
                allowed = self.permission_engine.decide(attending, self.prescribe_op, self.er_zone)
                if not allowed and self.use_czoa and self.surge:
                    # Gamma mapping may grant temporary permission
                    # For simplicity, we simulate that CZOA grants permission more often
                    allowed = random.random() < 0.95  # high probability during surge
                if allowed:
                    self.log_event("lab_ordered", {"pid": pid})
                    # Simulate treatment time
                    discharge_time = self.current_time + timedelta(minutes=np.random.exponential(30))
                    if discharge_time <= self.current_time + timedelta(seconds=1):
                        # Discharge now
                        self.log_event("discharge", {"pid": pid, "wait": (self.current_time - arrival).total_seconds()/60})
                        self.wait_times.append((self.current_time - arrival).total_seconds()/60)
                        self.active_patients.pop(i)
                        break
                else:
                    self.log_event("lab_denied", {"pid": pid})
            else:
                self.log_event("triage_denied", {"pid": pid})

        # Run safety daemon every 30 steps (30 seconds)
        if self.use_czoa and int(self.current_time.timestamp()) % 30 == 0:
            # Check random patient for sepsis
            if self.active_patients:
                pid, _ = random.choice(self.active_patients)
                risk = self.sepsis_predictor.predict({})
                if risk > 0.85:
                    self.log_event("sepsis_alert", {"pid": pid, "risk": risk})

    def setup_system(self):
        # Define zones
        root = Zone("HealthAuthority")
        self.er_zone = Zone("EmergencyRoom", parent=root)
        # Roles
        nurse = Role("Nurse", self.er_zone)
        attending = Role("Attending", self.er_zone)
        # Base permissions
        self.view_op = Operation("view_patient")
        self.prescribe_op = Operation("prescribe")
        nurse.grant_permission(self.view_op)
        attending.grant_permission(self.view_op)
        attending.grant_permission(self.prescribe_op)
        # Users
        nurse_user = User("nurse1", zone_role_assignments={self.er_zone.id: [(nurse, 1.0)]})
        attending_user = User("doc1", zone_role_assignments={self.er_zone.id: [(attending, 1.0)]})
        self.system.add_user(nurse_user)
        self.system.add_user(attending_user)
        # Gamma mapping (only used if CZOA)
        if self.use_czoa:
            gamma = GammaMapping(self.er_zone, nurse, self.er_zone, attending, weight=0.8)
            self.system.add_gamma_mapping(gamma)

    def run(self, duration, step_delta=timedelta(seconds=1)):
        self.setup_system()
        super().run(duration, step_delta)

    def analyze(self):
        base = super().analyze()
        base["avg_wait_minutes"] = np.mean(self.wait_times) if self.wait_times else 0
        return base

# ----- Run simulation and compare -----
def run_healthcare_comparison():
    # Baseline (static RBAC, no CZOA features)
    system = System()
    perm_engine = SimpleEngine(system)
    sim_baseline = HealthcareSimulation(system, perm_engine, use_czoa=False, surge=True)
    sim_baseline.run(duration=timedelta(hours=48))
    baseline_wait = sim_baseline.analyze()["avg_wait_minutes"]

    # CZOA with adaptation
    system = System()
    perm_engine = SimpleEngine(system)
    sim_czoa = HealthcareSimulation(system, perm_engine, use_czoa=True, surge=True)
    sim_czoa.run(duration=timedelta(hours=48))
    czoa_wait = sim_czoa.analyze()["avg_wait_minutes"]

    improvement = (baseline_wait - czoa_wait) / baseline_wait * 100
    print(f"Baseline avg wait: {baseline_wait:.2f} min")
    print(f"CZOA avg wait: {czoa_wait:.2f} min")
    print(f"Improvement: {improvement:.1f}%")

if __name__ == "__main__":
    run_healthcare_comparison()