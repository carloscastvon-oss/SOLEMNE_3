# --- IMPORTACIONES ---
from contextlib import contextmanager  # bloques con control de errores

import pandas as pd     # tablas de datos
import streamlit as st  # interfaz web

from datos.conexion import obtener_cliente  # conexión con Supabase
from datos.repositorio import Repositorio   # consultas a la base de datos


# --- ACCESO A LOS DATOS ---
def obtener_repositorio() -> Repositorio:
    return Repositorio(obtener_cliente())


# --- CARGA DE PERFILES ---
@st.cache_data(ttl=60, show_spinner=False)  # conserva el resultado 60 segundos
def cargar_perfiles() -> list:
    return obtener_repositorio().obtener_perfiles()


# --- CARGA DE INGREDIENTES Y RECETAS ---
@st.cache_data(ttl=60, show_spinner=False)  # conserva el resultado 60 segundos
def cargar_catalogo() -> tuple:
    repositorio = obtener_repositorio()
    ingredientes = repositorio.obtener_ingredientes()
    return ingredientes, repositorio.obtener_recetas(ingredientes)  # entrega ambas listas


# --- MANEJO DE ERRORES ---
@contextmanager
def manejar_errores(accion: str):
    try:
        yield                                  # ejecuta el bloque protegido
    except Exception as error:                 # captura cualquier falla
        print(f"[ERROR] {accion}: {error!r}")  # el detalle técnico queda en la consola
        st.error(                              # mensaje simple para el usuario
            f"No fue posible {accion}. Revise la conexión con Supabase y que se haya "
            "ejecutado sql/supabase_setup.sql."
        )
        st.stop()  # detiene la página


# --- TABLA DE DATOS ---
def tabla(filas: list, columnas: dict, formatos: dict | None = None, **opciones):
    datos = pd.DataFrame(filas, columns=list(columnas)).rename(columns=columnas)  # ordena las columnas y asigna sus títulos
    estilo = datos.style.format(  # aplica formato sin convertir los números en texto
        {columnas[clave]: funcion for clave, funcion in (formatos or {}).items()}
    )
    return st.dataframe(estilo, hide_index=True, width="stretch", **opciones)  # muestra la tabla
