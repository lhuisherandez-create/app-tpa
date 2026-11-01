from pathlib import Path
import zipfile

ARCHIVE = Path("mapa-tpa-main (1).zip")
ROOT = Path("mapa-tpa-main")
if not ARCHIVE.exists():
    raise SystemExit(f"No se encuentra {ARCHIVE}")

with zipfile.ZipFile(ARCHIVE) as z:
    z.extractall(".")

page = ROOT / "templates" / "index.html"
html = page.read_text(encoding="utf-8")

if "app-topbar" not in html:
    html = html.replace("<body>", """<body>
  <header class="app-topbar" aria-label="Cabecera">
    <div class="brand-lockup">
      <span class="brand-name">Jiménez</span><span class="brand-divider"></span>
      <span class="brand-gov">GOBIERNO<br><b>DE ARAGÓN</b></span>
    </div>
    <span class="topbar-alert" aria-label="Avisos"><i class="fa-regular fa-bell"></i></span>
  </header>
  <nav class="app-bottom-nav" aria-label="Navegación principal">
    <button class="app-tab active" type="button" data-tab="inicio" onclick="navegarPestana('inicio')"><i class="fa-solid fa-house"></i><span>Inicio</span></button>
    <button class="app-tab" type="button" data-tab="lineas" onclick="navegarPestana('lineas')"><i class="fa-solid fa-route"></i><span>Líneas</span></button>
    <button class="app-tab" type="button" data-tab="favoritos" onclick="navegarPestana('favoritos')"><i class="fa-regular fa-star"></i><span>Favoritos</span></button>
    <button class="app-tab" type="button" data-tab="mas" onclick="navegarPestana('mas')"><i class="fa-solid fa-ellipsis"></i><span>Más</span></button>
  </nav>""", 1)

    html = html.replace('''<div class="lista-botones">''', '''<label class="line-search-wrap">
        <input id="buscador-concesiones" type="search" placeholder="Buscar línea..." aria-label="Buscar línea">
        <i class="fa-solid fa-magnifying-glass"></i>
      </label>
      <div class="lista-botones">''', 1)

    css = """
    :root { --app-red:#b51235; --app-ink:#20242a; }
    html,body { background:#f4f5f7; color:var(--app-ink); }
    .app-topbar { position:fixed;z-index:12000;top:0;left:0;right:0;height:58px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;background:#fff;border-bottom:1px solid #e7e8eb;box-shadow:0 1px 5px #14192310; }
    .brand-lockup { display:flex;align-items:center;gap:9px;color:#222; }
    .brand-name { font-family:Georgia,serif;font-size:19px;font-weight:900;letter-spacing:-1px; }
    .brand-divider { width:1px;height:25px;background:#d5d7db; }
    .brand-gov { font-size:8px;line-height:1.15;font-weight:700;letter-spacing:.2px; }
    .brand-gov:before { content:"";display:inline-block;width:9px;height:14px;margin-right:4px;vertical-align:middle;background:linear-gradient(90deg,#e9b21b 0 48%,#bd1938 48%); }
    .topbar-alert { color:#20242a;font-size:17px;padding:8px; }
    .app-bottom-nav { position:fixed;z-index:12000;bottom:0;left:0;right:0;height:58px;padding-bottom:env(safe-area-inset-bottom);display:flex;justify-content:space-around;align-items:center;background:#fff;border-top:1px solid #e4e5e8; }
    .app-tab { flex:1;height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:3px;border:0;background:transparent;color:#4c5057;font-size:10px; }
    .app-tab i { font-size:17px; }.app-tab.active { color:var(--app-red);font-weight:800; }
    #pantalla-inicio { top:58px;bottom:58px;left:0;width:100%;height:auto;overflow:hidden;display:flex;justify-content:flex-start;align-items:stretch;padding:0;background:#f4f5f7;color:#20242a;z-index:9999; }
    .menu-card { width:100%;max-width:none;height:100%;overflow:hidden;border:0;border-radius:0;padding:14px 9px 8px;background:#f4f5f7;box-shadow:none;color:#20242a;text-align:left;backdrop-filter:none; }
    .menu-header { display:none; }
    .line-search-wrap { position:relative;display:block;margin:0 0 8px; }
    .line-search-wrap input { width:100%;height:38px;border:1px solid #e6e7e9;border-radius:5px;background:#fff;padding:0 38px 0 12px;color:#24272d;font-size:13px;outline:none; }
    .line-search-wrap i { position:absolute;right:13px;top:11px;color:#59616a; }
    .lista-botones { max-height:calc(100% - 48px);overflow-y:auto;gap:0;padding:0; }
    .btn-menu { min-height:43px;width:100%;border-radius:0;box-shadow:none;padding:5px 10px;gap:11px;background:#fff;color:#25282d;border-bottom:1px solid #e8e9eb;border-left:5px solid var(--bus-color,#b51235);transition:none; }
    .btn-menu:hover:not(.btn-deshabilitado),.btn-menu:active:not(.btn-deshabilitado) { transform:none;box-shadow:none;background:#fafafa; }
    .btn-title { min-width:44px;text-align:left;padding:0;background:transparent;border-radius:0;color:var(--bus-color,#b51235);font-size:11px;letter-spacing:.1px; }
    .btn-subtitle { color:#25282d;font-size:11px;font-weight:700;line-height:1.25; }
    .btn-deshabilitado { background:#fff;border:0;border-left:5px solid #d7d9dd;border-bottom:1px solid #e8e9eb; }
    .btn-deshabilitado .btn-title { color:#777;background:transparent; }.btn-deshabilitado .btn-subtitle { color:#555b63; }
    #map { position:fixed;inset:58px 0 58px;width:100%;height:auto;z-index:1; }
    .header-card { top:68px;left:10px;right:10px;max-width:520px;padding:12px;color:#24272d;background:#fffffff7;border:1px solid #e4e5e8;border-radius:10px;box-shadow:0 3px 14px #0002;backdrop-filter:blur(10px); }
    .badge-tag { background:var(--app-red);border-radius:5px;box-shadow:none;font-size:13px;padding:7px 10px; }
    .badge-text h1 { color:#25282d;font-size:13px; }.badge-text p { color:#747982; }
    .live-status { background:#f4f5f6;color:#555;border:1px solid #e5e6e8; }
    .info-grid { background:#f6f7f8; }.info-value { color:#343a42; }
    .footer-actions { gap:6px; }.btn-action { background:var(--app-red); }
    .btn-menu-back,.btn-layer { background:#f0f1f3;color:#333;border:1px solid #ddd; }
    .btn-layer.active { background:#fceef1;color:var(--app-red);border-color:#e9c1ca; }
    .panel-show-button { top:68px;background:#fff;color:#333;border:1px solid #ddd; }
    @media(max-width:640px) { .header-card{top:66px}.menu-card{padding-left:8px;padding-right:8px}.footer-actions .btn-action{min-height:34px} }
    @media(min-width:700px) { #pantalla-inicio{align-items:center}.menu-card{max-width:520px;height:min(85vh,850px);border-radius:12px} }
"""
    if "</style>" in html:
        html = html.replace("</style>", css + "\n  </style>", 1)

    js = """
    function navegarPestana(pestana) {
      document.querySelectorAll('.app-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === pestana));
      if (pestana === 'inicio' || pestana === 'lineas') {
        if (typeof lineaActiva !== 'undefined' && lineaActiva && typeof volverAlMenu === 'function') volverAlMenu();
        const pantalla = document.getElementById('pantalla-inicio');
        if (pantalla) pantalla.style.display = 'flex';
        if (pestana === 'lineas') document.getElementById('buscador-concesiones')?.focus();
      } else if (pestana === 'favoritos') {
        const fav = document.getElementById('panel-favoritos') || document.getElementById('lista-favoritos');
        if (fav) fav.scrollIntoView({behavior:'smooth',block:'center'});
        else alert('Selecciona una línea y pulsa la estrella para guardarla en Favoritos.');
      } else if (pestana === 'mas') {
        alert('Aplicación de transporte público de Aragón');
      }
    }
    document.getElementById('buscador-concesiones')?.addEventListener('input', function() {
      const q = this.value.trim().toLocaleLowerCase('es');
      document.querySelectorAll('.btn-menu').forEach(btn => {
        btn.style.display = btn.innerText.toLocaleLowerCase('es').includes(q) ? 'flex' : 'none';
      });
    });
"""
    if "function navegarPestana(" not in html:
        marker = "    cargarCatalogoConcesiones();"
        if marker in html:
            html = html.replace(marker, js + "\n" + marker, 1)
        else:
            html = html.replace("</script>", js + "\n  </script>", 1)

page.write_text(html, encoding="utf-8")
print("Proyecto extraído y plantilla móvil aplicada.")
