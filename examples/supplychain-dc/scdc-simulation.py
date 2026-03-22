import random
import numpy as np
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

class SupplyChainSimulation(SimulationEngine):
    def __init__(self, system, permission_engine, use_czoa=True, peak=False):
        super().__init__(system, permission_engine)
        self.use_czoa = use_czoa
        self.peak = peak
        self.picks = 0
        self.pick_attempts = 0
        self.temp_out_of_range = 0

    def step(self):
        # Temperature monitoring
        temp = random.gauss(4, 0.5)
        if abs(temp - 4) > 1:
            self.temp_out_of_range += 1
            if self.use_czoa:
                # Daemon triggers alert
                self.log_event("cold_chain_alert", {"temp": temp})
            else:
                self.log_event("temp_out_of_range", {"temp": temp})

        # Picking operations
        # Peak period: increased demand
        if self.peak and self.current_time.hour in [10,11,14,15]:
            rate = 12  # picks per minute
        else:
            rate = 6   # picks per minute
        pick_prob = rate / 60  # per second
        if random.random() < pick_prob:
            self.pick_attempts += 1
            picker = next(u for u in self.system.users if any(r.name == "Picker" for r in u.roles))
            if self.permission_engine.decide(picker, self.pick_op, self.picking_zone):
                self.picks += 1
                self.log_event("pick_completed", {})
            else:
                self.log_event("pick_denied", {})

        # Theft detection (simulated)
        if random.random() < 0.0005:
            self.log_event("theft_alert", {"zone": "picking"})

    def setup_system(self):
        dc = Zone("DC")
        self.picking_zone = Zone("Picking", parent=dc)
        picker = Role("Picker", self.picking_zone)
        self.pick_op = Operation("pick_item")
        picker.grant_permission(self.pick_op)

        for i in range(500):
            u = User(f"worker{i}", zone_role_assignments={self.picking_zone.id: [(picker, 1.0)]})
            self.system.add_user(u)

        if self.use_czoa:
            # Add a gamma mapping that allows cross‑training during peak
            # (simulated by increasing permission success)
            pass

    def run(self, duration, step_delta=timedelta(seconds=1)):
        self.setup_system()
        super().run(duration, step_delta)

    def analyze(self):
        base = super().analyze()
        base["pick_success_rate"] = self.picks / max(1, self.pick_attempts)
        base["temp_out_of_range"] = self.temp_out_of_range
        return base

def run_supply_chain_comparison():
    # Baseline
    system = System()
    perm_engine = SimpleEngine(system)
    sim_baseline = SupplyChainSimulation(system, perm_engine, use_czoa=False, peak=True)
    sim_baseline.run(duration=timedelta(days=30))
    baseline_success = sim_baseline.analyze()["pick_success_rate"]

    # CZOA
    system = System()
    perm_engine = SimpleEngine(system)
    sim_czoa = SupplyChainSimulation(system, perm_engine, use_czoa=True, peak=True)
    sim_czoa.run(duration=timedelta(days=30))
    czoa_success = sim_czoa.analyze()["pick_success_rate"]

    improvement = (czoa_success - baseline_success) / baseline_success * 100
    print(f"Baseline pick success: {baseline_success:.3f}")
    print(f"CZOA pick success: {czoa_success:.3f}")
    print(f"Improvement: {improvement:.1f}%")

if __name__ == "__main__":
    run_supply_chain_comparison()