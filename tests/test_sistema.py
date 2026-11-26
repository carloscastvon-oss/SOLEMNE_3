import math
import random
import unittest
from dataclasses import asdict
from decimal import Decimal

from algoritmos.busqueda import buscar_por_nombre
from algoritmos.ordenamiento import mergesort, ordenamiento_externo, quicksort
from estructuras.tda import ArbolBinarioBusqueda, Cola, ColaPrioridad, Pila
from logica import reportes
from logica.acceso import tiene_acceso
from logica.motor_calculo import ErrorValidacion, calcular_orden, validar_comensales
from logica.servicio_cocina import solicitar_servicio
from tests.catalogo_prueba import cargar_catalogo

INGREDIENTES, RECETAS = cargar_catalogo()


def receta(nombre):
    return next(r for r in RECETAS if r.nombre == nombre)


class TestCatalogo(unittest.TestCase):
    def test_totalidad_de_registros(self):
        self.assertEqual(len(INGREDIENTES), 10)
        self.assertEqual(len(RECETAS), 10)
        self.assertEqual(sum(len(r.items) for r in RECETAS), 40)

    def test_indicaciones_del_encargo(self):
        cebolla = next(i for i in INGREDIENTES if i.nombre == "Cebolla")
        self.assertEqual(cebolla.rendimiento, 4)
        nombres = [it.ingrediente.nombre for it in receta("Carne Molida con Papas").items]
        self.assertNotIn("Arroz", nombres)


class TestMotor(unittest.TestCase):
    def test_tallarines_4_comensales(self):
        r = calcular_orden(receta("Tallarines con Salsa de Tomate"), 4)
        self.assertEqual(r.costo_total, Decimal("4200.00"))
        self.assertEqual(r.perdida_merma, Decimal("1100.00"))  # 500 tomate + 600 aceite
        self.assertEqual(r.costo_por_plato, Decimal("1050.00"))
        self.assertEqual(r.venta_por_plato, Decimal("1312.50"))
        self.assertEqual(r.venta_total, Decimal("5250.00"))

    def test_tortilla_5_comensales_redondea_huevos(self):
        r = calcular_orden(receta("Tortilla de Papas y Cebolla"), 5)
        huevo = next(d for d in r.detalles if d.ingrediente.nombre == "Huevo")
        self.assertEqual(huevo.raciones, 8)  # ceil(7,5)
        self.assertEqual(huevo.unidades_completas, 1)
        self.assertEqual(huevo.perdida_merma, Decimal("1500.00"))  # sobran 4 de 12
        self.assertEqual(r.costo_total, Decimal("8500.00"))
        self.assertEqual(r.perdida_merma, Decimal("3125.00"))
        self.assertEqual(r.venta_por_plato, Decimal("2125.00"))

    def test_consumo_exacto_no_compra_de_mas(self):
        r = calcular_orden(receta("Arroz con Pollo y Ensalada"), 20)
        por_nombre = {d.ingrediente.nombre: d for d in r.detalles}
        self.assertEqual(por_nombre["Arroz"].unidades_completas, 2)
        self.assertEqual(por_nombre["Arroz"].cantidad_merma, 0)

    def test_invariantes_en_todos_los_menus(self):
        for r in RECETAS:
            for n in range(1, 61):
                resultado = calcular_orden(r, n)
                for d in resultado.detalles:
                    self.assertEqual(d.unidades_completas, math.ceil(d.cantidad_requerida))
                    self.assertTrue(0 <= d.cantidad_merma < 1)

    def test_validaciones(self):
        for valor in (None, 0, -3, 2.5, "4", True, float("nan"), float("inf"), 10_001):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                validar_comensales(valor)
        self.assertEqual(validar_comensales(4.0), 4)


class TestPrivacidadCocina(unittest.TestCase):
    def test_la_orden_de_cocina_no_tiene_datos_financieros(self):
        class RepositorioFalso:
            def registrar_orden(self, resultado, perfil):
                return 7

        orden = solicitar_servicio(RepositorioFalso(), RECETAS[0], 6, "cocina")
        texto = str(asdict(orden)).lower()
        for prohibido in ("costo", "venta", "merma", "perdida", "sobrante", "$"):
            self.assertNotIn(prohibido, texto)

    def test_permisos(self):
        perfiles = [{"codigo": "cocina", "vistas": ["nueva_preparacion"]}]
        self.assertTrue(tiene_acceso(perfiles, "cocina", "nueva_preparacion"))
        self.assertFalse(tiene_acceso(perfiles, "cocina", "resumen"))
        self.assertFalse(tiene_acceso(perfiles, None, "nueva_preparacion"))


class TestEstructurasYAlgoritmos(unittest.TestCase):
    def test_pila_y_cola(self):
        pila, cola = Pila(), Cola()
        for x in (1, 2, 3):
            pila.apilar(x)
            cola.encolar(x)
        self.assertEqual([pila.desapilar() for _ in range(3)], [3, 2, 1])
        self.assertEqual([cola.desencolar() for _ in range(3)], [1, 2, 3])
        with self.assertRaises(IndexError):
            cola.desencolar()

    def test_cola_prioridad_y_arbol(self):
        random.seed(1)
        datos = [random.randint(0, 50) for _ in range(500)]
        cola = ColaPrioridad(prioridad=lambda x: x, mayor_primero=True)
        arbol = ArbolBinarioBusqueda()
        for x in datos:
            cola.insertar(x)
            arbol.insertar(x, x)
        self.assertEqual([cola.extraer() for _ in datos], sorted(datos, reverse=True))
        self.assertEqual(arbol.rango(10, 20), sorted(x for x in datos if 10 <= x <= 20))

    def test_arbol_degenerado_no_desborda(self):
        arbol = ArbolBinarioBusqueda()
        for x in range(3000):
            arbol.insertar(x, x)
        self.assertEqual(len(arbol.rango(0, 3000)), 3000)

    def test_ordenamientos(self):
        random.seed(2)
        for n in (0, 1, 2, 7, 100, 731):
            datos = [{"id": i, "v": random.randint(0, 9), "t": random.choice("abcá")}
                     for i in range(n)]
            for campo in ("v", "t"):
                for desc in (False, True):
                    clave = lambda d, c=campo: d[c]
                    esperado = sorted(datos, key=clave, reverse=desc)  # referencia estable
                    self.assertEqual(mergesort(datos, clave, desc), esperado)
                    self.assertEqual(
                        ordenamiento_externo(datos, clave, desc, tam_bloque=3, max_archivos=3),
                        esperado,
                    )
                    rapido = quicksort(datos, clave, desc)
                    self.assertEqual([clave(d) for d in rapido], [clave(d) for d in esperado])
                    self.assertCountEqual([d["id"] for d in rapido], range(n))

    def test_busqueda_sin_tildes(self):
        self.assertEqual(
            [r.nombre for r in buscar_por_nombre(RECETAS, "charquican", lambda r: r.nombre)],
            ["Charquicán Simple"],
        )

    def test_grafo_y_ranking(self):
        grafo = reportes.construir_grafo(RECETAS)
        self.assertEqual(len(reportes.menus_que_usan(grafo, "Aceite")), 9)
        self.assertTrue(reportes.menus_relacionados(grafo, RECETAS[0].nombre))
        ranking = reportes.ranking_perdidas([{"perdida": 1}, {"perdida": 9}, {"perdida": 5}], 2)
        self.assertEqual([f["perdida"] for f in ranking], [9, 5])

    def test_kpis_sin_datos(self):
        self.assertEqual(reportes.calcular_kpis([])["porcentaje_merma"], 0.0)


if __name__ == "__main__":
    unittest.main()
