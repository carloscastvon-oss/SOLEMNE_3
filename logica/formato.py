from datetime import datetime
from zoneinfo import ZoneInfo

# Supabase guarda en UTC; en pantalla se muestra la hora de Chile.
ZONA_CHILE = ZoneInfo("America/Santiago")


def numero(valor, decimales: int = 2) -> str:
    """1234.5 -> '1.234,5' (miles con punto, sin ceros sobrantes)."""
    texto = f"{float(valor):,.{decimales}f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto


# Formato de moneda usado en todo el panel.
def pesos(valor) -> str:
    return f"$ {numero(valor)}"


def cantidad(valor, singular: str, plural: str) -> str:
    """Une número y unidad respetando singular/plural ('1 kg', '2 paquetes')."""
    return f"{numero(valor)} {singular if float(valor) == 1 else plural}"


def fecha_local(iso: str) -> str:
    """Convierte la marca de tiempo UTC de Supabase a hora de Chile."""
    momento = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return momento.astimezone(ZONA_CHILE).strftime("%d-%m-%Y %H:%M")
