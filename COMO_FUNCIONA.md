# Cómo funciona LeanView 5'S (flex.ruktu.com)

## 1. Resumen

LeanView 5'S es un dashboard de auditorías Lean/5S: KPIs y gráficas de
cumplimiento, un editor de "acciones" correctivas, un plano interactivo de
planta (Layout), un calendario de auditorías, Auditoría Cruzada, y **Gemba
Walk** — un flujo en vivo donde un administrador crea una "sala" con PIN y
varios participantes se unen desde su celular para levantar hallazgos en
tiempo real.

Es un fork de [GemaRomoflex/5-S-APP-PHILO](https://github.com/GemaRomoflex/5-S-APP-PHILO).
La app original dependía de un proyecto **Supabase Cloud** ajeno (URL y
anon key quedaban hardcodeados en el HTML). Este despliegue reemplaza esa
dependencia por un **backend propio (FastAPI + PostgreSQL) corriendo en
Docker** en esta misma máquina, publicado en **https://flex.ruktu.com**.

Toda la interfaz (`index.html`, ~8800 líneas, sin build step) es exactamente
la misma que en el fork original — el único cambio funcional es la capa de
datos: donde antes había un cliente `supabase-js`, ahora hay un pequeño shim
que habla con nuestra API por `fetch()`.

## 2. Arquitectura

```
Navegador
   │  HTTPS
   ▼
Cloudflare Tunnel (compartido con ruktu.com / visage.ruktu.com)
   │
   ▼
flex-nginx  (Docker, red "ruktu" compartida + red interna propia)
   ├── /              → archivos estáticos (index.html, iconos/, imágenes)
   ├── /evidence/*    → fotos de Auditoría Cruzada (bind mount de instance/uploads/evidence)
   └── /api/*         → proxy_pass → flex-backend:8000
                              │
                              ▼
                        flex-backend (FastAPI, Docker, red interna)
                              │
                              ▼
                        flex-postgres (Postgres 16, Docker, red interna, sin puerto expuesto al host)
```

`flex-nginx` está en dos redes Docker: la interna propia (`flex-internal`,
para hablar con el backend) y la red externa `ruktucom_ruktu` (para que el
`cloudflared` de `ruktu.com` pueda enrutarle tráfico). Todo vive bajo un
mismo hostname público — no hace falta CORS ni un segundo registro DNS.

## 3. Estructura de carpetas

```
5-S-APP-PHILO/
├── index.html, iconos/, *.png, *.webp, ppa.csv   ← frontend, sin tocar salvo la capa de datos
├── gemba_tables.sql        ← schema original de Supabase (referencia histórica)
├── backend/
│   ├── main.py             ← FastAPI app, registra los routers
│   ├── database.py         ← engine/SessionLocal/get_db()
│   ├── models.py           ← las 8 tablas (SQLAlchemy)
│   ├── utils.py            ← serialización de filas a dict
│   ├── routers/             ← un archivo por tabla/concern
│   └── Dockerfile
├── nginx/conf.d/default.conf
├── docker-compose.yml
├── .env                     ← credenciales de Postgres (NO se sube a git)
├── arrancar.sh              ← git pull + docker compose up
├── scripts/iniciar_en_boot.sh  ← lanza arrancar.sh dentro de `screen -S flex`
└── instance/                 ← datos persistentes (Postgres, uploads), NO se sube a git
```

## 4. Modelo de datos

8 tablas en Postgres, recreadas a partir del código original de `index.html`
(no hubo datos que migrar — se acordó explícitamente arrancar con base vacía
por ser un prototipo):

| Tabla | Para qué sirve |
|---|---|
| `actions` | Hallazgos/acciones correctivas del dashboard general. `actionId` es la clave real (upsert por ahí). |
| `layout_coords` | Recuadros del plano interactivo (planta B27/B29). |
| `owners_directory` | Directorio área → responsable/departamento. |
| `calendar_events` | Calendario de auditorías programadas. |
| `gemba_events` | "Salas" de Gemba Walk (PIN, turno, áreas, estado). |
| `gemba_participants` | Participantes que se unen a una sala por PIN, con su sección asignada. |
| `gemba_live_actions` | Acciones levantadas en vivo durante un Gemba Walk, con foto en base64. |
| `perfiles` | Tabla de perfiles de usuario — existe para uso futuro, no está conectada hoy (ver §7). |

`gemba_live_actions.photo_base64` guarda la foto comprimida directamente
como texto en la fila (no como archivo), tal como en el diseño original —
la razón, según el comentario original, es no saturar el canal de tiempo
real con referencias a Storage.

## 5. API

Todos los endpoints viven bajo `/api/`. Los más relevantes:

- `GET/POST /api/actions`, `POST /api/actions/upsert`, `PATCH|DELETE /api/actions/{action_id}`
- `GET /api/layout_coords`, `DELETE /api/layout_coords` (borra todo), `POST /api/layout_coords` (inserta en bloque)
- `GET/POST /api/owners_directory`, `PATCH|DELETE /api/owners_directory/{area_id}`
- `GET/POST /api/calendar_events`, `PATCH|DELETE /api/calendar_events/{id}`
- `POST /api/gemba_events`, `PATCH|GET /api/gemba_events/{id}`, `GET /api/gemba_events/by_pin/{pin}`
- `GET/POST /api/gemba_participants`, `PATCH|GET /api/gemba_participants/{id}`
- `GET/POST /api/gemba_live_actions`
- `POST /api/evidence` (sube una foto de Auditoría Cruzada, devuelve su URL pública)
- `GET /api/gemba_events/{id}/stream/admin` y `GET /api/gemba_events/{id}/stream/participant` (ver §6)

## 6. Reemplazo de Supabase Realtime por SSE

El Gemba Walk original usaba Supabase Realtime para avisar en vivo: al admin,
cuando entra un participante nuevo; al participante, cuando el admin arranca/
termina la sala o le asigna una sección. Aquí se reemplazó con **Server-Sent
Events**: el backend hace polling interno cada 3 segundos y solo emite un
evento cuando algo cambió. El frontend no lo nota — el shim de `index.html`
envuelve `EventSource` con la misma forma (`.channel().on().subscribe()`)
que usaba `supabase-js`, así que el código de la UI no cambió una sola línea.

## 7. Autenticación — estado actual (a propósito, no un descuido)

**Hoy no hay autenticación real.** `checkSession()` en `index.html` tiene un
bypass explícito ("MODO GEMBA ABIERTO") que mete a cualquiera como
`Administrador` automáticamente, sin pasar por login. Esto **ya era así antes
de esta migración** — no es una regresión: la app original tampoco validaba
nada server-side (la anon key de Supabase estaba expuesta en el HTML, así que
cualquiera con las herramientas de desarrollador ya podía leer/escribir toda
la base directamente).

Se preservó ese comportamiento tal cual, sin agregarle ni quitarle nada. La
tabla `perfiles` y sus endpoints existen por si algún día se quiere reactivar
el login real (`handleLogin`/`changePasswordOnFirstLogin` siguen en el código,
solo que inalcanzables porque el overlay de login nunca se muestra).

## 8. Cómo correr el proyecto

```bash
cd /home/diego/Documentos/5-S-APP-PHILO
docker compose up -d --build     # levanta postgres + backend + nginx
docker compose ps                 # ver estado
docker compose logs -f backend    # logs en vivo del backend
docker compose down                # apagar todo
```

Variables de entorno en `.env` (no se sube a git, ver `.env.example` para la
plantilla): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## 9. Arranque automático en boot

Al reiniciar la máquina, el crontab del usuario (`@reboot`) dispara
`scripts/iniciar_en_boot.sh`, que abre una sesión de `screen` llamada `flex`
y corre `arrancar.sh` dentro (git pull + `docker compose up --build` en
primer plano). Para ver los logs en vivo en cualquier momento:

```bash
screen -r flex      # Ctrl+A, D para salir sin matar la sesión
```

Los contenedores además tienen `restart: unless-stopped`, así que sobreviven
un reinicio de Docker incluso sin pasar por el script de `screen` — este es
solo el mecanismo que además deja los logs visibles en una sesión persistente,
tal como se pidió.

## 10. Cloudflare Tunnel

`flex.ruktu.com` se expone reutilizando el **mismo túnel** que ya usa
`ruktu.com`/`www.ruktu.com`/`visage.ruktu.com` (no se levantó un túnel
nuevo). La configuración vive en
`/home/diego/Documentos/ruktu.com/cloudflared/config.yml` — ahí se agregó
una regla de ingress más:

```yaml
- hostname: flex.ruktu.com
  service: http://flex-nginx:80
```

Si en el futuro hay que agregar otro hostname a este mismo túnel, es el
mismo patrón: agregar la regla en ese `config.yml` y correr
`docker compose restart cloudflared` desde `ruktu.com/` — eso interrumpe
brevemente los otros 3 hostnames que comparten el mismo contenedor, así que
conviene hacerlo con cuidado y verificar los 4 después.

El token de la API de Cloudflare usado para crear el registro DNS de
`flex.ruktu.com` está guardado en `/home/diego/Documentos/cloudflare API TOKEN.md`.

## 11. Evidencias fotográficas (Auditoría Cruzada)

Las fotos que se suben en el flujo de Auditoría Cruzada se guardan en
`instance/uploads/evidence/` y se sirven directo por nginx en
`https://flex.ruktu.com/evidence/<archivo>`. Igual que en el diseño
original (bucket público de Supabase Storage, sin control de acceso), estas
URLs son públicas y no hay limpieza/borrado automático — es el mismo nivel
de exposición que ya tenía la app, no una regresión introducida aquí.

## 12. Qué se dejó atrás de Supabase

- No hay equivalente de Row Level Security — la seguridad depende
  enteramente de qué endpoints expone el backend (todos, ninguno tiene auth
  hoy).
- El RBAC de la interfaz (`applyRBAC()`) sigue siendo 100% cosmético del
  lado del navegador, exactamente como antes.
- La migración del schema de `actions`/`layout_coords`/`owners_directory`/
  `calendar_events` se reconstruyó leyendo el código (no había SQL fuente
  para esas 4 tablas, solo para las 3 de Gemba en `gemba_tables.sql`).

## 13. Troubleshooting

- **Un contenedor no arranca**: `docker compose logs <servicio>`.
- **`flex.ruktu.com` no resuelve/da 502**: confirmar que `flex-nginx` está
  arriba (`docker compose ps`) y que el ingress en
  `ruktu.com/cloudflared/config.yml` sigue apuntando a `flex-nginx:80`.
- **La red `ruktu` no existe / flex-nginx no puede unirse**: verificar el
  nombre exacto con `docker network ls | grep ruktu` (hoy es
  `ruktucom_ruktu`) y que coincida con `docker-compose.yml`.
- **Cambios en `index.html` no se reflejan**: si el archivo se reemplazó
  (no editó in-place), Docker puede quedarse con el inodo viejo del bind
  mount — correr `docker compose up -d --force-recreate flex-nginx`.
- **Verificar que las 8 tablas existen**: `docker compose exec postgres psql -U flex -d flex -c '\dt'`.

## 14. Roadmap sugerido (no implementado)

- Autenticación real (la tabla `perfiles` y el flujo de login ya están, solo
  falta quitar el bypass y conectar `checkSession()`).
- Algún equivalente de control de acceso por fila si el uso deja de ser
  interno/confiable.
- Backup automático de Postgres (hoy no hay ninguno configurado).
- Servir `/evidence/*` por un endpoint del backend en vez de un mount
  estático de nginx, si algún día importa controlar el acceso a esas fotos.
