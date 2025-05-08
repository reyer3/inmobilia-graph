# src/agent/querys.py

def build_query_units(
        zona: str | None = None,
        tipo_propiedad: str | None = None,
        min_precio: float | None = None,
        max_precio: float | None = None,
        habitaciones: int | None = None,
        limit: int = 5
) -> str:
    """
    Busca hasta `limit` unidades que cumplan los criterios.
    """
    filters: list[str] = []
    if zona:
        filters.append(f"u.proyecto_direccion_distrito ILIKE '%{zona}%'")
    if tipo_propiedad:
        filters.append(f"u.proyecto_tipo = '{tipo_propiedad}'")
    if min_precio is not None:
        filters.append(f"u.unidad_precio >= {min_precio}")
    if max_precio is not None:
        filters.append(f"u.unidad_precio <= {max_precio}")
    if habitaciones is not None:
        filters.append(f"u.unidad_num_dormitorios >= {habitaciones}")

    where_clause = " AND ".join(filters) if filters else "TRUE"
    return f"""
    SELECT
      u.id,
      u.unidad_nombre    AS titulo,
      u.unidad_precio    AS precio,
      u.unidad_num_dormitorios AS habitaciones,
      u.unidad_num_banios       AS banios,
      u.unidad_area_total       AS area,
      u.proyecto_nombre         AS proyecto,
      u.proyecto_direccion_distrito AS zona
    FROM bd_project_units u
    JOIN bd_all_projects p ON u.project_id = p.project_id
    WHERE {where_clause}
    LIMIT {limit};
    """.strip()


def build_query_project_detail(project_id: int) -> str:
    return f"""
    SELECT *
    FROM bd_all_projects
    WHERE project_id = {project_id};
    """.strip()


def build_query_units_by_project(project_id: int) -> str:
    return f"""
    SELECT
      u.id,
      u.unidad_nombre    AS titulo,
      u.unidad_precio    AS precio,
      u.unidad_num_dormitorios AS habitaciones,
      u.unidad_num_banios       AS banios,
      u.unidad_area_total       AS area,
      u.tipologia_tipo   AS tipologia,
      i.proyecto_imagen_full AS imagen_principal
    FROM bd_project_units u
    LEFT JOIN bd_all_images_project i ON i.project_id = u.project_id
    WHERE u.project_id = {project_id};
    """.strip()


def build_query_project_images(project_id: int) -> str:
    return f"""
    SELECT 
      'principal_full' AS tipo, 
      proyecto_imagen_full AS url
    FROM bd_all_images_project
    WHERE project_id = {project_id}

    UNION

    SELECT 
      'principal_xmedium' AS tipo,
      proyecto_imagen_xmedium AS url
    FROM bd_all_images_project  
    WHERE project_id = {project_id}

    UNION

    SELECT 
      'principal_small' AS tipo,
      proyecto_imagen_small AS url
    FROM bd_all_images_project
    WHERE project_id = {project_id}

    ORDER BY
      CASE tipo
        WHEN 'principal_full' THEN 1
        WHEN 'principal_xmedium' THEN 2
        WHEN 'principal_small' THEN 3
        ELSE 4
      END;
    """.strip()


def build_query_similar_units(unit_id: int, max_results: int = 3) -> str:
    return f"""
    WITH ref AS (
      SELECT 
        u.project_id,
        u.unidad_precio           AS precio_ref,
        u.unidad_num_dormitorios  AS dorm_ref,
        u.proyecto_direccion_distrito AS zona
      FROM bd_project_units u
      WHERE u.id = {unit_id}
    )
    SELECT
      u.id,
      u.unidad_nombre    AS titulo,
      u.unidad_precio    AS precio,
      u.unidad_num_dormitorios AS habitaciones,
      u.proyecto_direccion_distrito AS zona
    FROM bd_project_units u
    JOIN ref ON TRUE
    WHERE
      u.id <> {unit_id}
      AND u.proyecto_direccion_distrito = ref.zona
      AND u.unidad_precio BETWEEN ref.precio_ref * 0.8 AND ref.precio_ref * 1.2
      AND u.unidad_num_dormitorios >= ref.dorm_ref
    LIMIT {max_results};
    """.strip()