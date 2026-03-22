"""
Simulation of a trading desk with an anomaly detector and circuit breaker.
"""

import random
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Application, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

# Setup
system = System()
desk = Zone("EquitiesDesk")

trader = Role("Trader", desk)
risk_manager = Role("RiskManager", desk)

trade_op = Operation("trade", app=None)
risk_op = Operation("approve_trade", app=None)
trader.grant_permission(trade_op)
risk_manager.grant_permission(risk_op)

alice = User("alice", zone_role_assignments={desk.id: [(trader, 1.0)]})
bob = User("bob", zone_role_assignments={desk.id: [(risk_manager, 1.0)]})
system.add_user(alice)
system.add_user(bob)

engine = SimpleEngine(system)

class TradingSimulation(SimulationEngine):
    def step(self):
        # Simulate order arrivals (Poisson)
        if random.random() < 0.01:  # ~0.01 per second → 36 per hour
            order = {"id": random.randint(1,1000), "value": random.uniform(1000, 50000)}
            self.log_event("order_submitted", order)

            # Trader attempts to execute
            if engine.decide(alice, trade_op, desk):
                # Anomaly detection: if order value > 40000, treat as suspicious
                if order["value"] > 40000 and random.random() < 0.8:
                    self.log_event("anomaly_detected", order)
                    # Circuit breaker: halt if too many anomalies in short time
                    if self.count_anomalies() > 5:
                        self.log_event("circuit_breaker_triggered", {})
                else:
                    # Normal execution
                    self.log_event("trade_executed", order)
            else:
                self.log_event("trade_denied", order)

    def count_anomalies(self):
        # Count anomalies in last 60 seconds
        window = self.current_time - timedelta(seconds=60)
        return sum(1 for e in self.logs if e["type"] == "anomaly_detected" and datetime.fromisoformat(e["timestamp"]) >= window)

sim = TradingSimulation(system, engine)
sim.run(duration=3600)  # 1 hour
print(sim.analyze())