(() => {
  const LINES = {
    'T05-01': ['Fraga - Zaragoza por pueblos', '#281173'],
    'T05-20': ['Castejón de Monegros - Zaragoza por pueblos', '#2FEC97'],
    'T05-50': ['Valfarta - Bujaraloz', '#5310D7']
  };
  let line = '', direction = '', route = null, routeMap = null, sheetMap = null, sheet = null, adapter = null, refresh = null, currentPage = 'inicio', currentSub = 'index';
  const $ = (s, root=document) => root.querySelector(s);
  const esc = s => typeof escaparHTML === 'function' ? escaparHTML(s) : String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ids = s => Array.isArray(s?.stop_ids) && s.stop_ids.length ? s.stop_ids.map(String) : [String(s?.id || s?.stop_id || '')].filter(Boolean);
  const css = `
    :root{--wine:#6d1838;--red:#b51235;--paper:#f3f4f6}
    html,body{height:100%;overflow:hidden;background:var(--paper);color:#252930}
    #t05-top{position:fixed;z-index:12000;top:0;left:0;right:0;height:58px;padding:0 15px;display:flex;flex-direction:column;justify-content:center;background:#fff;border-bottom:1px solid #e5e6e8}
    #t05-top strong{font-size:18px;line-height:21px;font-weight:800}#t05-top small{font-size:9px;color:#838a92}
    #t05-nav{position:fixed;z-index:30000;bottom:0;left:0;right:0;height:58px;display:flex;background:#fff;border-top:1px solid #e5e6e8}
    #t05-nav button{flex:1;border:0;background:#fff;color:#555d66;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font-size:10px}#t05-nav i{font-size:17px}#t05-nav .active{color:var(--red);font-weight:800}
    /* No ocultar #pantalla-inicio: en la plantilla original puede contener el mapa Leaflet. */#map{position:fixed!important;top:58px!important;bottom:58px!important;left:0!important;width:100%!important;height:auto!important;z-index:1}
    #header-card{position:fixed!important;z-index:1000!important;top:66px!important;left:9px!important;right:9px!important;width:auto!important;max-width:none!important;padding:0!important;background:transparent!important;border:0!important;box-shadow:none!important}
    #header-card .header-title,#header-card .info-grid,#header-card .footer-actions,#header-card #contenedor-filtros-lineas{display:none!important}#header-card .map-tools{padding:6px!important;background:#ffffffed!important;border:1px solid #e5e7eb!important;border-radius:7px!important;box-shadow:0 2px 8px #0002!important}
    #buscador-paradas{height:34px!important;border:0!important;background:white!important;font-size:12px!important}#btn-paradas-cercanas,#btn-mostrar-favoritos{display:none!important}
    .t05-screen{position:fixed;z-index:11000;inset:58px 0 58px;overflow-y:auto;background:var(--paper);padding:10px 9px 18px;-webkit-overflow-scrolling:touch}.t05-screen[hidden],.t05-view[hidden]{display:none!important}.t05-inner{max-width:600px;margin:0 auto}
    .t05-head{display:flex;justify-content:space-between;align-items:center;padding:5px 4px 12px}.t05-head h1{font-size:18px;font-weight:800}.t05-head p{font-size:10px;color:#808791;margin-top:3px}
    .t05-search{display:block;margin:0 0 8px}.t05-search input{width:100%;height:36px;padding:0 11px;border:1px solid #e4e6e9;border-radius:4px;background:#fff;color:#252930;font-size:12px;outline:none}.t05-search input::placeholder{color:#9aa0a8}
    .t05-routes{background:white;border:1px solid #e7e8eb}.t05-route{width:100%;min-height:44px;padding:5px 9px;display:flex;align-items:center;gap:10px;background:#fff;border:0;border-bottom:1px solid #e7e8eb;text-align:left;color:#252930}.t05-route:last-child{border-bottom:0}.t05-stripe{width:5px;height:31px;border-radius:1px}.t05-code{width:47px;font-size:10px;font-weight:800}.t05-name{flex:1;font-size:11px;font-weight:700}.t05-route i{font-size:10px;color:#7b828b}
    .t05-back{border:0;background:transparent;padding:7px 4px 10px;color:#282d34;font-size:12px}.t05-dir{background:white;border:1px solid #e2e3e5}.t05-dir-label{display:block;padding:7px;background:#d8d8d8;text-align:center;font-size:11px;font-weight:700;color:#333}.t05-dir button{width:100%;min-height:44px;padding:8px 11px;display:flex;justify-content:space-between;align-items:center;border:0;border-bottom:1px solid #eceef0;background:#fff;text-align:left;color:#252930;font-size:11px;font-weight:700}.t05-dir button i{color:#848b94}
    .t05-map-route{height:205px;background:#e8ecee;border:1px solid #e2e5e8}.t05-timeline{background:#fff;padding:5px 0 8px}.t05-stop-row{width:100%;min-height:39px;display:flex;align-items:stretch;gap:10px;padding:0 10px;border:0;background:#fff;text-align:left;color:#252930}.t05-track{width:20px;position:relative;display:flex;align-items:center;justify-content:center;flex:0 0 20px}.t05-track:before{content:'';position:absolute;top:0;bottom:0;width:3px;background:var(--wine)}.t05-dot{width:11px;height:11px;z-index:1;border:3px solid var(--wine);border-radius:50%;background:white}.t05-stop-row:first-child .t05-track:before{top:50%}.t05-stop-row:last-child .t05-track:before{bottom:50%}.t05-stop-name{flex:1;align-self:center;font-size:10px;font-weight:600}.t05-stop-row i{align-self:center;color:#9aa0a7;font-size:10px}
    .t05-shade{position:fixed;z-index:24000;inset:58px 0 58px;background:#17202a24}.t05-sheet{position:fixed;z-index:25000;left:0;right:0;bottom:58px;max-height:75dvh;min-height:350px;display:flex;flex-direction:column;overflow:hidden;background:white;border-radius:13px 13px 0 0;box-shadow:0 -4px 20px #0003;padding-bottom:env(safe-area-inset-bottom)}.t05-grab{width:34px;height:4px;margin:7px auto 5px;background:#cfd3d8;border-radius:4px}.t05-mini{height:110px;flex:0 0 110px;margin:0 9px 8px;border:1px solid #e4e7ea;border-radius:6px;overflow:hidden;background:#e9edef}.t05-stop-head{display:flex;align-items:center;gap:8px;padding:0 12px 8px}.t05-stop-head strong{flex:1;font-size:13px;line-height:1.25}.t05-icon{width:29px;height:28px;border:1px solid #e2e5e8;border-radius:5px;background:white;color:#555}.t05-label{display:block;padding:4px 12px 5px;font-size:9px;letter-spacing:.3px;text-transform:uppercase;font-weight:800;color:#818891}.t05-chips{display:flex;flex-wrap:wrap;gap:5px;padding:0 12px 9px;border-bottom:1px solid #eceef0}.t05-chip{min-height:27px;padding:0 9px;border:1px solid #e0e3e7;border-radius:4px;background:white;color:#505861;font-size:10px;font-weight:800}.t05-chip.active{background:var(--chip);border-color:var(--chip);color:white}.t05-arr-head{display:flex;align-items:center;justify-content:space-between;gap:7px;padding:8px 12px 5px}.t05-arr-head strong{font-size:11px}.t05-days{display:flex;gap:4px}.t05-days button{height:25px;min-width:52px;border:1px solid #e0e4e8;border-radius:4px;background:white;color:#666e77;font-size:9px;font-weight:700}.t05-days .active{background:#f4e9ed;color:var(--wine);border-color:#d8bdc7}.t05-arrivals{flex:1;overflow-y:auto;padding:0 12px 10px}.t05-arrivals .stop-schedule-group{padding:7px 0!important;border-top:1px solid #eceef0}.t05-arrivals .stop-schedule-line{font-size:10px!important;font-weight:800}.t05-arrivals .stop-schedule-destination{font-size:10px!important}.t05-arrivals .stop-schedule-times{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}.t05-arrivals .stop-schedule-time{min-width:55px;padding:5px 7px!important;background:#f3f4f6!important;border-radius:4px!important}.t05-arrivals .stop-schedule-time.live{background:#eaf7ef!important}.t05-arrivals .stop-schedule-time strong{font-size:12px!important}.t05-arrivals .stop-schedule-time small{font-size:8px!important}.t05-date{display:none!important}
    @media(min-width:700px){.t05-screen{left:50%;right:auto;width:520px;transform:translateX(-50%);border:1px solid #e5e7ea}.t05-sheet{left:50%;right:auto;width:520px;transform:translateX(-50%);border:1px solid #e5e7ea}}
    @media(max-width:480px){.t05-sheet{max-height:77dvh;min-height:340px}.t05-mini{height:102px;flex-basis:102px}.t05-map-route{height:190px}}

    /* Replica móvil: cabecera, franja superior, mapa, lista de líneas y ficha completa. */
    body > header:not(#t05-top){display:none!important}
    #t05-top{height:58px;padding:0 12px;flex-direction:row;align-items:center;justify-content:space-between}
    #t05-home-banner{display:none!important}
    body.t05-home-active #map{top:58px!important}
    body.t05-home-active #header-card{top:66px!important}
    #t05-header-back{width:27px;height:32px;border:0;background:transparent;color:#252930;font-size:17px;padding:0;margin-right:7px}
    #t05-header-back[hidden]{display:none!important}
    .t05-brand{display:flex;align-items:center;gap:8px;flex:1}
    .t05-brand strong{font-size:19px;line-height:1;font-weight:900;letter-spacing:-.6px}
    .t05-brand small{font-size:9px;font-weight:800;line-height:1.05;letter-spacing:.25px;color:#424951}
    .t05-bell{width:32px;height:32px;border:0;background:transparent;color:#252930;font-size:16px}
    #t05-home-banner{position:fixed;z-index:2;top:58px;left:0;right:0;height:78px;overflow:hidden;background:linear-gradient(115deg,#294c42,#8caa72 50%,#344c39)}
    #header-card .map-tools{position:absolute!important;top:0!important;right:0!important;left:auto!important;width:auto!important;padding:0!important;background:transparent!important;border:0!important;box-shadow:none!important;pointer-events:none!important}
    #header-card .stop-search-row{display:flex!important;flex-direction:column!important;align-items:center!important;gap:7px!important;pointer-events:none!important}
    #buscador-paradas{display:none!important}
    #btn-paradas-cercanas,#btn-mostrar-favoritos{display:flex!important;width:33px!important;height:33px!important;min-width:33px!important;align-items:center!important;justify-content:center!important;padding:0!important;border:1px solid #e0e4e7!important;border-radius:50%!important;background:#fff!important;color:#313840!important;box-shadow:0 2px 6px #0002!important;pointer-events:auto!important}
    #btn-mostrar-favoritos span:not(.favorite-count){display:none!important}
    .t05-route{min-height:45px;padding:5px 8px;gap:9px}
    .t05-stripe{width:5px;height:33px}
    .t05-code{width:51px;font-size:10px}
    .t05-name{font-size:10px;font-weight:700}
    .t05-dir-label{padding:7px;background:#d9d9d9;text-align:center;color:#30343a;font-size:10px;font-weight:700}
    .t05-dir button{min-height:41px;font-size:10px;font-weight:600}
    .t05-map-route{height:215px}
    .t05-timeline{padding:4px 0 10px}
    .t05-stop-row{min-height:39px}
    .t05-shade{display:none!important}
    .t05-sheet{position:fixed;z-index:22000;inset:58px 0 58px;left:0;right:0;top:58px;bottom:58px;width:auto;max-height:none;min-height:0;border-radius:0;box-shadow:none;padding:0;overflow-y:auto;display:block;background:#f3f4f6}
    .t05-grab{display:none}
    .t05-mini{height:190px;flex:none;margin:0;border:0;border-radius:0;border-bottom:1px solid #dfe3e7}
    .t05-days{height:39px;background:#fff;border-bottom:1px solid #e2e4e7;display:flex;gap:0;padding:0}
    .t05-days button{flex:1;height:39px;border:0;border-bottom:2px solid transparent;border-radius:0;background:#fff;font-size:10px;color:#757c84}
    .t05-days button.active{background:#fff;color:#6d1838;border-bottom-color:#6d1838}
    .t05-stop-head{min-height:43px;padding:7px 10px 5px;background:#f3f4f6}
    .t05-stop-head strong{font-size:13px;font-weight:800}
    .t05-stop-actions{display:flex;align-items:center;gap:9px}
    .t05-icon{width:25px;height:26px;border:0;background:transparent;color:#555d66;font-size:14px}
    .t05-label{display:none}
    .t05-chips{padding:5px 8px 7px;gap:4px;flex-wrap:nowrap;overflow-x:auto;background:#f3f4f6;border-bottom:0}
    .t05-chip{flex:0 0 auto;min-height:26px;padding:0 6px;border:1px solid #d8dce0;border-radius:2px;background:#fff;color:#525a63;font-size:9px;font-weight:800}
    .t05-chip.active{background:var(--chip);border-color:var(--chip);color:#fff}
    .t05-arr-head{padding:7px 9px 4px;background:#fff;border-top:1px solid #e3e5e8}
    .t05-arr-head strong{font-size:9px;color:#888f97;font-weight:600}
    .t05-arrivals{min-height:90px;max-height:none;overflow:visible;padding:0 7px 10px;background:#fff}
    .t05-arrivals .stop-schedule-group{padding:7px 2px!important;border-bottom:1px solid #e9ebed;border-top:0!important;background:#fff}
    .t05-arrivals .stop-schedule-line{font-size:10px!important}
    .t05-arrivals .stop-schedule-destination{font-size:10px!important}
    .t05-arrivals .stop-schedule-time{min-width:55px;padding:5px 6px!important}
    .t05-date{display:none!important}
    @media(max-width:480px){.t05-mini{height:188px}.t05-map-route{height:205px}}
    @media(min-width:700px){.t05-sheet{left:50%;right:auto;width:520px;transform:translateX(-50%);border-left:1px solid #e6e8ea;border-right:1px solid #e6e8ea}}


    /* La ficha reproduce el panel compacto inferior de la referencia. */
    .t05-shade{display:none!important}
    .t05-sheet{position:fixed;z-index:25000;left:0;right:0;top:auto;bottom:58px;width:auto;height:auto;max-height:69dvh;min-height:295px;display:flex;flex-direction:column;overflow:hidden;padding:0 0 env(safe-area-inset-bottom);background:#fff;border:1px solid #e5e7ea;border-bottom:0;border-radius:12px 12px 0 0;box-shadow:0 -4px 16px #0002}
    .t05-grab{display:none}
    .t05-mini{height:112px;flex:0 0 112px;margin:8px 9px 5px;border:1px solid #e2e5e8;border-radius:6px;overflow:hidden;background:#e9edef}
    .t05-stop-head{min-height:37px;flex:0 0 auto;display:flex;align-items:center;gap:8px;padding:5px 10px;background:#fff}
    .t05-stop-head strong{font-size:12px;line-height:1.25;font-weight:800;color:#292e34}
    .t05-stop-actions{display:flex;align-items:center;gap:5px}
    .t05-icon{width:27px;height:27px;border:1px solid #e2e5e8;border-radius:5px;background:#fff;color:#59616a;font-size:12px}
    .t05-chips{flex:0 0 auto;display:flex;flex-wrap:nowrap;gap:5px;overflow-x:auto;padding:4px 10px 8px;border-bottom:1px solid #eceef0;background:#fff}
    .t05-chip{flex:0 0 auto;min-height:26px;padding:0 9px;border:1px solid #dfe3e7;border-radius:4px;background:#fff;color:#505861;font-size:10px;font-weight:800}
    .t05-chip.active{background:var(--chip);border-color:var(--chip);color:#fff}
    .t05-empty-lines{font-size:10px;color:#8a9098;padding:4px 0}
    .t05-route-error{padding:9px 11px;color:#a51f45;font-size:10px;background:#fff;border-top:1px solid #eee}
    .t05-arr-head{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:7px;padding:7px 10px 6px;background:#fff}
    .t05-arr-head strong{font-size:10px;font-weight:700;color:#454b53}
    .t05-days{display:flex;gap:4px;flex:0 0 auto}
    .t05-days button{height:25px;min-width:48px;padding:0 7px;border:1px solid #e0e4e8;border-radius:4px;background:#fff;color:#68717a;font-size:9px;font-weight:700}
    .t05-days button.active{background:#f4e9ed;color:#6d1838;border-color:#d8bdc7}
    .t05-arrivals{flex:1;min-height:65px;overflow-y:auto;padding:0 10px 10px;background:#fff;-webkit-overflow-scrolling:touch}
    .t05-arrivals .stop-schedule-group{padding:7px 0!important;border-top:1px solid #eceef0;background:#fff}
    .t05-arrivals .stop-schedule-line{font-size:10px!important;font-weight:800}
    .t05-arrivals .stop-schedule-destination{font-size:10px!important}
    .t05-arrivals .stop-schedule-times{display:flex;flex-wrap:wrap;gap:5px;margin-top:5px}
    .t05-arrivals .stop-schedule-time{min-width:55px;padding:5px 7px!important;border-radius:4px!important;background:#f3f4f6!important}
    .t05-arrivals .stop-schedule-time.live{background:#eaf7ef!important}
    .t05-arrivals .stop-schedule-time strong{font-size:12px!important}
    .t05-arrivals .stop-schedule-time small{font-size:8px!important}
    @media(max-width:480px){.t05-sheet{max-height:72dvh;min-height:280px}.t05-mini{height:108px;flex-basis:108px}}
    @media(min-width:700px){.t05-sheet{left:50%;right:auto;width:520px;transform:translateX(-50%)}}


    /* Ficha de parada a pantalla completa: mapa arriba y contenido hasta el borde inferior. */
    body.t05-stop-open #t05-nav{display:none!important}
    body.t05-stop-open .t05-sheet{
      position:fixed!important;z-index:25000!important;inset:58px 0 0!important;
      left:0!important;right:0!important;top:58px!important;bottom:0!important;
      width:auto!important;height:auto!important;max-height:none!important;min-height:0!important;
      display:flex!important;flex-direction:column!important;overflow:hidden!important;
      transform:none!important;border:0!important;border-radius:0!important;box-shadow:none!important;
      padding:0 0 env(safe-area-inset-bottom)!important;background:#f3f4f6!important
    }
    body.t05-stop-open .t05-mini{
      height:164px!important;min-height:164px!important;max-height:164px!important;
      flex:0 0 164px!important;margin:0!important;border:0!important;border-bottom:1px solid #dfe3e7!important;
      border-radius:0!important
    }
    body.t05-stop-open .t05-stop-head{min-height:49px!important;padding:8px 12px!important;background:#fff!important}
    body.t05-stop-open .t05-stop-head strong{font-size:14px!important}
    body.t05-stop-open .t05-chips{padding:7px 10px 9px!important;background:#fff!important;flex:0 0 auto!important}
    body.t05-stop-open .t05-chip{min-height:29px!important;font-size:10px!important}
    body.t05-stop-open .t05-arr-head{padding:10px 12px 8px!important;background:#fff!important;border-top:1px solid #e5e7e9!important}
    body.t05-stop-open .t05-arr-head strong{font-size:11px!important}
    body.t05-stop-open .t05-days button{height:29px!important;min-width:57px!important;font-size:10px!important}
    body.t05-stop-open .t05-arrivals{
      display:block!important;flex:1 1 auto!important;min-height:0!important;max-height:none!important;
      overflow-y:auto!important;padding:0 12px 20px!important;background:#fff!important;
      -webkit-overflow-scrolling:touch
    }
    body.t05-stop-open .t05-arrivals .stop-schedule-group{padding:10px 2px!important}
    body.t05-stop-open .t05-arrivals .stop-schedule-time{min-width:62px!important;padding:7px 9px!important}
    body.t05-stop-open .t05-arrivals .stop-schedule-time strong{font-size:13px!important}
    body.t05-stop-open .t05-route-error{margin:0;padding:10px 12px;background:#fff}
    body.t05-stop-open #t05-top{z-index:30000!important}
    .t05-screen,.t05-screen *{box-sizing:border-box}
    .t05-screen{background:#f3f4f6!important;color:#252930}
    .t05-route,.t05-dir button,.t05-stop-row{font-family:inherit}
    .t05-route:active,.t05-dir button:active,.t05-stop-row:active{background:#f5f1f3}
    .t05-route-error{line-height:1.4}

  `;
  function shell(){
    const st=document.createElement('style');st.textContent=css;document.head.append(st);
    document.body.insertAdjacentHTML('afterbegin',`<header id="t05-top"><button id="t05-header-back" type="button" aria-label="Volver" hidden><i class="fa-solid fa-arrow-left"></i></button><div class="t05-brand"><strong>TPA</strong><small>GOBIERNO DE ARAGÓN</small></div><button class="t05-bell" type="button" aria-label="Notificaciones"><i class="fa-regular fa-bell"></i></button></header><nav id="t05-nav"><button data-page="inicio" class="active"><i class="fa-solid fa-house"></i><span>Inicio</span></button><button data-page="lineas"><i class="fa-solid fa-route"></i><span>Líneas</span></button><button data-page="favoritos"><i class="fa-regular fa-star"></i><span>Favoritos</span></button><button data-page="mas"><i class="fa-solid fa-ellipsis"></i><span>Más</span></button></nav>
      <main id="t05-lines" class="t05-screen" hidden><div class="t05-inner">
      <section id="t05-index"><label class="t05-search"><input id="t05-line-search" type="search" placeholder="Buscar línea…" aria-label="Buscar línea"></label><div id="t05-routes" class="t05-routes">${Object.entries(LINES).map(([c,v])=>`<button class="t05-route" data-line="${c}"><span class="t05-stripe" style="background:${v[1]}"></span><span class="t05-code">${c}</span><span class="t05-name">${v[0]}</span><i class="fa-solid fa-chevron-right"></i></button>`).join('')}</div></section>
      <section id="t05-directions" hidden><button class="t05-back" data-back="index"><i class="fa-solid fa-arrow-left"></i></button><div class="t05-head"><div><h1 id="t05-line-title"></h1></div></div><div class="t05-dir"><span class="t05-dir-label">Ida</span><button data-direction="ida"><span id="t05-ida">Cargando…</span><i class="fa-solid fa-chevron-right"></i></button><span class="t05-dir-label">Vuelta</span><button data-direction="vuelta"><span id="t05-vuelta">Cargando…</span><i class="fa-solid fa-chevron-right"></i></button></div></section>
      <section id="t05-route-screen" hidden><button class="t05-back" data-back="directions"><i class="fa-solid fa-arrow-left"></i></button><div class="t05-head"><div><h1 id="t05-route-title"></h1><p id="t05-route-subtitle"></p></div></div><div id="t05-route-map" class="t05-map-route"></div><div id="t05-route-stops" class="t05-timeline"></div></section>
      </div></main><main id="t05-more" class="t05-screen" hidden><div class="t05-head"><div><h1>Más</h1><p>Concesión T05</p></div></div></main>`);
    $('#t05-nav').addEventListener('click',e=>{const b=e.target.closest('[data-page]');if(b)page(b.dataset.page)});
    $('#t05-header-back').addEventListener('click', headerBack);
    $('#t05-lines').addEventListener('click',lineClick);
    $('#t05-line-search').addEventListener('input', e => {
      const q = e.target.value.trim().toLocaleLowerCase('es');
      document.querySelectorAll('#t05-routes .t05-route').forEach(b => {
        b.hidden = !((b.dataset.line || '').toLocaleLowerCase('es').includes(q) ||
          b.querySelector('.t05-name')?.textContent.toLocaleLowerCase('es').includes(q));
      });
    });
  }
  function setHeaderBack(show){$('#t05-header-back').hidden=!show}
  function headerBack(){
    if(sheet){closeSheet();return}
    if(currentPage==='lineas'&&currentSub==='route'){
      if(routeMap){routeMap.remove();routeMap=null}
      $('#t05-route-screen').hidden=true;$('#t05-directions').hidden=false;currentSub='directions';setHeaderBack(true);return;
    }
    if(currentPage==='lineas'&&currentSub==='directions'){resetLine();return}
    page('inicio');
  }
  function page(p){
    closeSheet();currentPage=p;
    $('#t05-nav').querySelectorAll('button').forEach(tab=>tab.classList.toggle('active',tab.dataset.page===p));
    $('#t05-lines').hidden=p!=='lineas';$('#t05-more').hidden=p!=='mas';
    document.body.classList.toggle('t05-home-active',p==='inicio');
    const hc=$('#header-card');if(hc)hc.style.display=p==='inicio'||p==='favoritos'?'block':'none';
    const fav=$('#panel-favoritos');if(fav)fav.hidden=p!=='favoritos';
    if(p==='lineas'){resetLine();setHeaderBack(false)}
    else setHeaderBack(false);
    if(p==='inicio'&&typeof map!=='undefined')setTimeout(()=>map.invalidateSize(),120);
  }
  function resetLine(){if(routeMap){routeMap.remove();routeMap=null}$('#t05-index').hidden=false;$('#t05-directions').hidden=true;$('#t05-route-screen').hidden=true;currentSub='index';setHeaderBack(false)}
  async function openLine(c){line=c;currentSub='directions';setHeaderBack(true);$('#t05-index').hidden=true;$('#t05-directions').hidden=false;$('#t05-route-screen').hidden=true;$('#t05-line-title').textContent=c+'  '+LINES[c][0];$('#t05-ida').textContent='Cargando…';$('#t05-vuelta').textContent='Cargando…';const prior=$('#t05-directions .t05-route-error');prior?.remove();route={};const load=async d=>{const response=await fetch('/api/t05-linea/'+encodeURIComponent(c)+'/'+d,{cache:'no-store',headers:{'Accept':'application/json'}});const raw=await response.text();let data;try{data=JSON.parse(raw)}catch(_){const preview=raw.replace(/\s+/g,' ').slice(0,150);throw Error('Respuesta no JSON del servidor (HTTP '+response.status+', '+(response.headers.get('content-type')||'sin tipo')+'). '+preview)}if(!response.ok)throw Error(data.error||('Error HTTP '+response.status));if(data.error)throw Error(data.error);if(!Array.isArray(data.stops)||!data.stops.length)throw Error('La API no encontró paradas para '+c+' ('+d+'). '+(data.debug?JSON.stringify(data.debug):''));return data};const results=await Promise.allSettled([load('ida'),load('vuelta')]);const errors=[];for(const [i,d] of ['ida','vuelta'].entries()){const target=i===0?$('#t05-ida'):$('#t05-vuelta');const result=results[i];if(result.status==='fulfilled'){route[d]=result.value;target.textContent=(result.value.origen||'Origen')+' - '+(result.value.destino||'Destino')}else{target.textContent='Error al cargar';errors.push((d==='ida'?'Ida: ':'Vuelta: ')+result.reason.message);console.error('Error cargando '+c+' '+d,result.reason)}}if(errors.length)$('#t05-directions').insertAdjacentHTML('beforeend','<p class="t05-route-error">'+esc(errors.join(' · '))+'</p>')}
  function openDirection(d){if(!route?.[d])return;direction=d;currentSub='route';setHeaderBack(true);const r=route[d];$('#t05-directions').hidden=true;$('#t05-route-screen').hidden=false;$('#t05-route-title').textContent=line+' · '+(d==='ida'?'Ida':'Vuelta');$('#t05-route-subtitle').textContent=r.origen+' - '+r.destino;$('#t05-route-stops').innerHTML=(r.stops||[]).map((s,i)=>`<button class="t05-stop-row" data-route-stop="${i}"><span class="t05-track"><span class="t05-dot"></span></span><span class="t05-stop-name">${esc(s.name)}</span><i class="fa-solid fa-chevron-right"></i></button>`).join('');if(routeMap)routeMap.remove();routeMap=L.map('t05-route-map',{zoomControl:false,scrollWheelZoom:false});L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'&copy; OpenStreetMap'}).addTo(routeMap);const layers=[];if(r.shape?.length>1)layers.push(L.polyline(r.shape,{color:LINES[line][1],weight:4}).addTo(routeMap));(r.stops||[]).forEach(s=>{if(s.lat!==null&&s.lon!==null&&s.lat!==''&&s.lon!==''&&Number.isFinite(Number(s.lat))&&Number.isFinite(Number(s.lon))){const m=L.circleMarker([+s.lat,+s.lon],{radius:5,color:'#fff',weight:2,fillColor:'#6d1838',fillOpacity:1}).addTo(routeMap);m.on('click',e=>{L.DomEvent.stop(e);openStop(s)});layers.push(m)}});if(layers.length)routeMap.fitBounds(L.featureGroup(layers).getBounds(),{padding:[12,12],maxZoom:11});setTimeout(()=>routeMap?.invalidateSize(),100)}
  function lineClick(e){const b=e.target.closest('[data-back]');if(b){if(b.dataset.back==='index')resetLine();else{if(routeMap){routeMap.remove();routeMap=null}$('#t05-route-screen').hidden=true;$('#t05-directions').hidden=false}return}const l=e.target.closest('[data-line]');if(l){openLine(l.dataset.line);return}const d=e.target.closest('[data-direction]');if(d){openDirection(d.dataset.direction);return}const s=e.target.closest('[data-route-stop]');if(s)openStop(route?.[direction]?.stops?.[+s.dataset.routeStop])}
  function findStop(s){const all=typeof listaParadas!=='undefined'?listaParadas:[];const set=new Set(ids(s));return all.find(x=>String(x.id)===String(s.id)||ids(x).some(id=>set.has(id)))?{...s,...all.find(x=>String(x.id)===String(s.id)||ids(x).some(id=>set.has(id)))}:s}
  function closeSheet(){
    if(refresh){clearInterval(refresh);refresh=null}
    if(adapter)adapter._solicitudLlegadasParada=(adapter._solicitudLlegadasParada||0)+1;
    if(sheetMap){sheetMap.remove();sheetMap=null}
    $('#t05-sheet')?.remove();$('#t05-shade')?.remove();sheet=null;adapter=null;document.body.classList.remove('t05-stop-open');
    setHeaderBack(currentPage==='lineas'&&currentSub!=='index');
  }
  function openStop(s){
    if(!s)return;
    closeSheet();s=findStop(s);document.body.classList.add('t05-stop-open');
    sheet=document.createElement('section');sheet.id='t05-sheet';sheet.className='t05-sheet';
    const served=[...new Set((s.lineas||[]).filter(x=>LINES[x]))].sort();
    const routes=served.length?served:(line?[line]:[]);
    sheet.innerHTML=`<div class="t05-mini" id="t05-mini" aria-label="Mapa de ubicación de la parada"></div>
      <div class="t05-stop-head"><strong>${esc(s.name)}</strong><div class="t05-stop-actions">
        <button class="t05-icon" type="button" data-close aria-label="Cerrar ficha"><i class="fa-solid fa-xmark"></i></button>
        <button class="t05-icon" type="button" data-refresh aria-label="Actualizar llegadas"><i class="fa-solid fa-rotate"></i></button>
        <button class="t05-icon" type="button" data-center aria-label="Centrar ubicación"><i class="fa-solid fa-location-crosshairs"></i></button>
        <button class="t05-icon" type="button" data-fav aria-label="Guardar parada"><i class="fa-regular fa-star"></i></button>
      </div></div>
      <div class="t05-chips" aria-label="Líneas que paran aquí">
        ${routes.length ? routes.map(x=>`<button class="t05-chip" data-chip="${x}" style="--chip:${LINES[x][1]}">${x}</button>`).join('') : '<span class="t05-empty-lines">No hay líneas identificadas</span>'}
      </div>
      <div class="t05-arr-head"><strong>Llegadas programadas / en tiempo real</strong>
        <div class="t05-days" role="tablist" aria-label="Día de consulta"><button class="active" data-day="0">Hoy</button><button data-day="1">Mañana</button></div>
      </div>
      <input type="date" class="stop-date-input t05-date" aria-label="Fecha de consulta">
      <div class="t05-arrivals"><div class="llegadas-parada stop-arrival-state">Consultando horarios…</div></div>`;
    document.body.append(sheet);
    const favorite=sheet.querySelector('[data-fav]');
    const favs=typeof favoritosParadas!=='undefined'?favoritosParadas:[];
    let saved=Array.isArray(favs)&&favs.some(x=>String(x.id)===String(s.id));
    if(saved)favorite.innerHTML='<i class="fa-solid fa-star"></i>';
    favorite.addEventListener('click',()=>{
      if(typeof alternarFavorito==='function')alternarFavorito(s);
      saved=!saved;favorite.innerHTML=saved?'<i class="fa-solid fa-star"></i>':'<i class="fa-regular fa-star"></i>';
    });
    const today=typeof fechaLocalISO==='function'?fechaLocalISO():new Date().toISOString().slice(0,10);
    const date=sheet.querySelector('.stop-date-input');date.min=today;date.value=today;
    adapter={_solicitudLlegadasParada:0,_lineaFiltroActiva:'',getElement:()=>$('#t05-sheet')};
    const load=()=>{if(typeof cargarLlegadasParada==='function')cargarLlegadasParada(s.id,adapter,date.value,ids(s),adapter._lineaFiltroActiva)};
    sheet.querySelectorAll('[data-day]').forEach(b=>b.addEventListener('click',()=>{
      sheet.querySelectorAll('[data-day]').forEach(x=>x.classList.toggle('active',x===b));
      date.value=typeof desplazarFechaISO==='function'?desplazarFechaISO(today,+b.dataset.day):today;load();
    }));
    date.addEventListener('change',load);
    sheet.querySelectorAll('[data-chip]').forEach(b=>b.addEventListener('click',()=>{
      adapter._lineaFiltroActiva=adapter._lineaFiltroActiva===b.dataset.chip?'':b.dataset.chip;
      sheet.querySelectorAll('[data-chip]').forEach(x=>x.classList.toggle('active',x.dataset.chip===adapter._lineaFiltroActiva));
      load();
    }));
    sheet.querySelector('[data-close]').addEventListener('click',closeSheet);
    sheet.querySelector('[data-refresh]').addEventListener('click',load);
    sheet.querySelector('[data-center]').addEventListener('click',()=>{
      if(sheetMap)sheetMap.setView([+s.lat,+s.lon],16);
    });
    const lat=s.lat===null||s.lat===undefined||s.lat===''?NaN:Number(s.lat),lonValue=s.lon===null||s.lon===undefined||s.lon===''?(s.lng??s.longitude):s.lon,lon=lonValue===null||lonValue===undefined||lonValue===''?NaN:Number(lonValue),node=$('#t05-mini');
    if(Number.isFinite(lat)&&Number.isFinite(lon)){
      sheetMap=L.map(node,{zoomControl:false,attributionControl:true,dragging:false,scrollWheelZoom:false,doubleClickZoom:false,keyboard:false}).setView([lat,lon],15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap'}).addTo(sheetMap);
      L.circleMarker([lat,lon],{radius:7,color:'#fff',weight:2,fillColor:'#6d1838',fillOpacity:1}).addTo(sheetMap);
      setTimeout(()=>sheetMap?.invalidateSize(),120);
    }else {node.textContent='Ubicación no disponible';sheet.querySelector('[data-center]').disabled=true;}
    setHeaderBack(true);load();refresh=setInterval(load,30000);
  }
  function attach(){if(typeof marcadoresParadas==='undefined')return;Object.entries(marcadoresParadas).forEach(([id,m])=>{const s=m?._t05StopData||(typeof listaParadas!=='undefined'?listaParadas.find(x=>String(x.id)===String(id)):null);if(!m||!s||m._t05Tactile)return;m._t05StopData=s;m._t05Tactile=true;m.unbindPopup?.();m.on('click',e=>{if(e.originalEvent)L.DomEvent.stop(e.originalEvent);openStop(s)})})}
  function ready(){shell();document.documentElement.removeAttribute('data-t05-boot');document.documentElement.classList.remove('t05-boot');document.body.classList.add('t05-home-active');setHeaderBack(false);const oldSelect=seleccionarParada;seleccionarParada=(id,con='T05')=>{const m=typeof marcadoresParadas!=='undefined'?marcadoresParadas[String(id)]:null;if(!m){oldSelect?.(id,con);return}if(typeof paradasVisibles!=='undefined'&&!paradasVisibles&&typeof alternarParadas==='function')alternarParadas();if(typeof map!=='undefined'&&map)map.flyTo(m.getLatLng(),15,{duration:.45});openStop(m._t05StopData||(typeof listaParadas!=='undefined'?listaParadas.find(s=>String(s.id)===String(id)):null));const r=$('#resultados-paradas');if(r)r.hidden=true;const q=$('#buscador-paradas');if(q)q.value=''};const wait=()=>{if(typeof catalogoConcesiones!=='undefined'&&catalogoConcesiones.T05){if(typeof map==='undefined'||!map||typeof lineaActiva==='undefined'||lineaActiva!=='T05')iniciarMapa('T05');setTimeout(()=>{if(typeof map!=='undefined'&&map)map.invalidateSize()},180);return}if(wait.n++<100)setTimeout(wait,80)};wait.n=0;wait();setInterval(attach,300);if($('#buscador-paradas'))$('#buscador-paradas').placeholder='Buscar parada…'}
  window.T05App={page,openLine,openDirection,openStop,closeSheet};document.addEventListener('keydown',e=>{if(e.key==='Escape')headerBack()});if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();
})();
