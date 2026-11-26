# --- IMPORTACIONES ---
import streamlit as st  # interfaz web

from algoritmos.busqueda import buscar_por_nombre, busqueda_secuencial                # búsqueda secuencial propia
from estructuras.tda import Pila  # pila propia
from logica.formato import fecha_local  # formato de fechas
from logica.motor_calculo import MAX_COMENSALES, ErrorValidacion, validar_comensales  # validación de datos
from logica.servicio_cocina import cola_de_pendientes, solicitar_servicio             # operaciones de cocina
from ui.comun import cargar_catalogo, manejar_errores, obtener_repositorio, tabla     # elementos comunes de la interfaz


# --- TABLA DE UNA ORDEN ---
def _mostrar_orden(orden) -> None:
    tabla(
        [vars(linea) for linea in orden.lineas],
        {
            "ingrediente": "Ingrediente",
            "a_preparar": "A preparar",
            "a_retirar": "Retirar de bodega (unidades completas)",
        },
    )


# --- PANTALLA: NUEVA PREPARACIÓN ---
def pagina_nueva_preparacion() -> None:
    st.title("Nueva preparación")
    with manejar_errores("cargar el catálogo"):  # carga las recetas
        _, recetas = cargar_catalogo()

    historial: Pila = st.session_state.setdefault("pila_sesion", Pila())  # órdenes de la sesión; la última queda arriba

    with st.form("form_servicio"):  # formulario: se envía solo con el botón
        nombre = st.selectbox(      # selección del menú
            "Menú", [r.nombre for r in recetas], index=None, placeholder="Seleccione un menú"
        )
        comensales = st.number_input(  # cantidad de personas
            "Cantidad de comensales",
            value=None,
            step=1,
            placeholder=f"Número entero entre 1 y {MAX_COMENSALES}",
        )
        enviado = st.form_submit_button("Generar orden de preparación", type="primary")  # botón de envío

    if enviado:  # procesa la solicitud
        receta = busqueda_secuencial(recetas, lambda r: r.nombre == nombre)  # busca la receta elegida
        try:
            if receta is None:
                raise ErrorValidacion("Debe seleccionar un menú.")
            validar_comensales(comensales)  # revisa la cantidad ingresada
        except ErrorValidacion as error:    # muestra el error al usuario
            st.error(str(error))
        else:
            with manejar_errores("guardar la orden"):
                orden = solicitar_servicio(  # calcula y guarda la orden
                    obtener_repositorio(), receta, comensales, st.session_state["perfil"]
                )
            historial.apilar(orden)  # la agrega a la pila de la sesión
            st.toast(f"Orden N° {orden.numero} guardada en Supabase")

    if historial.esta_vacia():  # aún no hay órdenes en la sesión
        st.info("Seleccione un menú e ingrese los comensales para generar la orden.")
        return

    ordenes = list(historial)  # de la más reciente a la más antigua
    ultima = ordenes[0]
    st.success(f"Orden N° {ultima.numero} registrada")
    st.subheader(f"{ultima.menu} · {ultima.comensales} comensales")
    _mostrar_orden(ultima)  # muestra la última orden

    receta = busqueda_secuencial(recetas, lambda r: r.nombre == ultima.menu)  # receta de la última orden
    if receta is not None:
        with st.expander(f"Ver receta base ({receta.comensales_base} comensales)"):  # receta base desplegable
            for item in receta.items:
                st.markdown(f"- **{item.ingrediente.nombre}:** {item.texto_receta}")

    if len(ordenes) > 1:  # órdenes anteriores
        st.markdown("#### Órdenes anteriores de esta sesión")
        for orden in ordenes[1:6]:  # muestra hasta 5
            with st.expander(f"N° {orden.numero} · {orden.menu} · {orden.comensales} comensales"):
                _mostrar_orden(orden)


# --- PANTALLA: ÓRDENES PENDIENTES ---
def pagina_ordenes_cocina() -> None:
    st.title("Órdenes pendientes")
    st.caption("Se atienden en orden de llegada (cola FIFO: la más antigua primero).")

    repositorio = obtener_repositorio()
    with manejar_errores("consultar las órdenes"):
        ingredientes, _ = cargar_catalogo()
        cola = cola_de_pendientes(repositorio.ordenes_cocina_pendientes(), ingredientes)  # forma la cola por orden de llegada

    if mensaje := st.session_state.pop("aviso_cola", None):  # aviso guardado antes de recargar
        st.success(mensaje)
    if cola.esta_vacia():  # no hay trabajo pendiente
        st.info("No hay órdenes pendientes.")
        return

    st.metric("Órdenes en espera", len(cola))  # total de órdenes en espera
    siguiente = cola.desencolar()              # toma la orden más antigua
    with st.container(border=True):
        st.subheader(f"Siguiente: N° {siguiente.numero} · {siguiente.menu}")
        st.write(f"{siguiente.comensales} comensales · solicitada {fecha_local(siguiente.fecha)}")
        _mostrar_orden(siguiente)
        if st.button("Marcar como preparada", type="primary", key=f"lista_{siguiente.numero}"):  # botón para finalizar la orden
            with manejar_errores("actualizar la orden"):
                actualizada = repositorio.marcar_preparada(siguiente.numero)  # actualiza el estado en Supabase
            st.session_state["aviso_cola"] = (                                # guarda el aviso
                f"Orden N° {siguiente.numero} preparada."
                if actualizada
                else f"La orden N° {siguiente.numero} ya había sido marcada."
            )
            st.rerun()  # recarga la lista

    if not cola.esta_vacia():  # resto de la cola
        st.markdown("#### En espera")
        posicion = 2
        while not cola.esta_vacia() and posicion <= 11:  # muestra las 10 siguientes
            orden = cola.desencolar()
            with st.expander(
                f"{posicion}.º · N° {orden.numero} · {orden.menu} · {orden.comensales} comensales"
            ):
                _mostrar_orden(orden)
            posicion += 1


# --- PANTALLA: CONSULTA DE INSUMOS ---
def pagina_consulta_insumos() -> None:
    st.title("Consulta de insumos")
    with manejar_errores("cargar el catálogo"):
        ingredientes, recetas = cargar_catalogo()

    texto = st.text_input("Buscar insumo por nombre", placeholder="Ej.: papa")  # texto a buscar
    encontrados = buscar_por_nombre(ingredientes, texto, lambda i: i.nombre)    # insumos que coinciden
    if not encontrados:  # sin resultados
        st.warning("No se encontraron insumos con ese nombre.")
        return

    filas = []
    for ingrediente in encontrados:  # arma una fila por insumo
        menus = [                    # menús que utilizan el insumo
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
    tabla(  # muestra los resultados sin costos
        filas,
        {"insumo": "Insumo", "unidad": "Unidad", "rinde": "Rinde para", "menus": "Se usa en"},
    )
