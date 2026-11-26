"""
===============================================================================
 Archivo      : logica/reportes.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : solo módulos del proyecto
 Descripción  : Cálculos del panel gerencial: KPIs, filtros, rankings de
                pérdida y relación menú-ingrediente. Funciones puras.
===============================================================================
"""

from algoritmos.busqueda import busqueda_secuencial_todos
from estructuras.tda import ArbolBinarioBusqueda, ColaPrioridad, Grafo
from logica.formato import numero
from logica.motor_calculo import calcular_orden


def aplanar_ordenes(filas: list) -> list[dict]:
    """
    Convierte la respuesta anidada de Supabase en registros planos. Solo usa
    tipos compatibles con JSON para poder aplicar el ordenamiento externo.
    """
    registros = []
    for fila in filas:
        detalle = []
        for d in fila["orden_detalle"]:
            # La relación detalle-merma es 1 a 1: la API la entrega como objeto
            # (o como lista de un elemento, según detecte la relación).
            merma = d["mermas"][0] if isinstance(d["mermas"], list) else d["mermas"]
            ingrediente = d["ingredientes"]
            detalle.append(
                {
                    "ingrediente": ingrediente["nombre"],
                    "unidad": ingrediente["unidad_compra"],
                    "unidad_plural": ingrediente["unidad_compra_plural"],
                    "raciones": float(d["raciones"]),
                    "cantidad_requerida": float(d["cantidad_requerida"]),
                    "unidades_completas": d["unidades_completas"],
                    "costo_unitario": d["costo_unitario"],
                    "costo_total": float(d["costo_total"]),
                    "cantidad_merma": float(merma["cantidad_merma"]),
                    "perdida": float(merma["perdida"]),
                }
            )
        registros.append(
            {
                "orden": fila["id"],
                "fecha": fila["creado_en"],
                "menu": fila["recetas"]["nombre"],
                "solicitado_por": fila["perfiles"]["nombre"],
                "estado": fila["estado"],
                "comensales": fila["comensales"],
                "costo_total": float(fila["costo_total"]),
                "costo_por_plato": float(fila["costo_por_plato"]),
                "venta_por_plato": float(fila["venta_por_plato"]),
                "venta_total": float(fila["venta_total"]),
                "perdida_merma": float(fila["perdida_merma"]),
                "merma_fisica": describir_merma(detalle),
                "detalle": detalle,
            }
        )
    return registros


def describir_merma(detalle: list) -> str:
    """
    La merma física tiene unidades distintas (kg, litros, paquetes): no se puede
    sumar en un solo número, por eso se describe ingrediente por ingrediente.
    """
    partes = [
        f"{d['ingrediente']}: {numero(d['cantidad_merma'], 3)} {d['unidad']}"
        for d in detalle
        if d["cantidad_merma"] > 0
    ]
    return "; ".join(partes) if partes else "Sin merma"


def calcular_kpis(registros: list) -> dict:
    """Indicadores globales (una sola pasada por los registros)."""
    kpis = {
        "servicios": 0, "comensales": 0, "costo_total": 0.0,
        "perdida_merma": 0.0, "ingresos": 0.0,
    }
    for r in registros:
        kpis["servicios"] += 1
        kpis["comensales"] += r["comensales"]
        kpis["costo_total"] += r["costo_total"]
        kpis["perdida_merma"] += r["perdida_merma"]
        kpis["ingresos"] += r["venta_total"]
    kpis["ganancia"] = kpis["ingresos"] - kpis["costo_total"]
    # Se protege la división cuando todavía no hay servicios.
    kpis["porcentaje_merma"] = (
        100 * kpis["perdida_merma"] / kpis["costo_total"] if kpis["costo_total"] else 0.0
    )
    return kpis


def filtrar_por_menu(registros: list, menus: list) -> list:
    """Búsqueda secuencial. Si no se elige ningún menú, se muestran todos."""
    if not menus:
        return list(registros)
    return busqueda_secuencial_todos(registros, lambda r: r["menu"] in menus)


