"""
Supply Chain Distribution Center Simulation for CZOA Evaluation
Based on Section 7.6 of the CZOA paper.

This simulation models a distribution center with:
- 500 workers across three shifts.
- 100,000 SKUs (Stock Keeping Units).
- Cold chain integrity monitoring.
- Order picking, receiving, packing, shipping.
- Theft detection using Isolation Forest on inventory discrepancies.
- Adaptive throughput: during peak, cross-trained workers assist.
- Metrics: throughput (orders/hour), theft detection precision/recall,
  cold chain violations, inventory accuracy.
"""

import random
import numpy as np
import simpy
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# ----------------------------------------------------------------------
# Mock CZOI classes (if toolkit not installed)
# ----------------------------------------------------------------------
class Zone:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        if parent:
            parent.children.append(self)

class Role:
    def __init__(self, name, zone):
        self.name = name
        self.zone = zone
        self.base_permissions = set()
    def grant_permission(self, op):
        self.base_permissions.add(op)

class User:
    def __init__(self, username, email=None):
        self.username = username
        self.email = email
        self.role_assignments = []  # list of (zone, role)
    def assign_role(self, zone, role):
        self.role_assignments.append((zone, role))

class Operation:
    def __init__(self, name, app=None, method=None):
        self.name = name

class Application:
    def __init__(self, name, owning_zone=None):
        self.name = name
        self.operations = []
    def add_operation(self, name, method=None):
        op = Operation(name, self, method)
        self.operations.append(op)
        return op

class SimpleEngine:
    def __init__(self, system):
        self.system = system
    def decide(self, user, operation, zone, context=None):
        # Simplified: check if user's roles have the operation in base permissions
        for _, role in user.role_assignments:
            if operation in role.base_permissions:
                # Additional constraints (e.g., forklift certification) can be checked here
                if operation.name in ["receive_shipment", "pick_order"]:
                    if not context.get('certified', False):
                        return False
                return True
        return False

# ----------------------------------------------------------------------
# Neural Components (simulated)
# ----------------------------------------------------------------------
class DemandForecaster:
    """
    Simulated Transformer-based demand forecaster.
    Returns predicted demand for each SKU.
    """
    def __init__(self):
        self.trained = False

    def train(self, data):
        self.trained = True

    def predict(self, sku_id, time_of_day, day_of_week):
        """
        Predict demand (units per hour) for a given SKU.
        Uses a simple sinusoidal pattern with noise to simulate real demand.
        """
        base = random.uniform(5, 50)  # base demand
        # Daily pattern: higher during daytime
        daily_factor = 0.5 + 0.5 * np.sin(2 * np.pi * (time_of_day - 12) / 24)
        # Weekly pattern: higher on weekdays
        weekly_factor = 1.0 if day_of_week < 5 else 0.8
        # Add noise
        noise = random.gauss(0, 0.1 * base)
        demand = base * daily_factor * weekly_factor + noise
        return max(0, demand)

    @classmethod
    def load(cls, path):
        return cls()

class TheftDetector:
    """
    Simulated Isolation Forest for theft detection.
    Returns anomaly score and flag based on inventory discrepancies.
    """
    def __init__(self, contamination=0.05):
        self.contamination = contamination
        self.trained = False

    def train(self, data):
        self.trained = True

    def predict(self, discrepancy, worker_id, time_of_day):
        """
        Predict theft probability (0-1) based on discrepancy magnitude and context.
        """
        # For simulation, we use a simple logistic function:
        # larger discrepancies and unusual times increase probability.
        # Also, certain workers might have higher "risk" (for evaluation).
        logit = -5.0 + 2.0 * discrepancy + 0.5 * (time_of_day < 6 or time_of_day > 20)
        # Simulate worker-specific bias (some workers are "thieves" for evaluation)
        if worker_id in [42, 99, 101]:  # predefined thief IDs
            logit += 2.0
        prob = 1.0 / (1.0 + np.exp(-logit))
        return prob, prob > 0.5

    @classmethod
    def load(cls, path):
        return cls()

