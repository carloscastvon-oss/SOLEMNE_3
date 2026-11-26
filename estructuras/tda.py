# --- IMPORTACIONES Y TIPOS ---
from typing import Any, Callable, Generic, Iterable, Iterator, Optional, TypeVar  # anotaciones de tipos

T = TypeVar("T")  # tipo genérico: admite cualquier clase de dato


# --- NODO DE LAS ESTRUCTURAS ENLAZADAS ---
class _Nodo(Generic[T]):

    __slots__ = ("dato", "siguiente")  # atributos fijos para ahorrar memoria

    # --- Crear nodo ---
    def __init__(self, dato: T):
        self.dato = dato                             # valor almacenado
        self.siguiente: Optional["_Nodo[T]"] = None  # enlace al nodo siguiente


# --- TDA LISTA ENLAZADA ---
class ListaEnlazada(Generic[T]):

    # --- Crear lista ---
    def __init__(self, elementos: Iterable[T] = ()):
        self._cabeza: Optional[_Nodo[T]] = None  # primer nodo
        self._final: Optional[_Nodo[T]] = None   # último nodo
        self._largo = 0                          # cantidad de elementos
        for elemento in elementos:               # carga los elementos iniciales
            self.agregar(elemento)

    # --- Agregar al final ---
    def agregar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        if self._cabeza is None:  # lista vacía: el nodo es el primero y el último
            self._cabeza = self._final = nodo
        else:  # se enlaza después del último nodo
            self._final.siguiente = nodo
            self._final = nodo
        self._largo += 1

    # --- Recorrer la lista ---
    def __iter__(self) -> Iterator[T]:
        actual = self._cabeza
        while actual is not None:  # avanza nodo por nodo
            yield actual.dato      # entrega un elemento a la vez
            actual = actual.siguiente

    # --- Obtener el largo ---
    def __len__(self) -> int:
        return self._largo


# --- TDA PILA (el último en entrar es el primero en salir) ---
class Pila(Generic[T]):

    # --- Crear pila ---
    def __init__(self):
        self._tope: Optional[_Nodo[T]] = None  # elemento superior
        self._largo = 0

    # --- Apilar ---
    def apilar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        nodo.siguiente = self._tope  # el nuevo nodo apunta al tope anterior
        self._tope = nodo            # y pasa a ser el tope
        self._largo += 1

    # --- Desapilar ---
    def desapilar(self) -> T:
        if self._tope is None:  # no se puede retirar de una pila vacía
            raise IndexError("La pila está vacía")
        dato = self._tope.dato
        self._tope = self._tope.siguiente  # el siguiente nodo queda como tope
        self._largo -= 1
        return dato

    # --- Consultar si está vacía ---
    def esta_vacia(self) -> bool:
        return self._tope is None

    # --- Recorrer sin desapilar ---
    def __iter__(self) -> Iterator[T]:
        actual = self._tope
        while actual is not None:  # avanza desde el tope hacia la base
            yield actual.dato
            actual = actual.siguiente

    # --- Obtener el largo ---
    def __len__(self) -> int:
        return self._largo


# --- TDA COLA (el primero en entrar es el primero en salir) ---
class Cola(Generic[T]):

    # --- Crear cola ---
    def __init__(self):
        self._frente: Optional[_Nodo[T]] = None  # extremo de salida
        self._final: Optional[_Nodo[T]] = None   # extremo de entrada
        self._largo = 0

    # --- Encolar ---
    def encolar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        if self._final is None:  # cola vacía: el nodo es frente y final
            self._frente = self._final = nodo
        else:  # se agrega después del final
            self._final.siguiente = nodo
            self._final = nodo
        self._largo += 1

    # --- Desencolar ---
    def desencolar(self) -> T:
        if self._frente is None:  # no se puede retirar de una cola vacía
            raise IndexError("La cola está vacía")
        dato = self._frente.dato
        self._frente = self._frente.siguiente  # avanza el frente
        if self._frente is None:               # si salió el último, no queda final
            self._final = None
        self._largo -= 1
        return dato

    # --- Consultar si está vacía ---
    def esta_vacia(self) -> bool:
        return self._frente is None

    # --- Obtener el largo ---
    def __len__(self) -> int:
        return self._largo


