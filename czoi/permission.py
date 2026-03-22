"""Permission engine stubs.
TODO: Replace with full implementation from the specification.
"""
from typing import Any, Optional

class PermissionEngine:
    def can_access(self, user: Any, operation: Any, context: Optional[dict] = None) -> bool:
        """Return whether `user` can perform `operation` under `context`."""
        return True

class SimpleEngine(PermissionEngine):
    pass