# ----------------------------------------------------------------------
# Daemons
# ----------------------------------------------------------------------
class Daemon:
    def __init__(self, name, interval):
        self.name = name
        self.interval = interval

class ColdChainDaemon(Daemon):
    """
    Monitors temperature sensors in cold storage zones.
    Triggers alert if temperature exceeds threshold.
    """
    def __init__(self, threshold=5.0, interval=10.0):
        super().__init__("ColdChain", interval)
        self.threshold = threshold
        self.violations = 0

    async def check(self, env, zone):
        """
        Simulate temperature reading. If > threshold, record violation.
        """
        # Simulate temperature with occasional spikes
        temp = 4.0 + random.gauss(0, 1.0)  # normal mean 4°C
        if random.random() < 0.05:
            temp += random.uniform(2, 6)  # spike
        if temp > self.threshold:
            self.violations += 1
            return [f"COLD_CHAIN_VIOLATION in {zone.name}: temp={temp:.1f}°C"]
        return []

class ProductivityDaemon(Daemon):
    """
    Monitors worker productivity (picks per hour).
    """
    def __init__(self, interval=60.0):
        super().__init__("Productivity", interval)
        self.productivity_data = []

    async def check(self, env, workers):
        """
        Compute productivity for each worker over the past interval.
        """
        productivity = []
        for w in workers:
            picks = w.picks_last_hour
            productivity.append((w.id, picks))
            w.picks_last_hour = 0
        self.productivity_data.append((env.now, productivity))
        return []

class InventoryMonitorDaemon(Daemon):
    """
    Monitors inventory discrepancies and triggers theft alerts.
    """
    def __init__(self, theft_detector, interval=60.0):
        super().__init__("InventoryMonitor", interval)
        self.theft_detector = theft_detector
        self.alerts = 0
        self.true_positives = 0
        self.false_positives = 0

    async def check(self, env, inventory_records):
        """
        Check each inventory record for anomalies.
        """
        alerts = []
        for rec in inventory_records:
            discrepancy = abs(rec.system_qty - rec.physical_qty)
            if discrepancy > 0:
                prob, is_theft = self.theft_detector.predict(
                    discrepancy, rec.worker_id, env.now % 86400 / 3600
                )
                if is_theft:
                    self.alerts += 1
                    if rec.actual_theft:
                        self.true_positives += 1
                    else:
                        self.false_positives += 1
                    alerts.append(f"THEFT_ALERT: SKU {rec.sku_id}, discrepancy {discrepancy}")
        return alerts

# ----------------------------------------------------------------------
# Worker and SKU classes
# ----------------------------------------------------------------------
class Worker:
    def __init__(self, worker_id, zone, role):
        self.id = worker_id
        self.zone = zone
        self.role = role
        self.picks_last_hour = 0
        self.certified_forklift = random.random() < 0.7  # 70% certified

class SKU:
    def __init__(self, sku_id, zone, cold_storage=False):
        self.id = sku_id
        self.zone = zone
        self.cold_storage = cold_storage
        self.system_qty = random.randint(50, 200)
        self.reorder_point = 20
        self.already_ordered = False
        self.physical_qty = self.system_qty  # initially accurate

class InventoryRecord:
    def __init__(self, sku, worker_id, system_qty, physical_qty, actual_theft):
        self.sku_id = sku.id
        self.worker_id = worker_id
        self.system_qty = system_qty
        self.physical_qty = physical_qty
        self.actual_theft = actual_theft

