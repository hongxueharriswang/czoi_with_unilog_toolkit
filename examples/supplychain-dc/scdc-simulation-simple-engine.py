"""
Simulation of a distribution center with temperature monitoring and theft detection.
"""

import random
from datetime import datetime, timedelta
from czoi.core import System, Zone, Role, User, Application, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine

# Setup
system = System()
dc = Zone("DC")
cold_storage = Zone("ColdStorage", parent=dc)
picker = Role("Picker", cold_storage)
pick_op = Operation("pick_item", app=None)
picker.grant_permission(pick_op)

alice = User("alice", zone_role_assignments={cold_storage.id: [(picker, 1.0)]})
system.add_user(alice)

engine = SimpleEngine(system)

class SupplyChainSimulation(SimulationEngine):
    def step(self):
        # Temperature reading (target 4°C)
        temp = random.gauss(4, 0.8)
        self.log_event("temp_reading", {"value": temp})

        if temp > 5:
            self.log_event("cold_chain_alert", {"temp": temp})

        # Picking operation
        if random.random() < 0.02:
            sku = f"SKU{random.randint(1,1000)}"
            if engine.decide(alice, pick_op, cold_storage):
                self.log_event("item_picked", {"sku": sku})
            else:
                self.log_event("pick_denied", {"sku": sku})

        # Theft detection (simulated)
        if random.random() < 0.001:
            self.log_event("theft_alert", {"zone": "cold_storage"})

sim = SupplyChainSimulation(system, engine)
sim.run(duration=timedelta(hours=48))
print(sim.analyze())