import unicodedata
from typing import Callable, Iterable, Optional


# Se usa búsqueda secuencial, O(n): los catálogos son pequeños, no requieren
# estar ordenados y permite coincidencias parciales de texto.


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
    # Se normaliza lo buscado y cada nombre antes de comparar.
    buscado = normalizar(texto)
    return busqueda_secuencial_todos(elementos, lambda e: buscado in normalizar(nombre(e)))
