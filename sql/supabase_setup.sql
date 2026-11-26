begin;

-- -----------------------------------------------------------------------------
-- 1. PERFILES Y PERMISOS (control de acceso por rol, sin claves de usuario)
-- -----------------------------------------------------------------------------
create table if not exists public.perfiles (
    id          smallint generated always as identity primary key,
    codigo      text not null unique check (codigo in ('cocina', 'administrador')),
    nombre      text not null,
    descripcion text not null
);

-- Cada fila autoriza a un perfil a abrir una vista de la aplicación.
create table if not exists public.perfil_permisos (
    perfil_id smallint not null references public.perfiles (id) on delete cascade,
    vista     text     not null,
    primary key (perfil_id, vista)
);

-- -----------------------------------------------------------------------------
-- 2. CATÁLOGO: INGREDIENTES Y RECETAS
-- -----------------------------------------------------------------------------
create table if not exists public.ingredientes (
    id                   integer generated always as identity primary key,
    nombre               text    not null unique,
    costo_unitario       integer not null check (costo_unitario > 0),
    rendimiento          integer not null check (rendimiento > 0),  -- personas por unidad
    unidad_compra        text    not null,
    unidad_compra_plural text    not null,
    pieza_entera         boolean not null default false,
    nombre_racion        text    not null default 'porciones'
);

create table if not exists public.recetas (
    id              integer generated always as identity primary key,
    nombre          text     not null unique,
    comensales_base smallint not null default 4 check (comensales_base > 0)
);

-- Relación muchos a muchos entre recetas e ingredientes.
create table if not exists public.receta_ingredientes (
    receta_id      integer  not null references public.recetas (id) on delete cascade,
    ingrediente_id integer  not null references public.ingredientes (id) on delete restrict,
    raciones_base  integer  not null check (raciones_base > 0),
    texto_receta   text     not null,
    posicion       smallint not null,
    primary key (receta_id, ingrediente_id)
);

-- -----------------------------------------------------------------------------
-- 3. OPERACIÓN: ÓRDENES DE SERVICIO, DETALLE DE INSUMOS Y MERMAS
-- -----------------------------------------------------------------------------
create table if not exists public.ordenes_servicio (
    id              bigint generated always as identity primary key,
    receta_id       integer       not null references public.recetas (id) on delete restrict,
    perfil_id       smallint      not null references public.perfiles (id) on delete restrict,
    comensales      integer       not null check (comensales > 0),
    costo_total     numeric(14,2) not null check (costo_total >= 0),
    costo_por_plato numeric(14,2) not null check (costo_por_plato >= 0),
    venta_por_plato numeric(14,2) not null check (venta_por_plato >= 0),
    venta_total     numeric(14,2) not null check (venta_total >= 0),
    perdida_merma   numeric(14,2) not null check (perdida_merma >= 0),
    margen          numeric(5,2)  not null,
    estado          text          not null default 'pendiente'
                    check (estado in ('pendiente', 'preparada')),
    creado_en       timestamptz   not null default now(),
    preparado_en    timestamptz
);

-- Se guarda el costo unitario vigente: si cambia el precio, el historial no cambia.
create table if not exists public.orden_detalle (
    id                 bigint generated always as identity primary key,
    orden_id           bigint        not null references public.ordenes_servicio (id) on delete cascade,
    ingrediente_id     integer       not null references public.ingredientes (id) on delete restrict,
    raciones           numeric(14,4) not null check (raciones > 0),
    cantidad_requerida numeric(14,4) not null check (cantidad_requerida > 0),
    unidades_completas integer       not null check (unidades_completas > 0),
    costo_unitario     integer       not null check (costo_unitario > 0),
    costo_total        numeric(14,2) not null check (costo_total >= 0),
    unique (orden_id, ingrediente_id)
);

-- Una merma por cada línea de detalle (relación 1 a 1).
create table if not exists public.mermas (
    id               bigint generated always as identity primary key,
    orden_detalle_id bigint        not null unique
                     references public.orden_detalle (id) on delete cascade,
    cantidad_merma   numeric(14,4) not null check (cantidad_merma >= 0),
    perdida          numeric(14,2) not null check (perdida >= 0)
);

