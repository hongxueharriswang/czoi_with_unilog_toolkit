"""
National Healthcare System (NHS) - CZOI Implementation
Demonstrates a three‑level zone hierarchy, clinical roles, gamma mappings,
identity/trigger/access constraints, neural sepsis predictor, and three simulations.
"""

import asyncio
import random
import datetime
import numpy as np
from uuid import uuid4
from czoi.core import System, Zone, Role, User, Application, Operation, GammaMapping
from czoi.permission import SimpleEngine
from czoi.constraint import Constraint, ConstraintType, ConstraintManager
from czoi.neural import NeuralComponent, AnomalyDetector
from czoi.daemons import Daemon, SecurityDaemon, ComplianceDaemon
from czoi.simulation import SimulationEngine
from czoi.embedding import EmbeddingService, InMemoryVectorStore
from czoi.unilog import UniLangParser, InferenceEngine, CZOIModelAdapter

# ----------------------------------------------------------------------
# Custom Neural Component: Sepsis Predictor (simplified LSTM)
# ----------------------------------------------------------------------
class LSTMPredictor(NeuralComponent):
    def __init__(self, input_size=50, hidden_size=128, output_size=1):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.trained = False
        # In real implementation, would use PyTorch; here we mock
    def train(self, data):
        self.trained = True
    def predict(self, input):
        # Return a random risk score between 0 and 1
        return float(np.random.rand(1))
    def save(self, path):
        pass
    @classmethod
    def load(cls, path):
        return cls()

