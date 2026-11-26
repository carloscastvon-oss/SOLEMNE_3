import os

import streamlit as st
from supabase import Client, create_client


# Las claves nunca se escriben en el código: se leen desde st.secrets
# (.streamlit/secrets.toml) o desde variables de entorno.


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
