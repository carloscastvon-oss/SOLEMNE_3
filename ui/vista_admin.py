# --- IMPORTACIONES ---
import altair as alt    # gráficos
import pandas as pd     # tablas de datos
import streamlit as st  # interfaz web

from algoritmos.busqueda import buscar_por_nombre, busqueda_secuencial                   # búsqueda secuencial propia
from algoritmos.ordenamiento import METODOS, mergesort, ordenamiento_externo, quicksort  # algoritmos de ordenamiento propios
from logica import reportes  # cálculos del panel
from logica.formato import fecha_local, numero, pesos                                    # formato de datos
from logica.motor_calculo import MAX_COMENSALES                                          # límite de comensales
from ui.comun import cargar_catalogo, manejar_errores, obtener_repositorio, tabla        # elementos comunes de la interfaz

# --- CAMPOS PARA ORDENAR EL HISTORIAL ---
CAMPOS_ORDEN = {  # título visible: nombre del dato
    "Fecha": "fecha",
    "Pérdida por merma": "perdida_merma",
    "Costo total": "costo_total",
    "Costo por plato": "costo_por_plato",
    "Valor de venta total": "venta_total",
    "Comensales": "comensales",
    "Menú": "menu",
}


# --- LECTURA DEL HISTORIAL ---
def _cargar_registros() -> list:
    with manejar_errores("consultar el historial"):
        return reportes.aplanar_ordenes(obtener_repositorio().ordenes_completas())


# --- FORMATO DE PORCENTAJE ---
def _porcentaje(valor) -> str:
    return f"{numero(valor, 1)} %"


# --- GRÁFICO DE BARRAS HORIZONTALES ---
def _grafico_barras(filas: list, categoria: str, valor: str, titulo_valor: str) -> None:
    datos = pd.DataFrame(filas)  # datos del gráfico
    grafico = (
        alt.Chart(datos)
        .mark_bar()  # tipo de gráfico: barras
        .encode(
            x=alt.X(f"{valor}:Q", title=titulo_valor, axis=alt.Axis(labelExpr=EJE_PESOS)),   # eje horizontal: valores
            y=alt.Y(f"{categoria}:N", sort=None, title=None, axis=alt.Axis(labelLimit=260)),  # eje vertical: nombres, en el orden recibido
            tooltip=[  # detalle al pasar el cursor
                alt.Tooltip(f"{categoria}:N", title="Nombre"),
                alt.Tooltip(f"{valor}:Q", title=titulo_valor, format=",.2f"),
            ],
        )
        .properties(height=max(120, 34 * len(datos)))  # altura según la cantidad de barras
    )
    st.altair_chart(grafico, width="stretch")  # muestra el gráfico


# --- COLORES DE LOS GRÁFICOS (azul: costo, naranja: merma, verde agua: ganancia e ingresos) ---
COLORES = {
    "light": {"costo": "#257de0", "merma": "#f47230", "ganancia": "#00b894", "texto": "#31333f", "fondo": "#ffffff"},
    "dark": {"costo": "#338ced", "merma": "#e76624", "ganancia": "#00a888", "texto": "#fafafa", "fondo": "#0e1117"},
}


# --- COLORES SEGÚN EL TEMA ---
def _colores() -> dict:
    return COLORES["dark" if st.context.theme.type == "dark" else "light"]  # tema claro u oscuro


# --- FORMATO DE LOS MONTOS EN LOS EJES ---
EJE_PESOS = "replace(format(datum.value, ',.0f'), /,/g, '.')"  # miles separados con punto


# --- ESCALA DE COLOR CON LEYENDA ---
def _escala_color(campo: str, nombres: list, colores: list, direccion: str = "horizontal"):
    return alt.Color(
        f"{campo}:N",
        scale=alt.Scale(domain=nombres, range=colores),  # cada concepto mantiene su color
        legend=alt.Legend(orient="bottom", direction=direccion, title=None, labelLimit=220),
    )


