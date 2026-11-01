from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import shutil
import zipfile

BASE = Path(__file__).resolve().parent
ARCHIVE = BASE / "mapa-tpa-main (1).zip"
ROOT = BASE / "mapa-tpa-main"
MOBILE = BASE / "t05-mobile.js"

if not ARCHIVE.exists():
    raise SystemExit(f"No se encuentra el proyecto original: {ARCHIVE}")
if not MOBILE.exists():
    raise SystemExit("Falta t05-mobile.js: no se puede publicar la interfaz T05.")

# Siempre reconstruir desde el ZIP original para evitar mezclar restos de builds previos.
if ROOT.exists():
    shutil.rmtree(ROOT)
with zipfile.ZipFile(ARCHIVE) as archive:
    archive.extractall(BASE)

app_path = ROOT / "app.py"
app = app_path.read_text(encoding="utf-8")
anchor = "@app.route('/api/concesiones')\ndef get_concesiones():"

endpoint = '''@app.route('/api/t05-linea/<nombre_linea>/<direccion>')
def api_paradas_direccion_t05(nombre_linea, direccion):
    """Devuelve un recorrido T05 para ambos sentidos, con fallback al catálogo GTFS."""
    nombre = str(nombre_linea or '').upper()
    sentido = str(direccion or '').lower()
    lineas_t05 = {'T05-01', 'T05-20', 'T05-50'}
    if nombre not in lineas_t05 or sentido not in {'ida', 'vuelta'}:
        return jsonify({"error": "Línea o sentido no reconocido", "stops": []}), 404

    dataset = obtener_dataset_gtfs('T05')
    mapa = dataset.get('map') or {}
    routes = mapa.get('routes') or {}
    route_id = next((
        rid for rid, info in routes.items()
        if str(info.get('short_name') or info.get('route_short_name') or '').upper() == nombre
        or str(rid).upper() == nombre
    ), None)
    schedule = dataset.get('schedule') or {}
    stop_times = schedule.get('stop_times') or []

    # Índice de paradas GTFS por línea y líneas que coinciden en cada parada.
    stop_by_id, lines_by_stop = {}, defaultdict(set)
    for line_code, items in (mapa.get('stops') or {}).items():
        if line_code not in lineas_t05:
            continue
        for item in items or []:
            item_ids = item.get('stop_ids') or [item.get('id') or item.get('stop_id') or '']
            for stop_id in item_ids:
                if not stop_id:
                    continue
                stop_id = str(stop_id)
                lines_by_stop[stop_id].add(line_code)
                if line_code == nombre:
                    stop_by_id[stop_id] = dict(item)

    # En GTFS estándar route_id y direction_id viven en trips.txt; algunas
    # fuentes los replican en stop_times. Se soportan ambas variantes.
    trip_records = schedule.get('trips') or []
    if isinstance(trip_records, dict):
        trip_records = list(trip_records.values())
    trip_meta = {}
    for record in trip_records:
        if isinstance(record, dict) and record.get('trip_id') is not None:
            trip_meta[str(record.get('trip_id'))] = record

    route_trip_ids = {
        trip_id for trip_id, record in trip_meta.items()
        if route_id is not None and str(record.get('route_id') or '') == str(route_id)
    }

    # Cada viaje constituye una secuencia ordenada de paradas.
    trips = defaultdict(list)
    for row in stop_times:
        trip_id = str(row.get('trip_id') or '')
        stop_id = str(row.get('stop_id') or '')
        if not trip_id or not stop_id or route_id is None:
            continue
        row_route = str(row.get('route_id') or '')
        if route_trip_ids:
            if trip_id not in route_trip_ids:
                continue
        elif not row_route or row_route != str(route_id):
            continue
        if row_route and row_route != str(route_id):
            continue
        trips[trip_id].append(row)

    journey_groups = {}
    for trip_id, rows in trips.items():
        rows.sort(key=lambda row: int(row.get('stop_sequence') or 0))
        if not rows:
            continue
        first, last = rows[0], rows[-1]
        direction_value = trip_meta.get(trip_id, {}).get('direction_id')
        if direction_value in (None, ''):
            direction_value = next((
                row.get('direction_id') for row in rows
                if row.get('direction_id') not in (None, '')
            ), None)
        direction_id = str(direction_value) if direction_value not in (None, '') else None
        if direction_id is None:
            key = ('terminals', str(first.get('stop_id') or ''), str(last.get('stop_id') or ''))
        else:
            key = ('direction', direction_id)
        departure = str(first.get('departure_time') or first.get('arrival_time') or '99:99:99')
        current = journey_groups.setdefault(key, [])
        current.append((departure, rows))

    keys = list(journey_groups)
    if keys and all(key[0] == 'direction' for key in keys):
        keys.sort(key=lambda key: (0, int(key[1])) if key[1].isdigit() else (1, key[1]))
    else:
        keys.sort(key=lambda key: min(item[0] for item in journey_groups[key]))

    index = 0 if sentido == 'ida' else 1
    selected_rows = None
    if keys:
        selected_key = keys[index] if index < len(keys) else keys[0]
        selected_rows = min(journey_groups[selected_key], key=lambda item: item[0])[1]
        if index == 1 and len(keys) == 1:
            selected_rows = list(reversed(selected_rows))

    # Si stop_times no contiene viajes utilizables (p. ej. calendario parcial),
    # se usa la lista de paradas que ya alimenta los marcadores del mapa.
    stop_list = []
    if selected_rows:
        included = set()
        for row in selected_rows:
            stop_id = str(row.get('stop_id') or '')
            base = stop_by_id.get(stop_id, {
                'id': stop_id,
                'name': row.get('stop_name') or row.get('stop_name_text') or 'Parada',
            })
            stop = dict(base)
            marker_id = str(stop.get('id') or stop.get('stop_id') or stop_id)
            if not marker_id or marker_id in included:
                continue
            included.add(marker_id)
            ids = stop.get('stop_ids') or [stop_id]
            served_lines = set(stop.get('lineas') or [])
            for stop_ref in ids:
                served_lines.update(lines_by_stop.get(str(stop_ref), set()))
            served_lines.add(nombre)
            stop.update({
                'id': marker_id,
                'concesion': 'T05',
                'stop_ids': ids,
                'lineas': sorted(line for line in served_lines if line in lineas_t05),
            })
            stop_list.append(stop)
    else:
        for source in (mapa.get('stops') or {}).get(nombre, []) or []:
            stop = dict(source)
            ids = stop.get('stop_ids') or [stop.get('id') or stop.get('stop_id') or '']
            served_lines = set(stop.get('lineas') or [])
            for stop_ref in ids:
                served_lines.update(lines_by_stop.get(str(stop_ref), set()))
            served_lines.add(nombre)
            stop['stop_ids'] = ids
            stop['lineas'] = sorted(line for line in served_lines if line in lineas_t05)
            stop['concesion'] = 'T05'
            stop_list.append(stop)
        if sentido == 'vuelta':
            stop_list.reverse()

    if not stop_list:
        return jsonify({
            "error": "No hay paradas cargadas para " + nombre,
            "stops": [],
        }), 200

    # El trazado se dibuja con las coordenadas de las paradas si el shape oficial
    # no está disponible en el resumen GTFS de la concesión.
    shape = []
    for stop in stop_list:
        try:
            lat = float(stop.get('lat') if stop.get('lat') is not None else stop.get('latitude'))
            lon_value = stop.get('lon')
            if lon_value is None:
                lon_value = stop.get('lng') if stop.get('lng') is not None else stop.get('longitude')
            lon = float(lon_value)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                shape.append([lat, lon])
        except (TypeError, ValueError):
            continue

    return jsonify({
        'linea': nombre,
        'sentido': sentido,
        'origen': stop_list[0].get('name') or stop_list[0].get('stop_name') or '',
        'destino': stop_list[-1].get('name') or stop_list[-1].get('stop_name') or '',
        'shape': shape,
        'stops': stop_list,
    })


'''''
if "def api_paradas_direccion_t05(" not in app:
    if anchor not in app:
        raise SystemExit("No se encontró el punto para registrar el endpoint GTFS T05.")
    app = app.replace(anchor, endpoint + anchor, 1)
