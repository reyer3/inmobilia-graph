import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agent.external_api import crm_api
from src.agent.models import (
    ContactInfo, Document,
    PreLead, Lead, EnrichedLead,
    ValidationResult, RegisterLeadResult,
    YesNo, PropertyType, ZoneOption,
    AreaRange, BedroomsOption, BudgetOption,
    TimeframeOption, PurposeOption, DocType
)
from src.agent.querys import (
    build_query_units, build_query_project_detail,
    build_query_units_by_project, build_query_project_images,
    build_query_similar_units
)
from src.agent.state import InmobiliaState


# ——————————————————————————————————————————————————————
# 1) VALIDACIONES COMUNES
# ——————————————————————————————————————————————————————

def _validate_email(e: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', e))


def _validate_phone(t: str) -> bool:
    return bool(re.match(r'^\+51\d{9}$', t))


def _validate_document(tipo: str, numero: str) -> bool:
    if tipo == "1":      return bool(re.match(r'^\d{8}$', numero))
    if tipo in ("2", "3"): return 3 <= len(numero) <= 15
    return False


@tool("validate_customer_data", parse_docstring=True)
def validate_customer_data(
        state: Annotated[InmobiliaState, InjectedState],
        nombre: Optional[str] = None,
        email: Optional[str] = None,
        telefono: Optional[str] = None,
        tipo_documento: Optional[str] = None,
        numero_documento: Optional[str] = None
) -> ValidationResult:
    """
    Valida los datos personales del cliente según reglas específicas.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Aquí se almacenan/actualizan user_data, interacción y demás.
        nombre (str, optional): Nombre completo del cliente.
        email (str, optional): Correo electrónico (debe validar formato).
        telefono (str, optional): Teléfono en formato +51XXXXXXXXX.
        tipo_documento (str, optional): Código de tipo de doc (1=DNI, 2=Pasaporte, 3=CE).
        numero_documento (str, optional): Número del documento.

    Returns:
        ValidationResult: Objeto con `valid: bool` y posibles `errors: List[str]`.
    """
    errors: List[str] = []
    if email and not _validate_email(email):
        errors.append("Email inválido.")
    if telefono and not _validate_phone(telefono):
        errors.append("Teléfono inválido.")
    if tipo_documento and numero_documento and not _validate_document(tipo_documento, numero_documento):
        errors.append("Documento inválido.")
    if not errors:
        ud = state.get("user_data", {})
        if nombre: ud["nombre"] = nombre
        if email:   ud["email"] = email
        if telefono: ud["telefono"] = telefono
        if tipo_documento: ud["tipo_documento"] = tipo_documento
        if numero_documento: ud["numero_documento"] = numero_documento
        state["user_data"] = ud
    return ValidationResult(valid=not errors, errors=errors)


# ——————————————————————————————————————————————————————
# 2) TOOLS CRM
# ——————————————————————————————————————————————————————

@tool("register_prelead", parse_docstring=True)
def register_prelead(
        state: Annotated[InmobiliaState, InjectedState],
        nombre: str,
        telefono: str,
        tipo_inmueble: str,
        zona: str,
        metraje: str,
        proyecto_id: str = "WEB001"
) -> RegisterLeadResult:
    """
    Registra un prelead con información básica de contacto y preferencias.

    Un prelead es la primera etapa del pipeline de ventas, capturando datos
    mínimos necesarios para un seguimiento inicial.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Almacena lead_id, user_data, etc.
        nombre (str): Nombre completo del cliente.
        telefono (str): Teléfono (+51XXXXXXXXX).
        tipo_inmueble (str): Código de tipo de inmueble (1-5).
        zona (str): Código de zona (1-8).
        metraje (str): Rango de área deseada (1-6).
        proyecto_id (str): ID del proyecto de interés (default "WEB001").

    Returns:
        RegisterLeadResult: Contiene `lead_id`, `status`, `timestamp`, `message` y opcionales `errors`.
    """
    v = validate_customer_data(state, nombre=nombre, telefono=telefono)
    if not v.valid:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message="Datos inválidos", errors=v.errors
        )
    try:
        contacto = ContactInfo(nombre=nombre, telefono=telefono)
        pl = PreLead(
            contacto=contacto,
            tipo_inmueble=PropertyType(tipo_inmueble),
            zona=ZoneOption(zona),
            metraje=AreaRange(metraje),
            consentimiento=YesNo.SI,
            proyecto_id=proyecto_id
        )
        lead_id = crm_api.register_prelead(pl.model_dump())
        ud = state.get("user_data", {})
        ud.update({
            "lead_id": lead_id, "lead_stage": "prelead",
            "nombre": nombre, "telefono": telefono,
            "tipo_inmueble": tipo_inmueble,
            "zona": zona, "metraje": metraje
        })
        state["user_data"] = ud
        return RegisterLeadResult(
            lead_id=lead_id, status="success",
            timestamp=datetime.now().isoformat(),
            message=f"PreLead ID={lead_id}"
        )
    except Exception as e:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message=str(e), errors=[str(e)]
        )


