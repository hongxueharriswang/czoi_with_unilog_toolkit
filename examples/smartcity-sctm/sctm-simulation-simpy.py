"""
Simulation of a smart city traffic system with sensors, signals, VMS.
Compares CZOA (congestion LSTM, incident CNN, adaptive signals) against static.
"""

from czoi.neural import CongestionLSTM, IncidentCNN
from czoi.daemons import SignalAdjustmentDaemon, VMSDaemon

def setup_traffic_system():
    system = System()
    city = Zone("City", parent=None)
    control = Zone("ControlCenter", parent=city)
    signals = Zone("SignalSystems", parent=city)
    vms = Zone("VMS", parent=city)
    incident = Zone("IncidentManagement", parent=city)
    
    # Roles
    operator = Role("TrafficOperator", zone=control, base_perms=["view_cameras", "override_signal"])
    commander = Role("IncidentCommander", zone=incident, base_perms=["deploy_responders", "set_vms"])
    engineer = Role("TrafficEngineer", zone=signals, base_perms=["adjust_timing"])
    
    # Users: 150
    users = []
    for i in range(150):
        u = User(f"user{i}")
        if i < 100:
            u.assign_role(operator, control)
        elif i < 130:
            u.assign_role(commander, incident)
        else:
            u.assign_role(engineer, signals)
        system.add_user(u)
    
    # Applications
    atms = Application("ATMS")
    atms.add_operation(Operation("adjust_signal", required_perm="adjust_timing"))
    atms.add_operation(Operation("set_vms", required_perm="set_vms"))
    system.add_application(atms)
    
    # Constraints
    constraints = ConstraintSet()
    constraints.add("emergency_override", lambda u, op, ctx: not (
        op.name == "override_signal" and "IncidentCommander" not in [r.name for r in u.roles]
    ))
    system.add_constraints(constraints)
    
    return system, control, signals, vms, incident, operator, commander, engineer

def sensor_data_loop(env, system, daemon_signal, daemon_vms, log, use_czoa):
    """Generate sensor readings every second."""
    while True:
        # Simulate sensor data: speed, occupancy, camera image (dummy)
        speed = np.random.normal(50, 15)  # km/h
        occupancy = np.random.uniform(0, 1)
        # Incident simulation: randomly trigger incident
        incident_prob = 0.0001  # 1 per 10000 seconds
        if np.random.random() < incident_prob:
            log.append(("incident_detected", env.now))
        data = {"speed": speed, "occupancy": occupancy, "timestamp": env.now}
        if use_czoa:
            daemon_signal.evaluate(data)
            daemon_vms.evaluate(data)
        yield env.timeout(1)

def run_traffic_simulation(use_czoa=True):
    env = simpy.Environment()
    system, control, signals, vms, incident, operator, commander, engineer = setup_traffic_system()
    log = []
    
    if use_czoa:
        congestion_model = CongestionLSTM.load("traffic_lstm.pt")
        incident_model = IncidentCNN.load("incident_cnn.pt")
        signal_daemon = SignalAdjustmentDaemon(congestion_model, adjustment_interval=300)
        vms_daemon = VMSDaemon(incident_model)
        env.process(sensor_data_loop(env, system, signal_daemon, vms_daemon, log, use_czoa))
    else:
        # No adaptation: static signal timings
        env.process(sensor_data_loop(env, system, None, None, log, use_czoa))
    
    env.run(until=7*24*60*60)  # 7 days
    
    # Compute incident response times: time from incident detection to resolution
    # For simplicity, we just count incidents
    incidents = sum(1 for e in log if e[0] == "incident_detected")
    # Response time is recorded by daemon; we simulate it
    # In a real simulation we would track times. We'll just report count.
    return incidents

if __name__ == "__main__":
    baseline_inc = run_traffic_simulation(use_czoa=False)
    czoa_inc = run_traffic_simulation(use_czoa=True)
    print(f"Baseline incidents detected: {baseline_inc}")
    print(f"CZOA incidents detected: {czoa_inc}")
    # The paper reports 18% reduction in response time; we would need to measure times.