from __future__ import annotations

from pathlib import Path
import shutil
import zipfile

ARCHIVE = Path('mapa-tpa-main (1).zip')
ROOT = Path('mapa-tpa-main')

if not ARCHIVE.exists():
    raise SystemExit(f'No se encuentra el proyecto original: {ARCHIVE}')

# Cada despliegue parte de una extracción limpia y reproducible del ZIP.
if ROOT.exists():
    shutil.rmtree(ROOT)
with zipfile.ZipFile(ARCHIVE) as archive:
    archive.extractall('.')

app_path = ROOT / 'app.py'
app = app_path.read_text(encoding='utf-8')

# API que conserva el orden GTFS de las paradas de cada ruta T05.
route_anchor = "@app.route('/api/concesiones')\ndef get_concesiones():"
route_endpoint = '''@app.route('/api/lineas/<concesion>/<nombre_linea>')
def get_paradas_linea_gtfs(concesion, nombre_linea):
    """Devuelve las paradas GTFS en el orden oficial de una línea concreta."""
    codigo = str(concesion or '').upper()
    nombre = str(nombre_linea or '').upper()
    if codigo != 'T05' or nombre not in {'T05-01', 'T05-20', 'T05-50'}:
        return jsonify({"error": "Línea no reconocida", "stops": []}), 404

    dataset = obtener_dataset_gtfs(codigo)
    mapa = dataset['map']
    ruta = next((
        info for info in mapa.get('routes', {}).values()
        if str(info.get('short_name', '')).upper() == nombre
    ), {})
    # Ordenar por stop_sequence del primer viaje programado de la ruta.
    # Los marcadores siguen usando el mismo stop_id y las coordenadas corregidas del mapa.
    paradas_mapa = {
        str(item.get('id') or item.get('stop_id') or ''): dict(item)
        for item in mapa.get('stops', {}).get(nombre, [])
    }
    horarios = dataset['schedule'].get('stop_times', [])
    horarios_ruta = [item for item in horarios if str(item.get('route_id')) == str(next(
        (route_id for route_id, info in mapa.get('routes', {}).items()
         if str(info.get('short_name', '')).upper() == nombre), ''
    ))]
    viajes = {}
    for item in horarios_ruta:
        viajes.setdefault(str(item.get('trip_id')), []).append(item)

    paradas = []
    if viajes:
        primer_viaje = min(
            viajes.values(),
            key=lambda items: min(str(item.get('departure_time', '99:99:99')) for item in items)
        )
        primer_viaje.sort(key=lambda item: int(item.get('stop_sequence', 0)))
        for paso in primer_viaje:
            stop_id = str(paso.get('stop_id') or '')
            parada = paradas_mapa.get(stop_id, {
                'id': stop_id,
                'name': paso.get('stop_name', 'Parada'),
            })
            parada['concesion'] = codigo
            parada['lineas'] = [nombre]
            paradas.append(parada)
    else:
        for parada_original in mapa.get('stops', {}).get(nombre, []):
            parada = dict(parada_original)
            parada['concesion'] = codigo
            parada['lineas'] = [nombre]
            paradas.append(parada)

    return jsonify({
        "concesion": codigo,
        "linea": nombre,
        "destino": ruta.get('long_name', ''),
        "stops": paradas,
        "funciones": {
            "paradas": dataset['has_map'],
            "horarios": dataset['has_schedules'],
            "tiempo_real": dataset['has_realtime'],
        }
    })


'''
if "def get_paradas_linea_gtfs(" not in app:
    if route_anchor not in app:
        raise SystemExit('No se encontró el punto de inserción para la API de líneas.')
    app = app.replace(route_anchor, route_endpoint + route_anchor, 1)
app_path.write_text(app, encoding='utf-8')

template_path = ROOT / 'templates' / 'index.html'
html = template_path.read_text(encoding='utf-8')
html = html.replace(
    '<title>Seguimiento de Autobuses - Tiempo Real</title>',
    '<title>TPA Aragón · Línea T05</title>', 1
)

