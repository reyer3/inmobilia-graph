# src/agent/mcp_setup.py
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.agent.configuration import CONFIG


def setup_mcp_client():
    """Configura y devuelve un cliente MCP y sus herramientas usando la configuración existente."""
    # Usar la configuración existente
    mcp_conf = CONFIG["mcp"]["servers"]

    # Inicializar el cliente MCP
    mcp_client = MultiServerMCPClient(mcp_conf)

    # Entrar en context manager para que el cliente quede listo
    asyncio.get_event_loop().run_until_complete(mcp_client.__aenter__())

    # Recuperar herramientas
    mcp_tools = mcp_client.get_tools()

    # Obtener la herramienta query específicamente
    query_tool = next(t for t in mcp_tools if t.name == "query")

    return mcp_client, mcp_tools, query_tool