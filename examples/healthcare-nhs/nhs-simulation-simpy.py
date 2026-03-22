"""
Simulation of a regional health authority with 15 hospitals and 40 clinics.
Compares CZOA (with sepsis predictor, gamma mappings, and safety daemon)
against a static RBAC baseline.
"""

from czoi.neural import SepsisPredictor  # pre‑trained LSTM model
from czoi.daemons import ClinicalSafetyDaemon
from czoi.simulation import SimulationEngine
from czoi import System, Zone, Role, User, Application, Operation, GammaMapping, ConstraintSet
import simpy
import numpy as np
import random
# -------------------------------
# Domain Setup
# -------------------------------
def setup_healthcare_system():
    system = System()
    root = Zone("RegionalAuthority", parent=None)
    
    # Create zones (simplified: one hospital, one clinic for demonstration)
    hosp1 = Zone("Hospital1", parent=root)
    clinic1 = Zone("Clinic1", parent=root)
    
    # Roles
    attending = Role("AttendingPhysician", zone=hosp1,
                     base_perms=["prescribe", "admit", "view_lab"])
    resident = Role("Resident", zone=hosp1,
                    base_perms=["prescribe", "view_lab"])
    nurse = Role("Nurse", zone=hosp1,
                 base_perms=["dispense", "record_vitals"])
    nurse_clinic = Role("Nurse", zone=clinic1,
                        base_perms=["dispense", "record_vitals"])
    
    # Intra‑zone hierarchy: attending inherits resident's perms
    attending.add_inherits(resident)
    
    # Gamma mapping: during surge, nurses in clinic1 can admit (via attending)
    gamma = GammaMapping(source_zone=clinic1, source_role=nurse_clinic,
                         target_zone=hosp1, target_role=attending,
                         weight=1.0, priority=1)
    system.add_gamma(gamma)
    
    # Users: generate 3500 users with random roles
    users = []
    for i in range(3500):
        u = User(f"user{i}")
        # assign to a random zone (simplified: 2500 in hospitals, 1000 in clinics)
        zone = hosp1 if random.random() < 0.714 else clinic1
        if zone == hosp1:
            role = random.choice([attending, resident, nurse])
        else:
            role = nurse_clinic
        u.assign_role(role, zone)
        users.append(u)
        system.add_user(u)
    
    # Applications and operations
    ehr = Application("EHR")
    ehr.add_operation(Operation("prescribe", required_perm="prescribe"))
    ehr.add_operation(Operation("admit", required_perm="admit"))
    ehr.add_operation(Operation("dispense", required_perm="dispense"))
    ehr.add_operation(Operation("view_lab", required_perm="view_lab"))
    system.add_application(ehr)
    
    # Constraints (simplified)
    constraints = ConstraintSet()
    constraints.add("sod_prescribe_dispense", lambda u, op, ctx: not (
        op.name == "dispense" and "prescribe" in u.roles_effective
    ))
    system.add_constraints(constraints)
    
    return system, hosp1, clinic1, attending, nurse, nurse_clinic

# -------------------------------
# Simulation Processes
# -------------------------------
class Patient:
    def __init__(self, pid, arrival_time):
        self.pid = pid
        self.arrival_time = arrival_time
        self.triage_time = None
        self.lab_time = None
        self.discharge_time = None

def patient_arrivals(env, system, zone, log):
    """Generate patients and simulate their care process."""
    i = 0
    while True:
        # Interarrival time: normal 1.2 min (50/hour) or surge 0.3 min (200/hour)
        # Surge flag is set externally; for simplicity we use a time‑varying rate.
        if env.now < 5*24*60:  # first 5 days normal, then surge
            iat = np.random.exponential(1.2)
        else:
            iat = np.random.exponential(0.3)
        yield env.timeout(iat)
        i += 1
        patient = Patient(i, env.now)
        env.process(patient_care(env, system, zone, patient, log))

