from datetime import date
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import (
    BaseModel, Field, EmailStr, HttpUrl,
    field_validator, model_validator, ConfigDict
)


# ===========================
# 1) ENUMS
# ===========================

class YesNo(str, Enum):
    SI = "SI"
    NO = "NO"


class PropertyType(str, Enum):
    DEPARTAMENTO = "1"
    CASA = "2"
    OFICINA = "3"
    LOTE = "4"
    OTRO = "5"


class ZoneOption(str, Enum):
    LIMA_TOP = "1";
    LIMA_MODERNA = "2";
    LIMA_CENTRO = "3"
    LIMA_SUR = "4";
    LIMA_NORTE = "5";
    LIMA_ESTE = "6"
    CALLAO = "7";
    FUERA_LIMA = "8"


class AreaRange(str, Enum):
    MENOS_40 = "1";
    DE_41_A_70 = "2";
    DE_71_A_90 = "3"
    DE_91_A_110 = "4";
    DE_111_A_130 = "5";
    MAS_130 = "6"


class DocType(str, Enum):
    DNI = "1"
    PASAPORTE = "2"
    CARNET_EXTRANJERIA = "3"


class BedroomsOption(str, Enum):
    UNO = "1";
    DOS = "2";
    TRES = "3";
    CUATRO = "4";
    CINCO_MAS = "5"


class BudgetOption(str, Enum):
    MENOS_350K = "1";
    ENTRE_350K_500K = "2";
    ENTRE_500K_650K = "3"
    ENTRE_650K_800K = "4";
    ENTRE_800K_1M = "5";
    MAS_1M = "6"


class TimeframeOption(str, Enum):
    HASTA_3_MESES = "1";
    HASTA_6_MESES = "2"
    HASTA_12_MESES = "3";
    MAS_12_MESES = "4"


class PurposeOption(str, Enum):
    VIVIENDA_PRINCIPAL = "vivienda_principal"
    INVERSION = "inversión"
    SEGUNDA_VIVIENDA = "segunda_vivienda"


# Modelos de conversacion / CRM

class Document(BaseModel):
    tipo: DocType
    numero: str = Field(
        strip_whitespace=True,
        min_length=3,
        max_length=15,
        pattern=r"^[A-Za-z0-9]+$"
    )
    model_config = ConfigDict(extra='forbid')


class ContactInfo(BaseModel):
    nombre: str = Field(min_length=1)
    telefono: str = Field(pattern=r"^\+51\d{9}$")
    email: Optional[EmailStr] = None
    model_config = ConfigDict(extra='forbid')


class PreLead(BaseModel):
    contacto: ContactInfo
    tipo_inmueble: PropertyType
    consentimiento: YesNo
    proyecto_id: str = Field(min_length=1)
    zona: ZoneOption
    metraje: AreaRange
    model_config = ConfigDict(extra='forbid')


class Lead(PreLead):
    contacto: ContactInfo = Field(..., description="ContactInfo con email obligatorio")
    document: Optional[Document] = None
    habitaciones: BedroomsOption
    presupuesto: BudgetOption
    tiempo_compra: TimeframeOption
    tiempo_busqueda: TimeframeOption
    model_config = ConfigDict(extra='forbid')


class EnrichedLead(Lead):
    credito_preaprobado: YesNo
    cuota_inicial: YesNo
    proposito: PurposeOption
    model_config = ConfigDict(extra='forbid')


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str]
    model_config = ConfigDict(extra='forbid')


class RegisterLeadResult(BaseModel):
    lead_id: str
    status: str
    timestamp: str
    message: str
    errors: Optional[List[str]] = None
    model_config = ConfigDict(extra='forbid')


# ===========================
# 2) MODELOS INMOBILIARIOS
# ===========================

class ProyectoFase(str, Enum):
    PLANOS = "planos"
    CONSTRUCCION = "construccion"
    ENTREGA_INMEDIATA = "entrega_inmediata"
    TERMINADO = "terminado"


class ProyectoTipo(str, Enum):
    DEPARTAMENTOS = "departamentos"
    CASAS = "casas"
    OFICINAS = "oficinas"
    LOTES = "lotes"
    MIXTO = "mixto"


class TipologiaTipo(str, Enum):
    FLAT = "flat";
    DUPLEX = "duplex";
    TRIPLEX = "triplex"
    PENTHOUSE = "penthouse";
    STUDIO = "studio"


