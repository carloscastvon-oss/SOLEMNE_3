from estructuras.tda import Cola
from logica.formato import cantidad
from logica.motor_calculo import calcular_orden
from modelos.entidades import Ingrediente, LineaPreparacion, OrdenPreparacion, Receta


# Traduce un cálculo a la línea que lee cocina: solo cantidades.
def crear_linea(ingrediente: Ingrediente, raciones, unidades: int) -> LineaPreparacion:
    nombre_racion = ingrediente.nombre_racion
    # Singular: "1 porción", "1 huevo", "1 tuto".
    singular = "porción" if nombre_racion == "porciones" else nombre_racion.rstrip("s")
    return LineaPreparacion(
        ingrediente=ingrediente.nombre,
        a_preparar=cantidad(raciones, singular, nombre_racion),
        a_retirar=cantidad(unidades, ingrediente.unidad_compra, ingrediente.unidad_compra_plural),
    )


def solicitar_servicio(repositorio, receta: Receta, comensales, perfil: str) -> OrdenPreparacion:
    """Valida, calcula, guarda en Supabase y retorna solo la vista operativa."""
    resultado = calcular_orden(receta, comensales)  # lanza ErrorValidacion
    # Se guardan todos los cálculos, aunque cocina no los vea.
    numero = repositorio.registrar_orden(resultado, perfil)
    return OrdenPreparacion(
        numero=numero,
        menu=receta.nombre,
        comensales=resultado.comensales,
        lineas=tuple(
            crear_linea(d.ingrediente, d.raciones, d.unidades_completas)
            for d in resultado.detalles
        ),
    )


def cola_de_pendientes(filas: list, ingredientes: list) -> Cola:
    """
    Encola las órdenes pendientes en orden de llegada: la cocina atiende primero
    la más antigua (FIFO).
    """
    # Índice para recuperar el ingrediente por su identificador.
    por_id = {i.id: i for i in ingredientes}
    cola: Cola = Cola()
    for fila in filas:
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