@tool("register_lead", parse_docstring=True)
def register_lead(
        state: Annotated[InmobiliaState, InjectedState],
        email: str,
        habitaciones: str,
        presupuesto: str,
        tiempo_compra: str,
        tiempo_busqueda: str,
        tipo_documento: Optional[str] = None,
        numero_documento: Optional[str] = None
) -> RegisterLeadResult:
    """
    Actualiza un prelead existente a lead completo con datos adicionales.

    Un lead completo incluye información más detallada sobre preferencias
    y documentación necesaria para avanzar en el proceso de compra.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
        email (str): Correo del cliente.
        habitaciones (str): # de habitaciones (1-5).
        presupuesto (str): Rango de presupuesto (1-6).
        tiempo_compra (str): Plazo compra (1-4).
        tiempo_busqueda (str): Tiempo de búsqueda (1-4).
        tipo_documento (str, optional): Tipo doc (1-3).
        numero_documento (str, optional): Número de doc.

    Returns:
        RegisterLeadResult: Resultado de la actualización.
    """
    ud = state.get("user_data", {})
    if "lead_id" not in ud:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message="No existe prelead", errors=["Prelead no encontrado"]
        )
    v = validate_customer_data(
        state, email=email,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento
    )
    if not v.valid:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message="Datos inválidos", errors=v.errors
        )
    try:
        contacto = ContactInfo(
            nombre=ud["nombre"], telefono=ud["telefono"], email=email
        )
        doc = None
        if tipo_documento and numero_documento:
            doc = Document(
                tipo=DocType(tipo_documento), numero=numero_documento
            )
        lead = Lead(
            contacto=contacto,
            tipo_inmueble=PropertyType(ud["tipo_inmueble"]),
            zona=ZoneOption(ud["zona"]),
            metraje=AreaRange(ud["metraje"]),
            habitaciones=BedroomsOption(habitaciones),
            presupuesto=BudgetOption(presupuesto),
            tiempo_compra=TimeframeOption(tiempo_compra),
            tiempo_busqueda=TimeframeOption(tiempo_busqueda),
            document=doc,
            consentimiento=YesNo.SI,
            proyecto_id=ud.get("proyecto_id", "WEB001")
        )
        ok = crm_api.update_lead(ud["lead_id"], lead.model_dump())
        if not ok:
            raise RuntimeError("CRM update_lead falló")
        ud.update({
            "email": email, "habitaciones": habitaciones,
            "presupuesto": presupuesto,
            "tiempo_compra": tiempo_compra,
            "tiempo_busqueda": tiempo_busqueda,
            "lead_stage": "lead"
        })
        state["user_data"] = ud
        return RegisterLeadResult(
            lead_id=ud["lead_id"], status="success",
            timestamp=datetime.now().isoformat(),
            message=f"Lead actualizado ID={ud['lead_id']}"
        )
    except Exception as e:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message=str(e), errors=[str(e)]
        )