def filtrar_por_rango_perdida(registros: list, minimo: float, maximo: float) -> list:
    """Indexa las órdenes en un árbol binario por pérdida y consulta el rango."""
    arbol = ArbolBinarioBusqueda()
    for registro in registros:
        arbol.insertar(registro["perdida_merma"], registro)
    return arbol.rango(minimo, maximo)


def perdida_por_menu(registros: list) -> list[dict]:
    acumulado: dict = {}
    for r in registros:
        fila = acumulado.setdefault(
            r["menu"], {"menu": r["menu"], "servicios": 0, "costo": 0.0, "perdida": 0.0}
        )
        fila["servicios"] += 1
        fila["costo"] += r["costo_total"]
        fila["perdida"] += r["perdida_merma"]
    for fila in acumulado.values():
        fila["perdida_promedio"] = fila["perdida"] / fila["servicios"]
        fila["porcentaje_merma"] = 100 * fila["perdida"] / fila["costo"]
    return list(acumulado.values())


def perdida_por_ingrediente(registros: list) -> list[dict]:
    acumulado: dict = {}
    for r in registros:
        for d in r["detalle"]:
            fila = acumulado.setdefault(
                d["ingrediente"],
                {
                    "ingrediente": d["ingrediente"], "unidad": d["unidad_plural"],
                    "merma_fisica": 0.0, "compra": 0.0, "perdida": 0.0,
                },
            )
            fila["merma_fisica"] += d["cantidad_merma"]
            fila["compra"] += d["costo_total"]
            fila["perdida"] += d["perdida"]
    for fila in acumulado.values():
        fila["porcentaje_merma"] = 100 * fila["perdida"] / fila["compra"]
    return list(acumulado.values())


def ranking_perdidas(filas: list, limite: int | None = None) -> list:
    """
    Jerarquiza por pérdida usando la cola con prioridad: se extrae siempre la
    mayor. Para un "Top k" no es necesario ordenar el resto de los datos.
    """
    cola: ColaPrioridad = ColaPrioridad(prioridad=lambda f: f["perdida"], mayor_primero=True)
    for fila in filas:
        cola.insertar(fila)
    limite = len(cola) if limite is None else min(limite, len(cola))
    return [cola.extraer() for _ in range(limite)]


def construir_grafo(recetas: list) -> Grafo:
    """
    Grafo bipartito menú <-> ingrediente. Los vértices son tuplas (tipo, nombre)
    para que un menú y un ingrediente nunca se confundan.
    """
    grafo = Grafo()
    for receta in recetas:
        for item in receta.items:
            grafo.agregar_arista(("menu", receta.nombre), ("ingrediente", item.ingrediente.nombre))
    return grafo


def menus_que_usan(grafo: Grafo, ingrediente: str) -> list[str]:
    return [nombre for _, nombre in grafo.vecinos(("ingrediente", ingrediente))]


def menus_relacionados(grafo: Grafo, menu: str) -> list[dict]:
    """Menús a distancia 2 (comparten al menos un ingrediente) con los comunes."""
    propios = {nombre for _, nombre in grafo.vecinos(("menu", menu))}
    relacionados = []
    for vertice in grafo.a_distancia(("menu", menu), 2):
        comunes = [n for _, n in grafo.vecinos(vertice) if n in propios]
        relacionados.append(
            {"menu": vertice[1], "compartidos": len(comunes), "ingredientes": ", ".join(comunes)}
        )
    return relacionados


def comparativo_teorico(recetas: list, comensales: int) -> list[dict]:
    """
    Simula todos los menús para la misma cantidad de comensales (no se guarda
    nada). Sirve para elegir el menú que desperdicia menos.
    """
    filas = []
    for receta in recetas:
        r = calcular_orden(receta, comensales)
        filas.append(
            {
                "menu": receta.nombre,
                "costo_total": float(r.costo_total),
                "costo_por_plato": float(r.costo_por_plato),
                "venta_por_plato": float(r.venta_por_plato),
                "perdida": float(r.perdida_merma),
                "porcentaje_merma": float(100 * r.perdida_merma / r.costo_total),
            }
        )
    return filas
