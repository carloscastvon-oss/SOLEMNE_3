import math
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from modelos.entidades import DetalleInsumo, ItemReceta, Receta, ResultadoCalculo

# Se usa Fraction y no float: un error mínimo de decimales podría hacer que
# math.ceil compre una unidad de más.
MARGEN_GANANCIA = Fraction(25, 100)  # 25% sobre el costo
MAX_COMENSALES = 10_000              # tope para detectar errores de digitación


class ErrorValidacion(ValueError):
    """Dato de entrada no válido; su mensaje se puede mostrar al usuario."""


def validar_comensales(valor) -> int:
    """Rechaza nulos, no enteros, negativos, cero y cantidades absurdas."""
    if valor is None:
        raise ErrorValidacion("Debe ingresar la cantidad de comensales.")
    # bool es subclase de int en Python, por eso se excluye explícitamente.
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorValidacion("La cantidad de comensales debe ser un número.")
    # (valor != int(valor)) fallaría con NaN/infinito, así que se revisa antes.
    if isinstance(valor, float) and (not math.isfinite(valor) or not valor.is_integer()):
        raise ErrorValidacion("La cantidad de comensales debe ser un número entero.")
    if valor <= 0:
        raise ErrorValidacion("La cantidad de comensales debe ser mayor que cero.")
    if valor > MAX_COMENSALES:
        raise ErrorValidacion(f"El máximo por servicio es de {MAX_COMENSALES} comensales.")
    return int(valor)


def a_pesos(valor: Fraction) -> Decimal:
    """Convierte una fracción exacta a pesos con 2 decimales (mitad hacia arriba)."""
    exacto = Decimal(valor.numerator) / Decimal(valor.denominator)
    return exacto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Fórmulas por ingrediente, con N comensales:
#   raciones           = raciones_base * N / 4  (pieza entera: ceil)
#   cantidad_requerida = raciones / rendimiento      (unidades de compra)
#   unidades_completas = math.ceil(cantidad_requerida)
#   merma_fisica       = unidades_completas - cantidad_requerida
#   perdida_merma      = merma_fisica * costo_unitario
# El rendimiento sale de la columna "Utilidad" (cebolla: 4 personas, según el
# encargo). El huevo tiene cantidad propia por receta (empaque de 12 contables).
# Lo abierto no se guarda: la merma se calcula por orden y no se reutiliza.
def calcular_insumo(item: ItemReceta, comensales: int, comensales_base: int) -> DetalleInsumo:
    """Aplica las fórmulas de requerimiento, indivisibilidad y merma."""
    ingrediente = item.ingrediente
    # Se escala la receta base a la cantidad real de comensales.
    raciones = Fraction(item.raciones_base * comensales, comensales_base)
    if ingrediente.pieza_entera:
        raciones = Fraction(math.ceil(raciones))

    requerida = raciones / ingrediente.rendimiento
    unidades = math.ceil(requerida)       # indivisibilidad: siempre hacia arriba
    merma = unidades - requerida          # parte abierta que se desecha

    return DetalleInsumo(
        ingrediente=ingrediente,
        raciones=raciones,
        cantidad_requerida=requerida,
        unidades_completas=unidades,
        cantidad_merma=merma,
        costo_total=a_pesos(Fraction(unidades * ingrediente.costo_unitario)),
        perdida_merma=a_pesos(merma * ingrediente.costo_unitario),
    )


def calcular_orden(receta: Receta, comensales) -> ResultadoCalculo:
    """Calcula el servicio completo para una receta y N comensales."""
    comensales = validar_comensales(comensales)
    if len(receta.items) == 0:
        raise ErrorValidacion(f"La receta '{receta.nombre}' no tiene ingredientes.")

    # Se calcula cada ingrediente por separado.
    detalles = tuple(
        calcular_insumo(item, comensales, receta.comensales_base) for item in receta.items
    )
    # Se cuesta lo comprado completo, aunque no se consuma todo.
    costo_total = sum((d.costo_total for d in detalles), Decimal("0"))
    # Se suman las pérdidas ya redondeadas para que el total cuadre con el detalle.
    perdida = sum((d.perdida_merma for d in detalles), Decimal("0"))

    costo = Fraction(costo_total)
    factor_venta = 1 + MARGEN_GANANCIA

    return ResultadoCalculo(
        receta=receta,
        comensales=comensales,
        detalles=detalles,
        costo_total=costo_total,
        perdida_merma=perdida,
        # El margen se aplica sobre el valor exacto y se redondea una sola vez.
        costo_por_plato=a_pesos(costo / comensales),
        venta_por_plato=a_pesos(costo * factor_venta / comensales),
        venta_total=a_pesos(costo * factor_venta),
        margen=a_pesos(MARGEN_GANANCIA),
    )
