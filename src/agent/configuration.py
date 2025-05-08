import os
from enum import Enum
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY es obligatoria")

# URL de Postgres para MCP
POSTGRES_URI = os.getenv("POSTGRES_URI")
if not POSTGRES_URI:
    raise ValueError("POSTGRES_URL es obligatoria para MCP-Postgres")

class ModelType(str, Enum):
    MANAGER     = "manager"
    SPECIALIZED = "specialized"
    GUARDRAIL   = "guardrail"

CONFIG: Dict[str, Any] = {
    "models": {
        ModelType.MANAGER:     os.getenv("MODEL_MANAGER",     "gpt-4o"),
        ModelType.SPECIALIZED: os.getenv("MODEL_SPECIALIZED", "gpt-4o-mini"),
        ModelType.GUARDRAIL:   os.getenv("MODEL_GUARDRAIL",   "gpt-4o-mini"),
    },
    "guardrails": {
        "max_input_length": 500,
        "max_input_length_per_guardrail": {
            "Relevance Guardrail": 300,
            "Security Guardrail": 400,
        },
        "cache_ttl": 300
    },
    "runtime": {
        "max_retries": 3,
    },
    "session": {
        "ttl": int(os.getenv("SESSION_TTL", "3600"))
    },
    # Nueva sección MCP
    "mcp": {
        "servers": {
            "postgres": {
                # Usamos el paquete oficial de MCP-Postgres via NPX
                "command": os.getenv("MCP_PG_COMMAND", "npx"),
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    POSTGRES_URI,
                    # Opcional: puedes añadir flags de esquema/tablas admitidas si el servidor los soporta
                    "--schema=public",
                    "--tables=bd_all_projects,bd_project_units,bd_all_images_project"
                ],
                "transport": "stdio"
            }
        }
    }
}

def get_model(model_type: ModelType) -> ChatOpenAI:
    return ChatOpenAI(
        model=CONFIG["models"][model_type],
        temperature=0.7,
        api_key=OPENAI_API_KEY
    )