# ----------------------------------------------------------------------
# Supply Chain System (CZOI-like)
# ----------------------------------------------------------------------
class SupplyChainSystem:
    def __init__(self, num_workers=500, num_skus=100000):
        self.num_workers = num_workers
        self.num_skus = num_skus
        self._build_zones()
        self._create_roles()
        self._create_applications()
        self._create_users()
        self._create_constraints()
        self._create_gamma_mappings()
        self._create_neural_components()
        self._create_daemons()
        self.permission_engine = SimpleEngine(self)
        self.workers = []
        self.skus = []
        self._create_workers()
        self._create_skus()

    def _build_zones(self):
        self.root = Zone("DistributionCenter")
        self.receiving = Zone("Receiving", self.root)
        self.storage = Zone("Storage", self.root)
        self.cold_storage = Zone("ColdStorage", self.root)
        self.picking = Zone("Picking", self.root)
        self.packing = Zone("Packing", self.root)
        self.shipping = Zone("Shipping", self.root)
        self.returns = Zone("Returns", self.root)
        self.admin = Zone("Administrative", self.root)

    def _create_roles(self):
        self.roles = {}
        roles_data = [
            ("WarehouseManager", self.admin),
            ("Supervisor", self.admin),
            ("Picker", self.picking),
            ("Receiver", self.receiving),
            ("InventoryController", self.storage)
        ]
        for name, zone in roles_data:
            r = Role(name, zone)
            self.roles[name] = r

    def _create_applications(self):
        wms = Application("WMS", self.root)
        self.receive_op = wms.add_operation("receive_shipment", "POST")
        self.pick_op = wms.add_operation("pick_order", "POST")
        self.cycle_op = wms.add_operation("cycle_count", "POST")
        lms = Application("LMS", self.admin)
        self.track_productivity = lms.add_operation("track_productivity", "GET")
        # Permissions
        self.roles["Receiver"].grant_permission(self.receive_op)
        self.roles["Picker"].grant_permission(self.pick_op)
        self.roles["InventoryController"].grant_permission(self.cycle_op)
        self.roles["WarehouseManager"].grant_permission(self.track_productivity)

    def _create_users(self):
        # Workers are created separately, but we need User objects for permission checks.
        # We'll create a mapping from Worker to User.
        self.users = []
        # For simplicity, we'll create User objects for each worker with same id.
        for i in range(self.num_workers):
            u = User(f"worker{i}", f"worker{i}@dc.com")
            # Assign role based on worker's role (we'll set later)
            self.users.append(u)

    def _create_constraints(self):
        # We'll simulate constraints via daemons and permission checks.
        # For example, forklift certification is checked in decide().
        pass

    def _create_gamma_mappings(self):
        # Cross-trained pickers can pack with weight 0.7
        # Not used in simulation directly, but can be.
        pass

    def _create_neural_components(self):
        self.demand_forecaster = DemandForecaster()
        self.theft_detector = TheftDetector(contamination=0.05)
        # Dummy training
        dummy_data = np.random.randn(1000, 10)
        self.demand_forecaster.train(dummy_data)
        self.theft_detector.train(dummy_data)

    def _create_daemons(self):
        self.cold_chain_daemon = ColdChainDaemon(threshold=5.0, interval=10.0)
        self.productivity_daemon = ProductivityDaemon(interval=60.0)
        self.inventory_monitor = InventoryMonitorDaemon(self.theft_detector, interval=60.0)

    def _create_workers(self):
        # Assign workers to zones and roles
        for i in range(self.num_workers):
            # Determine role: mostly pickers, some receivers, supervisors, etc.
            if i < 400:
                role = self.roles["Picker"]
                zone = self.picking
            elif i < 450:
                role = self.roles["Receiver"]
                zone = self.receiving
            elif i < 480:
                role = self.roles["InventoryController"]
                zone = self.storage
            elif i < 495:
                role = self.roles["Supervisor"]
                zone = self.admin
            else:
                role = self.roles["WarehouseManager"]
                zone = self.admin
            w = Worker(i, zone, role)
            self.workers.append(w)
            # Link to User object
            self.users[i].assign_role(zone, role)

    def _create_skus(self):
        for i in range(self.num_skus):
            # 10% of SKUs are cold storage
            cold = random.random() < 0.1
            zone = self.cold_storage if cold else self.storage
            sku = SKU(i, zone, cold)
            self.skus.append(sku)