# Cabecera neutra y navegación móvil, sin marca de operador.
if 'id="tpa-topbar"' not in html:
    shell = '''
  <header id="tpa-topbar" class="tpa-topbar">
    <div class="tpa-title">TPA <span>ARAGÓN</span></div>
    <div class="tpa-subtitle">Transporte público · Concesión T05</div>
  </header>
  <nav class="app-bottom-nav" aria-label="Navegación principal">
    <button class="app-tab active" type="button" data-tab="inicio" onclick="navegarPestana('inicio')">
      <i class="fa-solid fa-house"></i><span>Inicio</span>
    </button>
    <button class="app-tab" type="button" data-tab="lineas" onclick="navegarPestana('lineas')">
      <i class="fa-solid fa-route"></i><span>Líneas</span>
    </button>
    <button class="app-tab" type="button" data-tab="favoritos" onclick="navegarPestana('favoritos')">
      <i class="fa-regular fa-star"></i><span>Favoritos</span>
    </button>
    <button class="app-tab" type="button" data-tab="mas" onclick="navegarPestana('mas')">
      <i class="fa-solid fa-ellipsis"></i><span>Más</span>
    </button>
  </nav>
  <section id="lineas-panel" class="lines-screen" hidden>
    <div class="lines-screen-inner">
      <div id="lineas-index">
        <div class="screen-heading"><div><h1>Líneas</h1><p>Concesión T05 · Rutas disponibles</p></div><span class="t05-pill">T05</span></div>
        <div class="route-cards">
          <button class="route-card" type="button" data-route-code="T05-01">
            <span class="route-color" style="background:#281173"></span><span class="route-copy"><strong>T05-01</strong><small>Fraga – Zaragoza por pueblos</small></span><i class="fa-solid fa-chevron-right"></i>
          </button>
          <button class="route-card" type="button" data-route-code="T05-20">
            <span class="route-color" style="background:#2FEC97"></span><span class="route-copy"><strong>T05-20</strong><small>Castejón de Monegros – Zaragoza por pueblos</small></span><i class="fa-solid fa-chevron-right"></i>
          </button>
          <button class="route-card" type="button" data-route-code="T05-50">
            <span class="route-color" style="background:#5310D7"></span><span class="route-copy"><strong>T05-50</strong><small>Valfarta – Bujaraloz</small></span><i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
      <div id="linea-stops-view" hidden>
        <button type="button" id="volver-a-lineas" class="back-to-lines"><i class="fa-solid fa-arrow-left"></i> Todas las líneas</button>
        <div class="screen-heading route-detail-heading"><div><h1 id="route-stops-title">T05-01</h1><p id="route-stops-subtitle">Paradas de la línea</p></div><span class="t05-pill">T05</span></div>
        <div id="route-stops-list" class="route-stops-list"><div class="route-loading">Cargando paradas…</div></div>
      </div>
    </div>
  </section>
'''
    html = html.replace('<body>', '<body>\n' + shell, 1)

# El selector de concesiones anterior deja de ser una pantalla de usuario.
if 'id="pantalla-inicio"' in html:
    html = html.replace(
        '<div id="pantalla-inicio">',
        '<div id="pantalla-inicio" aria-hidden="true">', 1
    )

# La ficha se abre igual desde los marcadores del mapa o desde la lista de una línea.
old_popup = '''            '<div class="stop-popup">' +
              '<div class="stop-popup-top">' +
                '<b class="stop-popup-title">' + escaparHTML(parada.name) + '</b>' +
                '<button type="button" class="stop-favorite-button"><i class="fa-regular fa-star"></i> Guardar</button>' +
              '</div>' +
              '<span class="stop-popup-label">Líneas que paran aquí</span>' +
              '<div class="stop-line-list">' +
                (insigniasLineas || '<span class="stop-arrival-state">Sin líneas identificadas</span>') +
              '</div>' +
              '<div class="stop-arrivals">' +
                '<span class="stop-popup-label">Próximas salidas</span>' +
                (configuracionConcesionActiva?.funciones?.horarios
                  ? '<input type="date" class="stop-date-input" aria-label="Fecha de las salidas">' : '') +
                '<div class="llegadas-parada stop-arrival-state">Consultando información de servicio...</div>' +
                '<div class="stop-schedule-note">' +
                  (configuracionConcesionActiva?.funciones?.tiempo_real
                    ? '“En vivo” utiliza predicciones GTFS-RT; “Programado” corresponde al horario oficial.'
                    : 'La información mostrada procede del horario oficial GTFS.') +
                '</div>' +
              '</div>' +
            '</div>'''
