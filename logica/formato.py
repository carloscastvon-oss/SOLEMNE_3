"""
===============================================================================
 Archivo      : logica/formato.py
 Proyecto     : Sistema de Inventario de Alimentos y Gestión de Mermas
 Alumno       : [NOMBRE DEL ALUMNO]
 Curso        : I CRIM Sistemas de Armas - Programación Avanzada
 Institución  : Academia Politécnica Militar
 Profesor     : Dr. Carlos Santibáñez Rodríguez
 Evaluación   : N°3  -  Fecha: 26-11-2026
 Librerías    : datetime, zoneinfo (biblioteca estándar; tzdata en Windows)
 Descripción  : Funciones de presentación en formato chileno.
===============================================================================
"""

from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_CHILE = ZoneInfo("America/Santiago")


def numero(valor, decimales: int = 2) -> str:
    """1234.5 -> '1.234,5' (miles con punto, sin ceros sobrantes)."""
    texto = f"{float(valor):,.{decimales}f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto


def pesos(valor) -> str:
    return f"$ {numero(valor)}"


def cantidad(valor, singular: str, plural: str) -> str:
    """Une número y unidad respetando singular/plural ('1 kg', '2 paquetes')."""
    return f"{numero(valor)} {singular if float(valor) == 1 else plural}"


def fecha_local(iso: str) -> str:
    """Convierte la marca de tiempo UTC de Supabase a hora de Chile."""
    momento = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return momento.astimezone(ZONA_CHILE).strftime("%d-%m-%Y %H:%M")
