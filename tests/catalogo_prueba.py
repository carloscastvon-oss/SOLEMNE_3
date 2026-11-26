"""
 Lee los datos iniciales directamente desde sql/supabase_setup.sql, de modo que
 las pruebas verifican el mismo catálogo que se carga en Supabase.
 Alumno: [NOMBRE DEL ALUMNO] - I CRIM Sistemas de Armas - 26-11-2026
 Librerías: re, pathlib (biblioteca estándar)
"""

import re
from pathlib import Path

from modelos.entidades import Ingrediente, ItemReceta, Receta

SQL = (Path(__file__).parent.parent / "sql" / "supabase_setup.sql").read_text(encoding="utf-8")


def cargar_catalogo():
    patron_ingrediente = re.compile(
        r"\('([^']+)',\s*(\d+),\s*(\d+),\s*'([^']+)',\s*'([^']+)',\s*(true|false),\s*'([^']+)'\)"
    )
    ingredientes = [
        Ingrediente(n, m[0], int(m[1]), int(m[2]), m[3], m[4], m[5] == "true", m[6])
        for n, m in enumerate(patron_ingrediente.findall(SQL), start=1)
    ]
    por_nombre = {i.nombre: i for i in ingredientes}

    patron_linea = re.compile(r"\('([^']+)',\s*'([^']+)',\s*(\d+),\s*(\d+),\s*'([^']+)'\)")
    recetas: dict = {}
    for receta, ingrediente, _, raciones, texto in patron_linea.findall(SQL):
        if receta not in recetas:
            recetas[receta] = Receta(len(recetas) + 1, receta)
        recetas[receta].agregar_item(ItemReceta(por_nombre[ingrediente], int(raciones), texto))
    return ingredientes, list(recetas.values())
