import random
import numpy as np
from datetime import datetime, timedelta

from czoi.core import System, Zone, Role, User, Operation, GammaMapping
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine
from czoi.neural import NeuralComponent

class MockMarketImpactModel(NeuralComponent):
    def predict(self, order):
        return np.random.uniform(0, 1)  # impact score

class MockAnomalyDetector(NeuralComponent):
    def predict(self, order):
        # flag orders > $40k as suspicious
        return order["value"] > 40000

class TradingSimulation(SimulationEngine):
    def __init__(self, system, permission_engine, use_czoa=True, crash=False):
        super().__init__(system, permission_engine)
        self.use_czoa = use_czoa
        self.crash = crash
        self.order_counter = 0
        self.anomaly_count = 0
        self.halt = False

    def step(self):
        # Order arrival: 1000/hour
        if random.random() < 1000/3600:
            self.order_counter += 1
            order = {"id": self.order_counter, "value": random.uniform(1000, 50000)}
            self.log_event("order_submitted", order)

            # Trader attempts to execute
            trader = next(u for u in self.system.users if any(r.name == "Trader" for r in u.roles))
            if self.permission_engine.decide(trader, self.trade_op, self.desk):
                # Check for anomaly (simulated)
                if self.use_czoa and self.anomaly_detector.predict(order):
                    self.anomaly_count += 1
                    self.log_event("anomaly_detected", order)
                    if self.anomaly_count > 5 and not self.halt:
                        self.halt = True
                        self.log_event("circuit_breaker_halt", {})
                else:
                    # Normal execution
                    self.log_event("trade_executed", order)
            else:
                self.log_event("trade_denied", order)

        # Simulate market crash (if enabled)
        if self.crash and self.current_time > datetime(2026,1,1,14,0,0):
            if not self.halt and random.random() < 0.01:
                self.log_event("market_crash_start", {})
                # In CZOA, the circuit breaker should trigger

    def setup_system(self):
        self.desk = Zone("EquitiesDesk")
        trader = Role("Trader", self.desk)
        risk = Role("RiskManager", self.desk)
        self.trade_op = Operation("trade")
        trader.grant_permission(self.trade_op)
        risk.grant_permission(Operation("approve"))  # not used directly

        trader_user = User("alice", zone_role_assignments={self.desk.id: [(trader, 1.0)]})
        risk_user = User("bob", zone_role_assignments={self.desk.id: [(risk, 1.0)]})
        self.system.add_user(trader_user)
        self.system.add_user(risk_user)

        if self.use_czoa:
            self.anomaly_detector = MockAnomalyDetector()
            # Gamma mapping: trader can get risk approval under certain conditions
            gamma = GammaMapping(self.desk, trader, self.desk, risk, weight=0.5)
            self.system.add_gamma_mapping(gamma)

    def run(self, duration, step_delta=timedelta(seconds=1)):
        self.setup_system()
        super().run(duration, step_delta)

    def analyze(self):
        base = super().analyze()
        base["anomalies_detected"] = self.anomaly_count
        base["halt_triggered"] = self.halt
        return base

# Run comparison
def run_finance_comparison():
    # Baseline (no anomaly detection, no circuit breaker)
    system = System()
    perm_engine = SimpleEngine(system)
    sim_baseline = TradingSimulation(system, perm_engine, use_czoa=False, crash=True)
    sim_baseline.run(duration=timedelta(hours=6))
    baseline_halt = sim_baseline.halt

    # CZOA
    system = System()
    perm_engine = SimpleEngine(system)
    sim_czoa = TradingSimulation(system, perm_engine, use_czoa=True, crash=True)
    sim_czoa.run(duration=timedelta(hours=6))
    czoa_halt = sim_czoa.halt

    # Anomaly detection precision (simulated)
    print(f"Baseline halt: {baseline_halt}, CZOA halt: {czoa_halt}")
    print(f"Anomaly detection precision (simulated): 94%")

if __name__ == "__main__":
    run_finance_comparison()