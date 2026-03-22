"""
Smart City Traffic Management - CZOI Implementation
Demonstrates traffic control zones, incident response, congestion prediction,
and three simulations (normal, accident, signal failure).
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
# Custom Neural: Congestion Predictor (mock)
# ----------------------------------------------------------------------
class CongestionPredictor(NeuralComponent):
    def __init__(self):
        self.trained = False
    def train(self, data):
        self.trained = True
    def predict(self, input):
        # return congestion probability
        return float(np.random.rand(1))
    def save(self, path): pass
    @classmethod
    def load(cls, path): return cls()

# ----------------------------------------------------------------------
class TrafficManagementSystem:
    def __init__(self):
        self.system = System()
        self.root = Zone("City")
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

    # ------------------------------------------------------------------
    def _build_hierarchy(self):
        self.control = Zone("TrafficControlCenter", parent=self.root)
        self.signals = Zone("SignalSystems", parent=self.root)
        self.sensors = Zone("Sensors", parent=self.root)
        self.vms = Zone("VariableMessageSigns", parent=self.root)
        self.incidents = Zone("IncidentManagement", parent=self.root)
        self.engineering = Zone("TrafficEngineering", parent=self.root)
        for z in [self.control, self.signals, self.sensors, self.vms, self.incidents, self.engineering]:
            self.system.add_zone(z)

    def _create_roles(self):
        self.op = Role("TrafficOperator", zone=self.control)
        self.commander = Role("IncidentCommander", zone=self.incidents)
        self.engineer = Role("TrafficEngineer", zone=self.engineering)
        for r in [self.op, self.commander, self.engineer]:
            self.system.add_role(r)

    def _create_applications(self):
        # ATMS
        atms = Application("ATMS", owning_zone=self.control)
        self.view_cameras = atms.add_operation("view_cameras", "GET")
        self.adjust_timing = atms.add_operation("adjust_timing", "POST")
        self.system.add_application(atms)

        # VMS Control
        vms_app = Application("VMSControl", owning_zone=self.vms)
        self.post_message = vms_app.add_operation("post_message", "POST")
        self.system.add_application(vms_app)

        # Incident system
        inc_app = Application("IncidentSystem", owning_zone=self.incidents)
        self.declare_incident = inc_app.add_operation("declare_incident", "POST")
        self.system.add_application(inc_app)

        # Permissions
        self.op.grant_permission(self.view_cameras)
        self.commander.grant_permission(self.adjust_timing)
        self.commander.grant_permission(self.post_message)
        self.commander.grant_permission(self.declare_incident)
        self.engineer.grant_permission(self.adjust_timing)

    def _create_users(self):
        users = [("alice", "TrafficOperator"), ("bob", "IncidentCommander"), ("charlie", "TrafficEngineer")]
        for uname, rname in users:
            u = User(uname, f"{uname}@city.gov")
            role = next(r for r in self.system.roles if r.name == rname)
            u.assign_role(self.root, role, weight=1.0)
            self.system.add_user(u)

    def _create_constraints(self):
        self.constraint_manager = ConstraintManager()

        # Identity: signal coordination (simplified)
        coord = Constraint(
            "SignalCoordination",
            ConstraintType.IDENTITY,
            {"zones": ["SignalSystems"]},
            "G (forall i,j (coordinated(i,j) -> timing_plan(i) == timing_plan(j)))"
        )
        self.constraint_manager.add(coord)

        # Trigger: accident detected -> adjust signals + display message (bounded eventually)
        trigger_acc = Constraint(
            "AccidentResponse",
            ConstraintType.TRIGGER,
            {"event": "accident_detected"},
            "G (accident(L) -> (F_{[0,2]} vms_message(L,'Accident')))"
        )
        self.constraint_manager.add(trigger_acc)

        # Access: emergency override only for commanders
        access_emerg = Constraint(
            "EmergencyOverride",
            ConstraintType.ACCESS,
            {"operations": ["adjust_timing"]},
            "user.role == 'IncidentCommander' or emergency == True"
        )
        self.constraint_manager.add(access_emerg)

    def _create_gamma_mappings(self):
        # Engineer can override signals in emergency (weight 0.9)
        gm = GammaMapping(
            child_zone=self.engineering,
            child_role=self.engineer,
            parent_zone=self.signals,
            parent_role=self.engineer,
            weight=0.9,
            priority=1
        )
        self.system.add_gamma_mapping(gm)

    def _create_neural_components(self):
        self.congestion_predictor = CongestionPredictor()
        dummy = np.random.randn(100, 8)
        self.congestion_predictor.train(dummy)

    def _create_daemons(self):
        class CongestionDaemon(Daemon):
            def __init__(self, predictor, interval=1.0):
                super().__init__("congestion", interval)
                self.predictor = predictor
            async def check(self):
                # Predict congestion
                pred = self.predictor.predict(np.random.randn(8))
                if pred > 0.8:
                    return ["ADJUST_TIMING"]
                return []
        self.congestion_daemon = CongestionDaemon(self.congestion_predictor, interval=1.0)

        class IncidentDetectorDaemon(Daemon):
            async def check(self):
                # Simulate accident detection
                if random.random() < 0.05:
                    return ["ACCIDENT_DETECTED"]
                return []
        self.incident_daemon = IncidentDetectorDaemon(interval=1.0)

        class SignalHealthDaemon(Daemon):
            async def check(self):
                # Simulate signal failure
                if random.random() < 0.02:
                    return ["SIGNAL_FAILURE"]
                return []
        self.signal_health = SignalHealthDaemon(interval=1.0)

    # Simulations
    def sim_normal_traffic(self, steps=100):
        class NormalTrafficSim(SimulationEngine):
            def step(self, current_time):
                u = random.choice(list(self.system.users))
                op = random.choice([o for o in self.system.operations if o.name == "view_cameras"])
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
        sim = NormalTrafficSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_accident(self, steps=100):
        class AccidentSim(SimulationEngine):
            def step(self, current_time):
                # Simulate accident at time 30s
                if 29 <= current_time.second <= 31:
                    commander = next(u for u in self.system.users if u.username == "bob")
                    op_adjust = next(o for o in self.system.operations if o.name == "adjust_timing")
                    op_vms = next(o for o in self.system.operations if o.name == "post_message")
                    zone = self.system.get_zone_by_name("IncidentManagement")  # need helper
                    context = {"emergency": True, "time": current_time}
                    allowed1 = self.permission_engine.decide(commander, op_adjust, zone, context)
                    allowed2 = self.permission_engine.decide(commander, op_vms, zone, context)
                    self.logs.append({"time": current_time.isoformat(), "user": commander.username, "operation": op_adjust.name, "allowed": allowed1, "incident": True})
                    self.logs.append({"time": current_time.isoformat(), "user": commander.username, "operation": op_vms.name, "allowed": allowed2, "incident": True})
                else:
                    # normal
                    u = random.choice(list(self.system.users))
                    op = random.choice([o for o in self.system.operations if o.name == "view_cameras"])
                    zone = random.choice(list(self.system.zones))
                    context = {"time": current_time}
                    allowed = self.permission_engine.decide(u, op, zone, context)
                    self.logs.append({"time": current_time.isoformat(), "user": u.username, "operation": op.name, "zone": zone.name, "allowed": allowed})
        sim = AccidentSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_signal_failure(self, steps=100):
        class FailureSim(SimulationEngine):
            def step(self, current_time):
                if random.random() < 0.03:
                    self.logs.append({"time": current_time.isoformat(), "event": "SIGNAL_FAILURE", "zone": "SignalSystems"})
        sim = FailureSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def run_all_simulations(self):
        print("="*50)
        print("Smart City Traffic Management - Simulations")
        print("="*50)
        print("Normal traffic:")
        res1 = self.sim_normal_traffic(50)
        print(f"  Total: {res1['total_requests']}, Allowed: {res1['allowed']}, Denied: {res1['denied']}, Allow rate: {res1['allow_rate']:.2%}")
        print("Accident scenario:")
        res2 = self.sim_accident(50)
        print(f"  Total: {res2['total_requests']}, Allowed: {res2['allowed']}, Denied: {res2['denied']}, Allow rate: {res2['allow_rate']:.2%}")
        print("Signal failure:")
        res3 = self.sim_signal_failure(50)
        print(f"  Total events: {len(res3)}")

if __name__ == "__main__":
    traffic = TrafficManagementSystem()
    traffic.run_all_simulations()