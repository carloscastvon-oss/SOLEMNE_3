# --- IMPORTACIONES ---
from algoritmos.busqueda import busqueda_secuencial_todos               # búsqueda secuencial propia
from estructuras.tda import ArbolBinarioBusqueda, ColaPrioridad, Grafo  # árbol, cola con prioridad y grafo
from logica.formato import numero                                       # formato de números
from logica.motor_calculo import calcular_orden                         # motor de cálculo


# --- PREPARACIÓN DE LOS REGISTROS ---
def aplanar_ordenes(filas: list) -> list[dict]:
    registros = []  # lista de órdenes simplificadas
    for fila in filas:
        detalle = []
        for d in fila["orden_detalle"]:  # procesa cada ingrediente de la orden
            merma = d["mermas"][0] if isinstance(d["mermas"], list) else d["mermas"]  # la merma puede venir como objeto o como lista
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
        registros.append(  # agrega la orden con su detalle
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


# --- DESCRIPCIÓN DE LA MERMA FÍSICA ---
def describir_merma(detalle: list) -> str:
    partes = [  # detalle por ingrediente, porque las unidades difieren
        f"{d['ingrediente']}: {numero(d['cantidad_merma'], 3)} {d['unidad']}"
        for d in detalle
        if d["cantidad_merma"] > 0  # solo los ingredientes con sobrante
    ]
    return "; ".join(partes) if partes else "Sin merma"


# --- INDICADORES GLOBALES ---
def calcular_kpis(registros: list) -> dict:
    kpis = {  # acumuladores en cero
        "servicios": 0, "comensales": 0, "costo_total": 0.0,
        "perdida_merma": 0.0, "ingresos": 0.0,
    }
    for r in registros:  # suma los datos de cada orden
        kpis["servicios"] += 1
        kpis["comensales"] += r["comensales"]
        kpis["costo_total"] += r["costo_total"]
        kpis["perdida_merma"] += r["perdida_merma"]
        kpis["ingresos"] += r["venta_total"]
    kpis["ganancia"] = kpis["ingresos"] - kpis["costo_total"]  # ingresos menos costos
    kpis["porcentaje_merma"] = (                               # evita dividir por cero
        100 * kpis["perdida_merma"] / kpis["costo_total"] if kpis["costo_total"] else 0.0
    )
    return kpis


# --- FILTRO POR MENÚ ---
def filtrar_por_menu(registros: list, menus: list) -> list:
    if not menus:  # sin selección se muestran todos
        return list(registros)
    return busqueda_secuencial_todos(registros, lambda r: r["menu"] in menus)


# --- FILTRO POR RANGO DE PÉRDIDA ---
def filtrar_por_rango_perdida(registros: list, minimo: float, maximo: float) -> list:
    arbol = ArbolBinarioBusqueda()  # árbol ordenado por pérdida
    for registro in registros:
        arbol.insertar(registro["perdida_merma"], registro)
    return arbol.rango(minimo, maximo)  # órdenes dentro del rango


# --- PÉRDIDA ACUMULADA POR MENÚ ---
def perdida_por_menu(registros: list) -> list[dict]:
    acumulado: dict = {}  # un total por cada menú
    for r in registros:
        fila = acumulado.setdefault(
            r["menu"], {"menu": r["menu"], "servicios": 0, "costo": 0.0, "perdida": 0.0}
        )
        fila["servicios"] += 1
        fila["costo"] += r["costo_total"]
        fila["perdida"] += r["perdida_merma"]
    for fila in acumulado.values():  # calcula promedios y porcentajes
        fila["perdida_promedio"] = fila["perdida"] / fila["servicios"]
        fila["porcentaje_merma"] = 100 * fila["perdida"] / fila["costo"]
    return list(acumulado.values())


# --- PÉRDIDA ACUMULADA POR INGREDIENTE ---
def perdida_por_ingrediente(registros: list) -> list[dict]:
    acumulado: dict = {}  # un total por cada ingrediente
    for r in registros:
        for d in r["detalle"]:  # recorre los ingredientes de cada orden
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
    for fila in acumulado.values():  # porcentaje perdido de lo comprado
        fila["porcentaje_merma"] = 100 * fila["perdida"] / fila["compra"]
    return list(acumulado.values())


# --- RANKING DE PÉRDIDAS ---
def ranking_perdidas(filas: list, limite: int | None = None) -> list:
    cola: ColaPrioridad = ColaPrioridad(prioridad=lambda f: f["perdida"], mayor_primero=True)  # sale primero la pérdida mayor
    for fila in filas:
        cola.insertar(fila)
    limite = len(cola) if limite is None else min(limite, len(cola))  # cantidad de posiciones a entregar
    return [cola.extraer() for _ in range(limite)]                    # extrae en orden de mayor a menor


# --- GRAFO DE MENÚS E INGREDIENTES ---
def construir_grafo(recetas: list) -> Grafo:
    grafo = Grafo()
    for receta in recetas:
        for item in receta.items:
            grafo.agregar_arista(("menu", receta.nombre), ("ingrediente", item.ingrediente.nombre))  # conecta cada menú con sus ingredientes
    return grafo


# --- MENÚS QUE USAN UN INGREDIENTE ---
def menus_que_usan(grafo: Grafo, ingrediente: str) -> list[str]:
    return [nombre for _, nombre in grafo.vecinos(("ingrediente", ingrediente))]  # son los vecinos del ingrediente


# --- MENÚS CON INGREDIENTES EN COMÚN ---
def menus_relacionados(grafo: Grafo, menu: str) -> list[dict]:
    propios = {nombre for _, nombre in grafo.vecinos(("menu", menu))}  # ingredientes del menú elegido
    relacionados = []
    for vertice in grafo.a_distancia(("menu", menu), 2):                  # a distancia 2 están los menús relacionados
        comunes = [n for _, n in grafo.vecinos(vertice) if n in propios]  # ingredientes que comparten
        relacionados.append(
            {"menu": vertice[1], "compartidos": len(comunes), "ingredientes": ", ".join(comunes)}
        )
    return relacionados


# --- SIMULACIÓN COMPARATIVA DE MENÚS ---
def comparativo_teorico(recetas: list, comensales: int) -> list[dict]:
    filas = []
    for receta in recetas:  # calcula cada menú sin guardar
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