new_popup = '''            '<div class="stop-popup">' +
              '<div class="stop-mini-map" id="stop-mini-map-' + escaparHTML(String(parada.id || '').replace(/[^a-zA-Z0-9_-]/g, '')) + '" aria-label="Mapa de ubicación de la parada"></div>' +
              '<div class="stop-popup-top">' +
                '<b class="stop-popup-title">' + escaparHTML(parada.name) + '</b>' +
                '<button type="button" class="stop-favorite-button" aria-label="Guardar parada"><i class="fa-regular fa-star"></i></button>' +
              '</div>' +
              '<section class="stop-line-selector">' +
                '<span class="stop-popup-label">Líneas que paran aquí</span>' +
                '<div class="stop-line-list">' +
                  (insigniasLineas || '<span class="stop-arrival-state">Sin líneas identificadas</span>') +
                '</div>' +
              '</section>' +
              '<section class="stop-arrivals">' +
                '<div class="stop-arrivals-heading">' +
                  '<span class="stop-popup-label">Próximas llegadas</span>' +
                  '<div class="stop-day-tabs" role="tablist" aria-label="Día de consulta">' +
                    '<button type="button" class="stop-day-tab active" data-stop-day="0">Hoy</button>' +
                    '<button type="button" class="stop-day-tab" data-stop-day="1">Mañana</button>' +
                  '</div>' +
                '</div>' +
                (configuracionConcesionActiva?.funciones?.horarios
                  ? '<input type="date" class="stop-date-input" aria-label="Fecha de las salidas">' : '') +
                '<div class="llegadas-parada stop-arrival-state">Consultando información de servicio...</div>' +
                '<div class="stop-schedule-note">' +
                  (configuracionConcesionActiva?.funciones?.tiempo_real
                    ? 'En vivo = predicción del autobús · Programado = horario oficial.'
                    : 'Llegadas según el horario oficial GTFS.') +
                '</div>' +
              '</section>' +
            '</div>'''
if old_popup in html:
    html = html.replace(old_popup, new_popup, 1)

# Convierte las etiquetas de línea en selectores que filtran las llegadas de esta parada.
old_badges = '''          const insigniasLineas = lineasParada.map(nombre => {
            const color = coloresLineas[nombre] || '#475569';
            return '<span class="stop-line-badge" style="background:' + color + ';">' +
              escaparHTML(nombre) + '</span>';
          }).join('');'''
new_badges = '''          const insigniasLineas = ['__ALL__', ...lineasParada].map(nombre => {
            const todas = nombre === '__ALL__';
            const etiqueta = todas ? 'Todas' : nombre;
            const color = todas ? '#59616b' : (coloresLineas[nombre] || '#475569');
            return '<button type="button" class="stop-line-badge stop-line-filter' +
              (todas ? ' active' : '') + '" data-linea-filtro="' +
              escaparHTML(todas ? '__ALL__' : nombre) + '" style="--line-color:' + color + ';">' +
              escaparHTML(etiqueta) + '</button>';
          }).join('');'''
if old_badges in html:
    html = html.replace(old_badges, new_badges, 1)

old_date = '''            if (selectorFecha) {
              selectorFecha.min = hoy;
              selectorFecha.removeAttribute('max');
              selectorFecha.value = hoy;
              selectorFecha.addEventListener('change', () => {
                cargarLlegadasParada(parada.id, evento.popup, selectorFecha.value, parada.stop_ids);
              });
            }
'''
new_date = '''            if (selectorFecha) {
              selectorFecha.min = hoy;
              selectorFecha.removeAttribute('max');
              selectorFecha.value = hoy;
              selectorFecha.addEventListener('change', () => {
                cargarLlegadasParada(parada.id, evento.popup, selectorFecha.value, parada.stop_ids);
              });
              elemento?.querySelectorAll('[data-stop-day]').forEach(tab => {
                tab.addEventListener('click', () => {
                  elemento.querySelectorAll('[data-stop-day]').forEach(item => item.classList.toggle('active', item === tab));
                  selectorFecha.value = desplazarFechaISO(hoy, Number(tab.dataset.stopDay || 0));
                  selectorFecha.dispatchEvent(new Event('change', { bubbles: true }));
                });
              });
            }
'''
if old_date in html:
    html = html.replace(old_date, new_date, 1)

# Ficha fija inferior: evita el autopan de Leaflet y usa marcadores T05 color vino.
html = html.replace(
"""            {
              maxWidth: window.matchMedia('(max-width: 640px)').matches""",
"""            {
              autoPan: false,
              maxWidth: window.matchMedia('(max-width: 640px)').matches""", 1
)
html = html.replace("fillColor: '#334155', fillOpacity: 1", "fillColor: '#6d1838', fillOpacity: 1", 1)

