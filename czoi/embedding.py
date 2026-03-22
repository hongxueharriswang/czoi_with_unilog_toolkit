"""Embedding/vector store stubs. TODO: Implement."""
from typing import Any, Dict, List
class VectorStore:
    pass
class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._store: Dict[str, List[float]] = {}
    def put(self, key: str, vec: List[float]):
        self._store[key] = vec
    def get(self, key: str):
        return self._store.get(key)
class EmbeddingService:
    def embed(self, text: str):
        return []
