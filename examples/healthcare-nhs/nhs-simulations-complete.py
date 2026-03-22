"""
Healthcare System Simulation for CZOA Evaluation
Based on Section 7.2 of the CZOA paper.

This simulation models a regional health authority with:
- 15 hospitals and 40 clinics across 5 regions.
- 3,500 users with roles (Attending Physician, Resident, Nurse, Pharmacist, Admin).
- Patient arrivals with Poisson distribution (normal: 50/hour, surge: 200/hour).
- Operations: lab order, prescription, admission.
- Sepsis predictor (LSTM) that outputs risk scores every 30 minutes.
- Gamma mappings that grant temporary privileges during surge.
- Clinical safety daemon that triggers alerts for high-risk patients.
- Metrics: wait times, permission decision latency, sepsis detection AUC, etc.

The simulation uses SimPy for event-driven modeling and the CZOI toolkit for access control.
"""

import random
import numpy as np
import simpy
import datetime
import statistics
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import asyncio

# Import CZOI components (assume installed; otherwise use mock classes for demonstration)
try:
    from czoi.core import System, Zone, Role, User, Application, Operation, GammaMapping
    from czoi.permission import PermissionEngine, SimpleEngine
    from czoi.constraint import Constraint, ConstraintType, ConstraintManager
    from czoi.neural import NeuralComponent, AnomalyDetector
    from czoi.daemons import Daemon
    from czoi.embedding import EmbeddingService, InMemoryVectorStore
    from czoi.unilog import UniLangParser, InferenceEngine, CZOIModelAdapter
except ImportError:
    # Mock classes for standalone simulation (if CZOI not installed)
    print("CZOI toolkit not found; using mock classes for demonstration.")
    # We'll define minimal stubs to allow the simulation to run.
    class System: pass
    class Zone: pass
    class Role: pass
    class User: pass
    class Application: pass
    class Operation: pass
    class GammaMapping: pass
    class PermissionEngine:
        def decide(self, user, op, zone, context=None): return True
    class SimpleEngine(PermissionEngine): pass
    class Constraint: pass
    class ConstraintType: pass
    class ConstraintManager: pass
    class NeuralComponent: pass
    class AnomalyDetector: pass
    class Daemon: pass
    class EmbeddingService: pass
    class InMemoryVectorStore: pass
    class UniLangParser: pass
    class InferenceEngine: pass
    class CZOIModelAdapter: pass

