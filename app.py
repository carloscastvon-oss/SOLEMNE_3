"""
===============================================================================
 Archivo      : app.py  (punto de entrada)
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : streamlit 1.67, supabase 2.34, pandas 3.1, altair 6.3, tzdata
                Estándar: math, fractions, decimal, dataclasses, datetime,
                zoneinfo, json, os, tempfile, contextlib, typing, unicodedata
 Ejecución    : streamlit run app.py
 Descripción  : Identificación por perfil y navegación según permisos.

 ESTRUCTURA MODULAR
   estructuras/  TDA propios (lista, pila, cola, cola de prioridad, árbol, grafo)
   algoritmos/   ordenamiento interno/externo y búsqueda secuencial
   modelos/      clases del dominio
   logica/       motor de cálculo, acceso, servicio de cocina y reportes
   datos/        conexión y consultas a Supabase
   ui/           vistas de Streamlit (cocina y administrador)
===============================================================================
"""

import streamlit as st

from logica.acceso import buscar_perfil, tiene_acceso
from ui import vista_admin, vista_cocina
from ui.comun import cargar_perfiles, manejar_errores

st.set_page_config(page_title="Inventario y Mermas", layout="wide")

# Registro de vistas: código (igual al de la tabla perfil_permisos) ->
# (función, título, sección del menú, ruta en la URL).
VISTAS = {
    "resumen": (vista_admin.pagina_resumen, "Resumen ejecutivo", "Gerencia", "resumen"),
    "historial": (vista_admin.pagina_historial, "Historial", "Gerencia", "historial"),
    "analisis_mermas": (vista_admin.pagina_analisis_mermas, "Análisis de mermas", "Gerencia", "mermas"),
    "catalogo": (vista_admin.pagina_catalogo, "Catálogo y costos", "Gerencia", "catalogo"),
    "nueva_preparacion": (vista_cocina.pagina_nueva_preparacion, "Nueva preparación", "Cocina", "preparacion"),
    "ordenes_cocina": (vista_cocina.pagina_ordenes_cocina, "Órdenes pendientes", "Cocina", "pendientes"),
    "consulta_insumos": (vista_cocina.pagina_consulta_insumos, "Consulta de insumos", "Cocina", "insumos"),
}


# Pantalla inicial: una tarjeta por perfil, sin contraseña.
def pantalla_identificacion(perfiles: list) -> None:
    st.title("Sistema de Inventario y Gestión de Mermas")
    st.write("Seleccione su perfil para ingresar.")
    for columna, perfil in zip(st.columns(len(perfiles)), perfiles):
        with columna.container(border=True):
            st.subheader(perfil["nombre"])
            st.write(perfil["descripcion"])
            if st.button(
                f"Ingresar como {perfil['nombre']}",
                key=f"ingresar_{perfil['codigo']}",
                width="stretch",
            ):
                st.session_state["perfil"] = perfil["codigo"]
                st.rerun()


# Sale del perfil actual y vuelve a la pantalla de ingreso.
def cerrar_sesion() -> None:
    # Se borra todo el estado para no traspasar información entre perfiles.
    st.session_state.clear()


# Función principal: identifica el perfil y construye su navegación.
def main() -> None:
    with manejar_errores("conectar con la base de datos"):
        perfiles = cargar_perfiles()
    if not perfiles:
        st.error("No hay perfiles cargados. Ejecute sql/supabase_setup.sql en Supabase.")
        return

    # Se comprueba si ya hay un perfil válido en la sesión.
    perfil = buscar_perfil(perfiles, st.session_state.get("perfil"))
    if perfil is None:
        # Con navegación oculta, una URL escrita a mano no abre ninguna vista.
        pantalla = st.Page(lambda: pantalla_identificacion(perfiles), title="Ingreso", default=True)
        st.navigation([pantalla], position="hidden").run()
        return

    # Solo se REGISTRAN las páginas permitidas: las demás no existen para el
    # perfil, ni en el menú ni escribiendo la dirección.
    permitidas = [v for v in VISTAS if tiene_acceso(perfiles, perfil["codigo"], v)]
    if not permitidas:
        st.error("Este perfil no tiene vistas asignadas.")
        st.button("Cambiar de perfil", on_click=cerrar_sesion)
        return

    # El menú lateral se arma agrupado por sección.
    menu: dict = {}
    for posicion, codigo in enumerate(permitidas):
        funcion, titulo, seccion, ruta = VISTAS[codigo]
        menu.setdefault(seccion, []).append(
            st.Page(funcion, title=titulo, url_path=ruta, default=(posicion == 0))
        )
    navegacion = st.navigation(menu)

    with st.sidebar:
        st.markdown(f"**Perfil activo:** {perfil['nombre']}")
        st.button("Cambiar de perfil", on_click=cerrar_sesion, width="stretch")

    navegacion.run()


main()
