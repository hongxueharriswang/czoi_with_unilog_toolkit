"""CZOI: Constrained Zoned-Object Implementation toolkit.
A Python implementation of the CZOA framework for building intelligent organizational systems.
"""
from .core import Zone, Role, User, Application, Operation, GammaMapping, System
from .permission import PermissionEngine, SimpleEngine
from .constraint import Constraint, ConstraintType, ConstraintManager
from .neural import NeuralComponent, AnomalyDetector, RoleMiner
from .embedding import VectorStore, InMemoryVectorStore, EmbeddingService
from .daemon import Daemon, SecurityDaemon, ComplianceDaemon
from .simulation import SimulationEngine
from .storage import Storage
from . import utils, logic

__all__ = [
    'Zone', 'Role', 'User', 'Application', 'Operation', 'GammaMapping', 'System',
    'PermissionEngine', 'SimpleEngine',
    'Constraint', 'ConstraintType', 'ConstraintManager',
    'NeuralComponent', 'AnomalyDetector', 'RoleMiner',
    'VectorStore', 'InMemoryVectorStore', 'EmbeddingService',
    'Daemon', 'SecurityDaemon', 'ComplianceDaemon',
    'SimulationEngine', 'Storage', 'utils', 'unilog'
]

__version__ = '0.2.0'
