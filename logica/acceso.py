# --- IMPORTACIONES ---
from typing import Optional  # anotaciones de tipos

from algoritmos.busqueda import busqueda_secuencial  # búsqueda secuencial propia


# --- BÚSQUEDA DE UN PERFIL ---
def buscar_perfil(perfiles: list, codigo: Optional[str]) -> Optional[dict]:
    return busqueda_secuencial(perfiles, lambda p: p["codigo"] == codigo)  # compara por el código del perfil


# --- VALIDACIÓN DE PERMISOS ---
def tiene_acceso(perfiles: list, codigo: Optional[str], vista: str) -> bool:
    perfil = buscar_perfil(perfiles, codigo)  # localiza el perfil
    if perfil is None:                        # perfil inexistente: acceso denegado
        return False
    return busqueda_secuencial(perfil["vistas"], lambda v: v == vista) is not None  # verifica que la vista esté autorizada