# ----------------------------------------------------------------------
# Simulation Engine
# ----------------------------------------------------------------------
class SupplyChainSimulation:
    def __init__(self, system: SupplyChainSystem, peak_mode=False):
        self.system = system
        self.peak_mode = peak_mode
        self.env = simpy.Environment()
        self.workers = system.workers
        self.skus = system.skus
        self.orders = []               # list of orders (order_id, sku_id, quantity)
        self.order_id = 0
        self.cycle_counts = []         # list of InventoryRecord objects
        self.metrics = {
            'orders_picked': 0,
            'throughput': 0,
            'theft_alerts': 0,
            'true_positives': 0,
            'false_positives': 0,
            'cold_chain_violations': 0,
            'inventory_accuracy': []   # list of (system_qty, physical_qty)
        }

        # Start processes
        self.env.process(self.order_generator())
        self.env.process(self.worker_scheduler())
        self.env.process(self.cycle_count_generator())
        self.env.process(self.cold_chain_monitor())
        self.env.process(self.inventory_monitor())

    def order_generator(self):
        """
        Generate orders for SKUs based on demand forecast.
        Order rate: normal ~200/hour, peak ~400/hour.
        """
        while True:
            if self.peak_mode:
                rate = 400.0 / 3600.0  # 400 per hour
            else:
                rate = 200.0 / 3600.0  # 200 per hour
            interarrival = random.expovariate(rate)
            yield self.env.timeout(interarrival)

            # Choose a random SKU and quantity
            sku = random.choice(self.skus)
            time_of_day = (self.env.now % 86400) / 3600
            day_of_week = (self.env.now // 86400) % 7
            demand = self.system.demand_forecaster.predict(sku.id, time_of_day, day_of_week)
            quantity = int(max(1, random.poisson(demand)))
            self.order_id += 1
            self.orders.append((self.order_id, sku, quantity))

    def worker_scheduler(self):
        """
        Assign workers to pick orders.
        """
        while True:
            # Check for pending orders
            if self.orders:
                # Get a worker (pick from list, simulate queue)
                worker = random.choice(self.workers)
                if worker.role.name == "Picker":
                    order_id, sku, qty = self.orders.pop(0)
                    # Simulate picking time (depends on quantity and worker productivity)
                    pick_time = qty * 0.5 / 60.0  # 0.5 sec per unit -> minutes
                    yield self.env.timeout(pick_time)
                    # Update SKU inventory
                    sku.system_qty -= qty
                    # Record worker productivity
                    worker.picks_last_hour += 1
                    self.metrics['orders_picked'] += 1
            else:
                yield self.env.timeout(1.0)

    def cycle_count_generator(self):
        """
        Perform random cycle counts to detect theft.
        """
        while True:
            # Cycle count frequency: every 10 seconds on average
            yield self.env.timeout(random.expovariate(1/10.0))
            # Select a random SKU
            sku = random.choice(self.skus)
            # Simulate a worker performing cycle count
            worker = random.choice([w for w in self.workers if w.role.name == "InventoryController"])
            # Determine actual theft (some SKUs have theft for evaluation)
            # For simulation, we define theft as discrepancy > 0
            actual_theft = False
            # Simulate theft: 5% of counts have a small discrepancy
            if random.random() < 0.05:
                # Theft: physical quantity less than system
                discrepancy = random.randint(1, 5)
                physical_qty = sku.system_qty - discrepancy
                actual_theft = True
            else:
                physical_qty = sku.system_qty
            # Record the count
            rec = InventoryRecord(sku, worker.id, sku.system_qty, physical_qty, actual_theft)
            self.cycle_counts.append(rec)
            # Optionally update SKU physical quantity (not for simulation)
            # We'll just use the record for theft detection.

    def cold_chain_monitor(self):
        """
        Run cold chain daemon every 10 seconds.
        """
        while True:
            yield self.env.timeout(self.system.cold_chain_daemon.interval)
            alerts = self.system.cold_chain_daemon.check(self.env, self.system.cold_storage)
            self.metrics['cold_chain_violations'] += len(alerts)

    def inventory_monitor(self):
        """
        Run inventory monitor daemon every 60 seconds.
        """
        while True:
            yield self.env.timeout(self.system.inventory_monitor.interval)
            # Get records from last interval
            records = self.cycle_counts[-self.system.inventory_monitor.interval*10:]  # approx
            alerts = self.system.inventory_monitor.check(self.env, records)
            self.metrics['theft_alerts'] += len(alerts)
            # True positives/false positives are tracked inside daemon
            self.metrics['true_positives'] = self.system.inventory_monitor.true_positives
            self.metrics['false_positives'] = self.system.inventory_monitor.false_positives

    def run(self, duration_hours: float):
        """Run simulation for given duration (hours)."""
        self.env.run(until=duration_hours * 3600)

    def compute_metrics(self):
        runtime_hours = self.env.now / 3600.0
        self.metrics['throughput'] = self.metrics['orders_picked'] / runtime_hours
        total_alerts = self.metrics['true_positives'] + self.metrics['false_positives']
        if total_alerts > 0:
            self.metrics['theft_precision'] = self.metrics['true_positives'] / total_alerts
        else:
            self.metrics['theft_precision'] = 0
        # Recall: we need ground truth total thefts. In simulation, we know actual thefts from cycle counts.
        actual_thefts = sum(1 for rec in self.cycle_counts if rec.actual_theft)
        if actual_thefts > 0:
            self.metrics['theft_recall'] = self.metrics['true_positives'] / actual_thefts
        else:
            self.metrics['theft_recall'] = 0
        # Inventory accuracy: mean discrepancy
        discrepancies = [abs(rec.system_qty - rec.physical_qty) for rec in self.cycle_counts]
        self.metrics['mean_inventory_discrepancy'] = statistics.mean(discrepancies) if discrepancies else 0

    def print_results(self):
        print("\n=== Supply Chain Distribution Center Results ===")
        print(f"Runtime: {self.env.now/3600:.1f} hours")
        print(f"Orders picked: {self.metrics['orders_picked']}")
        print(f"Throughput: {self.metrics['throughput']:.1f} orders/hour")
        print(f"Theft detection precision: {self.metrics['theft_precision']:.2%}")
        print(f"Theft detection recall: {self.metrics['theft_recall']:.2%}")
        print(f"Cold chain violations: {self.metrics['cold_chain_violations']}")
        print(f"Mean inventory discrepancy: {self.metrics['mean_inventory_discrepancy']:.2f} units")

# ----------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------
def run_experiment(num_workers=500, num_skus=100000, duration_hours=90):
    """Run simulation for 90 days (as per paper) and output metrics."""
    print("Initializing Supply Chain System...")
    system = SupplyChainSystem(num_workers=num_workers, num_skus=num_skus)
    # Normal scenario
    sim_normal = SupplyChainSimulation(system, peak_mode=False)
    print(f"Running normal simulation for {duration_hours} hours...")
    sim_normal.run(duration_hours)
    sim_normal.compute_metrics()
    print("\n--- Normal Scenario ---")
    sim_normal.print_results()

    # Peak scenario (same system but with peak_mode=True)
    # For peak, we need a fresh simulation because state changes.
    system_peak = SupplyChainSystem(num_workers=num_workers, num_skus=num_skus)
    sim_peak = SupplyChainSimulation(system_peak, peak_mode=True)
    print(f"\nRunning peak simulation for {duration_hours} hours...")
    sim_peak.run(duration_hours)
    sim_peak.compute_metrics()
    print("\n--- Peak Scenario ---")
    sim_peak.print_results()
    # Compute throughput loss (paper says 5% loss)
    loss = (sim_normal.metrics['throughput'] - sim_peak.metrics['throughput']) / sim_normal.metrics['throughput']
    print(f"\nThroughput loss during peak: {loss:.1%}")

if __name__ == "__main__":
    # For demonstration, run a shorter simulation (1 day)
    run_experiment(num_workers=50, num_skus=1000, duration_hours=24)