# ----------------------------------------------------------------------
# Main System Class
# ----------------------------------------------------------------------
class NationalHealthSystem:
    def __init__(self):
        self.system = System()
        self.root = Zone("NHS_Root")
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
        self.embedding_service = EmbeddingService(InMemoryVectorStore())
        self.parser = UniLangParser()
        self.logic_engine = InferenceEngine.get_instance()

    # ------------------------------------------------------------------
    # Zone Hierarchy
    # ------------------------------------------------------------------
    def _build_hierarchy(self):
        regions = ["North", "South", "East", "West", "Central"]
        self.regions = {}
        for reg in regions:
            region = Zone(f"{reg}_Region", parent=self.root)
            self.system.add_zone(region)
            self.regions[reg] = region
            # Teaching hospitals (3 per region)
            for i in range(3):
                hosp = Zone(f"{reg}_TeachingHospital_{i+1}", parent=region)
                self.system.add_zone(hosp)
            # Primary Care Networks (2 per region)
            for i in range(2):
                pcn = Zone(f"{reg}_PCN_{i+1}", parent=region)
                self.system.add_zone(pcn)
        # National specialized agencies
        agencies = ["BloodService", "DiseaseControl", "HealthRecords"]
        for ag in agencies:
            agency = Zone(f"National_{ag}", parent=self.root)
            self.system.add_zone(agency)

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    def _create_roles(self):
        self.attending = Role("AttendingPhysician", zone=self.root)
        self.resident = Role("ResidentPhysician", zone=self.root)
        self.nurse = Role("RegisteredNurse", zone=self.root)
        self.pharmacist = Role("Pharmacist", zone=self.root)
        self.admin = Role("HospitalAdministrator", zone=self.root)
        self.quality = Role("QualityOfficer", zone=self.root)
        for r in [self.attending, self.resident, self.nurse, self.pharmacist, self.admin, self.quality]:
            self.system.add_role(r)

    # ------------------------------------------------------------------
    # Applications and Operations
    # ------------------------------------------------------------------
    def _create_applications(self):
        # Electronic Health Record
        ehr = Application("EHR", owning_zone=self.root)
        self.view_patient = ehr.add_operation("view_patient", "GET")
        self.order_test = ehr.add_operation("order_test", "POST")
        self.prescribe_med = ehr.add_operation("prescribe_med", "POST")
        self.dispense_med = ehr.add_operation("dispense_med", "POST")
        self.system.add_application(ehr)

        # CPOE
        cpoe = Application("CPOE", owning_zone=self.root)
        self.cpoe_order = cpoe.add_operation("cpoe_order", "POST")
        self.system.add_application(cpoe)

        # Pharmacy System
        pharm = Application("Pharmacy", owning_zone=self.root)
        self.pharm_dispense = pharm.add_operation("pharm_dispense", "POST")
        self.system.add_application(pharm)

        # Grant base permissions
        self.attending.grant_permission(self.view_patient)
        self.attending.grant_permission(self.order_test)
        self.attending.grant_permission(self.prescribe_med)
        self.resident.grant_permission(self.view_patient)
        self.nurse.grant_permission(self.view_patient)
        self.pharmacist.grant_permission(self.view_patient)
        self.pharmacist.grant_permission(self.dispense_med)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def _create_users(self):
        alice = User("alice", "alice@nhs.uk")
        alice.assign_role(self.root, self.attending, weight=1.0)
        bob = User("bob", "bob@nhs.uk")
        bob.assign_role(self.root, self.nurse, weight=1.0)
        charlie = User("charlie", "charlie@nhs.uk")
        charlie.assign_role(self.root, self.admin, weight=1.0)
        diana = User("diana", "diana@nhs.uk")
        diana.assign_role(self.root, self.pharmacist, weight=1.0)
        for u in [alice, bob, charlie, diana]:
            self.system.add_user(u)

    # ------------------------------------------------------------------
    # Constraints (with UniLang)
    # ------------------------------------------------------------------
    def _create_constraints(self):
        self.constraint_manager = ConstraintManager()

        # Identity: Zone containment (UniLang)
        zone_containment = Constraint(
            name="ZoneContainment",
            type=ConstraintType.IDENTITY,
            target={"zones": "all"},
            condition="G (forall u (inZone(u,z) -> inZone(u,parent(z))))"
        )
        self.constraint_manager.add(zone_containment)

        # Trigger: Critical lab alert (simulated)
        trigger_alert = Constraint(
            name="CriticalLabAlert",
            type=ConstraintType.TRIGGER,
            target={"event": "lab_result_posted"},
            condition="lab_result_critical == True"
        )
        self.constraint_manager.add(trigger_alert)

        # Access: Separation of duty (prescribe/dispense) – UniLang
        sod = Constraint(
            name="OrderDispenseSoD",
            type=ConstraintType.ACCESS,
            target={"roles": ["AttendingPhysician", "Pharmacist"]},
            condition="forall u, m . not (prescribe(u,m) and dispense(u,m))"
        )
        self.constraint_manager.add(sod)

    # ------------------------------------------------------------------
    # Gamma Mappings
    # ------------------------------------------------------------------
    def _create_gamma_mappings(self):
        for region in self.regions.values():
            teaching = [z for z in region.children if "TeachingHospital" in z.name]
            pcns = [z for z in region.children if "PCN" in z.name]
            for hosp in teaching:
                for pcn in pcns:
                    gm = GammaMapping(
                        child_zone=hosp,
                        child_role=self.attending,
                        parent_zone=pcn,
                        parent_role=self.attending,
                        weight=0.8,
                        priority=1
                    )
                    self.system.add_gamma_mapping(gm)

    # ------------------------------------------------------------------
    # Neural Components
    # ------------------------------------------------------------------
    def _create_neural_components(self):
        self.sepsis_detector = LSTMPredictor(input_size=50, hidden_size=128, output_size=1)
        # Train with dummy data (would use real EHR in production)
        dummy_data = np.random.randn(1000, 50)
        self.sepsis_detector.train(dummy_data)

        self.anomaly_detector = AnomalyDetector(contamination=0.05)
        dummy_logs = np.random.randn(500, 10)
        self.anomaly_detector.train(dummy_logs)

    # ------------------------------------------------------------------
    # Daemons
    # ------------------------------------------------------------------
    def _create_daemons(self):
        # Security daemon using anomaly detector
        class NHSecurityDaemon(SecurityDaemon):
            async def check(self):
                # Simplified: check recent logs and block if anomalous
                logs = self.storage.get_recent_logs(limit=50)
                actions = []
                for log in logs:
                    # Extract features (mock)
                    features = np.random.randn(10)
                    score = self.anomaly_detector.predict(features)
                    if score > self.threshold:
                        actions.append(f"BLOCK:{log['user_id']}")
                return actions

        self.security_daemon = NHSecurityDaemon(
            storage=None,
            permission_engine=self.permission_engine,
            threshold=0.9,
            interval=2.0
        )

        # Compliance daemon (dummy)
        self.compliance_daemon = ComplianceDaemon(storage=None, interval=10.0)

        # Clinical safety daemon using sepsis detector
        class ClinicalSafetyDaemon(Daemon):
            def __init__(self, detector, interval=1.0):
                super().__init__("clinical_safety", interval)
                self.detector = detector
            async def check(self):
                # Monitor ICU patients (mock)
                alerts = []
                for _ in range(5):
                    risk = self.detector.predict(np.random.randn(50))
                    if risk > 0.7:
                        alerts.append("SEPSIS_ALERT")
                return alerts

        self.clinical_daemon = ClinicalSafetyDaemon(self.sepsis_detector, interval=1.0)

    # ------------------------------------------------------------------
    # Simulations
    # ------------------------------------------------------------------
    def sim_normal_operations(self, steps=100):
        """Normal hospital operations: random access attempts."""
        class NHSNormalSim(SimulationEngine):
            def step(self, current_time):
                users = list(self.system.users)
                ops = list(self.system.operations)
                if users and ops:
                    u = random.choice(users)
                    op = random.choice(ops)
                    zone = random.choice(list(self.system.zones))
                    context = {"time": current_time, "lab_result_critical": False}
                    allowed = self.permission_engine.decide(u, op, zone, context)
                    self.logs.append({
                        "time": current_time.isoformat(),
                        "user": u.username,
                        "operation": op.name,
                        "zone": zone.name,
                        "allowed": allowed
                    })
        sim = NHSNormalSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_flu_surge(self, steps=100):
        """Flu season surge: higher volume, temporary role extensions."""
        class NHSSurgeSim(SimulationEngine):
            def step(self, current_time):
                for _ in range(random.randint(2,5)):
                    u = random.choice(list(self.system.users))
                    op = random.choice(list(self.system.operations))
                    zone = random.choice(list(self.system.zones))
                    context = {"time": current_time}
                    allowed = self.permission_engine.decide(u, op, zone, context)
                    self.logs.append({
                        "time": current_time.isoformat(),
                        "user": u.username,
                        "operation": op.name,
                        "zone": zone.name,
                        "allowed": allowed,
                        "surge": True
                    })
        sim = NHSSurgeSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_insider_threat(self, steps=100):
        """Insider threat: anomalous access pattern."""
        class NHSInsiderSim(SimulationEngine):
            def step(self, current_time):
                # Inject anomalous behaviour at certain times
                if random.random() < 0.1:
                    # Bob (nurse) tries to access many records
                    bob = next(u for u in self.system.users if u.username == "bob")
                    for _ in range(20):
                        op = next(o for o in self.system.operations if o.name == "view_patient")
                        zone = random.choice(list(self.system.zones))
                        context = {"time": current_time}
                        allowed = self.permission_engine.decide(bob, op, zone, context)
                        self.logs.append({
                            "time": current_time.isoformat(),
                            "user": bob.username,
                            "operation": op.name,
                            "zone": zone.name,
                            "allowed": allowed,
                            "anomalous": True
                        })
                else:
                    # normal
                    u = random.choice(list(self.system.users))
                    op = random.choice(list(self.system.operations))
                    zone = random.choice(list(self.system.zones))
                    context = {"time": current_time}
                    allowed = self.permission_engine.decide(u, op, zone, context)
                    self.logs.append({
                        "time": current_time.isoformat(),
                        "user": u.username,
                        "operation": op.name,
                        "zone": zone.name,
                        "allowed": allowed
                    })
        sim = NHSInsiderSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    # ------------------------------------------------------------------
    # Run all simulations
    # ------------------------------------------------------------------
    def run_all_simulations(self):
        print("="*50)
        print("National Healthcare System - Simulations")
        print("="*50)
        print("Normal operations:")
        res1 = self.sim_normal_operations(50)
        print(f"  Total requests: {res1['total_requests']}, Allowed: {res1['allowed']}, Denied: {res1['denied']}, Allow rate: {res1['allow_rate']:.2%}")
        print("Flu surge:")
        res2 = self.sim_flu_surge(50)
        print(f"  Total requests: {res2['total_requests']}, Allowed: {res2['allowed']}, Denied: {res2['denied']}, Allow rate: {res2['allow_rate']:.2%}")
        print("Insider threat:")
        res3 = self.sim_insider_threat(50)
        print(f"  Total requests: {res3['total_requests']}, Allowed: {res3['allowed']}, Denied: {res3['denied']}, Allow rate: {res3['allow_rate']:.2%}")

if __name__ == "__main__":
    nhs = NationalHealthSystem()
    nhs.run_all_simulations()