# El primer encuadre siempre muestra el conjunto de paradas T05, no solo Zaragoza.
old_fit = '''        if (!configuracionConcesionActiva?.funciones?.tiempo_real && primeraCarga) {
          const marcadores = Object.values(marcadoresParadas);
          if (marcadores.length === 1) {
            map.setView(marcadores[0].getLatLng(), 14);
          } else if (marcadores.length > 1) {
            const grupoParadas = L.featureGroup(marcadores);
            map.fitBounds(grupoParadas.getBounds(), { padding: [35, 35], maxZoom: 14 });
          }
          primeraCarga = false;
        }
'''
new_fit = '''        if (primeraCarga) {
          const marcadores = Object.values(marcadoresParadas);
          if (marcadores.length === 1) {
            map.setView(marcadores[0].getLatLng(), 14);
          } else if (marcadores.length > 1) {
            const grupoParadas = L.featureGroup(marcadores);
            map.fitBounds(grupoParadas.getBounds(), { padding: [38, 38], maxZoom: 10 });
          }
          primeraCarga = false;
        }
'''
if old_fit in html:
    html = html.replace(old_fit, new_fit, 1)

nav_script = r'''
    function navegarPestana(pestana) {
      if (map) map.closePopup();
      document.querySelectorAll('.app-tab').forEach(tab => {
        const activa = tab.dataset.tab === pestana;
        tab.classList.toggle('active', activa);
        tab.setAttribute('aria-current', activa ? 'page' : 'false');
      });
      const panelLineas = document.getElementById('lineas-panel');
      if (pestana === 'lineas') {
        panelLineas.hidden = false;
        document.getElementById('lineas-index').hidden = false;
        document.getElementById('linea-stops-view').hidden = true;
        document.body.classList.add('lines-open');
        return;
      }
      panelLineas.hidden = true;
      document.body.classList.remove('lines-open');
      if (pestana === 'inicio') {
        document.getElementById('panel-favoritos').hidden = true;
        if (!lineaActiva) iniciarMapa('T05');
        setTimeout(() => map?.invalidateSize(), 80);
      } else if (pestana === 'favoritos') {
        if (!lineaActiva) iniciarMapa('T05');
        document.getElementById('panel-favoritos').hidden = false;
        document.getElementById('panel-favoritos').scrollIntoView({behavior:'smooth', block:'nearest'});
      } else if (pestana === 'mas') {
        document.getElementById('panel-favoritos').hidden = true;
        alert('TPA Aragón · Concesión T05\nConsulta las líneas T05-01, T05-20 y T05-50.');
      }
    }

    async function abrirLineaT05(nombreLinea) {
      document.getElementById('lineas-index').hidden = true;
      document.getElementById('linea-stops-view').hidden = false;
      document.getElementById('route-stops-title').textContent = nombreLinea;
      const lista = document.getElementById('route-stops-list');
      lista.innerHTML = '<div class="route-loading"><i class="fa-solid fa-spinner fa-spin"></i> Cargando paradas…</div>';
      try {
        const response = await fetch('/api/lineas/T05/' + encodeURIComponent(nombreLinea), {cache:'no-store'});
        if (!response.ok) throw new Error('No se pudieron cargar las paradas de ' + nombreLinea);
        const data = await response.json();
        document.getElementById('route-stops-subtitle').textContent = data.destino || 'Paradas de la línea';
        const paradas = data.stops || [];
        if (!paradas.length) {
          lista.innerHTML = '<div class="route-loading">Esta línea no tiene paradas disponibles.</div>';
          return;
        }
        lista.innerHTML = paradas.map((parada, index) =>
          '<button type="button" class="route-stop-row" data-stop-id="' + escaparHTML(parada.id) + '">' +
            '<span class="route-stop-marker">' + (index + 1) + '</span>' +
            '<span class="route-stop-copy"><strong>' + escaparHTML(parada.name) + '</strong><small>' + escaparHTML(nombreLinea) + '</small></span>' +
            '<i class="fa-solid fa-chevron-right"></i>' +
          '</button>'
        ).join('');
      } catch (error) {
        lista.innerHTML = '<div class="route-loading route-error">' + escaparHTML(error.message) + '</div>';
      }
    }

    document.addEventListener('click', evento => {
      const linea = evento.target.closest('[data-route-code]');
      if (linea) {
        abrirLineaT05(linea.dataset.routeCode);
        return;
      }
      const stop = evento.target.closest('.route-stop-row[data-stop-id]');
      if (stop) {
        navegarPestana('inicio');
        seleccionarParada(stop.dataset.stopId, 'T05');
      }
    });
    document.getElementById('volver-a-lineas')?.addEventListener('click', () => {
      document.getElementById('linea-stops-view').hidden = true;
      document.getElementById('lineas-index').hidden = false;
    });

'''
if 'async function abrirLineaT05(' not in html:
    marker = '    cargarCatalogoConcesiones();'
    if marker not in html:
        raise SystemExit('No se encontró el arranque de catálogo en index.html')
    html = html.replace(marker, nav_script + '''    cargarCatalogoConcesiones().then(() => {
      iniciarMapa('T05');
      setTimeout(() => map?.invalidateSize(), 120);
    }).catch(error => {
      console.error('No se pudo iniciar T05:', error);
      iniciarMapa('T05');
    });''', 1)