create index if not exists idx_ordenes_estado on public.ordenes_servicio (estado, creado_en);
create index if not exists idx_ordenes_receta on public.ordenes_servicio (receta_id);

-- -----------------------------------------------------------------------------
-- 4. FUNCIÓN TRANSACCIONAL
--    Guarda orden + detalle + mermas en UNA sola transacción: si algo falla no
--    queda ningún registro a medias.
-- -----------------------------------------------------------------------------
create or replace function public.registrar_orden(p_orden jsonb, p_detalle jsonb)
returns bigint
language plpgsql
set search_path = public
as $$
declare
    v_orden_id   bigint;
    v_detalle_id bigint;
    v_linea      jsonb;
begin
    if coalesce(jsonb_array_length(p_detalle), 0) = 0 then
        raise exception 'La orden no tiene detalle de insumos';
    end if;

    insert into ordenes_servicio (receta_id, perfil_id, comensales, costo_total,
        costo_por_plato, venta_por_plato, venta_total, perdida_merma, margen)
    values (
        (p_orden->>'receta_id')::integer,
        (select id from perfiles where codigo = p_orden->>'perfil'),
        (p_orden->>'comensales')::integer,
        (p_orden->>'costo_total')::numeric,
        (p_orden->>'costo_por_plato')::numeric,
        (p_orden->>'venta_por_plato')::numeric,
        (p_orden->>'venta_total')::numeric,
        (p_orden->>'perdida_merma')::numeric,
        (p_orden->>'margen')::numeric
    )
    returning id into v_orden_id;

    for v_linea in select * from jsonb_array_elements(p_detalle) loop
        insert into orden_detalle (orden_id, ingrediente_id, raciones,
            cantidad_requerida, unidades_completas, costo_unitario, costo_total)
        values (
            v_orden_id,
            (v_linea->>'ingrediente_id')::integer,
            (v_linea->>'raciones')::numeric,
            (v_linea->>'cantidad_requerida')::numeric,
            (v_linea->>'unidades_completas')::integer,
            (v_linea->>'costo_unitario')::integer,
            (v_linea->>'costo_total')::numeric
        )
        returning id into v_detalle_id;

        insert into mermas (orden_detalle_id, cantidad_merma, perdida)
        values (v_detalle_id,
                (v_linea->>'cantidad_merma')::numeric,
                (v_linea->>'perdida_merma')::numeric);
    end loop;

    return v_orden_id;
end;
$$;

-- -----------------------------------------------------------------------------
-- 5. SEGURIDAD
--    RLS activado y SIN políticas: las claves públicas (anon/publishable) no
--    pueden leer ni escribir. Solo el servidor de Streamlit, con la secret key
--    (rol service_role), tiene acceso.
-- -----------------------------------------------------------------------------
alter table public.perfiles            enable row level security;
alter table public.perfil_permisos     enable row level security;
alter table public.ingredientes        enable row level security;
alter table public.recetas             enable row level security;
alter table public.receta_ingredientes enable row level security;
alter table public.ordenes_servicio    enable row level security;
alter table public.orden_detalle       enable row level security;
alter table public.mermas              enable row level security;

grant usage on schema public to service_role;
grant select, insert, update, delete on
    public.perfiles, public.perfil_permisos, public.ingredientes, public.recetas,
    public.receta_ingredientes, public.ordenes_servicio, public.orden_detalle,
    public.mermas
to service_role;

