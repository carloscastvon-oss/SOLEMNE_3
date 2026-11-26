from typing import Optional

from algoritmos.busqueda import busqueda_secuencial


# Por alcance del encargo no hay contraseñas: la persona elige su perfil. Los
# permisos de cada perfil están en la tabla perfil_permisos de Supabase.


# Busca secuencialmente el perfil por su código.
def buscar_perfil(perfiles: list, codigo: Optional[str]) -> Optional[dict]:
    return busqueda_secuencial(perfiles, lambda p: p["codigo"] == codigo)


def tiene_acceso(perfiles: list, codigo: Optional[str], vista: str) -> bool:
    """Niega por defecto: sin perfil válido o sin permiso explícito, no hay acceso."""
    perfil = buscar_perfil(perfiles, codigo)
    if perfil is None:
        return False
    return busqueda_secuencial(perfil["vistas"], lambda v: v == vista) is not None