# --- GRÁFICO DE TORTA: DISTRIBUCIÓN DE LOS INGRESOS ---
def _grafico_torta(partes: list) -> None:
    c = _colores()
    datos = pd.DataFrame(partes)
    datos["orden"] = range(len(datos))                                  # orden fijo de las porciones
    datos["etiqueta"] = [_porcentaje(p["porcentaje"]) for p in partes]  # porcentaje visible
    datos["monto_texto"] = [pesos(p["monto"]) for p in partes]          # monto en formato chileno
    base = alt.Chart(datos).encode(
        theta=alt.Theta("monto:Q", stack=True),
        order=alt.Order("orden:Q"),
        tooltip=[
            alt.Tooltip("concepto:N", title="Concepto"),
            alt.Tooltip("monto_texto:N", title="Monto"),
            alt.Tooltip("etiqueta:N", title="Del ingreso"),
        ],
    )
    porciones = base.mark_arc(innerRadius=55, outerRadius=105, stroke=c["fondo"], strokeWidth=2).encode(
        color=_escala_color("concepto", list(datos["concepto"]), [c["costo"], c["merma"], c["ganancia"]], "vertical")
    )
    etiquetas = base.mark_text(radius=130, fontSize=13).encode(  # porcentajes fuera de la torta
        text="etiqueta:N", color=alt.value(c["texto"])
    )
    st.altair_chart((porciones + etiquetas).properties(height=360), width="stretch")


# --- GRÁFICO DE BARRAS APILADAS: COSTO Y MERMA POR MENÚ ---
def _grafico_costo_menu(por_menu: list) -> None:
    c = _colores()
    filas = []
    for m in por_menu:  # cada barra se divide en costo aprovechado y merma
        tramos = [("Costo aprovechado", m["costo"] - m["perdida"]), ("Pérdida por merma", m["perdida"])]
        for posicion, (concepto, monto) in enumerate(tramos):
            filas.append(
                {"menu": m["menu"], "concepto": concepto, "orden": posicion,
                 "monto": monto, "monto_texto": pesos(monto), "total": pesos(m["costo"])}
            )
    nombres = [m["menu"] for m in por_menu]  # conserva el orden de mayor a menor costo
    grafico = (
        alt.Chart(pd.DataFrame(filas))
        .mark_bar(size=18, stroke=c["fondo"], strokeWidth=1)
        .encode(
            x=alt.X("monto:Q", title="Costo acumulado ($)", axis=alt.Axis(labelExpr=EJE_PESOS, tickCount=6)),
            y=alt.Y("menu:N", sort=nombres, title=None, axis=alt.Axis(labelLimit=210, labelOverlap=False)),  # muestra todos los nombres
            color=_escala_color("concepto", ["Costo aprovechado", "Pérdida por merma"], [c["costo"], c["merma"]]),
            order=alt.Order("orden:Q"),
            tooltip=[
                alt.Tooltip("menu:N", title="Menú"),
                alt.Tooltip("concepto:N", title="Concepto"),
                alt.Tooltip("monto_texto:N", title="Monto"),
                alt.Tooltip("total:N", title="Costo total del menú"),
            ],
        )
        .properties(height=max(360, 34 * len(nombres) + 120))  # espacio para barras, eje y leyenda
    )
    st.altair_chart(grafico, width="stretch")


