"""
memory_setup.py

Define los backends de memoria para LangGraph:
- Short-term memory (thread-level): InMemorySaver (o persistente en producción).
- Long-term memory (cross-thread): InMemoryStore (o persistente en producción).

Ambos son inyectados en los agentes con create_react_agent.
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

# SHORT-TERM MEMORY: guarda el historial de la sesión (thread)
checkpointer = InMemorySaver()

# LONG-TERM MEMORY: guarda datos de usuario o app entre sesiones
store = InMemoryStore()

# Para producción, podrías sustituir por SQLite, Redis, etc.
# from langgraph.checkpoint.sqlite import SqliteSaver
# from langgraph.store.sqlite import SqliteStore
# checkpointer = SqliteSaver(db_file="data/inmobilia_checkpoints.db")
# store = SqliteStore(db_file="data/inmobilia_store.db")