from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

BASE = Path(__file__).resolve().parent
ARCHIVE = BASE / 'mapa-tpa-main (1).zip'
ROOT = BASE / 'mapa-tpa-main'
MOBILE = BASE / 't05-mobile.js'

if not ARCHIVE.exists() or not MOBILE.exists():
    raise SystemExit('Falta el ZIP original o el script móvil T05.')
if ROOT.exists():
    shutil.rmtree(ROOT)
with zipfile.ZipFile(ARCHIVE) as archive:
    archive.extractall(BASE)

app_path = ROOT / 'app.py'
app = app_path.read_text(encoding='utf-8')
anchor = "@app.route('/api/concesiones')\ndef get_concesiones():"
endpoint = '''@app.route('/api/lineas/<nombre_linea>/<direccion>')
def api_paradas_direccion_t05(nombre_linea, direccion):
    """Paradas y trazado en orden GTFS para ida o vuelta de las tres líneas T05."""
    nombre = str(nombre_linea or '').upper()
    sentido = str(direccion or '').lower()
    if nombre not in {'T05-01', 'T05-20', 'T05-50'} or sentido not in {'ida', 'vuelta'}:
        return jsonify({"error": "Línea o sentido no reconocido", "stops": []}), 404
    dataset = obtener_dataset_gtfs('T05')
    mapa = dataset['map']
    ruta_id = next((rid for rid, info in mapa.get('routes', {}).items()
                    if str(info.get('short_name', '')).upper() == nombre), None)
    if not ruta_id:
        return jsonify({"error": "No hay datos GTFS para esta línea", "stops": []}), 404
    direction_id = '0' if sentido == 'ida' else '1'
    viajes = {}
    for row in dataset['schedule'].get('stop_times', []):
        if str(row.get('route_id')) == str(ruta_id) and str(row.get('direction_id', '0')) == direction_id:
            viajes.setdefault(str(row.get('trip_id')), []).append(row)
    if not viajes:
        return jsonify({"error": "No hay viajes publicados para este sentido", "stops": []}), 404
    viaje = min(viajes.values(), key=lambda rows: min(str(x.get('departure_time') or '99:99:99') for x in rows))
    viaje.sort(key=lambda row: int(row.get('stop_sequence') or 0))
    paradas_mapa = {}
    for item in mapa.get('stops', {}).get(nombre, []):
        ids = item.get('stop_ids') or [item.get('id') or item.get('stop_id') or '']
        for stop_id in ids:
            if stop_id:
                paradas_mapa[str(stop_id)] = dict(item)
    stops, incluidos = [], set()
    for row in viaje:
        stop_id = str(row.get('stop_id') or '')
        stop = dict(paradas_mapa.get(stop_id, {'id': stop_id, 'name': row.get('stop_name') or 'Parada', 'lat': None, 'lon': None}))
        marker_id = str(stop.get('id') or stop_id)
        if marker_id in incluidos:
            continue
        incluidos.add(marker_id)
        stop['id'] = marker_id
        stop['concesion'] = 'T05'
        stop['lineas'] = sorted(set((stop.get('lineas') or []) + [nombre]))
        stop['stop_ids'] = stop.get('stop_ids') or [stop_id]
        stops.append(stop)
    rutas = mapa.get('routes', {}).get(ruta_id, {})
    shapes = rutas.get('shapes', [])
    shape_id = shapes[0 if sentido == 'ida' else 1] if len(shapes) > (0 if sentido == 'ida' else 1) else None
    shape = mapa.get('shapes', {}).get(shape_id, []) if shape_id else []
    return jsonify({'linea': nombre, 'sentido': sentido, 'origen': stops[0]['name'] if stops else '',
                    'destino': stops[-1]['name'] if stops else '', 'shape': shape, 'stops': stops})


'''
if 'def api_paradas_direccion_t05(' not in app:
    if anchor not in app:
        raise SystemExit('No se encontró el punto de inserción de la API de líneas T05.')
    app = app.replace(anchor, endpoint + anchor, 1)