# --- GRÁFICO DE LÍNEAS: EVOLUCIÓN ACUMULADA ---
def _grafico_lineas(evolucion: list) -> None:
    c = _colores()
    series = {"ingresos": "Ingresos proyectados", "costo": "Costo de operación", "merma": "Pérdida por merma"}
    filas = [
        {"servicio": f["servicio"], "serie": titulo, "monto": f[clave]}
        for f in evolucion
        for clave, titulo in series.items()
    ]
    eje_x = alt.X(
        "servicio:Q", title="Servicios en orden cronológico",
        axis=alt.Axis(format="d", tickMinStep=1), scale=alt.Scale(zero=False, nice=False, padding=12),
    )
    lineas = (
        alt.Chart(pd.DataFrame(filas))
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=64, filled=True))
        .encode(
            x=eje_x,
            y=alt.Y("monto:Q", title="Monto acumulado ($)", axis=alt.Axis(labelExpr=EJE_PESOS)),
            color=_escala_color("serie", list(series.values()), [c["ganancia"], c["costo"], c["merma"]]),
        )
    )
    detalle = pd.DataFrame(evolucion)
    for clave in series:  # montos formateados para el detalle emergente
        detalle[f"{clave}_texto"] = [pesos(v) for v in detalle[clave]]
    cursor = alt.selection_point(fields=["servicio"], nearest=True, on="pointerover", empty=False)  # sigue al puntero
    guia = (
        alt.Chart(detalle)
        .mark_rule(color=c["texto"], strokeWidth=8)
        .encode(
            x=eje_x,
            opacity=alt.condition(cursor, alt.value(0.15), alt.value(0)),  # solo visible bajo el puntero
            tooltip=[
                alt.Tooltip("orden:Q", title="Orden N°"),
                alt.Tooltip("menu:N", title="Menú"),
                alt.Tooltip("ingresos_texto:N", title="Ingresos acumulados"),
                alt.Tooltip("costo_texto:N", title="Costo acumulado"),
                alt.Tooltip("merma_texto:N", title="Merma acumulada"),
            ],
        )
        .add_params(cursor)
    )
    st.altair_chart((lineas + guia).properties(height=320), width="stretch")


# --- PANTALLA: RESUMEN EJECUTIVO ---
def pagina_resumen() -> None:
    st.title("Resumen ejecutivo")
    registros = _cargar_registros()           # órdenes registradas
    kpis = reportes.calcular_kpis(registros)  # calcula los indicadores

    c1, c2, c3, c4 = st.columns(4)  # indicadores principales
    c1.metric("Servicios realizados", numero(kpis["servicios"], 0), border=True)
    c2.metric("Costo total de operación", pesos(kpis["costo_total"]), border=True)
    c3.metric("Pérdida total por merma", pesos(kpis["perdida_merma"]), border=True)
    c4.metric("Ingresos proyectados", pesos(kpis["ingresos"]), border=True)

    c5, c6, c7 = st.columns(3)  # indicadores complementarios
    c5.metric("Comensales atendidos", numero(kpis["comensales"], 0), border=True)
    c6.metric("Ganancia proyectada (25 %)", pesos(kpis["ganancia"]), border=True)
    c7.metric("Merma sobre el costo", _porcentaje(kpis["porcentaje_merma"]), border=True)
    st.caption(
        "Se consideran todas las órdenes registradas (pendientes y preparadas). "
        "La pérdida por merma ya está incluida dentro del costo de operación."
    )

    if not registros:  # sin datos para graficar
        st.info("Aún no hay servicios registrados.")
        return

    por_menu = reportes.perdida_por_menu(registros)                               # totales por menú
    ordenado = quicksort(por_menu, clave=lambda f: f["costo"], descendente=True)  # ordena de mayor a menor costo
    partes = reportes.composicion_ingresos(kpis)         # datos de la torta
    evolucion = reportes.evolucion_acumulada(registros)  # datos de las líneas

    columna_torta, columna_barras = st.columns([2, 3], gap="large")  # dos gráficos lado a lado
    with columna_torta:
        st.subheader("Distribución de los ingresos")
        _grafico_torta(partes)
    with columna_barras:
        st.subheader("Costo y merma por menú")
        _grafico_costo_menu(ordenado)

    st.subheader("Evolución acumulada")  # gráfico a todo el ancho
    _grafico_lineas(evolucion)
    if len(evolucion) < 2:  # con un solo punto no se forma una línea
        st.caption("Las líneas se forman a partir del segundo servicio registrado.")

    with st.expander("Ver los datos de los gráficos"):  # los mismos valores en tablas
        tabla(
            partes,
            {"concepto": "Concepto", "monto": "Monto", "porcentaje": "% del ingreso"},
            {"monto": pesos, "porcentaje": _porcentaje},
        )
        tabla(
            ordenado,
            {"menu": "Menú", "costo": "Costo", "perdida": "Pérdida por merma"},
            {"costo": pesos, "perdida": pesos},
        )
        tabla(
            evolucion,
            {"orden": "Orden N°", "menu": "Menú", "ingresos": "Ingresos acumulados",
             "costo": "Costo acumulado", "merma": "Merma acumulada"},
            {"ingresos": pesos, "costo": pesos, "merma": pesos},
        )


