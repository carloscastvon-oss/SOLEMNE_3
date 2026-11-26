# --- IMPORTACIONES ---
from datetime import datetime  # manejo de fechas
from zoneinfo import ZoneInfo  # zonas horarias

ZONA_CHILE = ZoneInfo("America/Santiago")  # zona horaria para mostrar las fechas


# --- FORMATO DE NÚMEROS ---
def numero(valor, decimales: int = 2) -> str:
    texto = f"{float(valor):,.{decimales}f}"                             # separa miles y fija los decimales
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")  # cambia al formato chileno: 1.234,5
    if "," in texto:  # quita los ceros sobrantes
        texto = texto.rstrip("0").rstrip(",")
    return texto


# --- FORMATO DE MONEDA ---
def pesos(valor) -> str:
    return f"$ {numero(valor)}"


# --- FORMATO DE CANTIDAD CON UNIDAD ---
def cantidad(valor, singular: str, plural: str) -> str:
    return f"{numero(valor)} {singular if float(valor) == 1 else plural}"  # usa singular o plural


# --- FORMATO DE FECHA LOCAL ---
def fecha_local(iso: str) -> str:
    momento = datetime.fromisoformat(iso.replace("Z", "+00:00"))      # convierte el texto de la base de datos a fecha
    return momento.astimezone(ZONA_CHILE).strftime("%d-%m-%Y %H:%M")  # hora de Chile: día-mes-año hora:minutos
