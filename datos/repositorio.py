# --- IMPORTACIONES ---
from datetime import datetime, timezone  # fecha y hora

from modelos.entidades import Ingrediente, ItemReceta, Receta, ResultadoCalculo  # clases del sistema


# --- CONSTANTES DE CONSULTA ---
TAM_PAGINA = 1000  # máximo de filas por consulta

COLUMNAS_COCINA = (  # columnas para cocina, sin costos ni mermas
    "id, comensales, estado, creado_en, recetas(nombre), "
    "orden_detalle(id, ingrediente_id, raciones, unidades_completas)"
)

COLUMNAS_ADMIN = (  # columnas completas para el administrador
    "id, comensales, estado, creado_en, costo_total, costo_por_plato, "
    "venta_por_plato, venta_total, perdida_merma, recetas(nombre), perfiles(nombre), "
    "orden_detalle(id, raciones, cantidad_requerida, unidades_completas, "
    "costo_unitario, costo_total, "
    "ingredientes(nombre, unidad_compra, unidad_compra_plural), "
    "mermas(cantidad_merma, perdida))"
)


# --- CLASE DE ACCESO A LA BASE DE DATOS ---
class Repositorio:
    # --- Crear repositorio ---
    def __init__(self, cliente):
        self._db = cliente  # cliente de Supabase

    # --- Leer perfiles y permisos ---
    def obtener_perfiles(self) -> list[dict]:
        filas = (  # consulta los perfiles con sus vistas
            self._db.table("perfiles")
            .select("codigo, nombre, descripcion, perfil_permisos(vista)")
            .order("id")
            .execute()
            .data
        )
        return [  # simplifica el resultado
            {
                "codigo": f["codigo"],
                "nombre": f["nombre"],
                "descripcion": f["descripcion"],
                "vistas": [p["vista"] for p in f["perfil_permisos"]],
            }
            for f in filas
        ]

    # --- Leer ingredientes ---
    def obtener_ingredientes(self) -> list[Ingrediente]:
        filas = self._db.table("ingredientes").select("*").order("id").execute().data
        return [Ingrediente(**fila) for fila in filas]  # convierte cada fila en un objeto

    # --- Leer recetas ---
    def obtener_recetas(self, ingredientes: list[Ingrediente]) -> list[Receta]:
        por_id = {i.id: i for i in ingredientes}  # ingredientes indexados por identificador
        filas = (                                 # consulta las recetas con sus líneas
            self._db.table("recetas")
            .select(
                "id, nombre, comensales_base, "
                "receta_ingredientes(ingrediente_id, raciones_base, texto_receta, posicion)"
            )
            .order("id")
            .order("posicion", foreign_table="receta_ingredientes")  # respeta el orden del recetario
            .execute()
            .data
        )
        recetas = []
        for fila in filas:  # construye cada objeto Receta
            receta = Receta(fila["id"], fila["nombre"], fila["comensales_base"])
            for linea in fila["receta_ingredientes"]:
                receta.agregar_item(  # agrega los ingredientes a la receta
                    ItemReceta(
                        por_id[linea["ingrediente_id"]],
                        linea["raciones_base"],
                        linea["texto_receta"],
                    )
                )
            recetas.append(receta)
        return recetas

    # --- Guardar una orden completa ---
    def registrar_orden(self, resultado: ResultadoCalculo, perfil: str) -> int:
        orden = {  # datos generales; los montos van como texto exacto
            "receta_id": resultado.receta.id,
            "perfil": perfil,
            "comensales": resultado.comensales,
            "costo_total": str(resultado.costo_total),
            "costo_por_plato": str(resultado.costo_por_plato),
            "venta_por_plato": str(resultado.venta_por_plato),
            "venta_total": str(resultado.venta_total),
            "perdida_merma": str(resultado.perdida_merma),
            "margen": str(resultado.margen),
        }
        detalle = [  # cálculo y merma de cada ingrediente
            {
                "ingrediente_id": d.ingrediente.id,
                "raciones": round(float(d.raciones), 4),
                "cantidad_requerida": round(float(d.cantidad_requerida), 4),
                "unidades_completas": d.unidades_completas,
                "costo_unitario": d.ingrediente.costo_unitario,
                "costo_total": str(d.costo_total),
                "cantidad_merma": round(float(d.cantidad_merma), 4),
                "perdida_merma": str(d.perdida_merma),
            }
            for d in resultado.detalles
        ]
        respuesta = self._db.rpc(  # guarda todo en una sola transacción
            "registrar_orden", {"p_orden": orden, "p_detalle": detalle}
        ).execute()
        return respuesta.data  # número de la orden creada

    # --- Leer órdenes pendientes ---
    def ordenes_cocina_pendientes(self) -> list[dict]:
        return self._paginar(
            lambda: self._db.table("ordenes_servicio")
            .select(COLUMNAS_COCINA)
            .eq("estado", "pendiente")  # solo las no preparadas
            .order("creado_en")         # de la más antigua a la más nueva
            .order("id")
            .order("id", foreign_table="orden_detalle")
        )

    # --- Marcar una orden como preparada ---
    def marcar_preparada(self, orden_id: int) -> bool:
        filas = (
            self._db.table("ordenes_servicio")
            .update(  # cambia el estado y registra la hora
                {
                    "estado": "preparada",
                    "preparado_en": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", orden_id)
            .eq("estado", "pendiente")  # evita marcarla dos veces
            .execute()
            .data
        )
        return bool(filas)  # False si ya estaba marcada

    # --- Leer el historial completo ---
    def ordenes_completas(self) -> list[dict]:
        return self._paginar(
            lambda: self._db.table("ordenes_servicio")
            .select(COLUMNAS_ADMIN)
            .order("id")
            .order("id", foreign_table="orden_detalle")
        )

    # --- Leer todas las páginas de resultados ---
    @staticmethod
    def _paginar(crear_consulta) -> list[dict]:
        filas, inicio = [], 0  # acumulador y posición inicial
        while True:
            pagina = crear_consulta().range(inicio, inicio + TAM_PAGINA - 1).execute().data  # pide el siguiente grupo de filas
            filas.extend(pagina)
            if len(pagina) < TAM_PAGINA:  # una página incompleta es la última
                return filas
            inicio += TAM_PAGINA  # avanza a la página siguiente