# --- PANTALLA: HISTORIAL DE PREPARACIONES ---
def pagina_historial() -> None:
    st.title("Historial de preparaciones")
    registros = _cargar_registros()  # órdenes registradas
    if not registros:                # sin órdenes
        st.info("Aún no hay servicios registrados.")
        return
    with manejar_errores("cargar el catálogo"):
        _, recetas = cargar_catalogo()

    menus = st.multiselect(  # filtro por tipo de menú
        "Filtrar por tipo de menú", [r.nombre for r in recetas], placeholder="Todos los menús"
    )
    c1, c2, c3 = st.columns(3)  # opciones de ordenamiento
    campo = c1.selectbox("Ordenar por", list(CAMPOS_ORDEN))
    sentido = c2.selectbox("Sentido", ["Descendente", "Ascendente"])
    metodo = c3.selectbox("Algoritmo de ordenamiento", list(METODOS))

    filtrados = reportes.filtrar_por_menu(registros, menus)  # aplica el filtro de menú

    if filtrados:  # filtro por rango de pérdida
        perdidas = [r["perdida_merma"] for r in filtrados]
        menor, mayor = min(perdidas), max(perdidas)
        if menor < mayor:  # el deslizador requiere valores distintos
            minimo, maximo = st.slider(
                "Rango de pérdida por merma ($)",
                min_value=menor, max_value=mayor, value=(menor, mayor),
            )
            filtrados = reportes.filtrar_por_rango_perdida(filtrados, minimo, maximo)  # aplica el rango elegido

    if not filtrados:  # ninguna orden cumple los filtros
        st.warning("No hay órdenes que cumplan los filtros.")
        return

    llave = CAMPOS_ORDEN[campo]  # dato por el que se ordena
    opciones = {}
    if METODOS[metodo] is ordenamiento_externo:  # opción propia del método externo
        opciones["tam_bloque"] = st.number_input(
            "Registros por bloque en disco", min_value=1, max_value=1000, value=5
        )
    ordenados = METODOS[metodo](  # ejecuta el algoritmo elegido
        filtrados,
        clave=lambda r: r[llave],
        descendente=(sentido == "Descendente"),
        **opciones,
    )

    kpis = reportes.calcular_kpis(ordenados)  # totales de las órdenes filtradas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Órdenes filtradas", kpis["servicios"])
    m2.metric("Costo", pesos(kpis["costo_total"]))
    m3.metric("Pérdida por merma", pesos(kpis["perdida_merma"]))
    m4.metric("Venta", pesos(kpis["ingresos"]))

    columnas = {  # columnas de la tabla
        "orden": "N°", "fecha": "Fecha", "menu": "Menú", "comensales": "Comensales",
        "costo_total": "Costo total", "costo_por_plato": "Costo por plato",
        "merma_fisica": "Merma física", "perdida_merma": "Pérdida por merma",
        "venta_por_plato": "Venta por plato", "venta_total": "Venta total",
        "estado": "Estado", "solicitado_por": "Solicitado por",
    }
    formatos = {  # formato de fechas y montos
        "fecha": fecha_local, "costo_total": pesos, "costo_por_plato": pesos,
        "perdida_merma": pesos, "venta_por_plato": pesos, "venta_total": pesos,
    }
    st.caption("Seleccione una fila (casilla de la izquierda) para ver su desglose.")
    seleccion = tabla(  # tabla con selección de una fila
        ordenados, columnas, formatos,
        on_select="rerun", selection_mode="single-row",
        key=f"historial_{llave}_{sentido}_{metodo}_{menus}_{len(ordenados)}",  # reinicia la selección si cambian los filtros
    )

    exportables = pd.DataFrame(ordenados, columns=list(columnas)).rename(columns=columnas)  # datos para la descarga
    st.download_button(  # botón para descargar en CSV
        "Descargar historial filtrado (CSV)",
        exportables.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="historial_preparaciones.csv",
        mime="text/csv",
    )

    filas_marcadas = seleccion.selection.rows                  # fila seleccionada
    if filas_marcadas and filas_marcadas[0] < len(ordenados):  # muestra el desglose de esa orden
        _mostrar_desglose(ordenados[filas_marcadas[0]])


