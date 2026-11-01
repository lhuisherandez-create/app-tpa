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

endpoint = "@app.route('/api/t05-linea/<nombre_linea>/<direccion>')\ndef api_paradas_direccion_t05(nombre_linea, direccion):\n    \"\"\"API de recorridos T05 con respuesta JSON incluso si el GTFS falla.\"\"\"\n    nombre = str(nombre_linea or '').strip().upper()\n    sentido = str(direccion or '').strip().lower()\n    lineas = {'T05-01', 'T05-20', 'T05-50'}\n\n    def norm(value):\n        return ''.join(c for c in str(value or '').upper() if c.isalnum())\n\n    def records(value):\n        if isinstance(value, dict):\n            result = []\n            for key, item in value.items():\n                if isinstance(item, dict):\n                    row = dict(item)\n                    row.setdefault('_key', key)\n                    result.append(row)\n                elif isinstance(item, (list, tuple)):\n                    result.extend(dict(x) for x in item if isinstance(x, dict))\n            return result\n        if isinstance(value, (list, tuple)):\n            return [dict(x) for x in value if isinstance(x, dict)]\n        return []\n\n    try:\n        if nombre not in lineas or sentido not in {'ida', 'vuelta'}:\n            return jsonify({'error': 'Línea o sentido no reconocido', 'stops': []}), 404\n        dataset = obtener_dataset_gtfs('T05')\n        if not isinstance(dataset, dict):\n            raise TypeError('obtener_dataset_gtfs no devolvió un diccionario')\n        mapa = dataset.get('map') or {}\n        if not isinstance(mapa, dict):\n            raise TypeError('El catálogo map GTFS tiene un formato inesperado')\n        routes_raw = mapa.get('routes') or {}\n        route_id = None\n        for item in records(routes_raw):\n            rid = item.get('route_id') or item.get('id') or item.get('_key')\n            short = item.get('short_name') or item.get('route_short_name') or item.get('linea')\n            if norm(short) == norm(nombre) or norm(rid) == norm(nombre):\n                route_id = str(rid) if rid is not None else None\n                break\n        if route_id is None and isinstance(routes_raw, dict):\n            route_id = next((str(k) for k in routes_raw if norm(k) == norm(nombre)), None)\n\n        schedule = dataset.get('schedule') or {}\n        if not isinstance(schedule, dict):\n            raise TypeError('El horario GTFS tiene un formato inesperado')\n        raw_times = schedule.get('stop_times') or schedule.get('stopTimes') or []\n        stop_times = records(raw_times)\n        if isinstance(raw_times, dict):\n            packed = []\n            for tid, items in raw_times.items():\n                for row in records(items):\n                    row.setdefault('trip_id', tid)\n                    packed.append(row)\n            if packed:\n                stop_times = packed\n\n        catalog = mapa.get('stops') or {}\n        catalog_by_line = {}\n        lines_by_stop = defaultdict(set)\n        stop_by_id = {}\n        if isinstance(catalog, dict):\n            entries = catalog.items()\n        elif isinstance(catalog, (list, tuple)):\n            entries = [(x.get('linea') or x.get('route_short_name'), [x]) for x in catalog if isinstance(x, dict)]\n        else:\n            entries = []\n        for key, raw_items in entries:\n            code = str(key or '').strip().upper()\n            if not code:\n                continue\n            items = records(raw_items)\n            catalog_by_line[code] = items\n            for item in items:\n                refs = item.get('stop_ids') or item.get('stop_id') or item.get('id') or []\n                if isinstance(refs, (str, int)):\n                    refs = [refs]\n                for ref in refs:\n                    if ref in (None, ''):\n                        continue\n                    sid = str(ref)\n                    lines_by_stop[sid].add(code)\n                    if norm(code) == norm(nombre):\n                        stop_by_id[sid] = dict(item)\n\n        raw_trips = schedule.get('trips') or schedule.get('trip') or []\n        trip_meta = {}\n        if isinstance(raw_trips, dict):\n            for key, item in raw_trips.items():\n                if isinstance(item, dict):\n                    meta = dict(item)\n                    meta.setdefault('trip_id', key)\n                    trip_meta[str(meta.get('trip_id'))] = meta\n        else:\n            for meta in records(raw_trips):\n                tid = meta.get('trip_id') or meta.get('id')\n                if tid is not None:\n                    trip_meta[str(tid)] = meta\n\n        route_trip_ids = {tid for tid, meta in trip_meta.items()\n                          if route_id is not None and str(meta.get('route_id') or '') == route_id}\n        trips = defaultdict(list)\n        for row in stop_times:\n            tid = str(row.get('trip_id') or '')\n            sid = str(row.get('stop_id') or row.get('stopId') or '')\n            if not tid or not sid:\n                continue\n            meta = trip_meta.get(tid, {})\n            row_route = str(row.get('route_id') or meta.get('route_id') or '')\n            route_short = row.get('route_short_name') or row.get('linea') or meta.get('route_short_name')\n            if route_id is not None:\n                if route_trip_ids and tid not in route_trip_ids:\n                    continue\n                if not route_trip_ids and row_route and row_route != route_id and norm(route_short) != norm(nombre):\n                    continue\n                if not route_trip_ids and not row_route and norm(route_short) != norm(nombre):\n                    continue\n                if row_route and row_route != route_id:\n                    continue\n            elif norm(route_short) != norm(nombre) and norm(row_route) != norm(nombre):\n                continue\n            trips[tid].append(row)\n\n        groups = {}\n        for tid, rows in trips.items():\n            def sequence(row):\n                try:\n                    return int(float(row.get('stop_sequence') or row.get('stopSequence') or 0))\n                except (TypeError, ValueError):\n                    return 0\n            rows.sort(key=sequence)\n            if not rows:\n                continue\n            meta = trip_meta.get(tid, {})\n            direction_id = meta.get('direction_id')\n            if direction_id in (None, ''):\n                direction_id = next((r.get('direction_id') for r in rows if r.get('direction_id') not in (None, '')), None)\n            first, last = rows[0], rows[-1]\n            key = ('direction', str(direction_id)) if direction_id not in (None, '') else ('terminals', str(first.get('stop_id')), str(last.get('stop_id')))\n            start_time = str(first.get('departure_time') or first.get('arrival_time') or '99:99:99')\n            groups.setdefault(key, []).append((start_time, rows))\n        keys = list(groups)\n        if keys and all(k[0] == 'direction' for k in keys):\n            keys.sort(key=lambda k: (0, int(k[1])) if k[1].isdigit() else (1, k[1]))\n        else:\n            keys.sort(key=lambda k: min(pair[0] for pair in groups[k]))\n        selected = None\n        index = 0 if sentido == 'ida' else 1\n        if keys:\n            selected = min(groups[keys[min(index, len(keys)-1)]], key=lambda pair: pair[0])[1]\n            if index == 1 and len(keys) == 1:\n                selected = list(reversed(selected))\n\n        result_stops = []\n        if selected:\n            seen = set()\n            for row in selected:\n                sid = str(row.get('stop_id') or row.get('stopId') or '')\n                stop = dict(stop_by_id.get(sid) or {'id': sid, 'name': row.get('stop_name') or 'Parada'})\n                marker_id = str(stop.get('id') or stop.get('stop_id') or sid)\n                if not marker_id or marker_id in seen:\n                    continue\n                seen.add(marker_id)\n                refs = stop.get('stop_ids') or stop.get('stop_id') or [sid]\n                if isinstance(refs, (str, int)):\n                    refs = [refs]\n                served = set(stop.get('lineas') or [])\n                for ref in refs:\n                    served.update(lines_by_stop.get(str(ref), set()))\n                served.add(nombre)\n                stop.update({'id': marker_id, 'stop_ids': refs, 'lineas': sorted(x for x in served if norm(x) in {norm(v) for v in lineas}), 'concesion': 'T05'})\n                result_stops.append(stop)\n        else:\n            match = next((key for key in catalog_by_line if norm(key) == norm(nombre)), None)\n            for item in catalog_by_line.get(match, []) if match else []:\n                stop = dict(item)\n                refs = stop.get('stop_ids') or stop.get('stop_id') or stop.get('id') or []\n                if isinstance(refs, (str, int)):\n                    refs = [refs]\n                served = set(stop.get('lineas') or [])\n                for ref in refs:\n                    served.update(lines_by_stop.get(str(ref), set()))\n                served.add(nombre)\n                stop.update({'stop_ids': refs, 'lineas': sorted(x for x in served if norm(x) in {norm(v) for v in lineas}), 'concesion': 'T05'})\n                result_stops.append(stop)\n            if sentido == 'vuelta':\n                result_stops.reverse()\n\n        if not result_stops:\n            return jsonify({'error': 'No hay paradas GTFS para ' + nombre + ' (' + sentido + ').',\n                            'linea': nombre, 'sentido': sentido, 'stops': [],\n                            'debug': {'route_id': route_id, 'stop_times': len(stop_times),\n                                      'trips': len(trip_meta), 'catalog_lines': list(catalog_by_line.keys())}}), 200\n\n        shape = []\n        for stop in result_stops:\n            try:\n                lat_value = stop.get('lat') if stop.get('lat') is not None else stop.get('latitude')\n                lon_value = stop.get('lon')\n                if lon_value is None:\n                    lon_value = stop.get('lng') if stop.get('lng') is not None else stop.get('longitude')\n                lat, lon = float(lat_value), float(lon_value)\n                if -90 <= lat <= 90 and -180 <= lon <= 180:\n                    shape.append([lat, lon])\n            except (TypeError, ValueError):\n                continue\n        return jsonify({'linea': nombre, 'sentido': sentido,\n                        'origen': result_stops[0].get('name') or result_stops[0].get('stop_name') or '',\n                        'destino': result_stops[-1].get('name') or result_stops[-1].get('stop_name') or '',\n                        'shape': shape, 'stops': result_stops})\n    except Exception as exc:\n        app.logger.exception('Error API recorridos T05 %s %s', nombre, sentido)\n        return jsonify({'error': 'Error preparando recorrido T05: ' + str(exc),\n                        'linea': nombre, 'sentido': sentido, 'stops': []}), 500"
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
