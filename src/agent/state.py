# src/agent/state.py - Solución con inicialización correcta
from typing import Dict, List, Any, Optional
from datetime import datetime

from langgraph.prebuilt.chat_agent_executor import AgentState
from pydantic import Field, model_validator, BaseModel


class InmobiliaState(AgentState):
    """Estado compartido entre los agentes inmobiliarios con soporte de memoria."""
    # Control de consentimiento y estado
    consent_obtained: bool = Field(default=False, description="Indica si se ha obtenido consentimiento")
    lead_registrado: bool = Field(default=False, description="Indica si el lead fue registrado")

    # Datos del usuario capturados
    user_data: Dict[str, Any] = Field(default_factory=dict, description="Datos del usuario capturados")

    # Preferencias inmobiliarias
    preferencias: Dict[str, Any] = Field(default_factory=dict, description="Preferencias inmobiliarias del usuario")

    # Historial de interacciones
    interaction_history: List[Dict[str, Any]] = Field(default_factory=list,
                                                      description="Registro de interacciones previas")

    # Memoria de contexto
    context: Dict[str, Any] = Field(default_factory=dict, description="Información de contexto para summarization")

    # Guardrails cache
    guardrail_cache: Dict[str, Any] = Field(default_factory=dict, description="Cache para resultados de guardrails")

    # Propiedades adicionales
    properties_shown: bool = Field(default=False, description="Indica si se han mostrado propiedades")
    interaction_count: int = Field(default=0, description="Contador de interacciones")

    def add_interaction(self, interaction_type: str, data: Dict[str, Any]) -> None:
        """Registra una nueva interacción."""
        if self.interaction_history is None:
            self.interaction_history = []

        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": interaction_type,
            "data": data
        })