# --- DESGLOSE DE UNA ORDEN ---
def _mostrar_desglose(r: dict) -> None:
    st.subheader(f"Desglose orden N° {r['orden']} · {r['menu']}")
    c1, c2, c3, c4 = st.columns(4)  # datos principales de la orden
    c1.metric("Comensales", r["comensales"])
    c2.metric("Costo por plato", pesos(r["costo_por_plato"]))
    c3.metric("Pérdida por merma", pesos(r["perdida_merma"]))
    c4.metric("Venta por plato (+25 %)", pesos(r["venta_por_plato"]))
    tabla(  # detalle por ingrediente
        r["detalle"],
        {
            "ingrediente": "Ingrediente", "unidad": "Unidad de compra",
            "raciones": "Raciones", "cantidad_requerida": "Cantidad requerida",
            "unidades_completas": "Unidades usadas", "cantidad_merma": "Merma física",
            "costo_unitario": "Costo unitario", "costo_total": "Costo",
            "perdida": "Pérdida",
        },
        {
            "raciones": numero,
            "cantidad_requerida": lambda v: numero(v, 3),
            "cantidad_merma": lambda v: numero(v, 3),
            "costo_unitario": pesos, "costo_total": pesos, "perdida": pesos,
        },
    )
    st.caption(
        f"Costo total {pesos(r['costo_total'])} · Venta total {pesos(r['venta_total'])}"
    )


