"""
Simulation of a distribution center with 500 workers, 100,000 SKUs.
Compares CZOA (demand forecaster, theft detector, cold chain daemon) against static.
"""

from czoi.neural import DemandForecasterTransformer, TheftDetector
from czoi.daemons import ColdChainDaemon
from czoi.core import System, Zone, Role, User, Application, Operation
from czoi.permission import SimpleEngine
from czoi.simulation import SimulationEngine
import simpy
def setup_supply_chain_system():
    system = System()
    dc = Zone("DistributionCenter", parent=None)
    receiving = Zone("Receiving", parent=dc)
    storage = Zone("Storage", parent=dc)
    picking = Zone("Picking", parent=dc)
    shipping = Zone("Shipping", parent=dc)
    
    # Roles
    manager = Role("WarehouseManager", zone=dc, base_perms=["override", "audit"])
    supervisor = Role("Supervisor", zone=dc, base_perms=["assign_work"])
    picker = Role("Picker", zone=picking, base_perms=["pick"])
    receiver = Role("Receiver", zone=receiving, base_perms=["receive"])
    
    # Users: 500
    users = []
    for i in range(500):
        u = User(f"worker{i}")
        if i < 10:
            u.assign_role(manager, dc)
        elif i < 30:
            u.assign_role(supervisor, dc)
        elif i < 300:
            u.assign_role(picker, picking)
        else:
            u.assign_role(receiver, receiving)
        system.add_user(u)
    
    # Applications
    wms = Application("WMS")
    wms.add_operation(Operation("pick", required_perm="pick"))
    wms.add_operation(Operation("receive", required_perm="receive"))
    wms.add_operation(Operation("audit", required_perm="audit"))
    system.add_application(wms)
    
    return system, picking, receiving, picker, receiver

def worker_loop(env, system, zone, role, log, use_czoa):
    """Simulate workers performing tasks."""
    while True:
        # Task generation rate depends on zone
        if zone.name == "Picking":
            iat = np.random.exponential(0.1)  # 10 per minute
        else:
            iat = np.random.exponential(0.2)  # 5 per minute
        yield env.timeout(iat)
        # Find a worker with the correct role
        workers = [u for u in system.users if role in u.roles]
        if not workers:
            continue
        worker = random.choice(workers)
        if zone.name == "Picking":
            op = "pick"
        else:
            op = "receive"
        if system.decide(worker, op, zone):
            # Task performed
            duration = np.random.exponential(2)  # 2 min average
            yield env.timeout(duration)
            log.append(("completed", op, env.now))
        else:
            log.append(("denied", op, worker.id))

def cold_chain_loop(env, daemon, log):
    """Simulate temperature sensor readings."""
    while True:
        temp = np.random.normal(4, 0.5)  # target 4°C ± 1°C
        if daemon:
            daemon.check_temperature(temp)
        yield env.timeout(60)  # every minute

def run_supply_chain_simulation(use_czoa=True):
    env = simpy.Environment()
    system, picking, receiving, picker, receiver = setup_supply_chain_system()
    log = []
    
    if use_czoa:
        demand_model = DemandForecasterTransformer.load("demand_transformer.pt")
        theft_detector = TheftDetector(isolation_forest_path="theft_if.pkl")
        cold_daemon = ColdChainDaemon(temp_sensor_id="fridge1", threshold=5.0)
        env.process(cold_chain_loop(env, cold_daemon, log))
    else:
        env.process(cold_chain_loop(env, None, log))
    
    env.process(worker_loop(env, system, picking, picker, log, use_czoa))
    env.process(worker_loop(env, system, receiving, receiver, log, use_czoa))
    
    # Run for 90 days
    env.run(until=90*24*60)
    
    completed = sum(1 for e in log if e[0] == "completed")
    denied = sum(1 for e in log if e[0] == "denied")
    # For cold chain, count out-of-range events from daemon
    out_of_range = sum(1 for e in log if e[0] == "temp_out_of_range")
    
    return completed, denied, out_of_range

if __name__ == "__main__":
    base_comp, base_den, base_temp = run_supply_chain_simulation(use_czoa=False)
    czoa_comp, czoa_den, czoa_temp = run_supply_chain_simulation(use_czoa=True)
    print(f"Baseline: completed={base_comp}, denied={base_den}, temp_out={base_temp}")
    print(f"CZOA: completed={czoa_comp}, denied={czoa_den}, temp_out={czoa_temp}")