def patient_care(env, system, zone, patient, log):
    # Triage: nurse assigns zone (actually the operation is performed by a nurse)
    # Find a nurse in the zone (simplified: we just check permission)
    nurse_role = next(r for r in system.roles if r.name == "Nurse" and r.zone == zone)
    # Simulate a nurse user
    nurse_user = next(u for u in system.users if nurse_role in u.roles)
    # Check permission
    if system.decide(nurse_user, "record_vitals", zone):
        patient.triage_time = env.now
    else:
        # If permission denied, wait and retry (simplified: wait and retry once)
        yield env.timeout(5)
        if system.decide(nurse_user, "record_vitals", zone):
            patient.triage_time = env.now
        else:
            log.append(("triage_denied", patient.pid))
            return
    
    # Lab order (by attending)
    attending_role = next(r for r in system.roles if r.name == "AttendingPhysician")
    attending_user = next(u for u in system.users if attending_role in u.roles)
    if system.decide(attending_user, "prescribe", zone):
        yield env.timeout(10)  # lab processing time
        patient.lab_time = env.now
    else:
        # Wait for permission elevation (gamma may help)
        yield env.timeout(2)
        if system.decide(attending_user, "prescribe", zone):
            yield env.timeout(10)
            patient.lab_time = env.now
        else:
            log.append(("lab_denied", patient.pid))
            return
    
    # Sepsis check: daemon triggers alert if risk high (handled asynchronously)
    # Here we just simulate the discharge
    yield env.timeout(np.random.exponential(30))  # treatment time
    patient.discharge_time = env.now
    log.append(("discharge", patient.pid, patient.discharge_time - patient.arrival_time))

def safety_daemon_loop(env, daemon, system, zone, log):
    """Periodically run the safety daemon to check sepsis risk."""
    while True:
        # In real simulation, we would collect patient vitals; here we simulate random risk
        risk = np.random.random()
        daemon.check_patient(risk)  # daemon triggers if risk > threshold
        yield env.timeout(30)  # check every 30 minutes

# -------------------------------
# Main Simulation
# -------------------------------
def run_healthcare_simulation(surge=False, use_czoa=True):
    env = simpy.Environment()
    system, hosp1, clinic1, attending, nurse, nurse_clinic = setup_healthcare_system()
    
    log = []  # collect events
    
    # Neural component and daemon
    if use_czoa:
        # Load pre‑trained sepsis predictor (mock)
        sepsis_model = SepsisPredictor.load("sepsis_lstm.pt")
        safety_daemon = ClinicalSafetyDaemon(sepsis_model, threshold=0.85)
        env.process(safety_daemon_loop(env, safety_daemon, system, hosp1, log))
    else:
        # Baseline: no daemon, no gamma mappings (we could disable gamma too)
        # But we already added gamma in setup; we could disable them
        for gamma in system.gamma_mappings:
            gamma.active = False
    
    # Start patient arrivals
    env.process(patient_arrivals(env, system, hosp1, log))
    
    # Run for 30 days (43200 minutes)
    env.run(until=30*24*60)
    
    # Compute metrics
    discharge_times = [entry[2] for entry in log if entry[0] == "discharge"]
    avg_wait = np.mean(discharge_times) if discharge_times else 0
    
    # Count denied accesses
    triage_denied = sum(1 for e in log if e[0] == "triage_denied")
    lab_denied = sum(1 for e in log if e[0] == "lab_denied")
    
    return avg_wait, triage_denied, lab_denied

if __name__ == "__main__":
    # Run baseline (static RBAC)
    baseline_wait, _, _ = run_healthcare_simulation(use_czoa=False)
    print(f"Baseline average wait: {baseline_wait:.2f} minutes")
    
    # Run CZOA
    czoa_wait, _, _ = run_healthcare_simulation(use_czoa=True)
    print(f"CZOA average wait: {czoa_wait:.2f} minutes")
    print(f"Improvement: {(1 - czoa_wait/baseline_wait)*100:.1f}%")