# --- PANTALLA: ANÁLISIS DE MERMAS ---
def pagina_analisis_mermas() -> None:
    st.title("Análisis de mermas e impacto económico")
    registros = _cargar_registros()  # órdenes registradas
    with manejar_errores("cargar el catálogo"):
        _, recetas = cargar_catalogo()

    tab_menu, tab_insumo, tab_simulador, tab_relacion = st.tabs(  # pestañas del análisis
        ["Por menú", "Por ingrediente", "Comparador de menús", "Relación menú-ingrediente"]
    )
    por_insumo = reportes.ranking_perdidas(reportes.perdida_por_ingrediente(registros))  # ingredientes de mayor a menor pérdida

    with tab_menu:  # pestaña: pérdida por menú
        if not registros:
            st.info("Aún no hay servicios registrados.")
        else:
            ranking = reportes.ranking_perdidas(reportes.perdida_por_menu(registros))  # menús de mayor a menor pérdida
            lider = ranking[0]  # menú con más pérdida
            st.error(
                f"Menú con mayor pérdida acumulada: **{lider['menu']}** "
                f"({pesos(lider['perdida']).replace('$', chr(92) + '$')})"
            )
            _grafico_barras(ranking, "menu", "perdida", "Pérdida por merma ($)")
            tabla(
                ranking,
                {
                    "menu": "Menú", "servicios": "Servicios", "costo": "Costo",
                    "perdida": "Pérdida", "perdida_promedio": "Pérdida por servicio",
                    "porcentaje_merma": "% merma",
                },
                {
                    "costo": pesos, "perdida": pesos, "perdida_promedio": pesos,
                    "porcentaje_merma": _porcentaje,
                },
            )

    with tab_insumo:  # pestaña: pérdida por ingrediente
        if not por_insumo:
            st.info("Aún no hay servicios registrados.")
        else:
            lider = por_insumo[0]  # ingrediente con más pérdida
            st.error(
                f"Ingrediente con mayor pérdida acumulada: **{lider['ingrediente']}** "
                f"({pesos(lider['perdida']).replace('$', chr(92) + '$')})"
            )
            _grafico_barras(por_insumo, "ingrediente", "perdida", "Pérdida por merma ($)")
            tabla(
                por_insumo,
                {
                    "ingrediente": "Ingrediente", "merma_fisica": "Merma física",
                    "unidad": "Unidad", "compra": "Compra", "perdida": "Pérdida",
                    "porcentaje_merma": "% merma",
                },
                {
                    "merma_fisica": lambda v: numero(v, 3), "compra": pesos,
                    "perdida": pesos, "porcentaje_merma": _porcentaje,
                },
            )

    with tab_simulador:  # pestaña: comparador de menús
        st.caption("Simulación para planificar compras: no guarda órdenes.")
        comensales = st.number_input(  # personas a simular
            "Comensales a comparar", min_value=1, max_value=MAX_COMENSALES, value=10, step=1
        )
        filas = mergesort(  # ordena de menor a mayor pérdida
            reportes.comparativo_teorico(recetas, int(comensales)),
            clave=lambda f: f["perdida"],
        )
        st.success(f"Menor pérdida para {comensales} comensales: **{filas[0]['menu']}**")
        _grafico_barras(filas, "menu", "perdida", "Pérdida estimada ($)")
        tabla(
            filas,
            {
                "menu": "Menú", "costo_total": "Costo total",
                "costo_por_plato": "Costo por plato", "venta_por_plato": "Venta por plato",
                "perdida": "Pérdida", "porcentaje_merma": "% merma",
            },
            {
                "costo_total": pesos, "costo_por_plato": pesos, "venta_por_plato": pesos,
                "perdida": pesos, "porcentaje_merma": _porcentaje,
            },
        )

    with tab_relacion:  # pestaña: relación entre menús e ingredientes
        grafo = reportes.construir_grafo(recetas)                                   # construye el grafo
        nombres = [v[1] for v in grafo.vertices() if v[0] == "ingrediente"]         # lista de ingredientes
        inicial = nombres.index(por_insumo[0]["ingrediente"]) if por_insumo else 0  # parte con el ingrediente de mayor pérdida
        insumo = st.selectbox("Ingrediente", nombres, index=inicial)
        menus = reportes.menus_que_usan(grafo, insumo)  # menús afectados por el ingrediente
        st.write(f"**{insumo}** afecta a **{len(menus)}** menú(s): {', '.join(menus)}.")

        menu = st.selectbox("Ver menús relacionados con", [r.nombre for r in recetas])
        relacionados = quicksort(  # ordena por ingredientes en común
            reportes.menus_relacionados(grafo, menu),
            clave=lambda f: f["compartidos"],
            descendente=True,
        )
        tabla(
            relacionados,
            {"menu": "Menú", "compartidos": "N° en común", "ingredientes": "Ingredientes en común"},
        )


# --- PANTALLA: CATÁLOGO Y COSTOS ---
def pagina_catalogo() -> None:
    st.title("Catálogo de insumos y recetas")
    with manejar_errores("cargar el catálogo"):
        ingredientes, recetas = cargar_catalogo()

    texto = st.text_input("Buscar insumo por nombre", placeholder="Ej.: carne")  # texto a buscar
    encontrados = buscar_por_nombre(ingredientes, texto, lambda i: i.nombre)     # insumos que coinciden
    if encontrados:  # muestra los insumos con su costo
        tabla(
            [vars(i) for i in encontrados],
            {
                "nombre": "Insumo", "costo_unitario": "Costo unitario",
                "unidad_compra": "Unidad de compra", "rendimiento": "Rinde (personas)",
            },
            {"costo_unitario": pesos},
        )
    else:
        st.warning("No se encontraron insumos con ese nombre.")

    st.subheader("Recetas")  # consulta de recetas
    nombre = st.selectbox("Receta", [r.nombre for r in recetas])
    receta = busqueda_secuencial(recetas, lambda r: r.nombre == nombre)  # receta seleccionada
    tabla(
        [
            {"insumo": it.ingrediente.nombre, "texto": it.texto_receta, "raciones": it.raciones_base}
            for it in receta.items
        ],
        {"insumo": "Insumo", "texto": "Cantidad en receta", "raciones": "Raciones (base 4)"},
    )
