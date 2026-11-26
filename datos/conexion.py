"""
===============================================================================
 Archivo      : datos/conexion.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : os, streamlit, supabase
 Descripción  : Conexión a Supabase con manejo seguro de credenciales. Las
                claves NUNCA se escriben en el código: se leen desde
                .streamlit/secrets.toml (st.secrets) o variables de entorno.
===============================================================================
"""

import os

import streamlit as st
from supabase import Client, create_client


class ErrorConfiguracion(RuntimeError):
    """Faltan las credenciales de conexión."""


def leer_credenciales() -> tuple[str, str]:
    """Prioridad: 1) st.secrets  2) variables de entorno."""
    url = key = None
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except (KeyError, FileNotFoundError):
        # No hay secrets.toml o le falta la sección: se intenta con el entorno.
        pass
    url = url or os.getenv("SUPABASE_URL")
    key = key or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ErrorConfiguracion(
            "No se encontraron las credenciales. Configure .streamlit/secrets.toml "
            "o las variables de entorno SUPABASE_URL y SUPABASE_KEY."
        )
    return url, key


@st.cache_resource(show_spinner=False)
def obtener_cliente() -> Client:
    """Un solo cliente reutilizado entre recargas de la página."""
    url, key = leer_credenciales()
    return create_client(url, key)
