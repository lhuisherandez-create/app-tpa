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

endpoint = "@app.route('/api/t05-linea/<nombre_linea>/<direccion>')\ndef api_paradas_direccion_t05(nombre_linea, direccion):\n    \"\"\"Expone el catálogo de paradas de T05 en ambos sentidos, siempre como JSON.\"\"\"\n    nombre = str(nombre_linea or '').strip().upper()\n    sentido = str(direccion or '').strip().lower()\n    permitidas = {'T05-01', 'T05-20', 'T05-50'}\n\n    def normalizar(valor):\n        return ''.join(c for c in str(valor or '').upper() if c.isalnum())\n\n    try:\n        if nombre not in permitidas or sentido not in {'ida', 'vuelta'}:\n            return jsonify({'error': 'Línea o sentido no reconocido', 'stops': []}), 404\n\n        dataset = obtener_dataset_gtfs('T05')\n        if not isinstance(dataset, dict):\n            raise TypeError('El conjunto T05 no está disponible o tiene un formato inesperado')\n        mapa = dataset.get('map') or {}\n        if not isinstance(mapa, dict):\n            raise TypeError('El catálogo de paradas no tiene el formato esperado')\n        catalogo = mapa.get('stops') or {}\n\n        raw = None\n        if isinstance(catalogo, dict):\n            for clave, valor in catalogo.items():\n                if normalizar(clave) == normalizar(nombre):\n                    raw = valor\n                    break\n        elif isinstance(catalogo, (list, tuple)):\n            raw = [item for item in catalogo if isinstance(item, dict) and\n                   normalizar(item.get('linea') or item.get('route_short_name') or item.get('line_code')) == normalizar(nombre)]\n\n        if isinstance(raw, dict):\n            if any(k in raw for k in ('id', 'stop_id', 'stop_ids', 'name', 'stop_name')):\n                paradas = [raw]\n            else:\n                paradas = [item for item in raw.values() if isinstance(item, dict)]\n        elif isinstance(raw, (list, tuple)):\n            paradas = [item for item in raw if isinstance(item, dict)]\n        else:\n            paradas = []\n\n        resultado = []\n        for indice, original in enumerate(paradas):\n            parada = dict(original)\n            refs = parada.get('stop_ids') or parada.get('stop_id') or parada.get('id')\n            if refs is None:\n                refs = []\n            elif not isinstance(refs, (list, tuple)):\n                refs = [refs]\n            refs = [str(ref) for ref in refs if ref not in (None, '')]\n            identificador = str(parada.get('id') or parada.get('stop_id') or (refs[0] if refs else indice))\n            if not parada.get('name'):\n                parada['name'] = parada.get('stop_name') or parada.get('nombre') or 'Parada'\n            parada.update({\n                'id': identificador,\n                'stop_ids': refs or [identificador],\n                'lineas': sorted(set((parada.get('lineas') or []) + [nombre])),\n                'concesion': 'T05',\n            })\n            resultado.append(parada)\n\n        if sentido == 'vuelta':\n            resultado.reverse()\n\n        if not resultado:\n            return jsonify({\n                'error': 'El catálogo T05 no contiene paradas para ' + nombre,\n                'linea': nombre, 'sentido': sentido, 'stops': [],\n                'catalogo_tipo': type(catalogo).__name__,\n                'claves_catalogo': list(catalogo.keys()) if isinstance(catalogo, dict) else [],\n            })\n\n        shape = []\n        for parada in resultado:\n            try:\n                lat = parada.get('lat') if parada.get('lat') is not None else parada.get('latitude')\n                lon = parada.get('lon')\n                if lon is None:\n                    lon = parada.get('lng') if parada.get('lng') is not None else parada.get('longitude')\n                lat, lon = float(lat), float(lon)\n                if -90 <= lat <= 90 and -180 <= lon <= 180:\n                    shape.append([lat, lon])\n            except (TypeError, ValueError):\n                continue\n\n        return jsonify({\n            'linea': nombre, 'sentido': sentido,\n            'origen': resultado[0].get('name') or '',\n            'destino': resultado[-1].get('name') or '',\n            'shape': shape, 'stops': resultado,\n        })\n    except Exception as exc:\n        app.logger.exception('Error preparando recorrido T05 %s %s', nombre, sentido)\n        # Se devuelve JSON HTTP 200 para que el cliente pueda enseñar el motivo\n        # sin sustituirlo por la página HTML genérica de error de Flask.\n        return jsonify({\n            'error': 'No se pudo preparar el recorrido: ' + str(exc),\n            'linea': nombre, 'sentido': sentido, 'stops': [],\n        }), 200"
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
script_tag = """  <script src="{{ url_for('static', filename='t05-mobile.js') }}?v=11"></script>
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
