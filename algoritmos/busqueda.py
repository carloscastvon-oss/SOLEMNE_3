# --- IMPORTACIONES ---
import unicodedata                               # tratamiento de tildes
from typing import Callable, Iterable, Optional  # anotaciones de tipos


# --- NORMALIZACIÓN DE TEXTO ---
def normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.strip().lower())          # pasa a minúsculas y separa las tildes
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")  # elimina las tildes


# --- BÚSQUEDA SECUENCIAL: PRIMERA COINCIDENCIA ---
def busqueda_secuencial(elementos: Iterable, condicion: Callable) -> Optional[object]:
    for elemento in elementos:  # revisa uno por uno
        if condicion(elemento):
            return elemento  # retorna el primero que cumple
    return None              # no hubo coincidencias


# --- BÚSQUEDA SECUENCIAL: TODAS LAS COINCIDENCIAS ---
def busqueda_secuencial_todos(elementos: Iterable, condicion: Callable) -> list:
    return [elemento for elemento in elementos if condicion(elemento)]  # recorre toda la colección


# --- BÚSQUEDA POR NOMBRE ---
def buscar_por_nombre(elementos: Iterable, texto: str, nombre: Callable) -> list:
    buscado = normalizar(texto)  # admite parte del nombre, con o sin tildes
    return busqueda_secuencial_todos(elementos, lambda e: buscado in normalizar(nombre(e)))
