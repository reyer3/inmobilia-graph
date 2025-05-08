# src/agent/graph.py

from langchain_core.globals import set_debug, set_verbose
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langgraph.constants import START
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from src.agent.configuration import ModelType, get_model
from src.agent.guardrails import add_guardrails_to_graph
from src.agent.memory_setup import checkpointer, store
from src.agent.prompts import CAPTURA_PROMPT, FILTRADO_PROMPT, SUPERVISOR_PROMPT
from src.agent.state import InmobiliaState
from src.agent.tools import (
    enrich_lead,
    query_project_detail,
    query_project_images,
    query_similar_units,
    query_units_by_project,
    register_lead,
    register_prelead,
    register_property_interest,
    # Herramientas de consulta de propiedades
    sql_query_units,
    # Herramientas de validación y CRM
    validate_customer_data,
)

set_debug(True)
set_verbose(False)

# 1) Pre-model hook para recortar el historial si crece demasiado
def pre_model_trim(state):
    trimmed = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=3500,
        start_on="human",
        end_on=("human", "tool"),
    )
    return {"llm_input_messages": trimmed}

def create_initial_state():
    """Crea un estado inicial con todos los valores por defecto."""
    return InmobiliaState(
        consent_obtained=False,
        lead_registrado=False,
        user_data={},
        preferencias={},
        interaction_history=[],
        context={},
        guardrail_cache={},
        properties_shown=False,
        interaction_count=0
    )

# 2) Crear los agentes con las herramientas específicas para cada uno
filtrado_agent = create_react_agent(
    name="filtrado_agent",
    model=get_model(ModelType.SPECIALIZED),
    # Este agente es especialista en búsqueda de propiedades
    tools=[
        sql_query_units,  # Búsqueda general
        query_project_detail,  # Ver detalles de un proyecto
        query_units_by_project,  # Ver unidades de un proyecto
        query_project_images,  # Ver imágenes de un proyecto
        query_similar_units  # Encontrar unidades similares
    ],
    prompt=FILTRADO_PROMPT,
    state_schema=InmobiliaState,
    checkpointer=checkpointer,
    store=store,
    pre_model_hook=pre_model_trim,
)

captura_agent = create_react_agent(
    name="captura_agent",
    model=get_model(ModelType.SPECIALIZED),
    # Este agente se enfoca en captura de datos y CRM, pero también puede
    # mostrar propiedades específicas si es necesario
    tools=[
        # Herramientas CRM
        validate_customer_data,
        register_prelead,
        register_lead,
        enrich_lead,
        register_property_interest,

        # Acceso limitado a propiedades
        sql_query_units  # Búsqueda general
    ],
    prompt=CAPTURA_PROMPT,
    state_schema=InmobiliaState,
    checkpointer=checkpointer,
    store=store,
    pre_model_hook=pre_model_trim,
)

# 3) Crear el supervisor multiagente
from langgraph_supervisor import create_supervisor

supervisor_agent = create_supervisor(
    agents=[filtrado_agent, captura_agent],
    model=get_model(ModelType.MANAGER),
    prompt=SUPERVISOR_PROMPT,
    state_schema=InmobiliaState,
    output_mode="last_message",
    add_handoff_messages=True,
    supervisor_name="supervisor_inmobiliario",
    include_agent_name="inline"
).compile()

# 4) Armar el StateGraph con guardrails y supervisor
workflow = StateGraph(InmobiliaState)
# Añade nodos y transiciones de guardrails
workflow = add_guardrails_to_graph(workflow)

# Nodo central del supervisor
workflow.add_node("agent_supervisor", supervisor_agent)
# Conecta guardrails → supervisor → siguiente guardrail → ...
# Agregar conexión desde START al primer guardrail
workflow.add_edge(START, "relevance_check")
workflow.add_edge("consent_check", "agent_supervisor")
workflow.add_edge("agent_supervisor", "pii_check")
workflow.add_edge("generate_guardrail_response", END)

# 5) Compilar el grafo
graph = workflow.compile()

# Eliminar la invocación directa para que no se ejecute durante la importación
# result = graph.invoke(create_initial_state())  <- Esta línea se elimina

# Exportar componentes necesarios
__all__ = ["graph", "workflow", "create_initial_state"]