app_path.write_text(app, encoding="utf-8")

# Instalar la interfaz T05 en los estáticos de Flask.
static_dir = ROOT / "static"
static_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(MOBILE, static_dir / "t05-mobile.js")

template_path = ROOT / "templates" / "index.html"
html = template_path.read_text(encoding="utf-8")

html = html.replace(
    "<title>Seguimiento de Autobuses - Tiempo Real</title>",
    "<title>TPA Aragón · Concesión T05</title>",
    1,
)

# Filtrar las llegadas con el código de la línea seleccionada sin cambiar el proveedor GTFS/GTFS-RT.
signature_old = "async function cargarLlegadasParada(stopId, popup, fecha = fechaLocalISO(), stopIds = null) {"
signature_new = "async function cargarLlegadasParada(stopId, popup, fecha = fechaLocalISO(), stopIds = null, lineaFiltro = undefined) {"
if signature_old not in html and signature_new not in html:
    raise SystemExit("No se encontró cargarLlegadasParada() en la plantilla original.")
html = html.replace(signature_old, signature_new, 1)

filter_start_old = """      if (!contenedor) return;

      // Solo la consulta del día actual"""
filter_start_new = """      if (!contenedor) return;
      if (lineaFiltro !== undefined) popup._lineaFiltroActiva = lineaFiltro;
      const filtroLineaActiva = popup._lineaFiltroActiva || '';

      // Solo la consulta del día actual"""
