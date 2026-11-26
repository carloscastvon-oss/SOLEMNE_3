# --- IMPORTACIONES ---
import json  # formato de los registros en disco
import os  # manejo de archivos
import tempfile                                       # archivos y carpetas temporales
from typing import Any, Callable, Iterable, Iterator  # anotaciones de tipos

from estructuras.tda import ColaPrioridad, Pila  # estructuras propias de apoyo

Clave = Callable[[Any], Any]  # función que indica por qué dato ordenar


# --- COMPARACIÓN DE DOS ELEMENTOS ---
def _va_antes(a, b, clave: Clave, descendente: bool) -> bool:
    return clave(a) > clave(b) if descendente else clave(a) < clave(b)  # el sentido depende de si es descendente


# --- ORDENAMIENTO INTERNO: QUICKSORT ---
def quicksort(datos: Iterable, clave: Clave, descendente: bool = False) -> list:
    arreglo = list(datos)                     # copia para no modificar el original
    pendientes: Pila = Pila()                 # tramos por ordenar (reemplaza la recursión)
    pendientes.apilar((0, len(arreglo) - 1))  # se parte con el arreglo completo

    while not pendientes.esta_vacia():
        inicio, fin = pendientes.desapilar()
        if inicio >= fin:  # tramo de 0 o 1 elemento: ya está ordenado
            continue
        pivote = arreglo[(inicio + fin) // 2]  # elemento central como referencia
        i, j = inicio, fin
        while i <= j:  # separa los elementos según el pivote
            while _va_antes(arreglo[i], pivote, clave, descendente):  # avanza desde la izquierda
                i += 1
            while _va_antes(pivote, arreglo[j], clave, descendente):  # retrocede desde la derecha
                j -= 1
            if i <= j:
                arreglo[i], arreglo[j] = arreglo[j], arreglo[i]  # intercambia los que están en el lado equivocado
                i += 1
                j -= 1
        pendientes.apilar((inicio, j))  # tramo izquierdo pendiente
        pendientes.apilar((i, fin))     # tramo derecho pendiente
    return arreglo


# --- ORDENAMIENTO INTERNO: MERGESORT ---
def mergesort(datos: Iterable, clave: Clave, descendente: bool = False) -> list:
    arreglo = list(datos)
    if len(arreglo) <= 1:  # caso base de la recursión
        return arreglo
    medio = len(arreglo) // 2                                   # punto de división
    izquierda = mergesort(arreglo[:medio], clave, descendente)  # ordena la primera mitad
    derecha = mergesort(arreglo[medio:], clave, descendente)    # ordena la segunda mitad

    resultado, i, j = [], 0, 0
    while i < len(izquierda) and j < len(derecha):                   # mezcla las dos mitades ordenadas
        if _va_antes(derecha[j], izquierda[i], clave, descendente):  # en un empate se toma primero la izquierda
            resultado.append(derecha[j])
            j += 1
        else:
            resultado.append(izquierda[i])
            i += 1
    resultado.extend(izquierda[i:])  # agrega los elementos restantes
    resultado.extend(derecha[j:])
    return resultado


# --- ESCRITURA DE UN BLOQUE EN DISCO ---
def _escribir_bloque(registros: Iterable[dict], carpeta: str) -> str:
    descriptor, ruta = tempfile.mkstemp(suffix=".jsonl", dir=carpeta)  # crea un archivo temporal
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        for registro in registros:  # un registro en formato JSON por línea
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return ruta


# --- LECTURA DE UN BLOQUE DESDE DISCO ---
def _leer_bloque(ruta: str) -> Iterator[dict]:
    with open(ruta, "r", encoding="utf-8") as archivo:
        for linea in archivo:  # lee línea por línea sin cargar todo en memoria
            yield json.loads(linea)


# --- MEZCLA DE BLOQUES ORDENADOS ---
def _fusionar(rutas: list, clave: Clave, descendente: bool) -> Iterator[dict]:
    lectores = [_leer_bloque(ruta) for ruta in rutas]  # un lector por archivo
    cabezas: ColaPrioridad = ColaPrioridad(            # contiene el siguiente registro de cada archivo
        prioridad=lambda t: (_Invertible(clave(t[0]), descendente), t[1])
    )
    for indice, lector in enumerate(lectores):  # carga el primer registro de cada archivo
        primero = next(lector, None)
        if primero is not None:
            cabezas.insertar((primero, indice))

    while not cabezas.esta_vacia():  # entrega siempre el que corresponde
        registro, indice = cabezas.extraer()
        yield registro
        siguiente = next(lectores[indice], None)  # repone desde el mismo archivo
        if siguiente is not None:
            cabezas.insertar((siguiente, indice))


# --- CLAVE CON ORDEN INVERTIBLE ---
class _Invertible:

    __slots__ = ("valor", "invertir")  # atributos fijos para ahorrar memoria

    # --- Crear la clave ---
    def __init__(self, valor, invertir: bool):
        self.valor = valor
        self.invertir = invertir

    # --- Comparar "menor que" ---
    def __lt__(self, otro):
        return otro.valor < self.valor if self.invertir else self.valor < otro.valor  # invierte la comparación si es descendente

    # --- Comparar "mayor que" ---
    def __gt__(self, otro):
        return otro.__lt__(self)

    # --- Comparar igualdad ---
    def __eq__(self, otro):
        return self.valor == otro.valor


# --- ORDENAMIENTO EXTERNO: MEZCLA EN DISCO ---
def ordenamiento_externo(
    datos: Iterable[dict],
    clave: Clave,
    descendente: bool = False,
    tam_bloque: int = 50,   # registros que se ordenan en memoria a la vez
    max_archivos: int = 8,  # archivos que se mezclan a la vez
) -> list:
    if tam_bloque < 1 or max_archivos < 2:  # valida los parámetros
        raise ValueError("tam_bloque debe ser >= 1 y max_archivos >= 2")

    with tempfile.TemporaryDirectory(prefix="orden_externo_") as carpeta:  # la carpeta temporal se borra al terminar
        rutas, bloque = [], []  # fase 1: crear bloques ordenados
        for registro in datos:
            bloque.append(registro)
            if len(bloque) == tam_bloque:  # bloque lleno: se ordena y se guarda
                rutas.append(_escribir_bloque(mergesort(bloque, clave, descendente), carpeta))
                bloque = []
        if bloque:  # guarda el último bloque incompleto
            rutas.append(_escribir_bloque(mergesort(bloque, clave, descendente), carpeta))

        while len(rutas) > max_archivos:  # fase 2: mezclar por grupos
            nuevas = []
            for i in range(0, len(rutas), max_archivos):
                grupo = rutas[i : i + max_archivos]
                nuevas.append(_escribir_bloque(_fusionar(grupo, clave, descendente), carpeta))
            rutas = nuevas

        return list(_fusionar(rutas, clave, descendente))  # mezcla final


# --- MÉTODOS DISPONIBLES EN LA INTERFAZ ---
METODOS = {
    "QuickSort (interno)": quicksort,
    "MergeSort (interno)": mergesort,
    "Mezcla externa en disco (externo)": ordenamiento_externo,
}
