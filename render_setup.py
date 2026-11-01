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
    """Devuelve las paradas y el trazado de ida/vuelta de una línea T05 desde GTFS."""
    nombre = str(nombre_linea or '').upper()
    sentido = str(direccion or '').lower()
    lineas_t05 = {'T05-01', 'T05-20', 'T05-50'}
    if nombre not in lineas_t05 or sentido not in {'ida', 'vuelta'}:
        return jsonify({"error": "Línea o sentido no reconocido", "stops": []}), 404

    dataset = obtener_dataset_gtfs('T05')
    mapa = dataset['map']
    ruta_id = next((
        route_id for route_id, info in mapa.get('routes', {}).items()
        if str(info.get('short_name', '')).upper() == nombre
    ), None)
    if not ruta_id:
        return jsonify({"error": "No hay datos GTFS para esta línea", "stops": []}), 404

    # Indexar cada stop_id GTFS con el marcador agrupado que ya utiliza el mapa.
    marcadores_por_stop = {}
    lineas_por_stop = defaultdict(set)
    for linea_servicio, elementos in mapa.get('stops', {}).items():
        if linea_servicio not in lineas_t05:
            continue
        for elemento in elementos:
            ids_elemento = elemento.get('stop_ids') or [
                elemento.get('id') or elemento.get('stop_id') or ''
            ]
            for stop_id in ids_elemento:
                if stop_id:
                    lineas_por_stop[str(stop_id)].add(linea_servicio)
                    if linea_servicio == nombre:
                        marcadores_por_stop[str(stop_id)] = dict(elemento)

    # Agrupar los horarios por viaje y distinguir los dos sentidos publicados.
    viajes = defaultdict(list)
    for fila in dataset['schedule'].get('stop_times', []):
        if str(fila.get('route_id')) == str(ruta_id) and fila.get('trip_id') is not None:
            viajes[str(fila['trip_id'])].append(fila)

    viajes_ordenados = []
    for trip_id, filas in viajes.items():
        filas.sort(key=lambda row: int(row.get('stop_sequence') or 0))
        if not filas:
            continue
        direction_id = next((
            str(row.get('direction_id')) for row in filas
            if row.get('direction_id') not in (None, '')
        ), None)
        if direction_id is not None:
            clave_sentido = ('id', direction_id)
        else:
            clave_sentido = (
                'terminales',
                str(filas[0].get('stop_id') or ''),
                str(filas[-1].get('stop_id') or '')
            )
        salida = str(filas[0].get('departure_time') or filas[0].get('arrival_time') or '99:99:99')
        viajes_ordenados.append((clave_sentido, salida, filas))

    grupos = defaultdict(list)
    for clave_sentido, salida, filas in viajes_ordenados:
        grupos[clave_sentido].append((salida, filas))

    claves = list(grupos)
    if not claves:
        return jsonify({"error": "No hay viajes programados para esta línea", "stops": []}), 404

    if all(clave[0] == 'id' for clave in claves):
        claves.sort(key=lambda clave: (
            0, int(clave[1])
        ) if clave[1].isdigit() else (1, clave[1]))
    else:
        claves.sort(key=lambda clave: min(salida for salida, _ in grupos[clave]))

    indice = 0 if sentido == 'ida' else 1
    if indice >= len(claves):
        return jsonify({"error": "El GTFS no publica ese sentido para esta línea", "stops": []}), 404

    viajes_sentido = grupos[claves[indice]]
    _, viaje = min(viajes_sentido, key=lambda elemento: elemento[0])
    viaje = sorted(viaje, key=lambda row: int(row.get('stop_sequence') or 0))

    paradas, marcadores_incluidos, shape = [], set(), []
    for fila in viaje:
        stop_id = str(fila.get('stop_id') or '')
        base = marcadores_por_stop.get(stop_id, {
            'id': stop_id,
            'name': fila.get('stop_name') or 'Parada',
        })
        parada = dict(base)
        marcador_id = str(parada.get('id') or parada.get('stop_id') or stop_id)
        if not marcador_id or marcador_id in marcadores_incluidos:
            continue
        marcadores_incluidos.add(marcador_id)
        ids_marcador = parada.get('stop_ids') or [stop_id]
        lineas_servidas = set(parada.get('lineas') or [])
        for identificador in ids_marcador:
            lineas_servidas.update(lineas_por_stop.get(str(identificador), set()))
        parada.update({
            'id': marcador_id,
            'concesion': 'T05',
            'stop_ids': ids_marcador,
            'lineas': sorted(lineas_servidas),
        })
        paradas.append(parada)
        try:
            lat, lon = float(parada.get('lat')), float(parada.get('lon'))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                shape.append([lat, lon])
        except (TypeError, ValueError):
            pass

    if not paradas:
        return jsonify({"error": "No se han encontrado paradas para este sentido", "stops": []}), 404

    return jsonify({
        'linea': nombre,
        'sentido': sentido,
        'origen': paradas[0].get('name', ''),
        'destino': paradas[-1].get('name', ''),
        'shape': shape,
        'stops': paradas,
    })


'''
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
script_tag = """  <script src="{{ url_for('static', filename='t05-mobile.js') }}?v=6"></script>
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
