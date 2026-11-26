from contextlib import contextmanager

import pandas as pd
import streamlit as st

from datos.conexion import obtener_cliente
from datos.repositorio import Repositorio


# Punto único para crear el acceso a los datos.
def obtener_repositorio() -> Repositorio:
    return Repositorio(obtener_cliente())


# El catálogo casi no cambia: se guarda en caché 60 s para navegar con fluidez.
# Las órdenes NO se cachean, así el panel siempre muestra datos actuales.
@st.cache_data(ttl=60, show_spinner=False)
def cargar_perfiles() -> list:
    return obtener_repositorio().obtener_perfiles()


# Ingredientes y recetas se cargan juntos, porque las recetas los referencian.
@st.cache_data(ttl=60, show_spinner=False)
def cargar_catalogo() -> tuple:
    repositorio = obtener_repositorio()
    ingredientes = repositorio.obtener_ingredientes()
    return ingredientes, repositorio.obtener_recetas(ingredientes)


@contextmanager
def manejar_errores(accion: str):
    """
    Muestra un mensaje entendible sin exponer detalles internos (URL, claves o
    trazas). El error técnico completo queda en la consola del servidor.
    """
    try:
        yield
    except Exception as error:  # límite de la interfaz: se informa y se detiene
        print(f"[ERROR] {accion}: {error!r}")
        st.error(
            f"No fue posible {accion}. Revise la conexión con Supabase y que se haya "
            "ejecutado sql/supabase_setup.sql."
        )
        st.stop()


def tabla(filas: list, columnas: dict, formatos: dict | None = None, **opciones):
    """
    Dibuja una tabla a partir de una lista de diccionarios.
    `columnas` = {clave: título}; `formatos` = {clave: función de formato}.
    El formato se aplica como estilo: las celdas siguen siendo numéricas y, al
    hacer clic en un encabezado, la tabla ordena por valor y no como texto.
    """
    datos = pd.DataFrame(filas, columns=list(columnas)).rename(columns=columnas)
    estilo = datos.style.format(
        {columnas[clave]: funcion for clave, funcion in (formatos or {}).items()}
    )
    return st.dataframe(estilo, hide_index=True, width="stretch", **opciones)
