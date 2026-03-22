"""Simple storage stub. TODO: Implement persistent storage as needed."""
class Storage:
    def __init__(self):
        self._db = {}
    def get(self, key, default=None):
        return self._db.get(key, default)
    def set(self, key, value):
        self._db[key] = value