@tool("enrich_lead", parse_docstring=True)
def enrich_lead(
        state: Annotated[InmobiliaState, InjectedState],
        credito_preaprobado: str,
        cuota_inicial: str,
        proposito: str
) -> RegisterLeadResult:
    """
    Enriquece un lead existente con información financiera y de intención.

    Esta etapa avanzada permite calificar mejor al lead, determinando
    su capacidad financiera y nivel de seriedad en la intención de compra.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
        credito_preaprobado (str): "SI" o "NO".
        cuota_inicial (str): "SI" o "NO".
        proposito (str): one of "vivienda_principal", "inversión", "segunda_vivienda".

    Returns:
        RegisterLeadResult: Resultado del enriquecimiento.
    """
    ud = state.get("user_data", {})
    if "lead_id" not in ud or "email" not in ud:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message="No existe lead completo", errors=["Lead no encontrado"]
        )
    try:
        contacto = ContactInfo(
            nombre=ud["nombre"], telefono=ud["telefono"], email=ud["email"]
        )
        doc = None
        if ud.get("tipo_documento") and ud.get("numero_documento"):
            doc = Document(
                tipo=DocType(ud["tipo_documento"]),
                numero=ud["numero_documento"]
            )
        enriched = EnrichedLead(
            contacto=contacto,
            tipo_inmueble=PropertyType(ud["tipo_inmueble"]),
            zona=ZoneOption(ud["zona"]),
            metraje=AreaRange(ud["metraje"]),
            habitaciones=BedroomsOption(ud["habitaciones"]),
            presupuesto=BudgetOption(ud["presupuesto"]),
            tiempo_compra=TimeframeOption(ud["tiempo_compra"]),
            tiempo_busqueda=TimeframeOption(ud["tiempo_busqueda"]),
            credito_preaprobado=YesNo(credito_preaprobado),
            cuota_inicial=YesNo(cuota_inicial),
            proposito=PurposeOption(proposito),
            document=doc,
            consentimiento=YesNo.SI,
            proyecto_id=ud.get("proyecto_id", "WEB001")
        )
        ok = crm_api.enrich_lead(ud["lead_id"], enriched.model_dump())
        if not ok:
            raise RuntimeError("CRM enrich_lead falló")
        ud.update({
            "credito_preaprobado": credito_preaprobado,
            "cuota_inicial": cuota_inicial,
            "proposito": proposito,
            "lead_stage": "enriched_lead"
        })
        state["user_data"] = ud
        return RegisterLeadResult(
            lead_id=ud["lead_id"], status="success",
            timestamp=datetime.now().isoformat(),
            message=f"Lead enriquecido ID={ud['lead_id']}"
        )
    except Exception as e:
        return RegisterLeadResult(
            lead_id="", status="error",
            timestamp=datetime.now().isoformat(),
            message=str(e), errors=[str(e)]
        )


# ——————————————————————————————————————————————————————
# 3) TOOLS PROPIEDADES
# ——————————————————————————————————————————————————————

def _map_budget(max_price: float) -> str:
    if max_price <= 350_000: return "1"
    if max_price <= 500_000: return "2"
    if max_price <= 650_000: return "3"
    if max_price <= 800_000: return "4"
    if max_price <= 1_000_000: return "5"
    return "6"


def generate_fallback_properties(
        zona: Optional[str] = None,
        tipo: Optional[str] = None,
        max_precio: Optional[float] = None,
        habitaciones: Optional[int] = None,
        max_results: int = 2
) -> List[Dict[str, Any]]:
    zd = zona or "Lima"
    tipo = tipo or "Departamento"
    base = max_precio * 0.9 if max_precio else 150_000
    hab = habitaciones or 2
    out = []
    for i in range(max_results):
        out.append({
            "id": f"FB-{zd}-{i + 1}",
            "titulo": f"{tipo} en {zd}",
            "precio": base * (1 + 0.05 * i),
            "habitaciones": hab + i,
            "descripcion": f"Propiedad en {zd} con {hab + i} habitaciones.",
            "amenidades": ["Seguridad 24/7", "Estacionamiento"],
            "fotos": []
        })
    return out


# ——————————————————————————————————————————————————————
# 4) TOOLS INTERÉS & SIMILARES
# ——————————————————————————————————————————————————————