class UnidadVista(str, Enum):
    INTERIOR = "interior";
    EXTERIOR = "exterior";
    CALLE = "calle"
    PARQUE = "parque";
    CIUDAD = "ciudad";
    MAR = "mar"


class Inmobiliaria(BaseModel):
    nombre: str = Field(..., alias="inmobiliaria")
    logo: Optional[HttpUrl] = Field(None, alias="inmobiliaria_logo")
    ruc: Optional[int] = Field(None, alias="inmobiliaria_ruc")


class Tipologia(BaseModel):
    tipo: Optional[TipologiaTipo] = Field(None, alias="tipologia_tipo")
    codigo: Optional[str] = Field(None, alias="tipologia_codigo")
    stock: Optional[int] = Field(None, alias="tipologia_stock")
    imagen_full: Optional[HttpUrl] = Field(None, alias="tipologia_imagen_full")
    imagen_xmedium: Optional[HttpUrl] = Field(None, alias="tipologia_imagen_xmedium")

    @field_validator("tipo", mode="before")
    @classmethod
    def _norm_tipo(cls, v):
        if not v: return None
        m = {
            "flat": TipologiaTipo.FLAT, "departamento": TipologiaTipo.FLAT,
            "duplex": TipologiaTipo.DUPLEX, "triplex": TipologiaTipo.TRIPLEX,
            "penthouse": TipologiaTipo.PENTHOUSE, "studio": TipologiaTipo.STUDIO,
            "estudio": TipologiaTipo.STUDIO
        }
        return m.get(str(v).lower(), v)


class Unidad(BaseModel):
    nombre: str = Field(..., alias="unidad_nombre")
    num_banios: Optional[float] = Field(None, alias="unidad_num_banios")
    num_dormitorios: Optional[float] = Field(None, alias="unidad_num_dormitorios")
    area_techada: Optional[float] = Field(None, alias="unidad_area_techada")
    area_total: Optional[float] = Field(None, alias="unidad_area_total")
    numero_piso: Optional[int] = Field(None, alias="unidad_numero_piso")
    vista: Optional[UnidadVista] = Field(None, alias="unidad_vista")
    precio: Optional[float] = Field(None, alias="unidad_precio")

    @field_validator("vista", mode="before")
    @classmethod
    def _norm_vista(cls, v):
        if not v: return None
        m = {
            "interior": UnidadVista.INTERIOR, "exterior": UnidadVista.EXTERIOR,
            "calle": UnidadVista.CALLE, "parque": UnidadVista.PARQUE,
            "ciudad": UnidadVista.CIUDAD, "mar": UnidadVista.MAR
        }
        return m.get(str(v).lower(), v)

    @property
    def precio_formatted(self) -> str:
        return f"${int(self.precio):,}" if self.precio else "Precio no disponible"

    @property
    def descripcion_corta(self) -> str:
        parts = []
        if self.num_dormitorios: parts.append(f"{int(self.num_dormitorios)} hab.")
        if self.num_banios:     parts.append(f"{int(self.num_banios)} baños")
        if self.area_total:     parts.append(f"{int(self.area_total)} m²")
        if self.precio:         parts.append(self.precio_formatted)
        return ", ".join(parts)


class ProyectoBase(BaseModel):
    project_id: int
    nombre: str = Field(..., alias="proyecto_nombre")


