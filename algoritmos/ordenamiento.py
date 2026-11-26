"""
===============================================================================
 Archivo      : algoritmos/ordenamiento.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : json, os, tempfile (biblioteca estándar)
 Descripción  : Algoritmos de ordenamiento implementados a mano (no se usa
                sorted() ni list.sort()):
                  - INTERNOS : QuickSort y MergeSort (todo en memoria RAM).
                  - EXTERNO  : Mezcla externa (external merge sort) usando
                    archivos temporales en disco.

 Criterio de elección:
   * QuickSort : rápido en promedio O(n log n) y casi sin memoria extra.
                 No es estable (puede alterar el orden entre empates).
   * MergeSort : O(n log n) garantizado y estable; usa memoria O(n).
   * Externo   : para historiales que no caben en memoria; solo se mantiene en
                 RAM un bloque y un registro por cada archivo que se fusiona.
===============================================================================
"""

import json
import os
import tempfile
from typing import Any, Callable, Iterable, Iterator

from estructuras.tda import ColaPrioridad, Pila

Clave = Callable[[Any], Any]


def _va_antes(a, b, clave: Clave, descendente: bool) -> bool:
    """True si `a` debe quedar estrictamente antes que `b`."""
    return clave(a) > clave(b) if descendente else clave(a) < clave(b)


# ---------------------------------------------------------------------------
# Ordenamiento interno
# ---------------------------------------------------------------------------
def quicksort(datos: Iterable, clave: Clave, descendente: bool = False) -> list:
    """
    QuickSort iterativo. Los subarreglos pendientes se guardan en una Pila
    propia (en vez de recursión). El pivote es el elemento central, lo que
    evita el peor caso cuando los datos ya vienen ordenados (algo habitual en
    un historial por fecha). La partición de Hoare reparte bien los repetidos.
    """
    arreglo = list(datos)  # copia: no se modifica la entrada
    pendientes: Pila = Pila()
    pendientes.apilar((0, len(arreglo) - 1))

    while not pendientes.esta_vacia():
        inicio, fin = pendientes.desapilar()
        if inicio >= fin:  # 0 o 1 elemento: ya está ordenado
            continue
        pivote = arreglo[(inicio + fin) // 2]
        i, j = inicio, fin
        while i <= j:
            while _va_antes(arreglo[i], pivote, clave, descendente):
                i += 1
            while _va_antes(pivote, arreglo[j], clave, descendente):
                j -= 1
            if i <= j:
                arreglo[i], arreglo[j] = arreglo[j], arreglo[i]
                i += 1
                j -= 1
        pendientes.apilar((inicio, j))
        pendientes.apilar((i, fin))
    return arreglo


def mergesort(datos: Iterable, clave: Clave, descendente: bool = False) -> list:
    """MergeSort recursivo y estable: divide en mitades y luego las mezcla."""
    arreglo = list(datos)
    if len(arreglo) <= 1:
        return arreglo
    medio = len(arreglo) // 2
    izquierda = mergesort(arreglo[:medio], clave, descendente)
    derecha = mergesort(arreglo[medio:], clave, descendente)

    resultado, i, j = [], 0, 0
    while i < len(izquierda) and j < len(derecha):
        # Ante empate se toma el de la izquierda: eso garantiza estabilidad.
        if _va_antes(derecha[j], izquierda[i], clave, descendente):
            resultado.append(derecha[j])
            j += 1
        else:
            resultado.append(izquierda[i])
            i += 1
    resultado.extend(izquierda[i:])
    resultado.extend(derecha[j:])
    return resultado


# ---------------------------------------------------------------------------
# Ordenamiento externo
# ---------------------------------------------------------------------------
def _escribir_bloque(registros: Iterable[dict], carpeta: str) -> str:
    """Guarda registros en un archivo temporal, un JSON por línea."""
    descriptor, ruta = tempfile.mkstemp(suffix=".jsonl", dir=carpeta)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        for registro in registros:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return ruta


def _leer_bloque(ruta: str) -> Iterator[dict]:
    """Lee un bloque línea a línea (no carga el archivo completo en memoria)."""
    with open(ruta, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            yield json.loads(linea)


def _fusionar(rutas: list, clave: Clave, descendente: bool) -> Iterator[dict]:
    """
    Mezcla k archivos ordenados. La cola con prioridad contiene solo el primer
    registro disponible de cada archivo; siempre se entrega el que corresponde.
    El desempate por número de archivo conserva la estabilidad.
    """
    lectores = [_leer_bloque(ruta) for ruta in rutas]
    cabezas: ColaPrioridad = ColaPrioridad(
        prioridad=lambda t: (_Invertible(clave(t[0]), descendente), t[1])
    )
    for indice, lector in enumerate(lectores):
        primero = next(lector, None)
        if primero is not None:
            cabezas.insertar((primero, indice))

    while not cabezas.esta_vacia():
        registro, indice = cabezas.extraer()
        yield registro
        siguiente = next(lectores[indice], None)
        if siguiente is not None:
            cabezas.insertar((siguiente, indice))


class _Invertible:
    """Envuelve una clave para poder invertir su orden (sirve también para texto)."""

    __slots__ = ("valor", "invertir")

    def __init__(self, valor, invertir: bool):
        self.valor = valor
        self.invertir = invertir

    def __lt__(self, otro):
        return otro.valor < self.valor if self.invertir else self.valor < otro.valor

    def __gt__(self, otro):
        return otro.__lt__(self)

    def __eq__(self, otro):
        return self.valor == otro.valor


def ordenamiento_externo(
    datos: Iterable[dict],
    clave: Clave,
    descendente: bool = False,
    tam_bloque: int = 50,
    max_archivos: int = 8,
) -> list:
    """
    External merge sort en dos fases:
      1. Se leen `tam_bloque` registros, se ordenan en memoria y se escriben
         como un bloque ordenado en disco.
      2. Los bloques se fusionan en grupos de hasta `max_archivos` (para no
         abrir demasiados archivos a la vez), repitiendo hasta terminar.
    Los registros deben poder convertirse a JSON. La carpeta temporal se borra
    automáticamente al finalizar, incluso si ocurre un error.
    Se retorna una lista porque la interfaz necesita mostrar la tabla completa.
    """
    if tam_bloque < 1 or max_archivos < 2:
        raise ValueError("tam_bloque debe ser >= 1 y max_archivos >= 2")

    with tempfile.TemporaryDirectory(prefix="orden_externo_") as carpeta:
        # Fase 1: generación de bloques ordenados.
        rutas, bloque = [], []
        for registro in datos:
            bloque.append(registro)
            if len(bloque) == tam_bloque:
                rutas.append(_escribir_bloque(mergesort(bloque, clave, descendente), carpeta))
                bloque = []
        if bloque:
            rutas.append(_escribir_bloque(mergesort(bloque, clave, descendente), carpeta))

        # Fase 2: pasadas de mezcla hasta que quepan en una sola fusión final.
        while len(rutas) > max_archivos:
            nuevas = []
            for i in range(0, len(rutas), max_archivos):
                grupo = rutas[i : i + max_archivos]
                nuevas.append(_escribir_bloque(_fusionar(grupo, clave, descendente), carpeta))
            rutas = nuevas

        return list(_fusionar(rutas, clave, descendente))


# Catálogo de métodos disponibles para el selector de la interfaz.
METODOS = {
    "QuickSort (interno)": quicksort,
    "MergeSort (interno)": mergesort,
    "Mezcla externa en disco (externo)": ordenamiento_externo,
}
