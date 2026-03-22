"""
Simulation module for the CZOI toolkit.

Provides a base class for running discrete-time simulations of CZOA systems,
with logging and analysis capabilities.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from czoi.core import System
from czoi.permission import PermissionEngine
from czoi.storage import Storage


logger = logging.getLogger(__name__)


class SimulationEngine(ABC):
    """
    Base class for running simulations of a CZOA system.

    Subclasses must implement the `step` method, which defines the behavior
    at each time tick. The `run` method advances time and calls `step`
    repeatedly.

    Attributes:
        system (System): The CZOA system under simulation.
        permission_engine (PermissionEngine): Engine for access decisions.
        storage (Storage, optional): Persistence layer for logging events.
        logs (List[Dict]): List of logged events (each a dict with timestamp, type, data).
        current_time (datetime): Current simulation time.
    """

    def __init__(
        self,
        system: System,
        permission_engine: PermissionEngine,
        storage: Optional[Storage] = None,
        start_time: Optional[datetime] = None,
    ):
        self.system = system
        self.permission_engine = permission_engine
        self.storage = storage
        self.logs: List[Dict] = []
        self.current_time = start_time or datetime.utcnow()

    @abstractmethod
    def step(self) -> None:
        """
        Execute one simulation step.

        This method should update the system state, generate events,
        log outcomes, and potentially call the permission engine.
        """
        raise NotImplementedError

    def run(self, duration: Union[timedelta, float], step_delta: timedelta = timedelta(seconds=1)) -> None:
        """
        Run the simulation for a given duration.

        Args:
            duration: How long to simulate (timedelta or seconds as float).
            step_delta: Time interval between steps (default 1 second).
        """
        if isinstance(duration, (int, float)):
            duration = timedelta(seconds=duration)

        end_time = self.current_time + duration
        logger.info(f"Starting simulation from {self.current_time} to {end_time}")

        while self.current_time < end_time:
            self.step()
            self.current_time += step_delta

        logger.info("Simulation finished")

    def log_event(self, event_type: str, data: Optional[Dict] = None) -> None:
        """
        Log an event during the simulation.

        Args:
            event_type: A string identifying the event (e.g., "access_attempt").
            data: Additional data associated with the event.
        """
        event = {
            "timestamp": self.current_time.isoformat(),
            "type": event_type,
            "data": data or {},
        }
        self.logs.append(event)
        logger.debug(f"Logged event: {event_type}")

        if self.storage:
            # Persist to storage if available (implementation depends on storage schema)
            self.storage.save_simulation_event(event)

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze the collected logs and return summary statistics.

        Returns:
            A dictionary containing metrics such as:
                - total_events: total number of logged events
                - event_counts: per‑type event counts
                - first_timestamp, last_timestamp
        """
        event_types = {}
        for event in self.logs:
            t = event["type"]
            event_types[t] = event_types.get(t, 0) + 1

        return {
            "total_events": len(self.logs),
            "event_counts": event_types,
            "first_timestamp": self.logs[0]["timestamp"] if self.logs else None,
            "last_timestamp": self.logs[-1]["timestamp"] if self.logs else None,
        }

    def save_logs(self, path: str) -> None:
        """
        Save logs to a JSON file.

        Args:
            path: Output file path.
        """
        with open(path, "w") as f:
            json.dump(self.logs, f, indent=2)


class SimpleSimulationEngine(SimulationEngine):
    """
    A concrete simulation engine that runs a user‑defined step function.

    This allows quick prototyping without subclassing.

    Attributes:
        step_function (callable): A function that takes (engine, current_time) and
            performs one step. It can access `engine.system`, `engine.permission_engine`,
            and call `engine.log_event`.
    """

    def __init__(self, step_function, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step_function = step_function

    def step(self) -> None:
        self.step_function(self, self.current_time)