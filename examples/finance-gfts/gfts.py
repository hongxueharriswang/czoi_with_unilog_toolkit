"""
Global Financial Trading System - CZOI Implementation
Demonstrates trading desks, risk management, gamma mappings, market anomaly detection,
and three simulations (normal, crash, insider).
"""

import asyncio
import random
import datetime
import numpy as np
from czoi.core import System, Zone, Role, User, Application, GammaMapping
from czoi.permission import SimpleEngine
from czoi.constraint import Constraint, ConstraintType, ConstraintManager
from czoi.neural import AnomalyDetector, NeuralComponent
from czoi.daemon import Daemon, SecurityDaemon, ComplianceDaemon
from czoi.simulation import SimulationEngine
from czoi.embedding import EmbeddingService, InMemoryVectorStore
from czoi.unilog import UniLangParser, InferenceEngine, CZOIModelAdapter

# ----------------------------------------------------------------------
# Custom Neural Component: Market Impact Predictor (mock)
# ----------------------------------------------------------------------
class MarketImpactPredictor(NeuralComponent):
    def __init__(self):
        self.trained = False
    def train(self, data):
        self.trained = True
    def predict(self, input):
        return float(np.random.rand(1))  # impact score
    def save(self, path):
        pass
    @classmethod
    def load(cls, path):
        return cls()

