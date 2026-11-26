from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction

from estructuras.tda import ListaEnlazada


@dataclass(frozen=True)
class Ingrediente:
    """Insumo del catálogo. Se compra solo en unidades completas."""

    id: int
    nombre: str
    costo_unitario: int          # pesos por unidad de compra
    rendimiento: int             # personas (raciones) que cubre una unidad
    unidad_compra: str           # "kg", "litro", "paquete", ...
    unidad_compra_plural: str
    # Piezas contables (huevo, tuto): las raciones se redondean a enteros porque
    # no se puede preparar medio huevo ni medio tuto.
    pieza_entera: bool = False
    nombre_racion: str = "porciones"


@dataclass(frozen=True)
class ItemReceta:
    """Línea de una receta, expresada para la base de 4 comensales."""

    ingrediente: Ingrediente
    raciones_base: int           # raciones consumidas por 4 comensales
    texto_receta: str            # cantidad tal como aparece en el recetario


# Menú del recetario; es modificable porque sus ítems se agregan al cargarlo.
@dataclass
class Receta:
    id: int
    nombre: str
    comensales_base: int = 4
    # TDA lista enlazada: los ítems se recorren en el orden del recetario.
    items: ListaEnlazada = field(default_factory=ListaEnlazada)

    # Añade un ingrediente al final de la lista enlazada.
    def agregar_item(self, item: ItemReceta) -> None:
        self.items.agregar(item)


@dataclass(frozen=True)
class DetalleInsumo:
    """Resultado del cálculo para un ingrediente dentro de una orden."""

    ingrediente: Ingrediente
    raciones: Fraction           # raciones que se preparan
    cantidad_requerida: Fraction # consumo exacto en unidades de compra
    unidades_completas: int      # unidades que se abren (redondeo hacia arriba)
    cantidad_merma: Fraction     # unidades_completas - cantidad_requerida
    costo_total: Decimal         # unidades_completas * costo unitario
    perdida_merma: Decimal       # cantidad_merma * costo unitario


@dataclass(frozen=True)
class ResultadoCalculo:
    """Cálculo completo de un servicio (información de nivel administrador)."""

    receta: Receta
    comensales: int
    detalles: tuple
    costo_total: Decimal
    perdida_merma: Decimal
    costo_por_plato: Decimal
    venta_por_plato: Decimal
    venta_total: Decimal
    margen: Decimal


@dataclass(frozen=True)
class LineaPreparacion:
    """Lo ÚNICO que ve cocina de cada ingrediente: sin costos ni merma."""

    ingrediente: str
    a_preparar: str              # p. ej. "8 huevos" o "6 porciones"
    a_retirar: str               # p. ej. "2 kg"


@dataclass(frozen=True)
class OrdenPreparacion:
    """
    Orden que se entrega a la vista de cocina. Al no tener atributos
    financieros, es imposible que esa pantalla los muestre por error.
    """

    numero: int
    menu: str
    comensales: int
    lineas: tuple
    estado: str = "pendiente"
    fecha: str = ""
