# --- IMPORTACIONES ---
from dataclasses import dataclass, field  # clases para almacenar datos
from decimal import Decimal               # montos exactos
from fractions import Fraction            # cantidades exactas

from estructuras.tda import ListaEnlazada  # lista enlazada propia


# --- CLASE INGREDIENTE ---
@dataclass(frozen=True)
class Ingrediente:

    id: int                           # identificador
    nombre: str                       # nombre del insumo
    costo_unitario: int               # precio por unidad de compra
    rendimiento: int                  # personas que cubre una unidad
    unidad_compra: str                # unidad en singular
    unidad_compra_plural: str         # unidad en plural
    pieza_entera: bool = False        # True si se usa por piezas completas
    nombre_racion: str = "porciones"  # nombre de la ración


# --- CLASE LÍNEA DE RECETA ---
@dataclass(frozen=True)
class ItemReceta:

    ingrediente: Ingrediente  # insumo utilizado
    raciones_base: int        # raciones para la base de comensales
    texto_receta: str         # cantidad escrita en el recetario


# --- CLASE RECETA ---
@dataclass
class Receta:
    id: int  # identificador
    nombre: str  # nombre del menú
    comensales_base: int = 4                                     # personas que considera la receta
    items: ListaEnlazada = field(default_factory=ListaEnlazada)  # ingredientes en una lista enlazada

    # --- Agregar ingrediente ---
    def agregar_item(self, item: ItemReceta) -> None:
        self.items.agregar(item)


# --- CLASE CÁLCULO POR INGREDIENTE ---
@dataclass(frozen=True)
class DetalleInsumo:

    ingrediente: Ingrediente      # insumo calculado
    raciones: Fraction            # raciones a preparar
    cantidad_requerida: Fraction  # consumo exacto en unidades de compra
    unidades_completas: int       # unidades que se deben abrir
    cantidad_merma: Fraction      # parte sobrante que se desecha
    costo_total: Decimal          # costo de las unidades completas
    perdida_merma: Decimal        # valor en dinero del sobrante


# --- CLASE CÁLCULO COMPLETO DEL SERVICIO ---
@dataclass(frozen=True)
class ResultadoCalculo:

    receta: Receta            # menú solicitado
    comensales: int           # cantidad de personas
    detalles: tuple           # cálculo de cada ingrediente
    costo_total: Decimal      # costo del servicio
    perdida_merma: Decimal    # pérdida total por merma
    costo_por_plato: Decimal  # costo por persona
    venta_por_plato: Decimal  # precio de venta por persona
    venta_total: Decimal      # precio de venta del servicio
    margen: Decimal           # porcentaje de ganancia


# --- CLASE LÍNEA PARA COCINA (sin datos financieros) ---
@dataclass(frozen=True)
class LineaPreparacion:

    ingrediente: str  # nombre del insumo
    a_preparar: str   # raciones o piezas a preparar
    a_retirar: str    # unidades completas que salen de bodega


# --- CLASE ORDEN PARA COCINA (sin datos financieros) ---
@dataclass(frozen=True)
class OrdenPreparacion:

    numero: int                # número de la orden
    menu: str                  # menú solicitado
    comensales: int            # cantidad de personas
    lineas: tuple              # ingredientes de la orden
    estado: str = "pendiente"  # pendiente o preparada
    fecha: str = ""            # fecha de la solicitud