class ProyectoCompleto(ProyectoBase):
    inmobiliaria: str
    inmobiliaria_logo: Optional[HttpUrl] = None
    inmobiliaria_ruc: Optional[int] = None
    proyecto_video: Optional[HttpUrl] = None
    proyecto_tour_virtual: Optional[HttpUrl] = None
    proyecto_logo: Optional[HttpUrl] = None
    proyecto_fase: Optional[ProyectoFase] = None
    proyecto_fase_de_construccion: Optional[str] = None
    proyecto_tipo: Optional[ProyectoTipo] = None
    proyecto_financiado_por_banco: Optional[str] = None
    proyecto_direccion_departamento: Optional[str] = None
    proyecto_direccion_provincia: Optional[str] = None
    proyecto_direccion_distrito: Optional[str] = None
    proyecto_direccion: Optional[str] = None
    proyecto_servicios: Optional[str] = None
    proyecto_fecha_entrega_proyecto: Optional[date] = None
    proyecto_total_unidades: Optional[int] = None
    proyecto_total_estacionamientos: Optional[int] = None
    proyecto_total_depositos: Optional[int] = None
    proyecto_total_etapas: Optional[int] = None
    proyecto_total_pisos: Optional[int] = None
    proyecto_total_sotanos: Optional[int] = None
    proyecto_total_ascensores: Optional[int] = None
    proyecto_imagen_principal_full: Optional[HttpUrl] = None
    proyecto_imagen_principal_xmedium: Optional[HttpUrl] = None
    proyecto_imagen_principal_small: Optional[HttpUrl] = None

    @field_validator("proyecto_fase", mode="before")
    @classmethod
    def _norm_fase(cls, v):
        if not v: return None
        m = {
            "planos": ProyectoFase.PLANOS, "en planos": ProyectoFase.PLANOS,
            "construccion": ProyectoFase.CONSTRUCCION, "en construccion": ProyectoFase.CONSTRUCCION,
            "entrega inmediata": ProyectoFase.ENTREGA_INMEDIATA, "terminado": ProyectoFase.TERMINADO
        }
        return m.get(str(v).lower(), v)

    @field_validator("proyecto_tipo", mode="before")
    @classmethod
    def _norm_ptipo(cls, v):
        if not v: return None
        m = {
            "departamentos": ProyectoTipo.DEPARTAMENTOS, "departamento": ProyectoTipo.DEPARTAMENTOS,
            "casas": ProyectoTipo.CASAS, "casa": ProyectoTipo.CASAS,
            "oficinas": ProyectoTipo.OFICINAS, "oficina": ProyectoTipo.OFICINAS,
            "lotes": ProyectoTipo.LOTES, "lote": ProyectoTipo.LOTES,
            "mixto": ProyectoTipo.MIXTO
        }
        return m.get(str(v).lower(), v)

    @field_validator("proyecto_fecha_entrega_proyecto", mode="before")
    @classmethod
    def _parse_fecha(cls, v):
        if not v: return None
        from datetime import datetime
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(v, fmt).date()
            except:
                continue
        return None

    def get_servicios_list(self) -> List[str]:
        if not self.proyecto_servicios: return []
        for sep in [',', ';', '|', '•']:
            if sep in self.proyecto_servicios:
                return [s.strip() for s in self.proyecto_servicios.split(sep) if s.strip()]
        return [self.proyecto_servicios.strip()]

    @property
    def zona(self) -> str:
        parts = []
        d = self.proyecto_direccion_distrito
        p = self.proyecto_direccion_provincia
        if d: parts.append(d)
        if p and p != d: parts.append(p)
        return ", ".join(parts)

    @property
    def descripcion_corta(self) -> str:
        parts = []
        if self.proyecto_tipo: parts.append(str(self.proyecto_tipo).capitalize())
        if self.zona:          parts.append(f"en {self.zona}")
        if self.proyecto_fase: parts.append(f"- {str(self.proyecto_fase).replace('_', ' ').capitalize()}")
        return " ".join(parts)


class ProjectUnit(BaseModel):
    inmobiliaria: Inmobiliaria
    proyecto: ProyectoCompleto
    tipologia: Tipologia
    unidad: Unidad

    @model_validator(mode="after")
    def _extract(cls, values):
        inm = {
            "inmobiliaria": values.inmobiliaria,
            "inmobiliaria_logo": values.inmobiliaria_logo,
            "inmobiliaria_ruc": values.inmobiliaria_ruc,
        }
        values.inmobiliaria = Inmobiliaria.model_validate(inm)

        proj = {k: v for k, v in values.model_dump().items() if k.startswith("proyecto_") or k == "project_id"}
        proj["proyecto_nombre"] = values.proyecto.nombre
        values.proyecto = ProyectoCompleto.model_validate(proj)

        tipo = {k: v for k, v in values.model_dump().items() if k.startswith("tipologia_")}
        values.tipologia = Tipologia.model_validate(tipo)

        uni = {k: v for k, v in values.model_dump().items() if k.startswith("unidad_")}
        values.unidad = Unidad.model_validate(uni)

        return values

    def to_dict_for_display(self) -> Dict[str, Any]:
        return {
            "id": f"U-{self.proyecto.project_id}-{self.unidad.nombre}",
            "titulo": f"{self.unidad.nombre} en {self.proyecto.nombre}",
            "precio": self.unidad.precio_formatted,
            "habitaciones": int(self.unidad.num_dormitorios) if self.unidad.num_dormitorios else None,
            "baños": int(self.unidad.num_banios) if self.unidad.num_banios else None,
            "area": int(self.unidad.area_total) if self.unidad.area_total else None,
            "piso": self.unidad.numero_piso,
            "vista": str(self.unidad.vista).capitalize() if self.unidad.vista else None,
            "tipologia": str(self.tipologia.tipo).capitalize() if self.tipologia.tipo else None,
            "inmobiliaria": self.inmobiliaria.nombre,
            "proyecto": self.proyecto.nombre,
            "zona": self.proyecto.zona,
            "imagen": self.proyecto.proyecto_imagen_principal_xmedium or self.tipologia.imagen_xmedium,
            "descripcion": f"{self.unidad.descripcion_corta} - {self.proyecto.descripcion_corta}"
        }