@tool("register_property_interest", parse_docstring=True)
def register_property_interest(
        state: Annotated[InmobiliaState, InjectedState],
        property_id: str,
        interest_level: str = "alto"
) -> Dict[str, Any]:
    """
    Registra el interés del cliente en una propiedad específica.

    Esta función permite trackear qué propiedades generan mayor interés
    y ayuda a priorizar leads en base a su comportamiento.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
        property_id: Identificador único de la propiedad
        interest_level: Nivel de interés (bajo/medio/alto)

    Returns:
        Resultado del registro con estado y mensaje
    """
    ud = state.get("user_data", {})
    if not ud.get("nombre") or not ud.get("telefono"):
        return {"status": "error", "message": "Faltan datos básicos"}
    ints = ud.get("propiedades_interes", [])
    now = datetime.now().isoformat()
    for i, x in enumerate(ints):
        if x["id"] == property_id:
            ints[i] = {"id": property_id, "nivel": interest_level, "timestamp": now}
            break
    else:
        ints.append({"id": property_id, "nivel": interest_level, "timestamp": now})
    ud["propiedades_interes"] = ints
    state["user_data"] = ud
    return {"status": "success", "message": f"Interés registrado en {property_id}"}


# ——————————————————————————————————————————————————————
# 5) TOOLS SQL
# ——————————————————————————————————————————————————————
@tool("sql_query_units", parse_docstring=True)
def sql_query_units(
        state: Annotated[InmobiliaState, InjectedState],
        zona: Optional[str] = None,
        tipo_propiedad: Optional[str] = None,
        min_precio: Optional[float] = None,
        max_precio: Optional[float] = None,
        habitaciones: Optional[int] = None,
        limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Busca propiedades según criterios específicos consultando la base de datos.

    Permite filtrar por zona, tipo, precio y habitaciones, ofreciendo
    resultados formateados listos para mostrar al usuario.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Se actualizan `properties_shown`, `interaction_count` y `user_data`.
        zona (str, optional): Distrito o zona.
        tipo_propiedad (str, optional): "departamento", "casa", etc.
        min_precio (float, optional): Precio mínimo USD.
        max_precio (float, optional): Precio máximo USD.
        habitaciones (int, optional): Mínimo # de habitaciones.
        limit (int): Máximo resultados a devolver.

    Returns:
        List[Dict[str, Any]]: Lista de propiedades formateadas.
    """
    # Actualizar el estado igual que hacía query_properties
    state["properties_shown"] = True
    state["interaction_count"] = state.get("interaction_count", 0) + 1
    ud = state.get("user_data", {})
    if zona and not ud.get("zona"): ud["zona"] = zona
    if tipo_propiedad and not ud.get("tipo_inmueble"): ud["tipo_inmueble"] = tipo_propiedad
    if habitaciones and not ud.get("habitaciones"): ud["habitaciones"] = str(habitaciones)
    if max_precio and not ud.get("presupuesto"):
        ud["presupuesto"] = _map_budget(max_precio)
    state["user_data"] = ud

    # Construir SQL y ejecutar
    import psycopg2.extras
    from src.agent.configuration import POSTGRES_URI

    sql = build_query_units(zona, tipo_propiedad, min_precio, max_precio, habitaciones, limit)

    try:
        conn = psycopg2.connect(POSTGRES_URI)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()

            # Convertir a formato esperado (estructura similar a la que retornaba project_units_to_properties)
            formatted_results = []
            for row in results:
                formatted_results.append({
                    "id": f"DB-{row['id']}",
                    "titulo": row['titulo'] or f"{tipo_propiedad or 'Propiedad'} en {zona or 'Lima'}",
                    "precio": row['precio'],
                    "habitaciones": row['habitaciones'],
                    "banios": row.get('banios'),
                    "area": row.get('area'),
                    "descripcion": f"Propiedad en {row.get('zona', zona or 'Lima')} con {row['habitaciones']} habitaciones.",
                    "proyecto": row.get('proyecto'),
                    "amenidades": [],  # Puedes adaptarlo si tienes esta información
                    "fotos": []  # Puedes adaptarlo si tienes URLs de imágenes
                })

            if not formatted_results:
                return generate_fallback_properties(zona, tipo_propiedad, max_precio, habitaciones)

            return formatted_results
    except Exception as e:
        # Log error y devolver fallback properties
        print(f"Error ejecutando SQL: {e}")
        return generate_fallback_properties(zona, tipo_propiedad, max_precio, habitaciones)
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@tool("query_project_detail", parse_docstring=True)
def query_project_detail(
        state: Annotated[InmobiliaState, InjectedState],
        project_id: int
) -> Dict[str, Any]:
    """
    Obtiene detalles completos de un proyecto inmobiliario específico.

    Consulta toda la información relacionada con un proyecto en particular,
    incluyendo ubicación, inmobiliaria, características principales, etc.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Se actualizan `properties_shown`, `interaction_count` y `user_data`.
        project_id: Identificador único del proyecto

    Returns:
        Datos completos del proyecto solicitado
    """
    import psycopg2.extras
    from src.agent.configuration import POSTGRES_URI

    sql = build_query_project_detail(project_id)

    try:
        conn = psycopg2.connect(POSTGRES_URI)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()

            if not result:
                return {"error": f"No se encontró el proyecto con ID {project_id}"}

            return dict(result)
    except Exception as e:
        print(f"Error ejecutando SQL: {e}")
        return {"error": f"Error al consultar el proyecto: {str(e)}"}
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@tool("query_units_by_project", parse_docstring=True)
def query_units_by_project(
        state: Annotated[InmobiliaState, InjectedState],
        project_id: int
) -> List[Dict[str, Any]]:
    """
    Lista todas las unidades disponibles en un proyecto específico.

    Permite explorar todas las opciones dentro de un mismo proyecto,
    facilitando la comparación entre diferentes unidades.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Se actualizan `properties_shown`, `interaction_count` y `user_data`.
        project_id: Identificador único del proyecto

    Returns:
        Lista de unidades disponibles con sus características
    """
    import psycopg2.extras
    from src.agent.configuration import POSTGRES_URI

    sql = build_query_units_by_project(project_id)

    try:
        conn = psycopg2.connect(POSTGRES_URI)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()

            if not results:
                return []

            formatted_results = []
            for row in results:
                formatted_results.append({
                    "id": f"U-{project_id}-{row['titulo']}",
                    "titulo": row['titulo'],
                    "precio": row['precio'],
                    "habitaciones": row['habitaciones'],
                    "banios": row.get('banios'),
                    "area": row.get('area'),
                    "tipologia": row.get('tipologia'),
                    "imagen": row.get('imagen_principal')
                })
            return formatted_results
    except Exception as e:
        print(f"Error ejecutando SQL: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@tool("query_project_images", parse_docstring=True)
def query_project_images(
        state: Annotated[InmobiliaState, InjectedState],
        project_id: int
) -> List[Dict[str, str]]:
    """
    Obtiene todas las imágenes disponibles de un proyecto.

    Recupera las URLs de imágenes en diferentes resoluciones,
    permitiendo mostrar galerías visuales de los proyectos.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Se actualizan `properties_shown`, `interaction_count` y `user_data`.
        project_id: Identificador único del proyecto

    Returns:
        Lista de imágenes con tipo y URL
    """
    import psycopg2.extras
    from src.agent.configuration import POSTGRES_URI

    sql = build_query_project_images(project_id)

    try:
        conn = psycopg2.connect(POSTGRES_URI)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()

            if not results:
                return []

            return [{"tipo": row["tipo"], "url": row["url"]} for row in results]
    except Exception as e:
        print(f"Error ejecutando SQL: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@tool("query_similar_units", parse_docstring=True)
def query_similar_units(
        state: Annotated[InmobiliaState, InjectedState],
        unit_id: int,
        max_results: int = 3
) -> List[Dict[str, Any]]:
    """
    Encuentra unidades similares a una unidad específica.

    Busca propiedades con características y precio similares,
    facilitando la comparación y ofreciendo alternativas al cliente.

    Args:
        state (InmobiliaState): Estado compartido inyectado.
            Se actualizan `properties_shown`, `interaction_count` y `user_data`.
        unit_id: Identificador de la unidad de referencia
        max_results: Cantidad máxima de resultados similares

    Returns:
        Lista de unidades similares a la de referencia
    """
    import psycopg2.extras
    from src.agent.configuration import POSTGRES_URI

    sql = build_query_similar_units(unit_id, max_results)

    try:
        conn = psycopg2.connect(POSTGRES_URI)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()

            if not results:
                return []

            formatted_results = []
            for row in results:
                formatted_results.append({
                    "id": f"U-{row['id']}",
                    "titulo": row['titulo'],
                    "precio": row['precio'],
                    "habitaciones": row['habitaciones'],
                    "zona": row.get('zona', "Lima")
                })
            return formatted_results
    except Exception as e:
        print(f"Error ejecutando SQL: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()