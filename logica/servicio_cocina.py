"""
===============================================================================
 Archivo      : logica/servicio_cocina.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : solo módulos del proyecto
 Descripción  : Casos de uso de cocina. Todo lo que sale de este módulo hacia
                la interfaz es una OrdenPreparacion, sin datos financieros.
===============================================================================
"""

from estructuras.tda import Cola
from logica.formato import cantidad
from logica.motor_calculo import calcular_orden
from modelos.entidades import Ingrediente, LineaPreparacion, OrdenPreparacion, Receta


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