css = r'''
    :root { --tpa-wine:#6d1838; --tpa-red:#a51f45; --tpa-paper:#f4f5f7; --tpa-ink:#20242a; }
    html, body { width:100%; height:100%; overflow:hidden; background:var(--tpa-paper); color:var(--tpa-ink); }
    .tpa-topbar { position:fixed; z-index:12000; top:0; left:0; right:0; height:58px; padding:0 16px; display:flex; flex-direction:column; justify-content:center; background:#fff; border-bottom:1px solid #e6e7ea; box-shadow:0 1px 4px rgba(20,25,35,.05); }
    .tpa-title { font-size:19px; line-height:21px; font-weight:800; letter-spacing:-.5px; color:#20242a; }
    .tpa-title span { margin-left:5px; font-size:10px; letter-spacing:1px; color:#777e88; vertical-align:2px; }
    .tpa-subtitle { margin-top:1px; font-size:9px; color:#7d838c; letter-spacing:.2px; }
    .app-bottom-nav { position:fixed; z-index:12000; left:0; right:0; bottom:0; height:58px; padding-bottom:env(safe-area-inset-bottom); display:flex; align-items:center; background:#fff; border-top:1px solid #e5e6e8; }
    .app-tab { flex:1; height:100%; border:0; background:transparent; color:#60656d; display:flex; flex-direction:column; justify-content:center; align-items:center; gap:3px; font-size:10px; }
    .app-tab i { font-size:17px; }.app-tab.active { color:var(--tpa-red); font-weight:800; }
    #pantalla-inicio { display:none !important; }
    #map { position:fixed !important; top:58px !important; bottom:58px !important; left:0 !important; width:100% !important; height:auto !important; z-index:1; }
    #header-card { position:fixed; top:66px; left:9px; right:9px; width:auto; max-width:none; margin:0; padding:0; border:0; border-radius:10px; background:transparent; box-shadow:none; z-index:1000; }
    #header-card .header-title, #header-card .info-grid, #header-card .footer-actions { display:none !important; }
    #header-card .map-tools { padding:7px; border-radius:10px; background:rgba(255,255,255,.96); border:1px solid #e5e7eb; box-shadow:0 2px 9px rgba(0,0,0,.12); backdrop-filter:blur(8px); }
    .stop-search-row { display:flex; gap:6px; }
    #buscador-paradas { flex:1; min-width:0; height:36px; border:1px solid #e4e6e9; border-radius:6px; background:#fff; color:#20242a; font-size:12px; padding:0 10px; }
    #buscador-paradas::placeholder { color:#90959d; }
    #btn-paradas-cercanas, #btn-mostrar-favoritos { height:36px; border:1px solid #e4e6e9; border-radius:6px; background:#fff; color:#4c5158; padding:0 10px; }
    #btn-mostrar-favoritos span:not(.favorite-count) { display:none; }
    .search-results { background:#fff; border:1px solid #e5e7eb; border-radius:7px; box-shadow:0 3px 10px rgba(0,0,0,.1); max-height:36vh; overflow:auto; }
    .search-result { background:#fff; color:#25282d; border-bottom:1px solid #eee; }
    #contenedor-filtros-lineas, .footer-actions { display:none !important; }
    .favorites-panel { background:#fff; color:#25282d; border:1px solid #e4e6e9; box-shadow:0 3px 12px rgba(0,0,0,.1); }
    .favorites-panel-heading { color:#25282d; }.favorites-note { color:#777e88; }
    .lines-screen { position:fixed; z-index:11000; top:58px; bottom:58px; left:0; right:0; overflow:auto; background:var(--tpa-paper); padding:12px 10px 18px; }
    .lines-screen[hidden], #lineas-index[hidden], #linea-stops-view[hidden] { display:none !important; }
    .lines-screen-inner { width:100%; max-width:620px; margin:0 auto; }
    .screen-heading { display:flex; align-items:center; justify-content:space-between; padding:8px 4px 14px; }
    .screen-heading h1 { font-size:19px; font-weight:800; color:#262a30; }
    .screen-heading p { margin-top:3px; font-size:11px; color:#747b84; }
    .t05-pill { color:var(--tpa-wine); background:#f2e8ed; border-radius:5px; padding:6px 9px; font-size:11px; font-weight:800; }
    .route-cards { display:flex; flex-direction:column; gap:1px; background:#e7e8eb; border:1px solid #e7e8eb; border-radius:8px; overflow:hidden; }
    .route-card { min-height:58px; display:flex; align-items:center; gap:12px; width:100%; text-align:left; border:0; background:#fff; padding:9px 12px; color:#25282d; }
    .route-card:active, .route-stop-row:active { background:#f8f1f4; }
    .route-color { width:5px; align-self:stretch; border-radius:3px; }
    .route-copy, .route-stop-copy { flex:1; min-width:0; display:flex; flex-direction:column; gap:3px; }
    .route-copy strong { font-size:12px; font-weight:800; }.route-copy small { font-size:11px; color:#737982; }
    .route-card > i { color:#9298a0; font-size:11px; }
    .back-to-lines { border:0; background:transparent; color:var(--tpa-wine); font-size:12px; font-weight:700; padding:8px 4px 12px; }
    .route-detail-heading { padding-top:2px; }
    .route-stops-list { overflow:hidden; border:1px solid #e7e8eb; border-radius:8px; background:#fff; }
    .route-stop-row { display:flex; align-items:center; gap:11px; width:100%; min-height:52px; padding:7px 11px; border:0; border-bottom:1px solid #eceef0; background:#fff; text-align:left; color:#25282d; }
    .route-stop-row:last-child { border-bottom:0; }
    .route-stop-marker { flex:0 0 23px; height:23px; border-radius:50%; display:grid; place-items:center; color:#fff; background:var(--tpa-wine); font-size:10px; font-weight:800; }
    .route-stop-copy strong { font-size:11px; font-weight:700; line-height:1.25; }.route-stop-copy small { font-size:9px; color:#9298a0; }
    .route-stop-row > i { color:#a0a5ad; font-size:10px; }
    .route-loading { padding:20px 12px; color:#7c838c; text-align:center; font-size:12px; }.route-error { color:#a51f45; }
    /* Ficha de parada con hoja inferior móvil: el mapa sigue visible arriba. */
    .leaflet-popup { z-index:11050 !important; }
    .leaflet-popup-content-wrapper { border-radius:14px 14px 0 0 !important; box-shadow:0 -3px 18px rgba(0,0,0,.17) !important; }
    .leaflet-popup-content { margin:0 !important; width:auto !important; min-width:0 !important; }
    .leaflet-popup-tip-container { display:none !important; }
    .leaflet-popup-close-button { z-index:3; top:8px !important; right:10px !important; color:#626873 !important; font-size:22px !important; }
    .stop-popup { min-width:0 !important; width:100%; color:#20242a; padding:7px 10px 10px; }
    .stop-day-tabs { display:flex; width:100%; border-bottom:1px solid #e9eaed; margin:0 0 9px; }
    .stop-day-tab { flex:1; border:0; border-bottom:2px solid transparent; background:#fff; color:#8b9098; height:32px; font-size:11px; font-weight:700; }
    .stop-day-tab.active { border-bottom-color:var(--tpa-wine); color:var(--tpa-wine); }
    .stop-popup-top { align-items:center !important; margin-bottom:8px; }
    .stop-popup-title { color:#25282d; font-size:14px !important; font-weight:800; }
    .stop-favorite-button { width:31px; height:30px; padding:0 !important; display:grid; place-items:center; color:#555b64 !important; border:1px solid #e5e6e9 !important; border-radius:6px !important; background:#fff !important; font-size:14px !important; }
    .stop-favorite-button.saved { color:#b08422 !important; background:#fffaf0 !important; }
    .stop-popup-label { color:#9298a0 !important; font-size:9px !important; letter-spacing:.04em !important; }
    .stop-line-list { gap:4px !important; margin-bottom:6px; }
    .stop-line-badge { border-radius:3px !important; padding:4px 6px !important; font-size:9px !important; }
    .stop-arrivals { margin-top:6px !important; }
    .stop-date-input { display:none !important; }
    .stop-schedule-group { padding:7px 0 !important; }
    .stop-schedule-heading { gap:8px; }
    .stop-schedule-line { font-size:10px !important; font-weight:800; }
    .stop-schedule-destination { font-size:10px !important; }
    .stop-schedule-times { gap:5px !important; }
    .stop-schedule-time { min-width:56px; padding:5px 7px !important; border-radius:4px !important; background:#f5f6f7 !important; }
    .stop-schedule-time strong { font-size:12px !important; color:#25282d !important; }
    .stop-schedule-time small { font-size:8px !important; }
    .stop-schedule-note { font-size:9px !important; color:#999fa7 !important; }
    @media (max-width:640px) {
      .leaflet-popup { position:fixed !important; left:0 !important; right:0 !important; top:auto !important; bottom:58px !important; width:100vw !important; margin:0 !important; transform:none !important; }
      .leaflet-popup-content-wrapper { max-height:60vh !important; overflow:hidden; }
      .leaflet-popup-content { max-height:60vh !important; overflow-y:auto; -webkit-overflow-scrolling:touch; }
      .stop-popup { padding:7px 12px calc(12px + env(safe-area-inset-bottom)); }
      .stop-arrivals { max-height:34vh; overflow-y:auto; }
    }
    @media (min-width:641px) { .leaflet-popup-content-wrapper { min-width:330px; max-width:390px; } }
'''

