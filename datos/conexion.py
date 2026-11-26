# --- IMPORTACIONES ---
import os  # variables de entorno

import streamlit as st                      # credenciales y caché
from supabase import Client, create_client  # cliente de la base de datos


# --- ERROR DE CREDENCIALES FALTANTES ---
class ErrorConfiguracion(RuntimeError):
    pass


# --- LECTURA SEGURA DE CREDENCIALES ---
def leer_credenciales() -> tuple[str, str]:
    url = key = None  # valores aún sin cargar
    try:
        url = st.secrets["supabase"]["url"]  # primero busca en secrets.toml
        key = st.secrets["supabase"]["key"]
    except (KeyError, FileNotFoundError):  # si no existe, se usan variables de entorno
        pass
    url = url or os.getenv("SUPABASE_URL")  # dirección del proyecto
    key = key or os.getenv("SUPABASE_KEY")  # clave de acceso
    if not url or not key:                  # sin credenciales no se puede conectar
        raise ErrorConfiguracion(
            "No se encontraron las credenciales. Configure .streamlit/secrets.toml "
            "o las variables de entorno SUPABASE_URL y SUPABASE_KEY."
        )
    return url, key


# --- CONEXIÓN CON SUPABASE ---
@st.cache_resource(show_spinner=False)  # reutiliza una sola conexión
def obtener_cliente() -> Client:
    url, key = leer_credenciales()
    return create_client(url, key)  # crea el cliente
