# --- IMPORTACIONES ---
import math                                 # redondeo hacia arriba
from decimal import ROUND_HALF_UP, Decimal  # montos exactos
from fractions import Fraction              # fracciones sin error de decimales

from modelos.entidades import DetalleInsumo, ItemReceta, Receta, ResultadoCalculo  # clases del sistema

# --- PARÁMETROS DEL CÁLCULO ---
MARGEN_GANANCIA = Fraction(25, 100)  # ganancia del 25 % sobre el costo
MAX_COMENSALES = 10_000              # límite para evitar errores de digitación


# --- ERROR DE DATOS DE ENTRADA ---
class ErrorValidacion(ValueError):
    pass


# --- VALIDACIÓN DE COMENSALES ---
def validar_comensales(valor) -> int:
    if valor is None:  # campo vacío
        raise ErrorValidacion("Debe ingresar la cantidad de comensales.")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):  # debe ser un número
        raise ErrorValidacion("La cantidad de comensales debe ser un número.")
    if isinstance(valor, float) and (not math.isfinite(valor) or not valor.is_integer()):  # debe ser un número entero y finito
        raise ErrorValidacion("La cantidad de comensales debe ser un número entero.")
    if valor <= 0:  # no se aceptan ceros ni negativos
        raise ErrorValidacion("La cantidad de comensales debe ser mayor que cero.")
    if valor > MAX_COMENSALES:  # no puede superar el límite
        raise ErrorValidacion(f"El máximo por servicio es de {MAX_COMENSALES} comensales.")
    return int(valor)  # valor validado


# --- CONVERSIÓN A PESOS ---
def a_pesos(valor: Fraction) -> Decimal:
    exacto = Decimal(valor.numerator) / Decimal(valor.denominator)   # convierte la fracción a decimal
    return exacto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # redondea a 2 decimales


# --- CÁLCULO DE UN INGREDIENTE ---
def calcular_insumo(item: ItemReceta, comensales: int, comensales_base: int) -> DetalleInsumo:
    ingrediente = item.ingrediente
    raciones = Fraction(item.raciones_base * comensales, comensales_base)  # escala la receta a los comensales
    if ingrediente.pieza_entera:  # las piezas no se pueden dividir
        raciones = Fraction(math.ceil(raciones))

    requerida = raciones / ingrediente.rendimiento  # consumo exacto en unidades de compra
    unidades = math.ceil(requerida)                 # solo se usan unidades completas
    merma = unidades - requerida                    # sobrante que no se puede guardar

    return DetalleInsumo(
        ingrediente=ingrediente,
        raciones=raciones,
        cantidad_requerida=requerida,
        unidades_completas=unidades,
        cantidad_merma=merma,
        costo_total=a_pesos(Fraction(unidades * ingrediente.costo_unitario)),  # costo de las unidades completas
        perdida_merma=a_pesos(merma * ingrediente.costo_unitario),             # pérdida en dinero por el sobrante
    )


# --- CÁLCULO COMPLETO DEL SERVICIO ---
def calcular_orden(receta: Receta, comensales) -> ResultadoCalculo:
    comensales = validar_comensales(comensales)  # valida antes de calcular
    if len(receta.items) == 0:                   # la receta debe tener ingredientes
        raise ErrorValidacion(f"La receta '{receta.nombre}' no tiene ingredientes.")

    detalles = tuple(  # calcula cada ingrediente
        calcular_insumo(item, comensales, receta.comensales_base) for item in receta.items
    )
    costo_total = sum((d.costo_total for d in detalles), Decimal("0"))  # suma el costo de los insumos
    perdida = sum((d.perdida_merma for d in detalles), Decimal("0"))    # suma las pérdidas por merma

    costo = Fraction(costo_total)       # costo exacto para dividir
    factor_venta = 1 + MARGEN_GANANCIA  # costo más la ganancia

    return ResultadoCalculo(
        receta=receta,
        comensales=comensales,
        detalles=detalles,
        costo_total=costo_total,
        perdida_merma=perdida,
        costo_por_plato=a_pesos(costo / comensales),                 # costo dividido por comensal
        venta_por_plato=a_pesos(costo * factor_venta / comensales),  # precio de venta por comensal
        venta_total=a_pesos(costo * factor_venta),                   # precio de venta del servicio
        margen=a_pesos(MARGEN_GANANCIA),
    )
