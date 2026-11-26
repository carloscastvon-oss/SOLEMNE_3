# Sistema de Inventario de Alimentos y Gestión de Mermas

| | |
|---|---|
| **Alumno** | CAPITÁN CARLOS CASTILLO VON-BISCHOFFSHAUSEN |
| **Curso** | I CRIM Sistemas de Armas, Programación Avanzada |
| **Institución** | Academia Politécnica Militar |
| **Profesor** | Dr. Carlos Santibáñez Rodríguez |
| **Evaluación** | N°3, 26-11-2026 |
| **Tecnologías** | Python, Streamlit, Supabase (PostgreSQL) |

## 1. Puesta en marcha

Probado con Python 3.14. Los comandos son para PowerShell.

1. **Base de datos (una sola vez):** en Supabase, abra *SQL Editor* → *New query*,
   pegue todo el contenido de `sql/supabase_setup.sql` y presione *Run*.
   El resultado debe mostrar `2 perfiles, 10 ingredientes, 10 recetas, 40 líneas`.
2. **Dependencias:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install -r requirements.txt
   ```
3. **Credenciales:** copie `.streamlit/secrets.toml.example` como
   `.streamlit/secrets.toml` y complete `url` y `key` (secret key).
   También se aceptan las variables de entorno `SUPABASE_URL` y `SUPABASE_KEY`.
4. **Ejecutar:**
   ```powershell
   .\.venv\Scripts\python -m streamlit run app.py
   ```
5. **Pruebas** (no necesitan conexión):
   ```powershell
   .\.venv\Scripts\python -m unittest discover -s tests -t .
   ```

## 2. Perfiles

| Perfil | Puede ver |
|---|---|
| **Cocina** | Nueva preparación, órdenes pendientes y consulta de insumos. Sin costos, precios ni mermas. |
| **Administrador** | Todo lo anterior, más resumen ejecutivo, historial, análisis de mermas y catálogo con costos. |

La protección de la información en cocina tiene tres niveles:

1. Solo se registran las páginas autorizadas en la tabla `perfil_permisos`.
   Escribir la dirección de otra página no la abre.
2. Cocina recibe un objeto `OrdenPreparacion`, que no tiene atributos financieros.
3. La consulta de órdenes de cocina no pide columnas de costo ni de merma.

**Alcance:** el sistema no gestiona contraseñas; la persona se identifica
eligiendo su perfil. Esto separa las vistas, pero no impide que alguien
elija "Administrador". Un sistema real requeriría autenticación.

## 3. Estructura

```
app.py                    Punto de entrada, identificación y navegación
estructuras/tda.py        Lista, pila, cola, cola con prioridad, árbol binario, grafo
algoritmos/               Ordenamiento interno y externo; búsqueda secuencial
modelos/entidades.py      Clases: Ingrediente, Receta, DetalleInsumo, etc.
logica/                   Motor de cálculo, acceso, servicio de cocina, reportes
datos/                    Conexión segura y consultas a Supabase
ui/                       Vistas de cocina y administrador
sql/supabase_setup.sql    Tablas, seguridad, función transaccional y datos iniciales
tests/                    Pruebas automáticas
```

## 4. Base de datos

```
perfiles ─< perfil_permisos
perfiles ─< ordenes_servicio >─ recetas ─< receta_ingredientes >─ ingredientes
             ordenes_servicio ─< orden_detalle >─ ingredientes
                                 orden_detalle ─ mermas   (1 a 1)
```

- `registrar_orden()` guarda la orden, el detalle y las mermas en una sola transacción.
- `orden_detalle` conserva el costo unitario del momento: un cambio de precio no altera el historial.
- RLS está activado sin políticas: solo la secret key, usada en el servidor, accede a los datos.

## 5. Cálculo

Para cada ingrediente, con N comensales:

| Valor | Fórmula |
|---|---|
| Raciones | `raciones_base × N / 4` (huevos y tutos: se redondea hacia arriba) |
| Cantidad requerida | `raciones / rendimiento` |
| Unidades completas | `math.ceil(cantidad requerida)` |
| Merma física | `unidades completas − cantidad requerida` |
| Pérdida por merma | `merma física × costo unitario` |
| Costo por plato | `suma de (unidades completas × costo unitario) / N` |
| Valor de venta | `costo por plato × 1,25` |

**Ejemplo:** Tallarines con Salsa de Tomate, 4 comensales.

| Ingrediente | Requerido | Se usa | Costo | Pérdida |
|---|---|---|---|---|
| Fideos | 1 paquete | 1 | $1.200 | $0 |
| Tomate | 0,667 kg | 1 | $1.500 | $500 |
| Cebolla | 1 | 1 | $500 | $0 |
| Aceite | 0,4 L | 1 | $1.000 | $600 |

Costo total $4.200; costo por plato $1.050; **venta por plato $1.312,5**; pérdida $1.100.

### Criterios de cálculo

- **Rendimiento:** cada ingrediente define cuántas personas cubre una unidad de compra.
  Las cantidades de la receta ("6 unidades" de papa) se muestran como referencia,
  porque el sistema no registra cuántas papas o tomates tiene un kilo.
  Por ejemplo, la cebolla rinde 4 personas y la lechuga, 10.
- **Huevo:** como el empaque trae 12 unidades contables, se usa la cantidad de cada
  receta (6 en la tortilla y 4 en las demás, por cada 4 comensales).
- **Productos indivisibles:** nada abierto se guarda; la merma se calcula por orden.
- **Ganancia del 25 %:** es un recargo sobre el costo.
- La pérdida por merma ya forma parte del costo; no se suma dos veces.
- El panel considera todas las órdenes registradas, pendientes y preparadas.

## 6. Estructuras y algoritmos aplicados

| Estructura o algoritmo | Dónde se usa |
|---|---|
| Lista enlazada | Ingredientes de cada `Receta` |
| Pila (LIFO) | Órdenes de la sesión en cocina; QuickSort iterativo; recorrido del árbol |
| Cola (FIFO) | Órdenes pendientes de cocina; recorrido en anchura del grafo |
| Cola con prioridad | Ranking de pérdidas por menú e ingrediente; mezcla externa |
| Árbol binario de búsqueda | Filtro del historial por rango de pérdida |
| Grafo | Relación menú-ingrediente en el análisis de mermas |
| Ordenamiento interno | QuickSort y MergeSort (historial, gráficos y comparador) |
| Ordenamiento externo | Mezcla de bloques ordenados en archivos temporales (historial) |
| Búsqueda secuencial | Consulta de insumos, validación de permisos y filtro por menú |

Los algoritmos de ordenamiento y las estructuras están implementados a mano.
`sorted()` solo se usa en las pruebas, como referencia para comparar resultados.