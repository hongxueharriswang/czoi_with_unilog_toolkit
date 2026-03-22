
"""
Simulation of a university with registration, advising, FERPA enforcement.
"""

from czoi.neural import StudentSuccessPredictor, CourseDemandForecaster
from czoi.daemons import FERPADaemon, AdvisingDaemon

def setup_university_system():
    system = System()
    uni = Zone("University", parent=None)
    eng = Zone("Engineering", parent=uni)
    arts = Zone("Arts", parent=uni)
    
    # Roles
    prof = Role("Professor", zone=eng, base_perms=["enter_grade", "view_student"])
    student = Role("Student", zone=eng, base_perms=["register", "view_grade"])
    advisor = Role("Advisor", zone=eng, base_perms=["view_student", "override_registration"])
    registrar = Role("Registrar", zone=uni, base_perms=["manage_registration"])
    
    # Users: 12000 students, 5000 faculty, 10000 staff (simplified)
    users = []
    for i in range(12000):
        u = User(f"student{i}")
        u.assign_role(student, eng if i%2==0 else arts)
        system.add_user(u)
    for i in range(5000):
        u = User(f"prof{i}")
        u.assign_role(prof, eng if i%2==0 else arts)
        system.add_user(u)
    for i in range(10000):
        u = User(f"staff{i}")
        if i < 2000:
            u.assign_role(advisor, eng)
        else:
            u.assign_role(registrar, uni)
        system.add_user(u)
    
    # Applications
    sis = Application("SIS")
    sis.add_operation(Operation("register", required_perm="register"))
    sis.add_operation(Operation("enter_grade", required_perm="enter_grade"))
    sis.add_operation(Operation("view_grade", required_perm="view_grade"))
    system.add_application(sis)
    
    # Constraints: FERPA
    constraints = ConstraintSet()
    constraints.add("ferpa", lambda u, op, ctx: not (
        op.name == "view_grade" and "Student" in [r.name for r in u.roles] and
        ctx.get("student_id") != u.id
    ))
    system.add_constraints(constraints)
    
    return system, eng, student, prof, advisor, registrar

def registration_loop(env, system, zone, log, use_czoa):
    """Simulate student registration requests during peak."""
    while True:
        # Registration period: high arrival rate
        iat = np.random.exponential(0.000833)  # 1200 per second? Actually we need realistic
        yield env.timeout(iat)
        # Choose a random student
        student_user = random.choice([u for u in system.users if any(r.name=="Student" for r in u.roles)])
        course = f"CS101"
        if system.decide(student_user, "register", zone):
            log.append(("registration_success", env.now))
        else:
            log.append(("registration_failure", env.now))
            # Possibly get advisor override
            if use_czoa:
                # Advisor daemon may trigger override
                pass

def grade_entry_loop(env, system, zone, log, use_czoa):
    """Simulate professors entering grades."""
    while True:
        yield env.timeout(np.random.exponential(30))  # every 30 minutes
        prof_user = random.choice([u for u in system.users if any(r.name=="Professor" for r in u.roles)])
        student = random.choice([u for u in system.users if any(r.name=="Student" for r in u.roles)])
        if system.decide(prof_user, "enter_grade", zone):
            log.append(("grade_entry", prof_user.id, student.id))
        else:
            log.append(("grade_denied", prof_user.id))

def run_education_simulation(use_czoa=True):
    env = simpy.Environment()
    system, eng, student, prof, advisor, registrar = setup_university_system()
    log = []
    
    if use_czoa:
        success_model = StudentSuccessPredictor.load("student_success_gb.pkl")
        demand_model = CourseDemandForecaster.load("course_demand_ts.pkl")
        ferpa_daemon = FERPADaemon()
        advising_daemon = AdvisingDaemon(success_model, threshold=0.5)
        env.process(ferpa_daemon.run(env, system))
        env.process(advising_daemon.run(env, system))
    
    env.process(registration_loop(env, system, eng, log, use_czoa))
    env.process(grade_entry_loop(env, system, eng, log, use_czoa))
    
    # Simulate a registration peak (first 3 days)
    env.run(until=3*24*60)
    
    reg_success = sum(1 for e in log if e[0] == "registration_success")
    reg_fail = sum(1 for e in log if e[0] == "registration_failure")
    grade_denied = sum(1 for e in log if e[0] == "grade_denied")
    
    return reg_success, reg_fail, grade_denied

if __name__ == "__main__":
    base_success, base_fail, base_den = run_education_simulation(use_czoa=False)
    czoa_success, czoa_fail, czoa_den = run_education_simulation(use_czoa=True)
    print(f"Baseline: success={base_success}, fail={base_fail}, grade_denied={base_den}")
    print(f"CZOA: success={czoa_success}, fail={czoa_fail}, grade_denied={czoa_den}")