css += r'''
    /* Contenido de la ficha: mapa de situación, selector de línea y llegadas. */
    .stop-mini-map { width:100%; height:112px; overflow:hidden; border-radius:8px; margin:0 0 9px; background:#e9edf0; border:1px solid #e2e5e8; }
    .stop-mini-map .leaflet-control-attribution { font-size:7px; }
    .stop-mini-map-missing { display:grid; height:100%; place-items:center; color:#7b838d; font-size:10px; }
    .stop-popup-top { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:8px; }
    .stop-popup-title { flex:1; margin:0 !important; font-size:13px !important; line-height:1.25; }
    .stop-line-selector { margin:2px 0 9px; }
    .stop-line-selector .stop-popup-label { margin:0 0 5px; }
    .stop-line-list { display:flex; flex-wrap:wrap; gap:5px; }
    .stop-line-filter { appearance:none; cursor:pointer; border:1px solid #dfe3e7 !important; background:#fff !important; color:#525a64 !important; padding:5px 9px !important; border-radius:5px !important; font-size:10px !important; font-weight:800; }
    .stop-line-filter.active { border-color:var(--line-color) !important; background:var(--line-color) !important; color:#fff !important; }
    .stop-arrivals { border-top:1px solid #e7e9ec; margin-top:7px; padding-top:7px; }
    .stop-arrivals-heading { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:3px; }
    .stop-arrivals-heading .stop-popup-label { margin:0; }
    .stop-day-tabs { display:flex; gap:3px; border:0; margin:0; }
    .stop-day-tab { height:25px; padding:0 9px; border:1px solid #e1e4e8; border-radius:5px; background:#fff; color:#646c75; font-size:9px; font-weight:700; }
    .stop-day-tab.active { background:#f4e9ed; color:#6d1838; border-color:#d8bdc7; }
    @media(max-width:640px) {
      .leaflet-popup-content-wrapper { max-height:68vh !important; }
      .leaflet-popup-content { max-height:68vh !important; }
      .stop-mini-map { height:105px; }
      .stop-arrivals { max-height:31vh; }
    }
'''

