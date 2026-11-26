import streamlit as st

from algoritmos.busqueda import buscar_por_nombre, busqueda_secuencial
from estructuras.tda import Pila
from logica.formato import fecha_local
from logica.motor_calculo import MAX_COMENSALES, ErrorValidacion, validar_comensales
from logica.servicio_cocina import cola_de_pendientes, solicitar_servicio
from ui.comun import cargar_catalogo, manejar_errores, obtener_repositorio, tabla


# Ninguna pantalla de cocina muestra costos, precios, sobrantes ni pérdidas.


# Tabla de preparación reutilizada en las pantallas de cocina.
def _mostrar_orden(orden) -> None:
    tabla(
        [vars(linea) for linea in orden.lineas],
        {
            "ingrediente": "Ingrediente",
            "a_preparar": "A preparar",
            "a_retirar": "Retirar de bodega (unidades completas)",
        },
    )


# --- Pantalla: formulario de solicitud de servicio ---
def pagina_nueva_preparacion() -> None:
    st.title("Nueva preparación")
    with manejar_errores("cargar el catálogo"):
        _, recetas = cargar_catalogo()

    # Pila de las órdenes generadas en esta sesión: la última queda arriba.
    historial: Pila = st.session_state.setdefault("pila_sesion", Pila())

    # st.form: nada se calcula ni se guarda hasta presionar el botón.
    with st.form("form_servicio"):
        nombre = st.selectbox(
            "Menú", [r.nombre for r in recetas], index=None, placeholder="Seleccione un menú"
        )
        # Sin min_value a propósito: así un 0 o un negativo llega a la validación
        # y la persona recibe un mensaje claro en vez de un ajuste silencioso.
        comensales = st.number_input(
            "Cantidad de comensales",
            value=None,
            step=1,
            placeholder=f"Número entero entre 1 y {MAX_COMENSALES}",
        )
        enviado = st.form_submit_button("Generar orden de preparación", type="primary")

    # Primero se valida; solo con datos correctos se calcula y guarda.
    if enviado:
        receta = busqueda_secuencial(recetas, lambda r: r.nombre == nombre)
        try:
            if receta is None:
                raise ErrorValidacion("Debe seleccionar un menú.")
            validar_comensales(comensales)
        except ErrorValidacion as error:
            st.error(str(error))
        else:
            with manejar_errores("guardar la orden"):
                orden = solicitar_servicio(
                    obtener_repositorio(), receta, comensales, st.session_state["perfil"]
                )
            historial.apilar(orden)
            st.toast(f"Orden N° {orden.numero} guardada en Supabase")

    # Sin órdenes en la sesión solo se muestran las instrucciones.
    if historial.esta_vacia():
        st.info("Seleccione un menú e ingrese los comensales para generar la orden.")
        return

    ordenes = list(historial)  # recorrido desde el tope: la más reciente primero
    ultima = ordenes[0]
    st.success(f"Orden N° {ultima.numero} registrada")
    st.subheader(f"{ultima.menu} · {ultima.comensales} comensales")
    _mostrar_orden(ultima)

    receta = busqueda_secuencial(recetas, lambda r: r.nombre == ultima.menu)
    if receta is not None:
        with st.expander(f"Ver receta base ({receta.comensales_base} comensales)"):
            for item in receta.items:
                st.markdown(f"- **{item.ingrediente.nombre}:** {item.texto_receta}")

    if len(ordenes) > 1:
        st.markdown("#### Órdenes anteriores de esta sesión")
        for orden in ordenes[1:6]:
            with st.expander(f"N° {orden.numero} · {orden.menu} · {orden.comensales} comensales"):
                _mostrar_orden(orden)


# --- Pantalla: cola de órdenes pendientes ---
def pagina_ordenes_cocina() -> None:
    st.title("Órdenes pendientes")
    st.caption("Se atienden en orden de llegada (cola FIFO: la más antigua primero).")

    repositorio = obtener_repositorio()
    with manejar_errores("consultar las órdenes"):
        ingredientes, _ = cargar_catalogo()
        cola = cola_de_pendientes(repositorio.ordenes_cocina_pendientes(), ingredientes)

    # El aviso se guarda en la sesión para que sobreviva a la recarga.
    if mensaje := st.session_state.pop("aviso_cola", None):
        st.success(mensaje)
    if cola.esta_vacia():
        st.info("No hay órdenes pendientes.")
        return

    st.metric("Órdenes en espera", len(cola))
    # Solo la primera de la cola se puede marcar como preparada.
    siguiente = cola.desencolar()
    with st.container(border=True):
        st.subheader(f"Siguiente: N° {siguiente.numero} · {siguiente.menu}")
        st.write(f"{siguiente.comensales} comensales · solicitada {fecha_local(siguiente.fecha)}")
        _mostrar_orden(siguiente)
        if st.button("Marcar como preparada", type="primary", key=f"lista_{siguiente.numero}"):
            with manejar_errores("actualizar la orden"):
                actualizada = repositorio.marcar_preparada(siguiente.numero)
            st.session_state["aviso_cola"] = (
                f"Orden N° {siguiente.numero} preparada."
                if actualizada
                else f"La orden N° {siguiente.numero} ya había sido marcada."
            )
            st.rerun()

    if not cola.esta_vacia():
        st.markdown("#### En espera")
        posicion = 2
        while not cola.esta_vacia() and posicion <= 11:  # se muestran las 10 siguientes
            orden = cola.desencolar()
            with st.expander(
                f"{posicion}.º · N° {orden.numero} · {orden.menu} · {orden.comensales} comensales"
            ):
                _mostrar_orden(orden)
            posicion += 1


# --- Pantalla: consulta de insumos sin costos ---
def pagina_consulta_insumos() -> None:
    st.title("Consulta de insumos")
    with manejar_errores("cargar el catálogo"):
        ingredientes, recetas = cargar_catalogo()

    texto = st.text_input("Buscar insumo por nombre", placeholder="Ej.: papa")
    encontrados = buscar_por_nombre(ingredientes, texto, lambda i: i.nombre)
    if not encontrados:
        st.warning("No se encontraron insumos con ese nombre.")
        return

    # Para cada insumo encontrado se buscan los menús que lo utilizan.
    filas = []
    for ingrediente in encontrados:
        menus = [
            r.nombre
            for r in recetas
            if busqueda_secuencial(r.items, lambda it: it.ingrediente.id == ingrediente.id)
        ]
        filas.append(
            {
                "insumo": ingrediente.nombre,
                "unidad": ingrediente.unidad_compra,
                "rinde": f"{ingrediente.rendimiento} persona(s)",
                "menus": ", ".join(menus),
            }
        )
    tabla(
        filas,
        {"insumo": "Insumo", "unidad": "Unidad", "rinde": "Rinde para", "menus": "Se usa en"},
    )
