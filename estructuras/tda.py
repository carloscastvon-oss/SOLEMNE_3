from typing import Any, Callable, Generic, Iterable, Iterator, Optional, TypeVar

# Tipo genérico: cada estructura puede guardar cualquier clase de dato.
T = TypeVar("T")


# TDA implementados desde cero y dónde se usan:
#   ListaEnlazada : ingredientes de cada Receta
#   Pila          : órdenes de la sesión en cocina, QuickSort y recorrido del árbol
#   Cola          : órdenes pendientes de cocina y recorrido del grafo
#   ColaPrioridad : ranking de pérdidas y mezcla del ordenamiento externo
#   ArbolBinario  : filtro de órdenes por rango de pérdida
#   Grafo         : relación menú-ingrediente


# Pieza básica de las estructuras enlazadas.
class _Nodo(Generic[T]):
    """Nodo simple: guarda un dato y la referencia al siguiente nodo."""

    __slots__ = ("dato", "siguiente")

    # El nodo se crea suelto, sin sucesor.
    def __init__(self, dato: T):
        self.dato = dato
        self.siguiente: Optional["_Nodo[T]"] = None


# --- TDA Lista: mantiene el orden de inserción ---
class ListaEnlazada(Generic[T]):
    """Lista simplemente enlazada con puntero a la cola (inserción O(1))."""

    # Crea la lista vacía y carga los elementos iniciales, si se entregan.
    def __init__(self, elementos: Iterable[T] = ()):
        self._cabeza: Optional[_Nodo[T]] = None
        self._final: Optional[_Nodo[T]] = None
        self._largo = 0
        for elemento in elementos:
            self.agregar(elemento)

    # Inserta al final sin recorrer la lista.
    def agregar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        if self._cabeza is None:  # lista vacía: el nodo es cabeza y final
            self._cabeza = self._final = nodo
        else:
            self._final.siguiente = nodo
            self._final = nodo
        self._largo += 1

    # Permite recorrer la lista con un ciclo for.
    def __iter__(self) -> Iterator[T]:
        actual = self._cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    # Cantidad de elementos, disponible con len().
    def __len__(self) -> int:
        return self._largo


# --- TDA Pila ---
class Pila(Generic[T]):
    """Pila LIFO (el último en entrar es el primero en salir), enlazada."""

    # Pila vacía: sin tope.
    def __init__(self):
        self._tope: Optional[_Nodo[T]] = None
        self._largo = 0

    # El nuevo nodo apunta al tope anterior y pasa a ser el tope.
    def apilar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        nodo.siguiente = self._tope
        self._tope = nodo
        self._largo += 1

    # Retira y entrega el elemento del tope.
    def desapilar(self) -> T:
        if self._tope is None:
            raise IndexError("La pila está vacía")
        dato = self._tope.dato
        self._tope = self._tope.siguiente
        self._largo -= 1
        return dato

    # Indica si no quedan elementos.
    def esta_vacia(self) -> bool:
        return self._tope is None

    def __iter__(self) -> Iterator[T]:
        """Recorre desde el tope hacia la base SIN desapilar (solo consulta)."""
        actual = self._tope
        while actual is not None:
            yield actual.dato
            actual = actual.siguiente

    # Cantidad de elementos apilados.
    def __len__(self) -> int:
        return self._largo


# --- TDA Cola: dos punteros, frente (salida) y final (entrada) ---
class Cola(Generic[T]):
    """Cola FIFO (el primero en entrar es el primero en salir), enlazada."""

    # Cola vacía: sin frente ni final.
    def __init__(self):
        self._frente: Optional[_Nodo[T]] = None
        self._final: Optional[_Nodo[T]] = None
        self._largo = 0

    # Los elementos ingresan por el final.
    def encolar(self, dato: T) -> None:
        nodo = _Nodo(dato)
        if self._final is None:
            self._frente = self._final = nodo
        else:
            self._final.siguiente = nodo
            self._final = nodo
        self._largo += 1

    # Los elementos salen por el frente.
    def desencolar(self) -> T:
        if self._frente is None:
            raise IndexError("La cola está vacía")
        dato = self._frente.dato
        self._frente = self._frente.siguiente
        if self._frente is None:  # se retiró el último elemento
            self._final = None
        self._largo -= 1
        return dato

    # Indica si no quedan elementos en espera.
    def esta_vacia(self) -> bool:
        return self._frente is None

    # Cantidad de elementos en espera.
    def __len__(self) -> int:
        return self._largo


# --- TDA Cola con prioridad ---
class ColaPrioridad(Generic[T]):
    """
    Cola con prioridad sobre un montículo binario (heap) almacenado en un arreglo.

    `prioridad` entrega el valor de comparación de cada elemento. Si
    `mayor_primero` es True sale primero el de mayor prioridad (max-heap);
    en caso contrario, el menor (min-heap). Ante empate sale primero el que
    ingresó antes (contador de llegada), lo que mantiene el orden estable.
    Insertar y extraer cuestan O(log n).
    """

    # Recibe el criterio de prioridad y si sale primero el mayor o el menor.
    def __init__(self, prioridad: Callable[[T], Any], mayor_primero: bool = False):
        self._prioridad = prioridad
        self._mayor_primero = mayor_primero
        self._heap: list = []  # tuplas (prioridad, orden_llegada, elemento)
        self._contador = 0

    # Decide cuál de dos entradas del montículo debe salir primero.
    def _va_antes(self, a: tuple, b: tuple) -> bool:
        if a[0] != b[0]:
            return a[0] > b[0] if self._mayor_primero else a[0] < b[0]
        return a[1] < b[1]

    # Agrega al final del arreglo y lo reubica según su prioridad.
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

    # La raíz es la prioritaria; el último elemento ocupa su lugar y se hunde.
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

    # Indica si el montículo no tiene elementos.
    def esta_vacia(self) -> bool:
        return not self._heap

    # Cantidad de elementos en el montículo.
    def __len__(self) -> int:
        return len(self._heap)


# --- TDA Árbol binario de búsqueda ---
class _NodoArbol:
    """Nodo del árbol: una clave y todos los valores que comparten esa clave."""

    __slots__ = ("clave", "valores", "izq", "der")

    # Un nodo nuevo parte sin hijos.
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

    # Árbol vacío: sin raíz.
    def __init__(self):
        self.raiz: Optional[_NodoArbol] = None

    # Baja desde la raíz hasta hallar un espacio libre o la misma clave.
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


# --- TDA Grafo ---
class Grafo:
    """Grafo no dirigido representado con listas de adyacencia."""

    # Diccionario: cada vértice apunta a la lista de sus vecinos.
    def __init__(self):
        self._adyacencia: dict = {}

    # Agrega el vértice solo si todavía no existe.
    def agregar_vertice(self, vertice) -> None:
        self._adyacencia.setdefault(vertice, [])

    # La arista se registra en ambos sentidos: el grafo no es dirigido.
    def agregar_arista(self, a, b) -> None:
        self.agregar_vertice(a)
        self.agregar_vertice(b)
        if b not in self._adyacencia[a]:
            self._adyacencia[a].append(b)
            self._adyacencia[b].append(a)

    # Copia de los vértices conectados directamente.
    def vecinos(self, vertice) -> list:
        return list(self._adyacencia.get(vertice, []))

    # Grado: cantidad de conexiones de un vértice.
    def grado(self, vertice) -> int:
        return len(self._adyacencia.get(vertice, []))

    # Todos los vértices del grafo.
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