if 'Ficha de parada con hoja inferior móvil' not in html:
    html = html.replace('</style>', css + '\n  </style>', 1)


# Permite filtrar las llegadas por la línea elegida sin volver a consultar otra parada.
html = html.replace(
    "async function cargarLlegadasParada(stopId, popup, fecha = fechaLocalISO(), stopIds = null) {",
    "async function cargarLlegadasParada(stopId, popup, fecha = fechaLocalISO(), stopIds = null, lineaFiltro = undefined) {", 1
)
html = html.replace(
"""      if (!contenedor) return;

      // Solo la consulta del día actual""",
"""      if (!contenedor) return;
      if (lineaFiltro !== undefined) popup._lineaFiltroActiva = lineaFiltro;
      const filtroLineaActiva = popup._lineaFiltroActiva || '';

      // Solo la consulta del día actual""", 1
)
html = html.replace(
"""        elementos.sort((a, b) => Number(a.timestampMostrado || 0) - Number(b.timestampMostrado || 0));

        if (!elementos.length)""",
"""        elementos.sort((a, b) => Number(a.timestampMostrado || 0) - Number(b.timestampMostrado || 0));
        if (filtroLineaActiva) {
          const filtrados = elementos.filter(item =>
            String(item.linea || '').trim().toUpperCase() === String(filtroLineaActiva).trim().toUpperCase()
          );
          elementos.splice(0, elementos.length, ...filtrados);
        }

        if (!elementos.length)""", 1
)