app_path.write_text(app, encoding='utf-8')

static_dir = ROOT / 'static'
static_dir.mkdir(exist_ok=True)
shutil.copy2(MOBILE, static_dir / 't05-mobile.js')

template_path = ROOT / 'templates' / 'index.html'
html = template_path.read_text(encoding='utf-8')
html = html.replace('<title>Seguimiento de Autobuses - Tiempo Real</title>', '<title>TPA Aragón · T05</title>', 1)
# Permite que el mismo cargador de llegadas oficial/GTFS-RT filtre por línea.
html = html.replace(
    "async function cargarLlegadasParada(stopId, popup, fecha = fechaLocalISO(), stopIds = null) {",
    "async function cargarLlegadasParada(stopId, popup, fecha = fechaLocalISO(), stopIds = null, lineaFiltro = undefined) {", 1)
html = html.replace(
    """      if (!contenedor) return;

      // Solo la consulta del día actual puede mezclar predicciones GTFS-RT.""",
    """      if (!contenedor) return;
      if (lineaFiltro !== undefined) popup._lineaFiltroActiva = lineaFiltro;
      const filtroLineaActiva = popup._lineaFiltroActiva || '';

      // Solo la consulta del día actual puede mezclar predicciones GTFS-RT.""", 1)
html = html.replace(
    """        elementos.sort((a, b) => Number(a.timestampMostrado || 0) - Number(b.timestampMostrado || 0));

        if (!elementos.length)""",
    """        elementos.sort((a, b) => Number(a.timestampMostrado || 0) - Number(b.timestampMostrado || 0));
        if (filtroLineaActiva) {
          const filtrados = elementos.filter(item => String(item.linea || '').trim().toUpperCase() === String(filtroLineaActiva).trim().toUpperCase());
          elementos.splice(0, elementos.length, ...filtrados);
        }
        if (!elementos.length && filtroLineaActiva) {
          contenedor.innerHTML = '<div class="stop-arrival-state">No hay salidas para ' + escaparHTML(filtroLineaActiva) + ' en la fecha seleccionada.</div>';
          return;
        }

        if (!elementos.length)""", 1)
# Los marcadores no abren el popup pequeño nativo: abren el panel fijo móvil.
marker_anchor = '          marcador.addTo(capasParadas);'
marker_patch = '''          marcador._t05StopData = parada;
          marcador.unbindPopup();
          marcador.on('click', eventoMarcador => {
            if (eventoMarcador.originalEvent) L.DomEvent.stop(eventoMarcador.originalEvent);
            window.T05App?.openStop(parada);
          });
          marcador.addTo(capasParadas);'''
if 'marcador._t05StopData = parada;' not in html:
    if marker_anchor not in html:
        raise SystemExit('No se encontró el punto donde añadir el evento táctil del marcador.')
    html = html.replace(marker_anchor, marker_patch, 1)
# El mapa inicial encuadra todas las paradas en T05 aunque exista feed RT.
html = html.replace('if (!configuracionConcesionActiva?.funciones?.tiempo_real && primeraCarga) {', 'if (primeraCarga) {', 1)
html = html.replace('map.fitBounds(grupoParadas.getBounds(), { padding: [35, 35], maxZoom: 14 });',
                    'map.fitBounds(grupoParadas.getBounds(), { padding: [38, 38], maxZoom: 10 });', 1)
script = '  <script src="{{ url_for(\'static\', filename=\'t05-mobile.js\') }}"></script>\n'
if "filename='t05-mobile.js'" not in html:
    html = html.replace('</body>', script + '</body>', 1)
if "filename='t05-mobile.js'" not in html or 'marcador._t05StopData = parada;' not in html:
    raise SystemExit('No se aplicó toda la integración de la interfaz T05.')
template_path.write_text(html, encoding='utf-8')
print('T05 lista: mapa de paradas, líneas, ida/vuelta, recorrido y ficha móvil de paradas.')
