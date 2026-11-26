"""
===============================================================================
 Archivo      : ui/vista_admin.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : streamlit, pandas, altair
 Descripción  : Panel gerencial del administrador: KPIs, historial filtrable y
                análisis de desechos e impacto económico.
===============================================================================
"""

import altair as alt
import pandas as pd
import streamlit as st

from algoritmos.busqueda import buscar_por_nombre, busqueda_secuencial
from algoritmos.ordenamiento import METODOS, mergesort, ordenamiento_externo, quicksort
from logica import reportes
from logica.formato import fecha_local, numero, pesos
from logica.motor_calculo import MAX_COMENSALES
from ui.comun import cargar_catalogo, manejar_errores, obtener_repositorio, tabla

# Campos por los que se puede ordenar el historial: título -> clave del registro.
CAMPOS_ORDEN = {
    "Fecha": "fecha",
    "Pérdida por merma": "perdida_merma",
    "Costo total": "costo_total",
    "Costo por plato": "costo_por_plato",
    "Valor de venta total": "venta_total",
    "Comensales": "comensales",
    "Menú": "menu",
}


def _cargar_registros() -> list:
    with manejar_errores("consultar el historial"):
        return reportes.aplanar_ordenes(obtener_repositorio().ordenes_completas())


def _porcentaje(valor) -> str:
    return f"{numero(valor, 1)} %"


def _grafico_barras(filas: list, categoria: str, valor: str, titulo_valor: str) -> None:
    """
    Barras horizontales (los nombres de menú son largos). Respeta el orden de
    la lista recibida, que ya viene jerarquizada por nuestros algoritmos.
    """
    datos = pd.DataFrame(filas)
    grafico = (
        alt.Chart(datos)
        .mark_bar()
        .encode(
            x=alt.X(f"{valor}:Q", title=titulo_valor),
            y=alt.Y(f"{categoria}:N", sort=None, title=None, axis=alt.Axis(labelLimit=260)),
            tooltip=[
                alt.Tooltip(f"{categoria}:N", title="Nombre"),
                alt.Tooltip(f"{valor}:Q", title=titulo_valor, format=",.2f"),
            ],
        )
        .properties(height=max(120, 34 * len(datos)))
    )
    st.altair_chart(grafico, width="stretch")


# ---------------------------------------------------------------------------
# 1. Resumen ejecutivo
# ---------------------------------------------------------------------------
def pagina_resumen() -> None:
    st.title("Resumen ejecutivo")
    registros = _cargar_registros()
    kpis = reportes.calcular_kpis(registros)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Servicios realizados", numero(kpis["servicios"], 0), border=True)
    c2.metric("Costo total de operación", pesos(kpis["costo_total"]), border=True)
    c3.metric("Pérdida total por merma", pesos(kpis["perdida_merma"]), border=True)
    c4.metric("Ingresos proyectados", pesos(kpis["ingresos"]), border=True)

    c5, c6, c7 = st.columns(3)
    c5.metric("Comensales atendidos", numero(kpis["comensales"], 0), border=True)
    c6.metric("Ganancia proyectada (25 %)", pesos(kpis["ganancia"]), border=True)
    c7.metric("Merma sobre el costo", _porcentaje(kpis["porcentaje_merma"]), border=True)
    st.caption(
        "Se consideran todas las órdenes registradas (pendientes y preparadas). "
        "La pérdida por merma ya está incluida dentro del costo de operación."
    )

    if not registros:
        st.info("Aún no hay servicios registrados.")
        return

    por_menu = reportes.perdida_por_menu(registros)
    ordenado = quicksort(por_menu, clave=lambda f: f["costo"], descendente=True)
    st.subheader("Costo acumulado por menú")
    _grafico_barras(ordenado, "menu", "costo", "Costo acumulado ($)")


