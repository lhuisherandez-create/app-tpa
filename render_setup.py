from __future__ import annotations

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

endpoint = "@app.route('/api/t05-linea/<nombre_linea>/<direccion>')\ndef api_paradas_direccion_t05(nombre_linea, direccion):\n    \"\"\"Recorrido oficial T05: ordenado por stop_sequence y direction_id del horario GTFS.\"\"\"\n    nombre = str(nombre_linea or '').strip().upper()\n    sentido = str(direccion or '').strip().lower()\n    lineas_permitidas = {'T05-01', 'T05-20', 'T05-50'}\n\n    try:\n        if nombre not in lineas_permitidas or sentido not in {'ida', 'vuelta'}:\n            return jsonify({'error': 'Línea o sentido no reconocido', 'stops': []}), 404\n\n        dataset = obtener_dataset_gtfs('T05')\n        mapa = dataset.get('map') or {}\n        horario = dataset.get('schedule') or {}\n        if not isinstance(mapa, dict) or not isinstance(horario, dict):\n            raise TypeError('El conjunto GTFS T05 no tiene el formato esperado.')\n\n        # El timetable ya contiene route_id, trip_id, direction_id y stop_sequence.\n        # Es la fuente de orden del recorrido; nunca ordenar por el catálogo del mapa.\n        catalogo_rutas = horario.get('routes') or mapa.get('routes') or {}\n        route_id = None\n        if isinstance(catalogo_rutas, dict):\n            for rid, info in catalogo_rutas.items():\n                if isinstance(info, dict):\n                    short_name = info.get('short_name') or info.get('route_short_name')\n                    if str(short_name or '').strip().upper() == nombre:\n                        route_id = str(rid)\n                        break\n        elif isinstance(catalogo_rutas, list):\n            for info in catalogo_rutas:\n                if isinstance(info, dict) and str(info.get('short_name') or info.get('route_short_name') or '').strip().upper() == nombre:\n                    route_id = str(info.get('route_id') or info.get('id') or '')\n                    break\n        if not route_id:\n            return jsonify({'error': 'No se encontró el route_id GTFS de ' + nombre, 'stops': []}), 200\n\n        direction_id = '0' if sentido == 'ida' else '1'\n        stop_times = horario.get('stop_times') or []\n        if not isinstance(stop_times, list):\n            return jsonify({'error': 'El horario GTFS no contiene stop_times en formato de lista.', 'stops': []}), 200\n\n        trips = {}\n        for row in stop_times:\n            if not isinstance(row, dict) or str(row.get('route_id') or '') != route_id:\n                continue\n            if str(row.get('direction_id') if row.get('direction_id') is not None else '') != direction_id:\n                continue\n            trip_id = str(row.get('trip_id') or '')\n            if not trip_id or not row.get('stop_id'):\n                continue\n            trips.setdefault(trip_id, []).append(row)\n\n        if not trips:\n            return jsonify({\n                'error': 'El GTFS no contiene viajes para ' + nombre + ' en sentido ' + sentido + '.',\n                'linea': nombre, 'sentido': sentido, 'direction_id': direction_id, 'stops': []\n            }), 200\n\n        def secuencia(row):\n            try:\n                return int(float(row.get('stop_sequence', 0)))\n            except (TypeError, ValueError):\n                return 0\n\n        # Unir viajes que recorren la misma secuencia de stop_id. Se elige\n        # el patrón más repetido para no mezclar variantes de servicio.\n        patrones = {}\n        for trip_id, rows in trips.items():\n            ordenadas = sorted(rows, key=secuencia)\n            firma = tuple(str(row.get('stop_id')) for row in ordenadas)\n            if firma:\n                inicio = str(ordenadas[0].get('departure_time') or ordenadas[0].get('arrival_time') or '99:99:99')\n                patrones.setdefault(firma, []).append((inicio, ordenadas))\n\n        if not patrones:\n            return jsonify({'error': 'No se pudo construir la secuencia de paradas de ' + nombre + '.', 'stops': []}), 200\n\n        variantes = list(patrones.values())\n        variante = min(\n            variantes,\n            key=lambda grupo: (-len(grupo), -len(grupo[0][1]), min(item[0] for item in grupo))\n        )\n        rows_recorrido = min(variante, key=lambda item: item[0])[1]\n\n        # Coordenadas y datos visibles se cruzan por stop_id, pero conservando\n        # estrictamente la secuencia proporcionada por stop_times.\n        paradas_mapa = mapa.get('stops') or {}\n        paradas_por_id = {}\n        lineas_por_parada = {}\n        for codigo_linea, items in paradas_mapa.items() if isinstance(paradas_mapa, dict) else []:\n            if not isinstance(items, list):\n                continue\n            codigo = str(codigo_linea).strip().upper()\n            if codigo not in lineas_permitidas:\n                continue\n            for item in items:\n                if not isinstance(item, dict):\n                    continue\n                refs = item.get('stop_ids') or item.get('stop_id') or item.get('id') or []\n                if isinstance(refs, (str, int)):\n                    refs = [refs]\n                refs = [str(ref) for ref in refs if ref not in (None, '')]\n                for ref in refs:\n                    paradas_por_id[ref] = item\n                    lineas_por_parada.setdefault(ref, set()).add(codigo)\n\n        resultado = []\n        forma = []\n        for row in rows_recorrido:\n            stop_id = str(row.get('stop_id') or '')\n            meta = dict(paradas_por_id.get(stop_id) or {})\n            refs = meta.get('stop_ids') or meta.get('stop_id') or meta.get('id') or []\n            if isinstance(refs, (str, int)):\n                refs = [refs]\n            refs = [str(ref) for ref in refs if ref not in (None, '')]\n            if stop_id and stop_id not in refs:\n                refs.append(stop_id)\n\n            nombre_parada = (\n                meta.get('name') or meta.get('stop_name') or\n                row.get('stop_name') or row.get('name') or 'Parada'\n            )\n            lineas_servicio = set(meta.get('lineas') or [])\n            for ref in refs:\n                lineas_servicio.update(lineas_por_parada.get(ref, set()))\n            lineas_servicio.add(nombre)\n\n            parada = dict(meta)\n            parada.update({\n                'id': str(meta.get('id') or stop_id),\n                'name': nombre_parada,\n                'stop_ids': refs or [stop_id],\n                'lineas': sorted(c for c in lineas_servicio if c in lineas_permitidas),\n                'concesion': 'T05',\n                'stop_sequence': secuencia(row),\n                'stop_id_gtfs': stop_id,\n            })\n            resultado.append(parada)\n\n            try:\n                lat_value = parada.get('lat') if parada.get('lat') is not None else parada.get('latitude')\n                lon_value = parada.get('lon')\n                if lon_value is None:\n                    lon_value = parada.get('lng') if parada.get('lng') is not None else parada.get('longitude')\n                lat, lon = float(lat_value), float(lon_value)\n                if -90 <= lat <= 90 and -180 <= lon <= 180:\n                    forma.append([lat, lon])\n            except (TypeError, ValueError):\n                pass\n\n        if not resultado:\n            return jsonify({'error': 'El recorrido ' + nombre + ' no tiene paradas válidas.', 'stops': []}), 200\n\n        return jsonify({\n            'linea': nombre,\n            'sentido': sentido,\n            'direction_id': direction_id,\n            'origen': resultado[0]['name'],\n            'destino': resultado[-1]['name'],\n            'shape': forma,\n            'stops': resultado,\n        })\n    except Exception as exc:\n        app.logger.exception('Error preparando recorrido GTFS T05 %s %s', nombre, sentido)\n        return jsonify({\n            'error': 'Error preparando recorrido GTFS T05: ' + str(exc),\n            'linea': nombre, 'sentido': sentido, 'stops': []\n        }), 500"
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

# Ocultar el contenido heredado desde el primer render hasta que arranque T05.
html_start = html.lower().find("<html")
html_end = html.find(">", html_start) if html_start >= 0 else -1
if html_end >= 0:
    html_open_tag = html[html_start:html_end + 1]
    if "data-t05-boot" not in html_open_tag:
        html = html[:html_end] + ' data-t05-boot="1"' + html[html_end:]
if 'id="t05-boot-style"' not in html:
    boot_css = '<style id="t05-boot-style">html[data-t05-boot="1"] body{visibility:hidden!important}#pantalla-inicio{display:none!important}</style>'
    html = html.replace("</head>", boot_css + "</head>", 1)

# Cargar la aplicación móvil después de los scripts originales, para reutilizar el mapa y sus datos.
script_tag = """  <script src="{{ url_for('static', filename='t05-mobile.js') }}?v=12"></script>
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