# ===========================
# 3) ADAPTADORES / UTILS
# ===========================

def csv_row_to_project_unit(row: Dict[str, Any]) -> ProjectUnit:
    return ProjectUnit.model_validate(row)


def filter_project_units(
        units: List[ProjectUnit],
        zona: Optional[str] = None,
        tipo_propiedad: Optional[str] = None,
        min_precio: Optional[float] = None,
        max_precio: Optional[float] = None,
        habitaciones: Optional[int] = None
) -> List[ProjectUnit]:
    f = units
    if zona:
        zl = zona.lower()
        f = [u for u in f
             if u.proyecto.proyecto_direccion_distrito
             and zl in u.proyecto.proyecto_direccion_distrito.lower()]
    if tipo_propiedad:
        tl = tipo_propiedad.lower()
        mapping = {
            "departamento": ["flat", "departamento", "studio", "penthouse", "duplex"],
            "casa": ["casa", "house"],
            "oficina": ["oficina", "office"],
            "lote": ["lote", "terreno", "land"]
        }
        valid = mapping.get(tl, [tl])
        f = [u for u in f if
             (u.tipologia.tipo and any(t in str(u.tipologia.tipo).lower() for t in valid))
             or (u.proyecto.proyecto_tipo and any(t in str(u.proyecto.proyecto_tipo).lower() for t in valid))]
    if min_precio is not None:
        f = [u for u in f if u.unidad.precio and u.unidad.precio >= min_precio]
    if max_precio is not None:
        f = [u for u in f if u.unidad.precio and u.unidad.precio <= max_precio]
    if habitaciones is not None:
        f = [u for u in f
             if u.unidad.num_dormitorios
             and int(u.unidad.num_dormitorios) >= habitaciones]
    return f


def project_units_to_properties(units: List[ProjectUnit]) -> List[Dict[str, Any]]:
    props: List[Dict[str, Any]] = []
    for u in units:
        props.append({
            "id": f"U-{u.proyecto.project_id}-{u.unidad.nombre}",
            "titulo": f"{u.tipologia.tipo or 'Departamento'} en {u.proyecto.proyecto_direccion_distrito or 'Lima'}",
            "precio": u.unidad.precio or 0,
            "habitaciones": int(u.unidad.num_dormitorios) if u.unidad.num_dormitorios else 1,
            "descripcion": (
                f"Unidad {u.unidad.nombre} en proyecto {u.proyecto.nombre} de {u.inmobiliaria.nombre}. "
                f"{int(u.unidad.area_total) if u.unidad.area_total else 0} m² totales, "
                f"{int(u.unidad.num_dormitorios) if u.unidad.num_dormitorios else 0} dormitorios, "
                f"{int(u.unidad.num_banios) if u.unidad.num_banios else 0} baños."
            ),
            "amenidades": u.proyecto.get_servicios_list(),
            "fotos": [u.proyecto.proyecto_imagen_principal_full, u.tipologia.imagen_full]
        })
    return props


class RelevanceOutput(BaseModel):
    is_relevant: bool
    reasoning: str

    model_config = ConfigDict(extra='forbid')


class ConsentVerificationOutput(BaseModel):
    consent_obtained: bool
    reasoning: str

    model_config = ConfigDict(extra='forbid')


class SecurityCheckOutput(BaseModel):
    is_safe: bool
    risk_level: Optional[str] = None
    threat_type: Optional[str] = None
    reasoning: str
    message: Optional[str] = None

    model_config = ConfigDict(extra='forbid')


class PIIDetectionOutput(BaseModel):
    contains_pii: bool
    detected_pii_types: List[str]
    severity: Optional[str] = None
    reasoning: str
    message: Optional[str] = None

    model_config = ConfigDict(extra='forbid')