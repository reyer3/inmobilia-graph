# app.py
from src.agent.memory_setup import checkpointer, store
from src.agent.graph import create_initial_state, workflow  # Removida la importación de 'graph'
from langgraph.func import entrypoint


@entrypoint(checkpointer=checkpointer, store=store)
def inmobilia_agent(input_data: dict) -> dict:
    """Entrypoint principal para el agente inmobiliario."""
    # Inicialización con estado completo
    messages = input_data.get("messages", [])

    # Creamos un estado inicial completo usando la función importada
    initial_state = create_initial_state()
    initial_state["messages"] = messages

    # Ejecutamos el grafo con el estado inicial
    result = workflow.invoke(initial_state)
    return result


# Exportar el grafo para langgraph-cli
graph = inmobilia_agent  # Esta variable es nueva, no es una redeclaración