# El minimapa usa las coordenadas reales de la parada.
html = html.replace(
"""            const elemento = evento.popup.getElement();
            const selectorFecha = elemento?.querySelector('.stop-date-input');""",
"""            const elemento = evento.popup.getElement();
            const miniMapaElemento = elemento?.querySelector('.stop-mini-map');
            const latitudParada = Number(parada.lat);
            const longitudParada = Number(parada.lon);
            if (miniMapaElemento && Number.isFinite(latitudParada) && Number.isFinite(longitudParada)) {
              evento.popup._miniMapaParada?.remove();
              const miniMapa = L.map(miniMapaElemento, {
                zoomControl: false,
                attributionControl: true,
                dragging: false,
                scrollWheelZoom: false,
                doubleClickZoom: false,
                boxZoom: false,
                keyboard: false,
                tap: false
              }).setView([latitudParada, longitudParada], 15);
              L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap'
              }).addTo(miniMapa);
              L.circleMarker([latitudParada, longitudParada], {
                radius: 7, color: '#ffffff', weight: 2, fillColor: '#6d1838', fillOpacity: 1
              }).addTo(miniMapa);
              evento.popup._miniMapaParada = miniMapa;
              setTimeout(() => miniMapa.invalidateSize(false), 100);
            } else if (miniMapaElemento) {
              miniMapaElemento.innerHTML = '<span class="stop-mini-map-missing">Ubicación no disponible</span>';
            }
            const selectorFecha = elemento?.querySelector('.stop-date-input');""", 1
)

# Selector de línea: "Todas" o una ruta concreta T05.
html = html.replace(
"""            const botonFavorito = elemento?.querySelector('.stop-favorite-button');""",
"""            evento.popup._lineaFiltroActiva = '';
            const filtrosLinea = Array.from(elemento?.querySelectorAll('[data-linea-filtro]') || []);
            filtrosLinea.forEach(boton => {
              boton.addEventListener('click', (click) => {
                L.DomEvent.stop(click);
                const elegida = boton.dataset.lineaFiltro === '__ALL__' ? '' : boton.dataset.lineaFiltro;
                evento.popup._lineaFiltroActiva = elegida;
                filtrosLinea.forEach(filtro => filtro.classList.toggle(
                  'active',
                  (filtro.dataset.lineaFiltro === '__ALL__' && !elegida) || filtro.dataset.lineaFiltro === elegida
                ));
                cargarLlegadasParada(
                  parada.id, evento.popup, selectorFecha?.value || hoy, parada.stop_ids, elegida
                );
              });
            });

            const botonFavorito = elemento?.querySelector('.stop-favorite-button');""", 1
)

# Mantener filtro de línea durante la actualización automática.
html = html.replace(
    "                cargarLlegadasParada(parada.id, evento.popup, fechaActual, parada.stop_ids);",
    "                cargarLlegadasParada(parada.id, evento.popup, fechaActual, parada.stop_ids, evento.popup._lineaFiltroActiva || '');", 1
)

# Cerrar el minimapa auxiliar al cerrar la ficha para liberar la instancia Leaflet.
html = html.replace(
"""            if (eventoCierre.popup) {
              eventoCierre.popup._solicitudLlegadasParada =""",
"""            if (eventoCierre.popup) {
              eventoCierre.popup._miniMapaParada?.remove();
              eventoCierre.popup._miniMapaParada = null;
              eventoCierre.popup._solicitudLlegadasParada =""", 1
)

template_path.write_text(html, encoding='utf-8')
print('Configuración aplicada: T05 exclusiva, mapa inicial, tres líneas y ficha de paradas con horarios.')
