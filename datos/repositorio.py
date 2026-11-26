from datetime import datetime, timezone

from modelos.entidades import Ingrediente, ItemReceta, Receta, ResultadoCalculo

# Esta es la única capa que consulta la base de datos.

# La API de Supabase entrega como máximo 1000 filas por consulta.
TAM_PAGINA = 1000

# Columnas que puede pedir COCINA: ninguna es financiera ni de merma. Así los
# datos sensibles ni siquiera salen de la base de datos hacia esa vista.
COLUMNAS_COCINA = (
    "id, comensales, estado, creado_en, recetas(nombre), "
    "orden_detalle(id, ingrediente_id, raciones, unidades_completas)"
)

COLUMNAS_ADMIN = (
    "id, comensales, estado, creado_en, costo_total, costo_por_plato, "
    "venta_por_plato, venta_total, perdida_merma, recetas(nombre), perfiles(nombre), "
    "orden_detalle(id, raciones, cantidad_requerida, unidades_completas, "
    "costo_unitario, costo_total, "
    "ingredientes(nombre, unidad_compra, unidad_compra_plural), "
    "mermas(cantidad_merma, perdida))"
)


# Agrupa todas las lecturas y escrituras en Supabase.
class Repositorio:
    # Recibe el cliente de Supabase (facilita probar con uno simulado).
    def __init__(self, cliente):
        self._db = cliente

    # ------------------------------------------------------------- Perfiles
    # Perfiles junto con las vistas que cada uno puede abrir.
    def obtener_perfiles(self) -> list[dict]:
        filas = (
            self._db.table("perfiles")
            .select("codigo, nombre, descripcion, perfil_permisos(vista)")
            .order("id")
            .execute()
            .data
        )
        return [
            {
                "codigo": f["codigo"],
                "nombre": f["nombre"],
                "descripcion": f["descripcion"],
                "vistas": [p["vista"] for p in f["perfil_permisos"]],
            }
            for f in filas
        ]

    # ------------------------------------------------------------- Catálogo
    # Cada fila se convierte en un objeto Ingrediente.
    def obtener_ingredientes(self) -> list[Ingrediente]:
        filas = self._db.table("ingredientes").select("*").order("id").execute().data
        return [Ingrediente(**fila) for fila in filas]

    def obtener_recetas(self, ingredientes: list[Ingrediente]) -> list[Receta]:
        """Reconstruye los objetos Receta (con su lista enlazada de ítems)."""
        por_id = {i.id: i for i in ingredientes}
        filas = (
            self._db.table("recetas")
            .select(
                "id, nombre, comensales_base, "
                "receta_ingredientes(ingrediente_id, raciones_base, texto_receta, posicion)"
            )
            .order("id")
            .order("posicion", foreign_table="receta_ingredientes")
            .execute()
            .data
        )
        recetas = []
        for fila in filas:
            receta = Receta(fila["id"], fila["nombre"], fila["comensales_base"])
            for linea in fila["receta_ingredientes"]:
                receta.agregar_item(
                    ItemReceta(
                        por_id[linea["ingrediente_id"]],
                        linea["raciones_base"],
                        linea["texto_receta"],
                    )
                )
            recetas.append(receta)
        return recetas

    # ------------------------------------------------------------- Órdenes
    def registrar_orden(self, resultado: ResultadoCalculo, perfil: str) -> int:
        """Guarda la orden completa mediante la función transaccional (RPC)."""
        orden = {
            "receta_id": resultado.receta.id,
            "perfil": perfil,
            "comensales": resultado.comensales,
            # Decimal -> str: JSON no admite Decimal y str no pierde precisión.
            "costo_total": str(resultado.costo_total),
            "costo_por_plato": str(resultado.costo_por_plato),
            "venta_por_plato": str(resultado.venta_por_plato),
            "venta_total": str(resultado.venta_total),
            "perdida_merma": str(resultado.perdida_merma),
            "margen": str(resultado.margen),
        }
        detalle = [
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
        respuesta = self._db.rpc(
            "registrar_orden", {"p_orden": orden, "p_detalle": detalle}
        ).execute()
        return respuesta.data

    def ordenes_cocina_pendientes(self) -> list[dict]:
        """Pendientes de la más antigua a la más nueva (orden de llegada)."""
        return self._paginar(
            lambda: self._db.table("ordenes_servicio")
            .select(COLUMNAS_COCINA)
            .eq("estado", "pendiente")
            .order("creado_en")
            .order("id")
            .order("id", foreign_table="orden_detalle")
        )

    def marcar_preparada(self, orden_id: int) -> bool:
        """Retorna False si otra sesión ya la había marcado."""
        filas = (
            self._db.table("ordenes_servicio")
            .update(
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
        return bool(filas)

    def ordenes_completas(self) -> list[dict]:
        """Historial con toda la información (solo para el administrador)."""
        return self._paginar(
            lambda: self._db.table("ordenes_servicio")
            .select(COLUMNAS_ADMIN)
            .order("id")
            .order("id", foreign_table="orden_detalle")
        )

    @staticmethod
    def _paginar(crear_consulta) -> list[dict]:
        """Pide páginas de 1000 filas hasta traer todos los registros."""
        filas, inicio = [], 0
        while True:
            pagina = crear_consulta().range(inicio, inicio + TAM_PAGINA - 1).execute().data
            filas.extend(pagina)
            if len(pagina) < TAM_PAGINA:
                return filas
            inicio += TAM_PAGINA