revoke execute on function public.registrar_orden(jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.registrar_orden(jsonb, jsonb) to service_role;

-- -----------------------------------------------------------------------------
-- 6. DATOS INICIALES: PERFILES Y PERMISOS
-- -----------------------------------------------------------------------------
insert into public.perfiles (codigo, nombre, descripcion) values
    ('cocina', 'Cocina', 'Solo funciones operativas: cantidades a preparar.'),
    ('administrador', 'Administrador', 'Acceso total: operación, costos, ventas y mermas.')
on conflict (codigo) do update
    set nombre = excluded.nombre, descripcion = excluded.descripcion;

delete from public.perfil_permisos;
insert into public.perfil_permisos (perfil_id, vista)
select p.id, v.vista
from (values
    ('cocina', 'nueva_preparacion'),
    ('cocina', 'ordenes_cocina'),
    ('cocina', 'consulta_insumos'),
    ('administrador', 'resumen'),
    ('administrador', 'historial'),
    ('administrador', 'analisis_mermas'),
    ('administrador', 'catalogo'),
    ('administrador', 'nueva_preparacion'),
    ('administrador', 'ordenes_cocina'),
    ('administrador', 'consulta_insumos')
) as v (perfil, vista)
join public.perfiles p on p.codigo = v.perfil;

-- -----------------------------------------------------------------------------
-- 7. DATOS INICIALES: LOS 10 INGREDIENTES
--    rendimiento = columna "Utilidad". Cebolla: 4 personas (indicación del encargo).
-- -----------------------------------------------------------------------------
insert into public.ingredientes
    (nombre, costo_unitario, rendimiento, unidad_compra, unidad_compra_plural,
     pieza_entera, nombre_racion)
values
    ('Cebolla',       500,  4, 'cebolla',               'cebollas',                 false, 'porciones'),
    ('Arroz',        1500, 10, 'paquete',               'paquetes',                 false, 'porciones'),
    ('Tuto de pollo',1200,  1, 'tuto',                  'tutos',                    true,  'tutos'),
    ('Carne molida', 1500,  4, 'paquete',               'paquetes',                 false, 'porciones'),
    ('Papa',         1000,  4, 'kg',                    'kg',                       false, 'porciones'),
    ('Tomate',       1500,  6, 'kg',                    'kg',                       false, 'porciones'),
    ('Fideos',       1200,  4, 'paquete',               'paquetes',                 false, 'porciones'),
    ('Lechuga',      1000, 10, 'lechuga',               'lechugas',                 false, 'porciones'),
    ('Huevo',        4500, 12, 'empaque (12 huevos)',   'empaques (12 huevos c/u)', true,  'huevos'),
    ('Aceite',       1000, 10, 'litro',                 'litros',                   false, 'porciones')
on conflict (nombre) do update set
    costo_unitario       = excluded.costo_unitario,
    rendimiento          = excluded.rendimiento,
    unidad_compra        = excluded.unidad_compra,
    unidad_compra_plural = excluded.unidad_compra_plural,
    pieza_entera         = excluded.pieza_entera,
    nombre_racion        = excluded.nombre_racion;

-- -----------------------------------------------------------------------------
-- 8. DATOS INICIALES: LAS 10 RECETAS (base 4 comensales)
-- -----------------------------------------------------------------------------
insert into public.recetas (nombre) values
    ('Arroz con Pollo y Ensalada'),
    ('Carne Molida con Papas'),
    ('Tallarines con Salsa de Tomate'),
    ('Tortilla de Papas y Cebolla'),
    ('Pollo Salteado con Verduras'),
    ('Charquicán Simple'),
    ('Fideos con Huevo y Tomate'),
    ('Carne Molida con Arroz y Ensalada'),
    ('Papas Cocidas con Huevo y Lechuga'),
    ('Arroz Graneado con Huevo y Cebolla')
on conflict (nombre) do nothing;

insert into public.receta_ingredientes
    (receta_id, ingrediente_id, posicion, raciones_base, texto_receta)
select r.id, i.id, v.posicion, v.raciones, v.texto
from (values
    ('Arroz con Pollo y Ensalada', 'Tuto de pollo', 1, 4, '4 unidades'),
    ('Arroz con Pollo y Ensalada', 'Arroz',         2, 4, '4 porciones'),
    ('Arroz con Pollo y Ensalada', 'Lechuga',       3, 4, '1 unidad'),
    ('Arroz con Pollo y Ensalada', 'Aceite',        4, 4, '4 porciones'),

    ('Carne Molida con Papas', 'Carne molida', 1, 4, '4 porciones'),
    ('Carne Molida con Papas', 'Papa',         2, 4, '6 unidades'),
    ('Carne Molida con Papas', 'Cebolla',      3, 4, '1 unidad'),
    ('Carne Molida con Papas', 'Aceite',       4, 4, '4 porciones'),

    ('Tallarines con Salsa de Tomate', 'Fideos',  1, 4, '4 porciones'),
    ('Tallarines con Salsa de Tomate', 'Tomate',  2, 4, '4 unidades'),
    ('Tallarines con Salsa de Tomate', 'Cebolla', 3, 4, '1 unidad'),
    ('Tallarines con Salsa de Tomate', 'Aceite',  4, 4, '4 porciones'),

    ('Tortilla de Papas y Cebolla', 'Papa',    1, 4, '6 unidades'),
    ('Tortilla de Papas y Cebolla', 'Cebolla', 2, 4, '1 unidad'),
    ('Tortilla de Papas y Cebolla', 'Huevo',   3, 6, '6 unidades'),
    ('Tortilla de Papas y Cebolla', 'Aceite',  4, 4, '4 porciones'),

    ('Pollo Salteado con Verduras', 'Tuto de pollo', 1, 4, '4 unidades'),
    ('Pollo Salteado con Verduras', 'Tomate',        2, 4, '3 unidades'),
    ('Pollo Salteado con Verduras', 'Cebolla',       3, 4, '1 unidad'),
    ('Pollo Salteado con Verduras', 'Aceite',        4, 4, '4 porciones'),

    ('Charquicán Simple', 'Papa',    1, 4, '6 unidades'),
    ('Charquicán Simple', 'Lechuga', 2, 4, '1 unidad'),
    ('Charquicán Simple', 'Cebolla', 3, 4, '1 unidad'),
    ('Charquicán Simple', 'Aceite',  4, 4, '4 porciones'),

    ('Fideos con Huevo y Tomate', 'Fideos', 1, 4, '4 porciones'),
    ('Fideos con Huevo y Tomate', 'Huevo',  2, 4, '4 unidades'),
    ('Fideos con Huevo y Tomate', 'Tomate', 3, 4, '3 unidades'),
    ('Fideos con Huevo y Tomate', 'Aceite', 4, 4, '4 porciones'),

    ('Carne Molida con Arroz y Ensalada', 'Carne molida', 1, 4, '4 porciones'),
    ('Carne Molida con Arroz y Ensalada', 'Arroz',        2, 4, '4 porciones'),
    ('Carne Molida con Arroz y Ensalada', 'Lechuga',      3, 4, '1 unidad'),
    ('Carne Molida con Arroz y Ensalada', 'Tomate',       4, 4, '2 unidades'),

    ('Papas Cocidas con Huevo y Lechuga', 'Papa',    1, 4, '6 unidades'),
    ('Papas Cocidas con Huevo y Lechuga', 'Huevo',   2, 4, '4 unidades'),
    ('Papas Cocidas con Huevo y Lechuga', 'Lechuga', 3, 4, '1 unidad'),
    ('Papas Cocidas con Huevo y Lechuga', 'Aceite',  4, 4, '4 porciones'),

    ('Arroz Graneado con Huevo y Cebolla', 'Arroz',   1, 4, '4 porciones'),
    ('Arroz Graneado con Huevo y Cebolla', 'Huevo',   2, 4, '4 unidades'),
    ('Arroz Graneado con Huevo y Cebolla', 'Cebolla', 3, 4, '1 unidad'),
    ('Arroz Graneado con Huevo y Cebolla', 'Aceite',  4, 4, '4 porciones')
) as v (receta, ingrediente, posicion, raciones, texto)
join public.recetas r      on r.nombre = v.receta
join public.ingredientes i on i.nombre = v.ingrediente
on conflict (receta_id, ingrediente_id) do update set
    posicion      = excluded.posicion,
    raciones_base = excluded.raciones_base,
    texto_receta  = excluded.texto_receta;

commit;

-- Hace que la API de Supabase reconozca de inmediato las tablas y la función.
notify pgrst, 'reload schema';

-- Verificación: debe mostrar 2 perfiles, 10 ingredientes, 10 recetas y 40 líneas.
select (select count(*) from public.perfiles)            as perfiles,
       (select count(*) from public.ingredientes)        as ingredientes,
       (select count(*) from public.recetas)             as recetas,
       (select count(*) from public.receta_ingredientes) as lineas_receta;
