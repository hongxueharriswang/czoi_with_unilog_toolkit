"""
Simulation of traffic signals with congestion prediction and adjustment.
"""

import random
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Application, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

# Setup
system = System()
city = Zone("City")
control = Zone("ControlCenter", parent=city)
engineer = Role("TrafficEngineer", control)
adjust_op = Operation("adjust_signal", app=None)
engineer.grant_permission(adjust_op)

alice = User("alice", zone_role_assignments={control.id: [(engineer, 1.0)]})
system.add_user(alice)

engine = SimpleEngine(system)

class TrafficSimulation(SimulationEngine):
    def step(self):
        # Simulate congestion (0-100)
        congestion = random.randint(0, 100)
        self.log_event("congestion_update", {"level": congestion})

        # If congestion > 70, engineer can adjust signals
        if congestion > 70:
            if engine.decide(alice, adjust_op, control):
                self.log_event("signal_adjusted", {"new_timing": random.randint(30,90)})
            else:
                self.log_event("adjustment_denied", {})

sim = TrafficSimulation(system, engine)
sim.run(duration=timedelta(minutes=10), step_delta=timedelta(seconds=5))
print(sim.analyze())