# --- TDA COLA CON PRIORIDAD (montículo binario) ---
class ColaPrioridad(Generic[T]):

    # --- Crear cola con prioridad ---
    def __init__(self, prioridad: Callable[[T], Any], mayor_primero: bool = False):
        self._prioridad = prioridad          # función que calcula la prioridad
        self._mayor_primero = mayor_primero  # True: sale primero el valor mayor
        self._heap: list = []                # montículo: (prioridad, llegada, elemento)
        self._contador = 0                   # orden de llegada para desempatar

    # --- Comparar dos entradas ---
    def _va_antes(self, a: tuple, b: tuple) -> bool:
        if a[0] != b[0]:  # prioridades distintas: decide la prioridad
            return a[0] > b[0] if self._mayor_primero else a[0] < b[0]
        return a[1] < b[1]  # empate: sale el que llegó primero

    # --- Insertar ---
    def insertar(self, elemento: T) -> None:
        self._heap.append((self._prioridad(elemento), self._contador, elemento))  # se agrega al final del arreglo
        self._contador += 1
        i = len(self._heap) - 1
        while i > 0:              # el elemento sube mientras supere a su padre
            padre = (i - 1) // 2  # posición del nodo padre
            if not self._va_antes(self._heap[i], self._heap[padre]):
                break
            self._heap[i], self._heap[padre] = self._heap[padre], self._heap[i]
            i = padre

    # --- Extraer el prioritario ---
    def extraer(self) -> T:
        if not self._heap:
            raise IndexError("La cola con prioridad está vacía")
        raiz = self._heap[0]       # la raíz tiene la mayor prioridad
        ultimo = self._heap.pop()  # retira el último elemento
        if self._heap:
            self._heap[0] = ultimo  # lo coloca en la raíz
            self._hundir(0)         # y lo reubica hacia abajo
        return raiz[2]

    # --- Reordenar hacia abajo ---
    def _hundir(self, i: int) -> None:
        n = len(self._heap)
        while True:
            elegido = i
            for hijo in (2 * i + 1, 2 * i + 2):  # revisa el hijo izquierdo y el derecho
                if hijo < n and self._va_antes(self._heap[hijo], self._heap[elegido]):
                    elegido = hijo
            if elegido == i:  # ya está en su posición
                return
            self._heap[i], self._heap[elegido] = self._heap[elegido], self._heap[i]
            i = elegido

    # --- Consultar si está vacía ---
    def esta_vacia(self) -> bool:
        return not self._heap

    # --- Obtener el largo ---
    def __len__(self) -> int:
        return len(self._heap)


# --- NODO DEL ÁRBOL BINARIO ---
class _NodoArbol:

    __slots__ = ("clave", "valores", "izq", "der")

    # --- Crear nodo ---
    def __init__(self, clave, valor):
        self.clave = clave                       # valor usado para ordenar
        self.valores = [valor]                   # elementos que comparten la clave
        self.izq: Optional["_NodoArbol"] = None  # hijo con claves menores
        self.der: Optional["_NodoArbol"] = None  # hijo con claves mayores


# --- TDA ÁRBOL BINARIO DE BÚSQUEDA ---
class ArbolBinarioBusqueda:

    # --- Crear árbol ---
    def __init__(self):
        self.raiz: Optional[_NodoArbol] = None

    # --- Insertar ---
    def insertar(self, clave, valor) -> None:
        if self.raiz is None:  # árbol vacío: el nodo es la raíz
            self.raiz = _NodoArbol(clave, valor)
            return
        actual = self.raiz
        while True:                    # desciende hasta encontrar su posición
            if clave == actual.clave:  # clave repetida: se agrupa en el mismo nodo
                actual.valores.append(valor)
                return
            lado = "izq" if clave < actual.clave else "der"  # menor a la izquierda, mayor a la derecha
            hijo = getattr(actual, lado)
            if hijo is None:  # espacio libre: se crea el nodo
                setattr(actual, lado, _NodoArbol(clave, valor))
                return
            actual = hijo

    # --- Buscar un rango de claves ---
    def rango(self, minimo, maximo) -> list:
        resultado: list = []
        pendientes: Pila = Pila()  # pila que reemplaza a la recursión
        actual = self.raiz
        while actual is not None or not pendientes.esta_vacia():  # recorrido en orden: izquierda, nodo, derecha
            while actual is not None:
                pendientes.apilar(actual)
                actual = actual.izq if actual.clave > minimo else None  # baja a la izquierda solo si puede haber claves válidas
            nodo = pendientes.desapilar()
            if minimo <= nodo.clave <= maximo:  # guarda los valores dentro del rango
                resultado.extend(nodo.valores)
            actual = nodo.der if nodo.clave < maximo else None  # sigue a la derecha solo si puede haber claves válidas
        return resultado


# --- TDA GRAFO NO DIRIGIDO ---
class Grafo:

    # --- Crear grafo ---
    def __init__(self):
        self._adyacencia: dict = {}  # cada vértice con su lista de vecinos

    # --- Agregar vértice ---
    def agregar_vertice(self, vertice) -> None:
        self._adyacencia.setdefault(vertice, [])  # solo se crea si no existe

    # --- Conectar dos vértices ---
    def agregar_arista(self, a, b) -> None:
        self.agregar_vertice(a)
        self.agregar_vertice(b)
        if b not in self._adyacencia[a]:  # evita conexiones repetidas
            self._adyacencia[a].append(b)
            self._adyacencia[b].append(a)  # la conexión va en ambos sentidos

    # --- Obtener vecinos ---
    def vecinos(self, vertice) -> list:
        return list(self._adyacencia.get(vertice, []))

    # --- Contar conexiones ---
    def grado(self, vertice) -> int:
        return len(self._adyacencia.get(vertice, []))

    # --- Listar vértices ---
    def vertices(self) -> list:
        return list(self._adyacencia)

    # --- Buscar por distancia (recorrido en anchura) ---
    def a_distancia(self, origen, distancia: int) -> list:
        if origen not in self._adyacencia:  # el vértice no existe
            return []
        niveles = {origen: 0}  # distancia de cada vértice visitado
        cola: Cola = Cola()    # vértices pendientes de visitar
        cola.encolar(origen)
        while not cola.esta_vacia():
            actual = cola.desencolar()
            for vecino in self._adyacencia[actual]:  # revisa las conexiones del vértice actual
                if vecino not in niveles:            # solo vértices no visitados
                    niveles[vecino] = niveles[actual] + 1
                    cola.encolar(vecino)
        return [v for v, nivel in niveles.items() if nivel == distancia]  # vértices a la distancia pedida