if filter_start_old in html:
    html = html.replace(filter_start_old, filter_start_new, 1)
elif filter_start_new not in html:
    raise SystemExit("No se pudo integrar el filtro de líneas en las llegadas.")

sort_old = """        elementos.sort((a, b) => Number(a.timestampMostrado || 0) - Number(b.timestampMostrado || 0));

        if (!elementos.length)"""
sort_new = """        elementos.sort((a, b) => Number(a.timestampMostrado || 0) - Number(b.timestampMostrado || 0));
        if (filtroLineaActiva) {
          const filtrados = elementos.filter(item =>
            String(item.linea || '').trim().toUpperCase() === String(filtroLineaActiva).trim().toUpperCase()
          );
          elementos.splice(0, elementos.length, ...filtrados);
        }
        if (!elementos.length && filtroLineaActiva) {
          contenedor.innerHTML = '<div class="stop-arrival-state">No hay salidas para ' +
            escaparHTML(filtroLineaActiva) + ' en la fecha seleccionada.</div>';
          return;
        }

        if (!elementos.length)"""
if sort_old in html:
    html = html.replace(sort_old, sort_new, 1)
elif sort_new not in html:
    raise SystemExit("No se pudo integrar el filtrado de las llegadas por línea.")

# Cargar la aplicación móvil después de los scripts originales, para reutilizar el mapa y sus datos.
script_tag = """  <script src="{{ url_for('static', filename='t05-mobile.js') }}?v=9"></script>
"""
if "filename='t05-mobile.js'" not in html:
    if "</body>" not in html:
        raise SystemExit("La plantilla original no contiene </body>.")
    html = html.replace("</body>", script_tag + "</body>", 1)

# Guardas: Render no debe desplegar una versión que haya dejado fuera la interfaz T05.
required = [
    "filename='t05-mobile.js'",
    "cargarLlegadasParada",
    "id=\"map\"",
]
missing = [item for item in required if item not in html]
if missing:
    raise SystemExit("Build incompleto; faltan elementos: " + ", ".join(missing))

template_path.write_text(html, encoding="utf-8")
print("Build T05 completado: interfaz móvil cargada, mapa original conservado y API de recorridos GTFS instalada.")
