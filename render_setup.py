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
    })endpoint = "@app.route('/api/t05-linea/<nombre_linea>/<direccion>')\ndef api_paradas_direccion_t05(nombre_linea, direccion):\n    \"\"\"API T05: devuelve los dos sentidos y siempre responde en JSON, incluso ante fallos.\"\"\"\n    nombre = str(nombre_linea or '').strip().upper()\n    sentido = str(direccion or '').strip().lower()\n    lineas_t05 = {'T05-01', 'T05-20', 'T05-50'}\n\n    def norm(value):\n        return ''.join(ch for ch in str(value or '').upper() if ch.isalnum())\n\n    def records(value):\n        if isinstance(value, dict):\n            out = []\n            for key, item in value.items():\n                if isinstance(item, dict):\n                    item = dict(item)\n                    item.setdefault('_key', key)\n                    out.append(item)\n                elif isinstance(item, (list, tuple)):\n                    out.extend(x for x in item if isinstance(x, dict))\n            return out\n        if isinstance(value, (list, tuple)):\n            return [x for x in value if isinstance(x, dict)]\n        return []\n\n    try:\n        if nombre not in lineas_t05 or sentido not in {'ida', 'vuelta'}:\n            return jsonify({'error': 'Línea o sentido no reconocido', 'stops': []}), 404\n\n        dataset = obtener_dataset_gtfs('T05')\n        if not isinstance(dataset, dict):\n            raise TypeError('El cargador GTFS no devolvió un conjunto de datos.')\n        mapa = dataset.get('map') or {}\n        if not isinstance(mapa, dict):\n            raise TypeError('El catálogo del mapa GTFS tiene un formato inesperado.')\n\n        route_source = mapa.get('routes') or {}\n        route_id = None\n        for route_item in records(route_source):\n            rid = route_item.get('route_id') or route_item.get('id') or route_item.get('_key')\n            short = route_item.get('short_name') or route_item.get('route_short_name') or route_item.get('linea')\n            if norm(short) == norm(nombre) or norm(rid) == norm(nombre):\n                route_id = str(rid) if rid is not None else None\n                break\n\n        schedule = dataset.get('schedule') or {}\n        if not isinstance(schedule, dict):\n            raise TypeError('El horario GTFS tiene un formato inesperado.')\n\n        raw_stop_times = schedule.get('stop_times') or schedule.get('stopTimes') or []\n        stop_times = records(raw_stop_times)\n        if isinstance(raw_stop_times, dict):\n            flattened = []\n            for trip_key, rows in raw_stop_times.items():\n                for row_item in records(rows):\n                    row_item = dict(row_item)\n                    row_item.setdefault('trip_id', trip_key)\n                    flattened.append(row_item)\n            if flattened:\n                stop_times = flattened\n\n        stop_catalog = mapa.get('stops') or {}\n        catalog_by_line = {}\n        lines_by_stop = defaultdict(set)\n        stop_by_id = {}\n        if isinstance(stop_catalog, dict):\n            catalog_entries = stop_catalog.items()\n        elif isinstance(stop_catalog, (list, tuple)):\n            catalog_entries = []\n            for item in stop_catalog:\n                if isinstance(item, dict):\n                    code = item.get('linea') or item.get('route_short_name') or item.get('line_code')\n                    catalog_entries.append((code, [item]))\n        else:\n            catalog_entries = []\n        for line_code, raw_items in catalog_entries:\n            code = str(line_code or '').strip().upper()\n            if not code:\n                continue\n            items = records(raw_items)\n            catalog_by_line[code] = items\n            for item in items:\n                raw_ids = item.get('stop_ids') or item.get('stop_id') or item.get('id') or []\n                if isinstance(raw_ids, (str, int)):\n                    raw_ids = [raw_ids]\n                for sid in raw_ids:\n                    if sid in (None, ''):\n                        continue\n                    sid = str(sid)\n                    lines_by_stop[sid].add(code)\n                    if norm(code) == norm(nombre):\n                        stop_by_id[sid] = dict(item)\n\n        trip_source = schedule.get('trips') or schedule.get('trip') or []\n        trip_meta = {}\n        if isinstance(trip_source, dict):\n            for key, value in trip_source.items():\n                if isinstance(value, dict):\n                    value = dict(value)\n                    value.setdefault('trip_id', key)\n                    trip_meta[str(value.get('trip_id'))] = value\n        else:\n            for trip_item in records(trip_source):\n                tid = trip_item.get('trip_id') or trip_item.get('id')\n                if tid is not None:\n                    trip_meta[str(tid)] = trip_item\n\n        route_trip_ids = {\n            tid for tid, meta in trip_meta.items()\n            if route_id is not None and str(meta.get('route_id') or '') == route_id\n        }\n\n        trips = defaultdict(list)\n        for row in stop_times:\n            trip_id = str(row.get('trip_id') or '')\n            stop_id = str(row.get('stop_id') or row.get('stopId') or '')\n            if not trip_id or not stop_id:\n                continue\n            meta = trip_meta.get(trip_id, {})\n            row_route = str(row.get('route_id') or meta.get('route_id') or '')\n            if route_id is not None:\n                if route_trip_ids:\n                    if trip_id not in route_trip_ids:\n                        continue\n                elif row_route and row_route != route_id:\n                    continue\n                elif not row_route:\n                    route_name = row.get('route_short_name') or row.get('linea') or meta.get('route_short_name')\n                    if norm(route_name) != norm(nombre):\n                        continue\n            else:\n                route_name = row.get('route_short_name') or row.get('linea') or meta.get('route_short_name')\n                if norm(route_name) != norm(nombre):\n                    continue\n            if row_route and route_id is not None and row_route != route_id:\n                continue\n            trips[trip_id].append(row)\n\n        journey_groups = {}\n        for trip_id, rows in trips.items():\n            rows.sort(key=lambda row: int(float(row.get('stop_sequence') or row.get('stopSequence') or 0)))\n            if not rows:\n                continue\n            meta = trip_meta.get(trip_id, {})\n            direction_value = meta.get('direction_id')\n            if direction_value in (None, ''):\n                direction_value = next((row.get('direction_id') for row in rows if row.get('direction_id') not in (None, '')), None)\n            first, last = rows[0], rows[-1]\n            key = ('direction', str(direction_value)) if direction_value not in (None, '') else (\n                'terminals', str(first.get('stop_id') or ''), str(last.get('stop_id') or '')\n            )\n            departure = str(first.get('departure_time') or first.get('arrival_time') or '99:99:99')\n            journey_groups.setdefault(key, []).append((departure, rows))\n\n        keys = list(journey_groups)\n        if keys and all(key[0] == 'direction' for key in keys):\n            keys.sort(key=lambda key: (0, int(key[1])) if key[1].isdigit() else (1, key[1]))\n        else:\n            keys.sort(key=lambda key: min(item[0] for item in journey_groups[key]))\n\n        index = 0 if sentido == 'ida' else 1\n        selected_rows = None\n        if keys:\n            selected_key = keys[index] if index < len(keys) else keys[0]\n            selected_rows = min(journey_groups[selected_key], key=lambda item: item[0])[1]\n            if index == 1 and len(keys) == 1:\n                selected_rows = list(reversed(selected_rows))\n\n        stop_list = []\n        if selected_rows:\n            seen = set()\n            for row in selected_rows:\n                sid = str(row.get('stop_id') or row.get('stopId') or '')\n                base = stop_by_id.get(sid, {'id': sid, 'name': row.get('stop_name') or row.get('stop_name_text') or 'Parada'})\n                stop = dict(base)\n                marker_id = str(stop.get('id') or stop.get('stop_id') or sid)\n                if not marker_id or marker_id in seen:\n                    continue\n                seen.add(marker_id)\n                raw_ids = stop.get('stop_ids') or stop.get('stop_id') or [sid]\n                if isinstance(raw_ids, (str, int)):\n                    raw_ids = [raw_ids]\n                served = set(stop.get('lineas') or [])\n                for ref in raw_ids:\n                    served.update(lines_by_stop.get(str(ref), set()))\n                served.add(nombre)\n                stop.update({\n                    'id': marker_id,\n                    'concesion': 'T05',\n                    'stop_ids': raw_ids,\n                    'lineas': sorted(code for code in served if norm(code) in {norm(x) for x in lineas_t05}),\n                })\n                stop_list.append(stop)\n        else:\n            matching_key = next((key for key in catalog_by_line if norm(key) == norm(nombre)), None)\n            for source in catalog_by_line.get(matching_key, []) if matching_key else []:\n                stop = dict(source)\n                raw_ids = stop.get('stop_ids') or stop.get('stop_id') or stop.get('id') or []\n                if isinstance(raw_ids, (str, int)):\n                    raw_ids = [raw_ids]\n                served = set(stop.get('lineas') or [])\n                for ref in raw_ids:\n                    served.update(lines_by_stop.get(str(ref), set()))\n                served.add(nombre)\n                stop['stop_ids'] = raw_ids\n                stop['lineas'] = sorted(code for code in served if norm(code) in {norm(x) for x in lineas_t05})\n                stop['concesion'] = 'T05'\n                stop_list.append(stop)\n            if sentido == 'vuelta':\n                stop_list.reverse()\n\n        if not stop_list:\n            return jsonify({\n                'error': 'No se encontraron paradas T05 para ' + nombre + '. Comprueba el catálogo y los horarios GTFS.',\n                'linea': nombre, 'sentido': sentido, 'stops': [],\n                'debug': {'routes_type': type(route_source).__name__, 'route_id_found': route_id is not None,\n                          'stop_times': len(stop_times), 'trips': len(trip_meta), 'catalog_lines': list(catalog_by_line.keys())},\n            }), 200\n\n        shape = []\n        for stop in stop_list:\n            try:\n                lat_value = stop.get('lat') if stop.get('lat') is not None else stop.get('latitude')\n                lon_value = stop.get('lon')\n                if lon_value is None:\n                    lon_value = stop.get('lng') if stop.get('lng') is not None else stop.get('longitude')\n                lat, lon = float(lat_value), float(lon_value)\n                if -90 <= lat <= 90 and -180 <= lon <= 180:\n                    shape.append([lat, lon])\n            except (TypeError, ValueError):\n                continue\n\n        return jsonify({\n            'linea': nombre, 'sentido': sentido,\n            'origen': stop_list[0].get('name') or stop_list[0].get('stop_name') or '',\n            'destino': stop_list[-1].get('name') or stop_list[-1].get('stop_name') or '',\n            'shape': shape, 'stops': stop_list,\n        })\n    except Exception as exc:\n        app.logger.exception('Error API recorridos T05 %s %s', nombre, sentido)\n        return jsonify({\n            'error': 'Error al preparar el recorrido T05: ' + str(exc),\n            'linea': nombre, 'sentido': sentido, 'stops': [],\n        }), 500"
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
script_tag = """  <script src="{{ url_for('static', filename='t05-mobile.js') }}?v=10"></script>
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