# ---------------------------------------------------------------------------
# 2. Historial detallado y filtrable
# ---------------------------------------------------------------------------
def pagina_historial() -> None:
    st.title("Historial de preparaciones")
    registros = _cargar_registros()
    if not registros:
        st.info("Aún no hay servicios registrados.")
        return
    with manejar_errores("cargar el catálogo"):
        _, recetas = cargar_catalogo()

    menus = st.multiselect(
        "Filtrar por tipo de menú", [r.nombre for r in recetas], placeholder="Todos los menús"
    )
    c1, c2, c3 = st.columns(3)
    campo = c1.selectbox("Ordenar por", list(CAMPOS_ORDEN))
    sentido = c2.selectbox("Sentido", ["Descendente", "Ascendente"])
    metodo = c3.selectbox("Algoritmo de ordenamiento", list(METODOS))

    filtrados = reportes.filtrar_por_menu(registros, menus)

    # Filtro por rango de pérdida (árbol binario de búsqueda).
    if filtrados:
        perdidas = [r["perdida_merma"] for r in filtrados]
        menor, mayor = min(perdidas), max(perdidas)
        if menor < mayor:  # el deslizador necesita un rango no vacío
            minimo, maximo = st.slider(
                "Rango de pérdida por merma ($)",
                min_value=menor, max_value=mayor, value=(menor, mayor),
            )
            filtrados = reportes.filtrar_por_rango_perdida(filtrados, minimo, maximo)

    if not filtrados:
        st.warning("No hay órdenes que cumplan los filtros.")
        return

    llave = CAMPOS_ORDEN[campo]
    opciones = {}
    if METODOS[metodo] is ordenamiento_externo:
        # Bloques pequeños para que se generen varios archivos y exista mezcla.
        opciones["tam_bloque"] = st.number_input(
            "Registros por bloque en disco", min_value=1, max_value=1000, value=5
        )
    ordenados = METODOS[metodo](
        filtrados,
        clave=lambda r: r[llave],
        descendente=(sentido == "Descendente"),
        **opciones,
    )

    # Totales del subconjunto filtrado.
    kpis = reportes.calcular_kpis(ordenados)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Órdenes filtradas", kpis["servicios"])
    m2.metric("Costo", pesos(kpis["costo_total"]))
    m3.metric("Pérdida por merma", pesos(kpis["perdida_merma"]))
    m4.metric("Venta", pesos(kpis["ingresos"]))

    columnas = {
        "orden": "N°", "fecha": "Fecha", "menu": "Menú", "comensales": "Comensales",
        "costo_total": "Costo total", "costo_por_plato": "Costo por plato",
        "merma_fisica": "Merma física", "perdida_merma": "Pérdida por merma",
        "venta_por_plato": "Venta por plato", "venta_total": "Venta total",
        "estado": "Estado", "solicitado_por": "Solicitado por",
    }
    formatos = {
        "fecha": fecha_local, "costo_total": pesos, "costo_por_plato": pesos,
        "perdida_merma": pesos, "venta_por_plato": pesos, "venta_total": pesos,
    }
    st.caption("Seleccione una fila (casilla de la izquierda) para ver su desglose.")
    seleccion = tabla(
        ordenados, columnas, formatos,
        on_select="rerun", selection_mode="single-row",
        # La llave cambia con los filtros: evita que quede marcada otra orden.
        key=f"historial_{llave}_{sentido}_{metodo}_{menus}_{len(ordenados)}",
    )

    exportables = pd.DataFrame(ordenados, columns=list(columnas)).rename(columns=columnas)
    st.download_button(
        "Descargar historial filtrado (CSV)",
        exportables.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="historial_preparaciones.csv",
        mime="text/csv",
    )

    filas_marcadas = seleccion.selection.rows
    if filas_marcadas and filas_marcadas[0] < len(ordenados):
        _mostrar_desglose(ordenados[filas_marcadas[0]])


def _mostrar_desglose(r: dict) -> None:
    st.subheader(f"Desglose orden N° {r['orden']} · {r['menu']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Comensales", r["comensales"])
    c2.metric("Costo por plato", pesos(r["costo_por_plato"]))
    c3.metric("Pérdida por merma", pesos(r["perdida_merma"]))
    c4.metric("Venta por plato (+25 %)", pesos(r["venta_por_plato"]))
    tabla(
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


# ---------------------------------------------------------------------------
# 3. Análisis de desechos e impacto económico
# ---------------------------------------------------------------------------
def pagina_analisis_mermas() -> None:
    st.title("Análisis de mermas e impacto económico")
    registros = _cargar_registros()
    with manejar_errores("cargar el catálogo"):
        _, recetas = cargar_catalogo()

    tab_menu, tab_insumo, tab_simulador, tab_relacion = st.tabs(
        ["Por menú", "Por ingrediente", "Comparador de menús", "Relación menú-ingrediente"]
    )
    por_insumo = reportes.ranking_perdidas(reportes.perdida_por_ingrediente(registros))

    with tab_menu:
        if not registros:
            st.info("Aún no hay servicios registrados.")
        else:
            ranking = reportes.ranking_perdidas(reportes.perdida_por_menu(registros))
            lider = ranking[0]
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

    with tab_insumo:
        if not por_insumo:
            st.info("Aún no hay servicios registrados.")
        else:
            lider = por_insumo[0]
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

    with tab_simulador:
        st.caption("Simulación para planificar compras: no guarda órdenes.")
        comensales = st.number_input(
            "Comensales a comparar", min_value=1, max_value=MAX_COMENSALES, value=10, step=1
        )
        filas = mergesort(
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

    with tab_relacion:
        grafo = reportes.construir_grafo(recetas)
        nombres = [v[1] for v in grafo.vertices() if v[0] == "ingrediente"]
        # Por defecto se analiza el ingrediente que más dinero está perdiendo.
        inicial = nombres.index(por_insumo[0]["ingrediente"]) if por_insumo else 0
        insumo = st.selectbox("Ingrediente", nombres, index=inicial)
        menus = reportes.menus_que_usan(grafo, insumo)
        st.write(f"**{insumo}** afecta a **{len(menus)}** menú(s): {', '.join(menus)}.")

        menu = st.selectbox("Ver menús relacionados con", [r.nombre for r in recetas])
        relacionados = quicksort(
            reportes.menus_relacionados(grafo, menu),
            clave=lambda f: f["compartidos"],
            descendente=True,
        )
        tabla(
            relacionados,
            {"menu": "Menú", "compartidos": "N° en común", "ingredientes": "Ingredientes en común"},
        )


# ---------------------------------------------------------------------------
# 4. Catálogo con costos
# ---------------------------------------------------------------------------
def pagina_catalogo() -> None:
    st.title("Catálogo de insumos y recetas")
    with manejar_errores("cargar el catálogo"):
        ingredientes, recetas = cargar_catalogo()

    texto = st.text_input("Buscar insumo por nombre", placeholder="Ej.: carne")
    encontrados = buscar_por_nombre(ingredientes, texto, lambda i: i.nombre)
    if encontrados:
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

    st.subheader("Recetas")
    nombre = st.selectbox("Receta", [r.nombre for r in recetas])
    receta = busqueda_secuencial(recetas, lambda r: r.nombre == nombre)
    tabla(
        [
            {"insumo": it.ingrediente.nombre, "texto": it.texto_receta, "raciones": it.raciones_base}
            for it in receta.items
        ],
        {"insumo": "Insumo", "texto": "Cantidad en receta", "raciones": "Raciones (base 4)"},
    )
