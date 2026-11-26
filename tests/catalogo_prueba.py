# --- IMPORTACIONES ---
import re                 # búsqueda de patrones de texto
from pathlib import Path  # rutas de archivos

from modelos.entidades import Ingrediente, ItemReceta, Receta  # clases del sistema

SQL = (Path(__file__).parent.parent / "sql" / "supabase_setup.sql").read_text(encoding="utf-8")  # contenido del archivo SQL


# --- CATÁLOGO DE PRUEBA LEÍDO DESDE EL SQL ---
def cargar_catalogo():
    patron_ingrediente = re.compile(  # formato de cada ingrediente
        r"\('([^']+)',\s*(\d+),\s*(\d+),\s*'([^']+)',\s*'([^']+)',\s*(true|false),\s*'([^']+)'\)"
    )
    ingredientes = [  # crea los objetos Ingrediente
        Ingrediente(n, m[0], int(m[1]), int(m[2]), m[3], m[4], m[5] == "true", m[6])
        for n, m in enumerate(patron_ingrediente.findall(SQL), start=1)
    ]
    por_nombre = {i.nombre: i for i in ingredientes}

    patron_linea = re.compile(r"\('([^']+)',\s*'([^']+)',\s*(\d+),\s*(\d+),\s*'([^']+)'\)")  # formato de cada línea de receta
    recetas: dict = {}
    for receta, ingrediente, _, raciones, texto in patron_linea.findall(SQL):  # arma las recetas con sus ingredientes
        if receta not in recetas:
            recetas[receta] = Receta(len(recetas) + 1, receta)
        recetas[receta].agregar_item(ItemReceta(por_nombre[ingrediente], int(raciones), texto))
    return ingredientes, list(recetas.values())