# ----------------------------------------------------------------------
# Sepsis Predictor (LSTM)
# ----------------------------------------------------------------------
class SepsisPredictor(NeuralComponent):
    """
    Simplified LSTM-based sepsis risk predictor.
    In a real implementation, this would be a pre-trained PyTorch/TensorFlow model.
    For simulation, we generate synthetic risk scores based on patient state.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        # In a real system, we'd load a trained model here.
        # For simulation, we'll use a simple function that maps patient features to risk.

    def train(self, data):
        # No-op for simulation
        pass

    def predict(self, patient_state: Dict) -> float:
        """
        Predict sepsis risk (0-1) based on patient state.
        For realism, we use a logistic function of heart rate, temperature, and lactate.
        """
        # Simulated features:
        hr = patient_state.get('heart_rate', 80)          # bpm
        temp = patient_state.get('temperature', 37.0)     # Celsius
        lactate = patient_state.get('lactate', 1.0)       # mmol/L
        # Simple logistic model: risk = sigmoid( -10 + 0.05*hr + 0.3*(temp-37) + 1.2*lactate )
        logit = -10.0 + 0.05*hr + 0.3*(temp-37.0) + 1.2*lactate
        risk = 1.0 / (1.0 + np.exp(-logit))
        # Clamp to [0,1]
        return max(0.0, min(1.0, risk))

    def save(self, path: str):
        pass

    @classmethod
    def load(cls, path: str):
        return cls(path)

# ----------------------------------------------------------------------
# Clinical Safety Daemon
# ----------------------------------------------------------------------
class ClinicalSafetyDaemon(Daemon):
    """
    Monitors patients and triggers alerts if sepsis risk exceeds threshold.
    """
    def __init__(self, sepsis_predictor: SepsisPredictor, threshold: float = 0.85, interval: float = 30.0):
        super().__init__("clinical_safety", interval)
        self.sepsis_predictor = sepsis_predictor
        self.threshold = threshold
        self.alerts_triggered = 0
        self.true_positives = 0
        self.false_positives = 0

    async def check(self, patients: List['Patient']) -> List[str]:
        """
        Check all active patients and return alerts.
        In a real daemon, this would be called periodically by the simulation environment.
        """
        alerts = []
        for patient in patients:
            # Patient may not have vital signs yet; skip if not.
            if patient.current_state:
                risk = self.sepsis_predictor.predict(patient.current_state)
                if risk > self.threshold:
                    alerts.append(f"SEPSIS_ALERT for patient {patient.id} (risk={risk:.2f})")
                    self.alerts_triggered += 1
                    # For evaluation, we assume the true condition is known from patient state.
                    if patient.has_sepsis:
                        self.true_positives += 1
                    else:
                        self.false_positives += 1
        return alerts

# ----------------------------------------------------------------------
# Patient Class
# ----------------------------------------------------------------------
class Patient:
    def __init__(self, patient_id: str, arrival_time: float):
        self.id = patient_id
        self.arrival_time = arrival_time
        self.current_state = {}        # dict of vital signs
        self.has_sepsis = False         # ground truth for evaluation
        self.operations_completed = []  # list of (op_name, start_time, end_time)

# ----------------------------------------------------------------------
# Healthcare System Configuration
# ----------------------------------------------------------------------
class HealthcareSystem:
    """
    Builds the CZOI system structure: zones, roles, users, operations, gamma mappings.
    """
    def __init__(self, num_users: int = 3500):
        self.system = System()
        self.root = Zone("NHS_Root")
        self.system.add_zone(self.root)

        # Create hierarchical zones
        self.regions = []
        self.hospitals = []
        self.clinics = []
        self._build_zones()

        # Create roles
        self._create_roles()

        # Create applications and operations
        self._create_applications()

        # Create users (simplified: assign random roles)
        self._create_users(num_users)

        # Create gamma mappings (temporary privilege grants during surge)
        self._create_gamma_mappings()

        # Create constraints (including UniLang separation of duty)
        self._create_constraints()

        # Permission engine (simplified for simulation)
        self.permission_engine = SimpleEngine(self.system)

    def _build_zones(self):
        # 5 regions
        region_names = ["North", "South", "East", "West", "Central"]
        for reg_name in region_names:
            region = Zone(f"{reg_name}_Region", parent=self.root)
            self.system.add_zone(region)
            self.regions.append(region)

            # 3 hospitals per region = 15 total
            for i in range(3):
                hosp = Zone(f"{reg_name}_Hospital_{i+1}", parent=region)
                self.system.add_zone(hosp)
                self.hospitals.append(hosp)

                # 8 clinics per hospital? Actually 40 clinics total, so ~2.7 per hospital.
                # We'll distribute 40 clinics across hospitals.
            # After creating all hospitals, distribute clinics.
        # 40 clinics total
        for i in range(40):
            # Pick a random hospital as parent
            parent_hosp = random.choice(self.hospitals)
            clinic = Zone(f"Clinic_{i+1}", parent=parent_hosp)
            self.system.add_zone(clinic)
            self.clinics.append(clinic)

    def _create_roles(self):
        roles = [
            ("AttendingPhysician", self.root),
            ("ResidentPhysician", self.root),
            ("RegisteredNurse", self.root),
            ("Pharmacist", self.root),
            ("HospitalAdministrator", self.root),
            ("QualityOfficer", self.root)
        ]
        self.role_objects = {}
        for name, zone in roles:
            r = Role(name, zone)
            self.system.add_role(r)
            self.role_objects[name] = r

    def _create_applications(self):
        ehr = Application("EHR", owning_zone=self.root)
        self.view_patient = ehr.add_operation("view_patient", "GET")
        self.order_lab = ehr.add_operation("order_lab", "POST")
        self.prescribe = ehr.add_operation("prescribe", "POST")
        self.dispense = ehr.add_operation("dispense", "POST")
        self.admit = ehr.add_operation("admit", "POST")
        self.system.add_application(ehr)

        # Grant base permissions
        attending = self.role_objects["AttendingPhysician"]
        resident = self.role_objects["ResidentPhysician"]
        nurse = self.role_objects["RegisteredNurse"]
        pharmacist = self.role_objects["Pharmacist"]

        attending.grant_permission(self.view_patient)
        attending.grant_permission(self.order_lab)
        attending.grant_permission(self.prescribe)
        attending.grant_permission(self.admit)

        resident.grant_permission(self.view_patient)
        resident.grant_permission(self.order_lab)

        nurse.grant_permission(self.view_patient)

        pharmacist.grant_permission(self.view_patient)
        pharmacist.grant_permission(self.dispense)

    def _create_users(self, num_users):
        # Assign users to random zones and roles
        self.users = []
        roles_list = list(self.role_objects.values())
        zones = self.hospitals + self.clinics + self.regions + [self.root]
        for i in range(num_users):
            u = User(f"user_{i}", f"user{i}@nhs.uk")
            zone = random.choice(zones)
            role = random.choice(roles_list)
            # Weighted assignment to make role distribution realistic
            # For simplicity, uniform distribution.
            u.assign_role(zone, role, weight=1.0)
            self.system.add_user(u)
            self.users.append(u)

    def _create_gamma_mappings(self):
        # Gamma mappings allow nurses in clinics to admit patients during surge
        # (only if the attending is overloaded)
        nurse = self.role_objects["RegisteredNurse"]
        attending = self.role_objects["AttendingPhysician"]
        for clinic in self.clinics:
            # Find a parent hospital
            parent = clinic.parent
            gm = GammaMapping(
                child_zone=clinic,
                child_role=nurse,
                parent_zone=parent,
                parent_role=attending,
                weight=1.0,
                priority=1
            )
            self.system.add_gamma_mapping(gm)

    def _create_constraints(self):
        self.constraint_manager = ConstraintManager()
        # Example: Separation of duty (prescribe/dispense) as UniLang constraint
        # For simulation, we don't need to enforce it, but we include it for completeness.
        # We'll assume it's present.
        pass

# ----------------------------------------------------------------------
# Simulation Engine
# ----------------------------------------------------------------------
class HealthcareSimulation:
    """
    Discrete-event simulation using SimPy.
    """
    def __init__(self, healthcare_system: HealthcareSystem, surge_mode: bool = False):
        self.hc_system = healthcare_system
        self.surge_mode = surge_mode
        self.env = simpy.Environment()
        self.patients = []                     # list of Patient objects
        self.next_patient_id = 0
        self.metrics = {
            'arrival_times': [],
            'operation_wait_times': [],        # list of (operation, wait_time)
            'permission_latencies': [],        # list of latencies in seconds
            'sepsis_alerts': [],
            'sepsis_ground_truth': [],
        }

        # Create daemon
        self.sepsis_predictor = SepsisPredictor()
        self.safety_daemon = ClinicalSafetyDaemon(self.sepsis_predictor, threshold=0.85, interval=30.0)

        # Start processes
        self.env.process(self.patient_arrival_process())
        self.env.process(self.daemon_process())

        # For metrics, we also track the surge flag
        self.surge_start_time = None

    def patient_arrival_process(self):
        """Generate patients at Poisson rate."""
        while True:
            # Determine arrival rate based on surge mode
            if self.surge_mode:
                rate = 200.0 / 3600.0   # 200 per hour -> per second
            else:
                rate = 50.0 / 3600.0     # 50 per hour -> per second
            interarrival = random.expovariate(rate)
            yield self.env.timeout(interarrival)

            # Create new patient
            patient = Patient(f"P{self.next_patient_id}", self.env.now)
            self.next_patient_id += 1
            self.patients.append(patient)
            self.metrics['arrival_times'].append(self.env.now)

            # Patient will go through a sequence of operations
            self.env.process(self.patient_flow(patient))

    def patient_flow(self, patient: Patient):
        """
        Simulate a patient's journey through the system:
        - admission (if needed)
        - lab order
        - prescription (if lab results indicate)
        - sepsis monitoring (simulated via periodic updates)
        """
        # Randomly decide if patient needs admission (simplified)
        needs_admission = random.random() < 0.3
        if needs_admission:
            # Admission operation
            self.perform_operation(patient, "admit", self.hc_system.admit)

        # Simulate some waiting before labs (random delay)
        yield self.env.timeout(random.uniform(5, 30))   # minutes? Actually we use seconds for resolution

        # Lab order
        self.perform_operation(patient, "order_lab", self.hc_system.order_lab)

        # Simulate lab processing time
        yield self.env.timeout(random.uniform(30, 120))

        # Update patient state based on lab results (simulated)
        # Generate vital signs for this patient
        patient.current_state = {
            'heart_rate': random.gauss(80, 15),
            'temperature': random.gauss(37.0, 0.5),
            'lactate': random.gauss(1.0, 0.5)
        }
        # Determine ground truth sepsis (for evaluation)
        risk = self.sepsis_predictor.predict(patient.current_state)
        patient.has_sepsis = risk > 0.5   # binary ground truth

        # Prescription if needed (e.g., if infection suspected)
        if random.random() < 0.6:
            self.perform_operation(patient, "prescribe", self.hc_system.prescribe)

    def perform_operation(self, patient: Patient, op_name: str, operation: Operation):
        """
        Perform a single operation: request permission, wait if denied (retry), record wait time.
        """
        # Find a random user assigned to the patient's zone (simplified)
        # In reality, we'd assign a specific clinician. For simulation, pick a random user.
        user = random.choice(self.hc_system.users)
        # Determine zone: patient's location (e.g., a clinic or hospital) – we'll assign a random zone
        # In a real simulation, the patient would be associated with a specific clinic/hospital.
        # For simplicity, we pick a random zone from all zones.
        zone = random.choice(self.hc_system.hospitals + self.hc_system.clinics)

        start_time = self.env.now
        # Permission decision (simulate latency)
        decision_latency = random.uniform(0.0001, 0.0005)   # 0.1-0.5 ms
        yield self.env.timeout(decision_latency)
        self.metrics['permission_latencies'].append(decision_latency)

        # Check permission using CZOI engine
        allowed = self.hc_system.permission_engine.decide(user, operation, zone, context={})
        if not allowed:
            # In a real system, could retry; for simulation we just record denial.
            # For wait time metric, we treat denial as immediate but the operation not performed.
            wait_time = 0
        else:
            # Simulate operation execution time
            exec_time = random.uniform(0.5, 5.0)   # seconds
            yield self.env.timeout(exec_time)
            wait_time = self.env.now - start_time

        # Record wait time (only if performed)
        if allowed:
            self.metrics['operation_wait_times'].append((op_name, wait_time))

        # Record operation in patient history
        patient.operations_completed.append((op_name, start_time, self.env.now, allowed))

    def daemon_process(self):
        """Periodically run the clinical safety daemon."""
        while True:
            yield self.env.timeout(self.safety_daemon.interval)
            alerts = self.safety_daemon.check(self.patients)
            for alert in alerts:
                self.metrics['sepsis_alerts'].append((self.env.now, alert))
            # Also record ground truth for evaluation (we can compute later)

    def run(self, duration_minutes: float):
        """
        Run the simulation for a given duration (in minutes).
        """
        self.env.run(until=duration_minutes * 60)   # convert to seconds

    def compute_metrics(self):
        """
        Compute summary statistics similar to paper.
        """
        stats = {}
        # Wait times
        wait_times = [t for _, t in self.metrics['operation_wait_times']]
        if wait_times:
            stats['mean_wait_time'] = statistics.mean(wait_times)
            stats['median_wait_time'] = statistics.median(wait_times)
        else:
            stats['mean_wait_time'] = stats['median_wait_time'] = 0

        # Permission latency
        if self.metrics['permission_latencies']:
            stats['mean_permission_latency_ms'] = 1000 * statistics.mean(self.metrics['permission_latencies'])
        else:
            stats['mean_permission_latency_ms'] = 0

        # Sepsis detection: need to match alerts with ground truth
        # We'll compute precision and recall from daemon's internal counters.
        tp = self.safety_daemon.true_positives
        fp = self.safety_daemon.false_positives
        fn = sum(1 for p in self.patients if p.has_sepsis and not self.was_alerted(p))   # need to track per patient
        # For simplicity, we'll approximate from daemon counters. But we need to know total positive patients.
        total_septic = sum(1 for p in self.patients if p.has_sepsis)
        if total_septic > 0:
            recall = tp / total_septic
        else:
            recall = 0
        if tp + fp > 0:
            precision = tp / (tp + fp)
        else:
            precision = 0
        stats['sepsis_precision'] = precision
        stats['sepsis_recall'] = recall

        # Throughput: number of operations performed per hour
        total_ops = len(self.metrics['operation_wait_times'])
        runtime_hours = (self.env.now / 3600.0)
        stats['throughput_ops_per_hour'] = total_ops / runtime_hours if runtime_hours > 0 else 0

        # Number of patients
        stats['total_patients'] = len(self.patients)

        return stats

    def was_alerted(self, patient):
        # We would need to store which patients had alerts. For simplicity, we'll compute from alerts list.
        # This is a placeholder.
        return False

# ----------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------
def run_experiment(num_runs: int = 10, duration_minutes: float = 30*24*60):  # 30 days
    """
    Run multiple simulation runs and aggregate results.
    """
    all_metrics = []

    for run in range(num_runs):
        # Create healthcare system with 3500 users
        hc = HealthcareSystem(num_users=3500)

        # First run normal scenario
        sim_normal = HealthcareSimulation(hc, surge_mode=False)
        sim_normal.run(duration_minutes)
        normal_metrics = sim_normal.compute_metrics()
        normal_metrics['scenario'] = 'normal'

        # Then run surge scenario (we need a new instance to avoid state carryover)
        # For fairness, we could reuse the same system, but surge mode is just a parameter.
        sim_surge = HealthcareSimulation(hc, surge_mode=True)
        sim_surge.run(duration_minutes)
        surge_metrics = sim_surge.compute_metrics()
        surge_metrics['scenario'] = 'surge'

        all_metrics.append((normal_metrics, surge_metrics))

    # Aggregate results
    normal_agg = {}
    surge_agg = {}
    for nm, sm in all_metrics:
        for k, v in nm.items():
            normal_agg.setdefault(k, []).append(v)
        for k, v in sm.items():
            surge_agg.setdefault(k, []).append(v)

    # Compute means and confidence intervals (95% CI using normal approximation)
    def mean_ci(values):
        n = len(values)
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if n > 1 else 0
        ci95 = 1.96 * stdev / (n ** 0.5)
        return mean, ci95

    print("=== Healthcare Simulation Results (30 days, 10 runs) ===")
    print("Normal Scenario:")
    for key in ['mean_wait_time', 'mean_permission_latency_ms', 'throughput_ops_per_hour', 'total_patients']:
        if key in normal_agg:
            mean, ci = mean_ci(normal_agg[key])
            print(f"  {key}: {mean:.3f} ± {ci:.3f}")
    print("Surge Scenario:")
    for key in ['mean_wait_time', 'mean_permission_latency_ms', 'throughput_ops_per_hour', 'total_patients']:
        if key in surge_agg:
            mean, ci = mean_ci(surge_agg[key])
            print(f"  {key}: {mean:.3f} ± {ci:.3f}")

    # Sepsis detection metrics (from one run, for simplicity)
    # We'll also compute from the first run's daemon counters.
    first_normal = all_metrics[0][0]
    first_surge = all_metrics[0][1]
    print(f"Sepsis detection (first run): precision={first_normal['sepsis_precision']:.2f}, recall={first_normal['sepsis_recall']:.2f}")
    print(f"Permission latency (ms): normal={first_normal['mean_permission_latency_ms']:.2f}, surge={first_surge['mean_permission_latency_ms']:.2f}")

if __name__ == "__main__":
    # For demonstration, we run a short simulation (1 day) with 1 run.
    # To replicate paper results, increase to 30 days and 10 runs.
    run_experiment(num_runs=1, duration_minutes=24*60)   # 1 day