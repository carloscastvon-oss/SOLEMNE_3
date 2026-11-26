"""
===============================================================================
 Archivo      : algoritmos/busqueda.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : unicodedata (biblioteca estándar)
 Descripción  : Búsqueda secuencial (lineal) para consultar insumos y validar
                accesos.

 ¿Por qué secuencial? Los catálogos son pequeños (10 insumos, 10 recetas, 2
 perfiles) y no requieren estar ordenados; además permite coincidencias
 parciales de texto, algo que una búsqueda binaria no resuelve. Costo O(n).
===============================================================================
"""

import unicodedata
from typing import Callable, Iterable, Optional


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para que 'carne' o 'aceíte' coincidan igual."""
    descompuesto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def busqueda_secuencial(elementos: Iterable, condicion: Callable) -> Optional[object]:
    """Recorre uno a uno y retorna el PRIMER elemento que cumple, o None."""
    for elemento in elementos:
        if condicion(elemento):
            return elemento
    return None


def busqueda_secuencial_todos(elementos: Iterable, condicion: Callable) -> list:
    """Recorre toda la colección y retorna TODAS las coincidencias."""
    return [elemento for elemento in elementos if condicion(elemento)]


def buscar_por_nombre(elementos: Iterable, texto: str, nombre: Callable) -> list:
    """Coincidencia parcial por nombre. Un texto vacío retorna todo."""
    buscado = normalizar(texto)
    return busqueda_secuencial_todos(elementos, lambda e: buscado in normalizar(nombre(e)))