# ----------------------------------------------------------------------
# Main System Class
# ----------------------------------------------------------------------
class FinancialTradingSystem:
    def __init__(self):
        self.system = System()
        self.root = Zone("InvestmentBank")
        self.system.add_zone(self.root)
        self._build_hierarchy()
        self._create_roles()
        self._create_applications()
        self._create_users()
        self._create_constraints()
        self._create_gamma_mappings()
        self._create_neural_components()
        self._create_daemons()
        self.permission_engine = SimpleEngine(self.system)
        self.embedding_service = EmbeddingService(InMemoryVectorStore())
        self.parser = UniLangParser()
        self.logic_engine = InferenceEngine.get_instance()

    # ------------------------------------------------------------------
    # Zones
    # ------------------------------------------------------------------
    def _build_hierarchy(self):
        # Trading desks
        equities = Zone("Equities", parent=self.root)
        fixed = Zone("FixedIncome", parent=self.root)
        fx = Zone("FX", parent=self.root)
        self.system.add_zone(equities)
        self.system.add_zone(fixed)
        self.system.add_zone(fx)

        # Sub‑zones within Equities
        self.cash = Zone("CashEquities", parent=equities)
        self.program = Zone("ProgramTrading", parent=equities)
        self.block = Zone("BlockTrading", parent=equities)
        self.sales = Zone("SalesTrading", parent=equities)
        self.research = Zone("Research", parent=equities)
        self.market = Zone("MarketMaking", parent=equities)
        for z in [self.cash, self.program, self.block, self.sales, self.research, self.market]:
            self.system.add_zone(z)

        # Risk, Compliance, Operations (as separate zones)
        self.risk = Zone("RiskManagement", parent=self.root)
        self.compliance = Zone("Compliance", parent=self.root)
        self.ops = Zone("Operations", parent=self.root)
        self.system.add_zone(self.risk)
        self.system.add_zone(self.compliance)
        self.system.add_zone(self.ops)

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    def _create_roles(self):
        self.trader = Role("Trader", zone=self.cash)  # will be used in multiple zones via gamma
        self.sales_trader = Role("SalesTrader", zone=self.sales)
        self.risk_manager = Role("RiskManager", zone=self.risk)
        self.compliance_officer = Role("ComplianceOfficer", zone=self.compliance)
        self.quant = Role("Quant", zone=self.program)
        for r in [self.trader, self.sales_trader, self.risk_manager, self.compliance_officer, self.quant]:
            self.system.add_role(r)

    # ------------------------------------------------------------------
    # Applications
    # ------------------------------------------------------------------
    def _create_applications(self):
        # Order Management System
        oms = Application("OMS", owning_zone=self.root)
        self.enter_order = oms.add_operation("enter_order", "POST")
        self.cancel_order = oms.add_operation("cancel_order", "DELETE")
        self.system.add_application(oms)

        # Risk System
        risk_sys = Application("RiskSystem", owning_zone=self.risk)
        self.check_limit = risk_sys.add_operation("check_limit", "GET")
        self.system.add_application(risk_sys)

        # Surveillance
        surv = Application("Surveillance", owning_zone=self.compliance)
        self.surveillance_alert = surv.add_operation("surveillance_alert", "POST")
        self.system.add_application(surv)

        # Grant permissions
        self.trader.grant_permission(self.enter_order)
        self.trader.grant_permission(self.cancel_order)
        self.risk_manager.grant_permission(self.check_limit)
        self.compliance_officer.grant_permission(self.surveillance_alert)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def _create_users(self):
        users_data = [
            ("trader1", "Trader"),
            ("trader2", "Trader"),
            ("risk1", "RiskManager"),
            ("comp1", "ComplianceOfficer"),
            ("quant1", "Quant")
        ]
        for uname, rname in users_data:
            u = User(uname, f"{uname}@bank.com")
            role = next(r for r in self.system.roles if r.name == rname)
            u.assign_role(self.root, role, weight=1.0)
            self.system.add_user(u)

    # ------------------------------------------------------------------
    # Constraints (UniLang)
    # ------------------------------------------------------------------
    def _create_constraints(self):
        self.constraint_manager = ConstraintManager()

        # Identity: position limits
        pos_limit = Constraint(
            "PositionLimit",
            ConstraintType.IDENTITY,
            {"zones": ["Equities"]},
            "G (position <= position_limit)"
        )
        self.constraint_manager.add(pos_limit)

        # Trigger: limit breach → halt trading
        trigger_breach = Constraint(
            "LimitBreach",
            ConstraintType.TRIGGER,
            {"event": "trade_attempt"},
            "position > 0.9 * limit"
        )
        self.constraint_manager.add(trigger_breach)

        # Access: separation of duty (trader ≠ risk manager)
        sod = Constraint(
            "SoD_TraderRisk",
            ConstraintType.ACCESS,
            {"roles": ["Trader", "RiskManager"]},
            "not (exists t (trader(t) and riskmanager(t)))"
        )
        self.constraint_manager.add(sod)

    # ------------------------------------------------------------------
    # Gamma Mappings
    # ------------------------------------------------------------------
    def _create_gamma_mappings(self):
        # Trader in CashEquities can also trade in ProgramTrading with weight 0.5
        gm = GammaMapping(
            child_zone=self.cash,
            child_role=self.trader,
            parent_zone=self.program,
            parent_role=self.trader,
            weight=0.5,
            priority=2
        )
        self.system.add_gamma_mapping(gm)

    # ------------------------------------------------------------------
    # Neural Components
    # ------------------------------------------------------------------
    def _create_neural_components(self):
        self.market_impact = MarketImpactPredictor()
        # Train with dummy data
        self.market_impact.train(np.random.randn(100, 10))

        self.anomaly_detector = AnomalyDetector(contamination=0.1)
        dummy_logs = np.random.randn(500, 15)
        self.anomaly_detector.train(dummy_logs)

    # ------------------------------------------------------------------
    # Daemons
    # ------------------------------------------------------------------
    def _create_daemons(self):
        class MarketSurveillanceDaemon(Daemon):
            def __init__(self, detector, interval=1.0):
                super().__init__("market_surveillance", interval)
                self.detector = detector
            async def check(self):
                # Monitor trades (mock)
                if random.random() < 0.05:
                    return ["SUSPICIOUS_ACTIVITY"]
                return []
        self.surveillance_daemon = MarketSurveillanceDaemon(self.anomaly_detector, interval=1.0)

        class CircuitBreakerDaemon(Daemon):
            async def check(self):
                # Simulate VIX threshold
                vix = random.uniform(20, 40)
                if vix > 30:
                    return ["HALT_TRADING"]
                return []
        self.circuit_breaker = CircuitBreakerDaemon(interval=1.0)

    # ------------------------------------------------------------------
    # Simulations
    # ------------------------------------------------------------------
    def sim_normal_trading(self, steps=100):
        class NormalTradingSim(SimulationEngine):
            def step(self, current_time):
                trader = random.choice([u for u in self.system.users if any(r.name=="Trader" for r in u.zone_role_assignments[self.root_zone.id])])
                op = random.choice([o for o in self.system.operations if o.name in ("enter_order","cancel_order")])
                zone = random.choice(list(self.system.zones))
                position = random.uniform(0,80)
                context = {"position": position, "limit": 100}
                allowed = self.permission_engine.decide(trader, op, zone, context)
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": trader.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "position": position,
                    "allowed": allowed
                })
        sim = NormalTradingSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_market_crash(self, steps=100):
        class CrashSim(SimulationEngine):
            def step(self, current_time):
                # High volatility: many trades near limit
                trader = random.choice([u for u in self.system.users if any(r.name=="Trader" for r in u.zone_role_assignments[self.root_zone.id])])
                op = random.choice([o for o in self.system.operations if o.name=="enter_order"])
                zone = random.choice(list(self.system.zones))
                position = random.uniform(90,120)
                context = {"position": position, "limit": 100}
                allowed = self.permission_engine.decide(trader, op, zone, context)
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": trader.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "position": position,
                    "allowed": allowed,
                    "crash": True
                })
        sim = CrashSim(self.system, self.permission_engine, storage=None)
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def sim_insider_trading(self, steps=100):
        class InsiderSim(SimulationEngine):
            def step(self, current_time):
                # One trader occasionally exhibits suspicious pattern
                trader = next(u for u in self.system.users if u.username == "trader1")
                op = random.choice([o for o in self.system.operations if o.name=="enter_order"])
                zone = random.choice(list(self.system.zones))
                # Use anomaly detector to flag
                features = np.random.randn(15)
                score = self.neural_components[0].predict(features)
                if score > 0.9:
                    action = "block"
                else:
                    action = "allow"
                self.logs.append({
                    "time": current_time.isoformat(),
                    "user": trader.username,
                    "operation": op.name,
                    "zone": zone.name,
                    "anomaly_score": float(score),
                    "action": action
                })
        sim = InsiderSim(self.system, self.permission_engine, storage=None)
        sim.neural_components = [self.anomaly_detector]
        sim.run(datetime.timedelta(minutes=steps), step=datetime.timedelta(seconds=1))
        return sim.analyze()

    def run_all_simulations(self):
        print("="*50)
        print("Global Financial Trading System - Simulations")
        print("="*50)
        print("Normal trading:")
        res1 = self.sim_normal_trading(50)
        print(f"  Total: {res1['total_requests']}, Allowed: {res1['allowed']}, Denied: {res1['denied']}, Allow rate: {res1['allow_rate']:.2%}")
        print("Market crash:")
        res2 = self.sim_market_crash(50)
        print(f"  Total: {res2['total_requests']}, Allowed: {res2['allowed']}, Denied: {res2['denied']}, Allow rate: {res2['allow_rate']:.2%}")
        print("Insider trading detection:")
        res3 = self.sim_insider_trading(50)
        print(f"  Total: {res3['total_requests']}, Allowed: {res3['allowed']}, Denied: {res3['denied']}, Allow rate: {res3['allow_rate']:.2%}")

if __name__ == "__main__":
    fin = FinancialTradingSystem()
    fin.run_all_simulations()