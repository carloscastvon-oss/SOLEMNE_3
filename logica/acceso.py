"""
===============================================================================
 Archivo      : logica/acceso.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : solo módulos del proyecto
 Descripción  : Validación de acceso por PERFIL usando búsqueda secuencial.
                Por alcance del encargo no se gestionan contraseñas: la persona
                se identifica eligiendo su perfil. Los permisos de cada perfil
                están en la tabla perfil_permisos de Supabase.
===============================================================================
"""

from typing import Optional

from algoritmos.busqueda import busqueda_secuencial


def buscar_perfil(perfiles: list, codigo: Optional[str]) -> Optional[dict]:
    return busqueda_secuencial(perfiles, lambda p: p["codigo"] == codigo)


def tiene_acceso(perfiles: list, codigo: Optional[str], vista: str) -> bool:
    """Niega por defecto: sin perfil válido o sin permiso explícito, no hay acceso."""
    perfil = buscar_perfil(perfiles, codigo)
    if perfil is None:
        return False
    return busqueda_secuencial(perfil["vistas"], lambda v: v == vista) is not None
