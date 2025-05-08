# src/agent/memory_setup.py
import os

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

# Obtener la URI de PostgreSQL
POSTGRES_URI = os.getenv("POSTGRES_URI")
if not POSTGRES_URI:
    raise ValueError("POSTGRES_URI es obligatoria")

# SHORT-TERM MEMORY: checkpointer
checkpointer = PostgresSaver(conn=POSTGRES_URI)

# LONG-TERM MEMORY: store entre sesiones
store = PostgresStore(conn=POSTGRES_URI)