"""
Supply Chain Distribution Center - CZOI Implementation
Demonstrates receiving, storage, picking, packing zones, cold chain constraints,
SKU embeddings, and three simulations (normal, peak season, theft detection).
"""

import asyncio
import random
import datetime
import numpy as np
from czoi.core import System, Zone, Role, User, Application, GammaMapping
from czoi.permission import SimpleEngine
from czoi.constraint import Constraint, ConstraintType, ConstraintManager
from czoi.neural import NeuralComponent, AnomalyDetector
from czoi.daemon import Daemon
from czoi.simulation import SimulationEngine
from czoi.embedding import EmbeddingService, InMemoryVectorStore
from czoi.unilog import UniLangParser, InferenceEngine, CZOIModelAdapter

# ----------------------------------------------------------------------
# Custom Neural: Demand Forecaster (mock)
# ----------------------------------------------------------------------
class DemandForecaster(NeuralComponent):
    def __init__(self):
        self.trained = False
    def train(self, data):
        self.trained = True
    def predict(self, input):
        return float(np.random.rand(1))
    def save(self, path): pass
    @classmethod
    def load(cls, path): return cls()

# ----------------------------------------------------------------------
class DistributionCenter:
    def __init__(self):
        self.system = System()
        self.root = Zone("DistributionCenter")
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
        self.receiving = Zone("Receiving", parent=self.root)
        self.storage = Zone("Storage", parent=self.root)
        self.picking = Zone("Picking", parent=self.root)
        self.packing = Zone("Packing", parent=self.root)
        self.shipping = Zone("Shipping", parent=self.root)
        self.returns = Zone("Returns", parent=self.root)
        self.admin = Zone("Administrative", parent=self.root)
        for z in [self.receiving, self.storage, self.picking, self.packing, self.shipping, self.returns, self.admin]:
            self.system.add_zone(z)

    def _create_roles(self):
        self.manager = Role("WarehouseManager", zone=self.admin)
        self.supervisor = Role("Supervisor", zone=self.admin)
        self.picker = Role("Picker", zone=self.picking)
        self.receiver = Role("Receiver", zone=self.receiving)
        self.inv_controller = Role("InventoryController", zone=self.storage)
        for r in [self.manager, self.supervisor, self.picker, self.receiver, self.inv_controller]:
            self.system.add_role(r)
        # Hierarchy
        self.manager.add_senior(self.supervisor)
        self.supervisor.add_senior(self.picker)

    def _create_applications(self):
        # WMS
        wms = Application("WMS", owning_zone=self.root)
        self.receive_op = wms.add_operation("receive_shipment", "POST")
        self.pick_op = wms.add_operation("pick_order", "POST")
        self.cycle_op = wms.add_operation("cycle_count", "POST")
        self.system.add_application(wms)

        # LMS (Labor Management)
        lms = Application("LMS", owning_zone=self.admin)
        self.track_productivity = lms.add_operation("track_productivity", "GET")
        self.system.add_application(lms)

        # Permissions
        self.receiver.grant_permission(self.receive_op)
        self.picker.grant_permission(self.pick_op)
        self.inv_controller.grant_permission(self.cycle_op)
        self.manager.grant_permission(self.track_productivity)

    def _create_users(self):
        users = [
            ("mgr", "WarehouseManager"), ("sup", "Supervisor"),
            ("pick1", "Picker"), ("pick2", "Picker"),
            ("rec1", "Receiver"), ("inv1", "InventoryController")
        ]
        for uname, rname in users:
            u = User(uname, f"{uname}@dc.com")
            role = next(r for r in self.system.roles if r.name == rname)
            u.assign_role(self.root, role, weight=1.0)
            self.system.add_user(u)

    def _create_constraints(self):
        self.constraint_manager = ConstraintManager()

        # Identity: inventory accuracy
        inv_acc = Constraint(
            "InventoryAccuracy",
            ConstraintType.IDENTITY,
            {"zones": ["Storage"]},
            "G (abs(system_qty - physical_qty) <= tolerance)"
        )
        self.constraint_manager.add(inv_acc)

        # Trigger: low stock reorder
        low_stock = Constraint(
            "LowStockReorder",
            ConstraintType.TRIGGER,
            {"event": "cycle_count"},
            "quantity < reorder_point and not already_ordered"
        )
        self.constraint_manager.add(low_stock)

        # Access: forklift requires certification (simplified)
        forklift_access = Constraint(
            "ForkliftCert",
            ConstraintType.ACCESS,
            {"operations": ["receive_shipment", "pick_order"]},
            "certified == True"
        )
        self.constraint_manager.add(forklift_access)

    def _create_gamma_mappings(self):
        # Cross‑trained pickers can pack with weight 0.7
        gm = GammaMapping(
            child_zone=self.picking,
            child_role=self.picker,
            parent_zone=self.packing,
            parent_role=self.picker,
            weight=0.7,
            priority=1
        )
        self.system.add_gamma_mapping(gm)

    def _create_neural_components(self):
        self.demand_forecaster = DemandForecaster()
        dummy = np.random.randn(100, 5)
        self.demand_forecaster.train(dummy)

        self.theft_detector = AnomalyDetector(contamination=0.05)
        dummy_logs = np.random.randn(200, 8)
        self.theft_detector.train(dummy_logs)

    def _create_daemons(self):
        class TemperatureDaemon(Daemon):
            async def check(self):
                # Simulate temperature readings
                temp = random.uniform(2, 10)
                if temp > 8:
                    return [f"TEMP_VIOLATION:Storage"]
                return []
        self.temp_daemon = TemperatureDaemon(interval=1.0)

        class ProductivityDaemon(Daemon):
            async def check(self):
                # Monitor pick rates
                return []
        self.prod_daemon = ProductivityDaemon(interval=5.0)

        class InventoryMonitorDaemon(Daemon):
            async def check(self):
                # Detect anomalies (theft)
                if random.random() < 0.02:
                    return ["THEFT_ALERT"]
                return []
        self.inv_monitor = InventoryMonitorDaemon(interval=1.0)

    # Simulations
    def sim_normal_fulfillment(self, steps=100):
        class NormalSim(SimulationEngine):
            def step(self, current_time):
                picker = random.choice([u for u in self.system.users if any(r.name=="Picker" for r in u.zone_role_assignments[self.root_zone.id])])
                op = self.system.get_operation_by_name("pick_order")
                zone = next(z for z in self.system.zones if z.name == "Picking")
                context = {"time": current_time}
                allowed = self.permission_engine.decide(picker, op, zone, context)
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": picker.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "allowed": allowed
                })
        sim = NormalSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_peak_season(self, steps=100):
        class PeakSim(SimulationEngine):
            def step(self, current_time):
                for _ in range(random.randint(2,4)):
                    picker = random.choice([u for u in self.system.users if any(r.name=="Picker" for r in u.zone_role_assignments[self.root_zone.id])])
                    op = self.system.get_operation_by_name("pick_order")
                    zone = next(z for z in self.system.zones if z.name == "Picking")
                    context = {"time": current_time, "peak": True}
                    allowed = self.permission_engine.decide(picker, op, zone, context)
                    self.logs.append({
                        "time": current_time.isoformat(),
                        "user": picker.username,
                        "operation": op.name,
                        "zone": zone.name,
                        "allowed": allowed,
                        "peak": True
                    })
        sim = PeakSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_theft_detection(self, steps=100):
        class TheftSim(SimulationEngine):
            def step(self, current_time):
                # Simulate cycle count with possible theft
                inv = next(u for u in self.system.users if u.username == "inv1")
                op = self.system.get_operation_by_name("cycle_count")
                zone = next(z for z in self.system.zones if z.name == "Storage")
                system_qty = random.randint(50,100)
                physical_qty = system_qty - random.randint(0,5)  # possible theft
                discrepancy = abs(system_qty - physical_qty) > 2
                context = {"system_qty": system_qty, "physical_qty": physical_qty, "tolerance": 2}
                allowed = self.permission_engine.decide(inv, op, zone, context)
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": inv.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "allowed": allowed,
                    "system_qty": system_qty,
                    "physical_qty": physical_qty,
                    "discrepancy": discrepancy
                })
        sim = TheftSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def run_all_simulations(self):
        print("="*50)
        print("Supply Chain Distribution Center - Simulations")
        print("="*50)
        print("Normal fulfillment:")
        res1 = self.sim_normal_fulfillment(50)
        print(f"  Total: {res1['total_requests']}, Allowed: {res1['allowed']}, Denied: {res1['denied']}, Allow rate: {res1['allow_rate']:.2%}")
        print("Peak season:")
        res2 = self.sim_peak_season(50)
        print(f"  Total: {res2['total_requests']}, Allowed: {res2['allowed']}, Denied: {res2['denied']}, Allow rate: {res2['allow_rate']:.2%}")
        print("Theft detection:")
        res3 = self.sim_theft_detection(50)
        print(f"  Total: {res3['total_requests']}, Allowed: {res3['allowed']}, Denied: {res3['denied']}, Allow rate: {res3['allow_rate']:.2%}")

if __name__ == "__main__":
    dc = DistributionCenter()
    dc.run_all_simulations()