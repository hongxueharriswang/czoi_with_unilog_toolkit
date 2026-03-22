from abc import ABC, abstractmethod
import asyncio
import logging
from typing import List, Optional, Any, Dict, Union
from .core import System
from .permission import PermissionEngine
from .unilog.parser import UniLangParser
from .unilog.engine import InferenceEngine
from .unilog.integration import CZOIModelAdapter
from .unilog.ast.base import Formula
from .storage import Storage

class Daemon(ABC):
    def __init__(self, name: str, interval: float = 1.0):
        self.name = name
        self.interval = interval
        self.running = False
        self.logger = logging.getLogger(f"daemon.{name}")

    @abstractmethod
    async def check(self) -> List[str]:
        pass

    async def execute(self, action: str):
        self.logger.info(f"Executing action: {action}")

    async def run(self):
        self.running = True
        while self.running:
            try:
                actions = await self.check()
                for action in actions:
                    await self.execute(action)
            except Exception as e:
                self.logger.error(f"Error in check: {e}")
            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False

class SecurityDaemon(Daemon):
    def __init__(self, storage: 'Storage', permission_engine: PermissionEngine,
                 threshold: float = 0.8, interval: float = 1.0):
        super().__init__("security", interval)
        self.storage = storage
        self.permission_engine = permission_engine
        self.threshold = threshold
        self.anomaly_detector = None  # would load a model

    async def check(self) -> List[str]:
        # In real implementation, would analyze logs
        return []

class ComplianceDaemon(Daemon):
    def __init__(self, storage: 'Storage', interval: float = 60.0):
        super().__init__("compliance", interval)
        self.storage = storage

    async def check(self) -> List[str]:
        # Check for violations
        return []

# New: TriggeredDaemon that uses UniLang formulas
class TriggeredDaemon(Daemon):
    """Daemon that triggers actions based on UniLang formulas evaluated on system state."""
    def __init__(self, name: str, formula: Union[str, 'Formula'], interval: float = 1.0):
        super().__init__(name, interval)
        if isinstance(formula, str):
            parser = UniLangParser()
            self.formula = parser.parse_string(formula)
        else:
            self.formula = formula
        self.engine = InferenceEngine.get_instance()

    async def check(self) -> List[str]:
        # Need to get current system state; this would be passed or stored.
        # For simplicity, assume we have access to a system via self.system.
        # We'll implement later.
        return []