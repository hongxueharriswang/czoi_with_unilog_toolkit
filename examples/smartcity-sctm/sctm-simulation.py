import random
import numpy as np
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

class TrafficSimulation(SimulationEngine):
    def __init__(self, system, permission_engine, use_czoa=True):
        super().__init__(system, permission_engine)
        self.use_czoa = use_czoa
        self.incident_response_times = []

    def step(self):
        # Generate sensor data (simulated)
        congestion = random.gauss(50, 15)  # % congestion
        self.log_event("congestion_update", {"level": congestion})

        # Incident simulation (rare)
        if random.random() < 0.0001:  # once per 10000 seconds
            incident_time = self.current_time
            self.log_event("incident_detected", {"time": incident_time})

            # Operator attempts to respond
            operator = next(u for u in self.system.users if any(r.name == "Operator" for r in u.roles))
            if self.permission_engine.decide(operator, self.respond_op, self.control_zone):
                # Simulate response time
                if self.use_czoa:
                    # CZOA daemon adjusts signals automatically, reducing response time
                    response_time = np.random.exponential(120)  # 2 min average
                else:
                    response_time = np.random.exponential(300)  # 5 min average
                self.incident_response_times.append(response_time)
                self.log_event("incident_resolved", {"response_seconds": response_time})
            else:
                self.log_event("response_denied", {})

        # Signal adjustment daemon (if CZOA)
        if self.use_czoa and congestion > 70:
            # Engineer can adjust signals
            engineer = next(u for u in self.system.users if any(r.name == "Engineer" for r in u.roles))
            if self.permission_engine.decide(engineer, self.adjust_op, self.control_zone):
                self.log_event("signal_adjusted", {"new_timing": random.randint(30,90)})

    def setup_system(self):
        city = Zone("City")
        self.control_zone = Zone("ControlCenter", parent=city)
        operator = Role("Operator", self.control_zone)
        engineer = Role("Engineer", self.control_zone)
        self.respond_op = Operation("respond_to_incident")
        self.adjust_op = Operation("adjust_signal")
        operator.grant_permission(self.respond_op)
        engineer.grant_permission(self.adjust_op)

        op_user = User("op1", zone_role_assignments={self.control_zone.id: [(operator, 1.0)]})
        eng_user = User("eng1", zone_role_assignments={self.control_zone.id: [(engineer, 1.0)]})
        self.system.add_user(op_user)
        self.system.add_user(eng_user)

    def run(self, duration, step_delta=timedelta(seconds=1)):
        self.setup_system()
        super().run(duration, step_delta)

    def analyze(self):
        base = super().analyze()
        base["avg_response_time_seconds"] = np.mean(self.incident_response_times) if self.incident_response_times else 0
        return base

def run_traffic_comparison():
    # Baseline
    system = System()
    perm_engine = SimpleEngine(system)
    sim_baseline = TrafficSimulation(system, perm_engine, use_czoa=False)
    sim_baseline.run(duration=timedelta(days=7))
    baseline_rt = sim_baseline.analyze()["avg_response_time_seconds"]

    # CZOA
    system = System()
    perm_engine = SimpleEngine(system)
    sim_czoa = TrafficSimulation(system, perm_engine, use_czoa=True)
    sim_czoa.run(duration=timedelta(days=7))
    czoa_rt = sim_czoa.analyze()["avg_response_time_seconds"]

    reduction = (baseline_rt - czoa_rt) / baseline_rt * 100
    print(f"Baseline response time: {baseline_rt:.1f} s")
    print(f"CZOA response time: {czoa_rt:.1f} s")
    print(f"Reduction: {reduction:.1f}%")

if __name__ == "__main__":
    run_traffic_comparison()