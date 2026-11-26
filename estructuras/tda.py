"""
===============================================================================
 Archivo      : estructuras/tda.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : heapq NO se usa (el montículo se implementa a mano); solo typing.
 Descripción  : Tipos de Datos Abstractos (TDA) implementados desde cero:
                Lista enlazada, Pila, Cola, Cola con prioridad, Árbol binario
                de búsqueda y Grafo.

 ¿Dónde se usa cada uno en el sistema?
   - ListaEnlazada : ingredientes que componen una Receta (modelos/entidades.py)
   - Pila          : quicksort iterativo y "últimas preparaciones" en cocina
   - Cola          : órdenes pendientes de cocina (se atiende la más antigua)
   - ColaPrioridad : ranking de pérdidas y fusión del ordenamiento externo
   - ArbolBinario  : filtro de órdenes por rango de pérdida (administrador)
   - Grafo         : relación menú <-> ingrediente para el análisis logístico
===============================================================================
"""

from typing import Any, Callable, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class _Nodo(Generic[T]):
    """Nodo simple: guarda un dato y la referencia al siguiente nodo."""

    __slots__ = ("dato", "siguiente")

    def __init__(self, dato: T):
        self.dato = dato
        self.siguiente: Optional["_Nodo[T]"] = None


class ListaEnlazada(Generic[T]):
    """Lista simplemente enlazada con puntero a la cola (inserción O(1))."""

    def __init__(self, elementos: Iterable[T] = ()):
        self._cabeza: Optional[_Nodo[T]] = None
        self._final: Optional[_Nodo[T]] = None
        self._largo = 0
        for elemento in elementos:
            self.agregar(elemento)

    def agregar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        if self._cabeza is None:  # lista vacía: el nodo es cabeza y final
            self._cabeza = self._final = nodo
        else:
            self._final.siguiente = nodo
            self._final = nodo
        self._largo += 1

    def __iter__(self) -> Iterator[T]:
        actual = self._cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    def __len__(self) -> int:
        return self._largo


class Pila(Generic[T]):
    """Pila LIFO (el último en entrar es el primero en salir), enlazada."""

    def __init__(self):
        self._tope: Optional[_Nodo[T]] = None
        self._largo = 0

    def apilar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        nodo.siguiente = self._tope
        self._tope = nodo
        self._largo += 1

    def desapilar(self) -> T:
        if self._tope is None:
            raise IndexError("La pila está vacía")
        dato = self._tope.dato
        self._tope = self._tope.siguiente
        self._largo -= 1
        return dato

    def esta_vacia(self) -> bool:
        return self._tope is None

    def __iter__(self) -> Iterator[T]:
        """Recorre desde el tope hacia la base SIN desapilar (solo consulta)."""
        actual = self._tope
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    def __len__(self) -> int:
        return self._largo


class Cola(Generic[T]):
    """Cola FIFO (el primero en entrar es el primero en salir), enlazada."""

    def __init__(self):
        self._frente: Optional[_Nodo[T]] = None
        self._final: Optional[_Nodo[T]] = None
        self._largo = 0

    def encolar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        if self._final is None:
            self._frente = self._final = nodo
        else:
            self._final.siguiente = nodo
            self._final = nodo
        self._largo += 1

    def desencolar(self) -> T:
        if self._frente is None:
            raise IndexError("La cola está vacía")
        dato = self._frente.dato
        self._frente = self._frente.siguiente
        if self._frente is None:  # se retiró el último elemento
            self._final = None
        self._largo -= 1
        return dato

    def esta_vacia(self) -> bool:
        return self._frente is None

    def __len__(self) -> int:
        return self._largo


