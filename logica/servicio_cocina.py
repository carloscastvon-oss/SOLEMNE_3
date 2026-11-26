# --- IMPORTACIONES ---
from estructuras.tda import Cola  # cola propia
from logica.formato import cantidad  # formato de cantidades
from logica.motor_calculo import calcular_orden                                        # motor de cálculo
from modelos.entidades import Ingrediente, LineaPreparacion, OrdenPreparacion, Receta  # clases del sistema


# --- LÍNEA DE PREPARACIÓN PARA COCINA ---
def crear_linea(ingrediente: Ingrediente, raciones, unidades: int) -> LineaPreparacion:
    nombre_racion = ingrediente.nombre_racion
    singular = "porción" if nombre_racion == "porciones" else nombre_racion.rstrip("s")  # nombre de la ración en singular
    return LineaPreparacion(
        ingrediente=ingrediente.nombre,
        a_preparar=cantidad(raciones, singular, nombre_racion),                                     # raciones o piezas a preparar
        a_retirar=cantidad(unidades, ingrediente.unidad_compra, ingrediente.unidad_compra_plural),  # unidades completas a retirar
    )


# --- SOLICITUD DE UN SERVICIO ---
def solicitar_servicio(repositorio, receta: Receta, comensales, perfil: str) -> OrdenPreparacion:
    resultado = calcular_orden(receta, comensales)           # valida y calcula
    numero = repositorio.registrar_orden(resultado, perfil)  # guarda todos los cálculos y obtiene el número
    return OrdenPreparacion(                                 # entrega a cocina solo las cantidades
        numero=numero,
        menu=receta.nombre,
        comensales=resultado.comensales,
        lineas=tuple(
            crear_linea(d.ingrediente, d.raciones, d.unidades_completas)
            for d in resultado.detalles
        ),
    )


# --- COLA DE ÓRDENES PENDIENTES ---
def cola_de_pendientes(filas: list, ingredientes: list) -> Cola:
    por_id = {i.id: i for i in ingredientes}  # ingredientes indexados por identificador
    cola: Cola = Cola()                       # la orden más antigua se atiende primero
    for fila in filas:                        # las filas vienen en orden de llegada
        cola.encolar(
            OrdenPreparacion(
                numero=fila["id"],
                menu=fila["recetas"]["nombre"],
                comensales=fila["comensales"],
                lineas=tuple(
                    crear_linea(
                        por_id[d["ingrediente_id"]], d["raciones"], d["unidades_completas"]
                    )
                    for d in fila["orden_detalle"]
                ),
                estado=fila["estado"],
                fecha=fila["creado_en"],
            )
        )
    return cola
