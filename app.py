"""
 Archivo      : app.py  (punto de entrada principal, el resto del codigo se encuentra en modulos)
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : Capitán Carlos Castillo Von-bischoffshausen
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : streamlit (interfaz gráfica verisón web)
                supabase  (conexión a las tablas de la base de datos)
                pandas    (manejo de tablas de datos)
                altair    (gráficos)
                tzdata    (zonas horarias, hora de Chile)
 Ejecución    : streamlit run app.py
 Descripción  : Identificación por perfil y navegación según permisos.

"""

# --- IMPORTACIONES ---
import streamlit as st  # librería de la interfaz web

from logica.acceso import buscar_perfil, tiene_acceso  # validación de perfiles y permisos
from ui import vista_admin, vista_cocina               # pantallas de cocina y administrador
from ui.comun import cargar_perfiles, manejar_errores  # carga de perfiles y manejo de errores

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Inventario y Mermas", layout="wide")  # nombre de la pestaña y diseño a todo el ancho

# --- REGISTRO DE VISTAS ---
VISTAS = {  # código: (función, título, sección del menú, dirección)
    "resumen": (vista_admin.pagina_resumen, "Resumen ejecutivo", "Gerencia", "resumen"),
    "historial": (vista_admin.pagina_historial, "Historial", "Gerencia", "historial"),
    "analisis_mermas": (vista_admin.pagina_analisis_mermas, "Análisis de mermas", "Gerencia", "mermas"),
    "catalogo": (vista_admin.pagina_catalogo, "Catálogo y costos", "Gerencia", "catalogo"),
    "nueva_preparacion": (vista_cocina.pagina_nueva_preparacion, "Nueva preparación", "Cocina", "preparacion"),
    "ordenes_cocina": (vista_cocina.pagina_ordenes_cocina, "Órdenes pendientes", "Cocina", "pendientes"),
    "consulta_insumos": (vista_cocina.pagina_consulta_insumos, "Consulta de insumos", "Cocina", "insumos"),
}


# --- PANTALLA DE INGRESO POR PERFIL ---
def pantalla_identificacion(perfiles: list) -> None:
    st.title("Sistema de Inventario y Gestión de Mermas")  # título principal
    st.write("Seleccione su perfil para ingresar.")
    for columna, perfil in zip(st.columns(len(perfiles)), perfiles):  # una columna por cada perfil
        with columna.container(border=True):
            st.subheader(perfil["nombre"])
            st.write(perfil["descripcion"])
            if st.button(  # botón para ingresar
                f"Ingresar como {perfil['nombre']}",
                key=f"ingresar_{perfil['codigo']}",
                width="stretch",
            ):
                st.session_state["perfil"] = perfil["codigo"]  # guarda el perfil elegido
                st.rerun()                                     # recarga la página con el nuevo perfil


# --- CAMBIO DE PERFIL ---
def cerrar_sesion() -> None:
    st.session_state.clear()  # borra los datos de la sesión


# --- FUNCIÓN PRINCIPAL ---
def main() -> None:
    with manejar_errores("conectar con la base de datos"):  # controla fallas de conexión
        perfiles = cargar_perfiles()                        # lee los perfiles desde Supabase
    if not perfiles:                                        # detiene la app si no hay perfiles
        st.error("No hay perfiles cargados. Ejecute sql/supabase_setup.sql en Supabase.")
        return

    perfil = buscar_perfil(perfiles, st.session_state.get("perfil"))  # perfil activo en la sesión
    if perfil is None:  # sin perfil: solo se muestra el ingreso
        pantalla = st.Page(lambda: pantalla_identificacion(perfiles), title="Ingreso", default=True)
        st.navigation([pantalla], position="hidden").run()  # el menú queda oculto
        return

    permitidas = [v for v in VISTAS if tiene_acceso(perfiles, perfil["codigo"], v)]  # vistas autorizadas para el perfil
    if not permitidas:  # perfil sin vistas asignadas
        st.error("Este perfil no tiene vistas asignadas.")
        st.button("Cambiar de perfil", on_click=cerrar_sesion)
        return

    menu: dict = {}                                 # menú agrupado por sección
    for posicion, codigo in enumerate(permitidas):  # crea una página por cada vista autorizada
        funcion, titulo, seccion, ruta = VISTAS[codigo]
        menu.setdefault(seccion, []).append(
            st.Page(funcion, title=titulo, url_path=ruta, default=(posicion == 0))
        )
    navegacion = st.navigation(menu)  # construye el menú lateral

    with st.sidebar:  # datos del perfil en la barra lateral
        st.markdown(f"**Perfil activo:** {perfil['nombre']}")
        st.button("Cambiar de perfil", on_click=cerrar_sesion, width="stretch")

    navegacion.run()  # muestra la página seleccionada


# --- INICIO DE LA APLICACIÓN ---
main()
