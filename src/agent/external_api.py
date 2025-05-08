# external_api.py - Simulación de API externa para el CRM
import logging
import random
from datetime import datetime
from typing import Any, Dict


class CRMApi:
    """Simulación de API externa para comunicación con el CRM."""

    def __init__(self):
        self.leads_db = {}  # Simulación de base de datos
        self.logger = logging.getLogger("crm_api")

    def register_prelead(self, prelead_data: Dict[str, Any]) -> str:
        """Registra un prelead en el CRM."""
        lead_id = f"L{random.randint(10000, 99999)}"
        self.leads_db[lead_id] = {
            "data": prelead_data,
            "stage": "prelead",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.logger.info(f"Prelead registrado: {lead_id}")
        return lead_id

    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> bool:
        """Actualiza un lead existente a estado completo."""
        if lead_id not in self.leads_db:
            self.logger.error(f"Lead ID no encontrado: {lead_id}")
            return False

        self.leads_db[lead_id].update({
            "data": lead_data,
            "stage": "lead",
            "updated_at": datetime.now().isoformat()
        })
        self.logger.info(f"Lead actualizado: {lead_id}")
        return True

    def enrich_lead(self, lead_id: str, enriched_data: Dict[str, Any]) -> bool:
        """Enriquece un lead con datos adicionales."""
        if lead_id not in self.leads_db:
            self.logger.error(f"Lead ID no encontrado: {lead_id}")
            return False

        self.leads_db[lead_id].update({
            "data": enriched_data,
            "stage": "enriched_lead",
            "updated_at": datetime.now().isoformat()
        })
        self.logger.info(f"Lead enriquecido: {lead_id}")
        return True

    def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """Obtiene el estado actual de un lead."""
        if lead_id not in self.leads_db:
            return {"error": "Lead no encontrado"}

        lead = self.leads_db[lead_id]
        return {
            "lead_id": lead_id,
            "stage": lead["stage"],
            "created_at": lead["created_at"],
            "updated_at": lead["updated_at"]
        }


# Instancia global para usar en herramientas
crm_api = CRMApi()