class ColaPrioridad(Generic[T]):
    """
    Cola con prioridad sobre un montículo binario (heap) almacenado en un arreglo.

    `prioridad` entrega el valor de comparación de cada elemento. Si
    `mayor_primero` es True sale primero el de mayor prioridad (max-heap);
    en caso contrario, el menor (min-heap). Ante empate sale primero el que
    ingresó antes (contador de llegada), lo que mantiene el orden estable.
    Insertar y extraer cuestan O(log n).
    """

    def __init__(self, prioridad: Callable[[T], Any], mayor_primero: bool = False):
        self._prioridad = prioridad
        self._mayor_primero = mayor_primero
        self._heap: list = []  # tuplas (prioridad, orden_llegada, elemento)
        self._contador = 0

    def _va_antes(self, a: tuple, b: tuple) -> bool:
        if a[0] != b[0]:
            return a[0] > b[0] if self._mayor_primero else a[0] < b[0]
        return a[1] < b[1]

    def insertar(self, elemento: T) -> None:
        self._heap.append((self._prioridad(elemento), self._contador, elemento))
        self._contador += 1
        # "Flotar": el nuevo elemento sube mientras le gane a su padre.
        i = len(self._heap) - 1
        while i > 0:
            padre = (i - 1) // 2
            if not self._va_antes(self._heap[i], self._heap[padre]):
                break
            self._heap[i], self._heap[padre] = self._heap[padre], self._heap[i]
            i = padre

    def extraer(self) -> T:
        if not self._heap:
            raise IndexError("La cola con prioridad está vacía")
        raiz = self._heap[0]
        ultimo = self._heap.pop()
        if self._heap:
            self._heap[0] = ultimo
            self._hundir(0)
        return raiz[2]

    def _hundir(self, i: int) -> None:
        """El elemento en i baja intercambiándose con su hijo más prioritario."""
        n = len(self._heap)
        while True:
            elegido = i
            for hijo in (2 * i + 1, 2 * i + 2):
                if hijo < n and self._va_antes(self._heap[hijo], self._heap[elegido]):
                    elegido = hijo
            if elegido == i:
                return
            self._heap[i], self._heap[elegido] = self._heap[elegido], self._heap[i]
            i = elegido

    def esta_vacia(self) -> bool:
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)


class _NodoArbol:
    """Nodo del árbol: una clave y todos los valores que comparten esa clave."""

    __slots__ = ("clave", "valores", "izq", "der")

    def __init__(self, clave, valor):
        self.clave = clave
        self.valores = [valor]
        self.izq: Optional["_NodoArbol"] = None
        self.der: Optional["_NodoArbol"] = None


class ArbolBinarioBusqueda:
    """
    Árbol binario de búsqueda: menores a la izquierda, mayores a la derecha.

    Las operaciones son iterativas para no depender del límite de recursión de
    Python si los datos llegan ya ordenados (árbol degenerado).
    """

    def __init__(self):
        self.raiz: Optional[_NodoArbol] = None

    def insertar(self, clave, valor) -> None:
        if self.raiz is None:
            self.raiz = _NodoArbol(clave, valor)
            return
        actual = self.raiz
        while True:
            if clave == actual.clave:  # clave repetida: se agrupa en el nodo
                actual.valores.append(valor)
                return
            lado = "izq" if clave < actual.clave else "der"
            hijo = getattr(actual, lado)
            if hijo is None:
                setattr(actual, lado, _NodoArbol(clave, valor))
                return
            actual = hijo

    def rango(self, minimo, maximo) -> list:
        """
        Valores con minimo <= clave <= maximo, en orden ascendente (in-orden).
        Se "podan" las ramas que no pueden contener claves del rango.
        """
        resultado: list = []
        pendientes: Pila = Pila()
        actual = self.raiz
        while actual is not None or not pendientes.esta_vacia():
            while actual is not None:
                pendientes.apilar(actual)
                # Solo vale la pena bajar a la izquierda si quedan claves >= mínimo.
                actual = actual.izq if actual.clave > minimo else None
            nodo = pendientes.desapilar()
            if minimo <= nodo.clave <= maximo:
                resultado.extend(nodo.valores)
            actual = nodo.der if nodo.clave < maximo else None
        return resultado


class Grafo:
    """Grafo no dirigido representado con listas de adyacencia."""

    def __init__(self):
        self._adyacencia: dict = {}

    def agregar_vertice(self, vertice) -> None:
        self._adyacencia.setdefault(vertice, [])

    def agregar_arista(self, a, b) -> None:
        self.agregar_vertice(a)
        self.agregar_vertice(b)
        if b not in self._adyacencia[a]:
            self._adyacencia[a].append(b)
            self._adyacencia[b].append(a)

    def vecinos(self, vertice) -> list:
        return list(self._adyacencia.get(vertice, []))

    def grado(self, vertice) -> int:
        return len(self._adyacencia.get(vertice, []))

    def vertices(self) -> list:
        return list(self._adyacencia)

    def a_distancia(self, origen, distancia: int) -> list:
        """
        Recorrido en anchura (BFS) usando la Cola propia: retorna los vértices
        cuya distancia mínima al origen es exactamente `distancia`.
        """
        if origen not in self._adyacencia:
            return []
        niveles = {origen: 0}
        cola: Cola = Cola()
        cola.encolar(origen)
        while not cola.esta_vacia():
            actual = cola.desencolar()
            for vecino in self._adyacencia[actual]:
                if vecino not in niveles:
                    niveles[vecino] = niveles[actual] + 1
                    cola.encolar(vecino)
        return [v for v, nivel in niveles.items() if nivel == distancia]
