"""Visor · GERENCIA con registros de polinización: tablero, módulos, sincronización, calidad, auditoría (y App), reportes. GitHub simulado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, PLANTACION, TMP, BASE
import sys, time, json, re
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)
from datetime import datetime, timedelta, timezone
AHORA = datetime.now(timezone.utc)
iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%SZ')
COMMITS = [
    {'commit': {'message': 'Polinización · GOMEZ PEREZ ANDRES · jornada 2026-11-14 · 3 registro(s) · u:1000000001', 'committer': {'date': iso(AHORA - timedelta(hours=3))}}},
    {'commit': {'message': 'Polinización · LOPEZ DIAZ CARLOS · jornada 2026-11-08 · 2 diagnóstico(s)', 'committer': {'date': iso(AHORA - timedelta(days=6))}}},
    {'commit': {'message': 'Pruebas fuera del visor', 'committer': {'date': iso(AHORA - timedelta(days=1))}}}]
EST = {'guardado': None, 'puts': []}
def gh(route):
    req = route.request; u = req.url; m = req.method
    if '/commits?' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps(COMMITS if re.search(r'[?&]page=1(&|$)', u) else []))
    if m == 'PUT' and '/contents/auditoria/' in u:
        b = json.loads(req.post_data); import base64; EST['guardado'] = json.loads(base64.b64decode(b['content']).decode('utf-8')); EST['puts'].append(u)
        return route.fulfill(status=201, content_type='application/json', body=json.dumps({'content': {'sha': 'audsha'}}))
    if '/contents/auditoria?' in u:
        l = [{'type': 'file', 'name': EST['guardado']['id'] + '.json', 'sha': 'audsha'}] if EST['guardado'] else []
        return route.fulfill(status=200, content_type='application/json', body=json.dumps(l))
    if u.endswith('/git/blobs/audsha'): return route.fulfill(status=200, body=json.dumps(EST['guardado']), content_type='application/json')
    if '/contents/auditoria/' in u and m == 'GET': return route.fulfill(status=200, body=json.dumps(EST['guardado']), content_type='application/json')
    if '/contents/jornadas?' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps([{'type': 'dir', 'name': (AHORA - timedelta(hours=5)).strftime('%Y-%m-%d'), 'sha': 'dia1'}]))
    if u.endswith('/git/trees/dia1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps({'tree': [{'path': 'JSUP.geojson', 'type': 'blob', 'sha': 'gsup'}]}))
    if u.endswith('/git/blobs/gsup'):
        g = EST['guardado']; feats = []
        for k, x in enumerate(g['palmas'][:2]):  # el auditor registra 2 palmas: una coincide y otra no
            o = x['original']
            pr = {'a': o['a'], 'p': o['p'], 'b': o['b'], 'cond': o['cond'], 'n1_codigo': o['codigo'], 'nivel1': o['resumen']} if k == 0 else {'a': 0, 'p': 0, 'b': 0, 'cond': 'V', 'n1_codigo': 'V', 'nivel1': 'V: Palma con Avispas'}
            feats.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [x['lng'], x['lat']]}, 'properties': {'tipo': 'diagnostico', 'palma_id': x['palma_id'], **pr, 'creado': iso(AHORA), 'auditoria': g['id']}})
        return route.fulfill(status=200, content_type='application/json', body=json.dumps({'type': 'FeatureCollection', 'jornada': {'usuario': 'sup1', 'evaluador': 'Sara Supervisora'}, 'features': feats}))
    if '/contents/reportes?' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps([{'type': 'dir', 'name': '2026-S45', 'sha': 'rep45'}]))
    if u.endswith('/git/trees/rep45'): return route.fulfill(status=200, content_type='application/json', body=json.dumps({'tree': [{'path': 'reporte_2026-S45.pdf', 'type': 'blob', 'sha': 'p1'}, {'path': 'reporte_2026-S45.xlsx', 'type': 'blob', 'sha': 'x1'}]}))
    route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')
DATOS = """()=>{document.querySelector('#login').hidden=true;document.querySelector('#app').hidden=false;mapa.invalidateSize();window.chunkLote=async()=>[];
  SES={u:'admin1',nombre:'Admin',rol:'admin',token:'tok',repo:{owner:'didpalmares',repo:'PolinizacionData',rama:'main'}};
  USUARIOS_PAQ=[{u:'1000000001',nombre:'GOMEZ PEREZ ANDRES',rol:'operario',labores:['polinizacion']},{u:'1000000002',nombre:'LOPEZ DIAZ CARLOS',rol:'operario',labores:['polinizacion']},
    {u:'1000000003',nombre:'MORA RUIZ JAVIER',rol:'operario',labores:['polinizacion']},{u:'sup1',nombre:'Sara Supervisora',rol:'supervisor'},{u:'x9',nombre:'Suspendido',rol:'operario',inactivo:true}];
  const hoy=hoyISO();const mk=(id,u,nom,fecha,regs)=>{const t0=Date.parse(fecha+'T07:00:00-05:00');const c=[],t=[];for(let i=0;i<=60;i++){c.push([-78.70,1.50+i*0.0001]);t.push(t0+i*60000);}
    const ds=regs.map((x,k)=>normPol({tipo:'diagnostico',id:id+'d'+k,palma_id:id+'P'+k,lote:x.lote||'IT01',linea:3,palma:k+1,labor:'polinizacion',a:x.a??2,p:x.p??1,b:x.b??0,cond:x.cond||'',fuente:'boton',
      transitabilidad:'Transitable',evaluador:nom,creado:new Date(t0+(x.min??(5+k*3))*60000+(x.s||0)*1000).toISOString(),lat:1.50+k*0.0002,lng:-78.70,n_fotos:0,fotos:'',dist_gps_palma_m:x.dist||3,gps_precision_m:x.prec||5}));
    const j={id,fecha,evaluador:nom,usuario:u,inicio:new Date(t0).toISOString(),fin:new Date(t0+60*60000).toISOString(),hora_inicio:'07:00',hora_fin:'08:00',duracion_min:60,km:1.2,ha:2.5,palmas:280,metodo:'calle',
      n_paradas:1,min_paradas:10,min_mov:50,por_lote:[{lote:'IT01',palmas_visitadas:280,ha:2.5}],densidad:115,app:'',lotes:new Set(['IT01']),paradas:[],track:{c,t,acc:c.map(()=>4)},header:{},secuencias:null,tiempos:{min_efectivo_labor:50},vel:2,
      transito:[{lote:'IT01',entrada:'Transitable',t_entrada:new Date(t0+60000).toISOString(),salida:'Poco transitable',t_salida:new Date(t0+59*60000).toISOString()}],diags:ds};
    ds.forEach(d=>d._j=j);return j;};
  const lejos={dist:40},imp={prec:30};
  JOR=[mk('J1','1000000001','GOMEZ PEREZ ANDRES',hoy,[{},{...lejos,a:1},{...imp,b:2},{cond:'R'},{min:20,a:3},{min:20,s:2,p:2}]),
       mk('J2','1000000002','LOPEZ DIAZ CARLOS',hoy,[...Array(16)].map((_,k)=>({a:1,p:0,b:0,min:5+k*2}))),
       mk('J3','1000000003','MORA RUIZ JAVIER',hoyISO(new Date(Date.now()-40*86400000)),[{lote:'IT05'}])];
  JOR[2].por_lote=[{lote:'IT05',palmas_visitadas:100,ha:1}];JOR[2].lotes=new Set(['IT05']);JOR[2].transito=[];
  LOTES={type:'FeatureCollection',features:['IT01','IT05','IT09'].map((l,k)=>({type:'Feature',properties:{_lote:l},geometry:{type:'Polygon',coordinates:[[[-78.701+k*0.01,1.499],[-78.699+k*0.01,1.499],[-78.699+k*0.01,1.512],[-78.701+k*0.01,1.512],[-78.701+k*0.01,1.499]]]}}))};IND_LOTES={IT01:{n:1000},IT05:{n:800},IT09:{n:500}};
  document.querySelector('#fDesde').value=hoyISO(new Date(Date.now()-45*86400000));document.querySelector('#fHasta').value=hoy;
  aplicarFiltros(false);}"""
errores = []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 1400, 'height': 950}, accept_downloads=True)
    ctx.route('https://api.github.com/**', gh)
    vz = ctx.new_page(); vz.on('pageerror', lambda e: errores.append('visor: ' + str(e)[:200] + ' ' + (e.stack or '')[:200]))
    vz.goto(BASE + '/visor.html'); vz.wait_for_function("typeof alternarGerencia==='function'", timeout=30000); time.sleep(1)
    vz.evaluate(DATOS)
    vz.click('#btGer'); time.sleep(.6)
    txt = lambda: vz.inner_text('#gerPanel')
    T = txt()
    check('Gerencia abre con el Tablero', 'GERENCIA' in T and 'PRODUCTIVIDAD POR OPERARIO' in T.upper(), T[:80])
    check('Tablero: KPIs de la polinización (sin enfermedades)', 'Jornadas' in T and 'Palmas registradas' in T and 'Inflorescencias (A + P + B)' in T and 'PC' not in T and 'Diagnósticos' not in T)
    check('Tablero: productividad por operario (ha/hora)', vz.evaluate("[...document.querySelectorAll('#gerPanel table')][0].innerText").count('\n') >= 3)
    ciclo = vz.evaluate("[...document.querySelectorAll('#gerPanel table')].pop().innerText")
    check('Ciclo de polinización: IT05 con 40 días (alerta) e IT09 sin polinización', '40 días' in ciclo and 'Sin polinización en el periodo' in ciclo, ciclo.replace('\n', ' | ')[:200])
    check('Ciclo de polinización: aviso de lotes atrasados', 'más de 30 días sin polinización' in T)
    check('Tablero: sin textos de censo ni enfermedades', 'censo' not in T.lower() and 'enfermedad' not in T.lower())
    vz.click('[data-tsub=pol]'); time.sleep(.8)
    K = vz.inner_text('#polKpis')
    check('Sección 🐝 Polinización: KPIs', 'Palmas registradas' in K and 'Total A: Inflorescencia en Antesis' in K and '% Balón' in K and 'Palmas R: Palma Rancho / Tapada' in K, re.sub(r'\s+', ' ', K)[:200])
    vz.click('[data-tsub=resumen]'); time.sleep(.3)
    check('Módulos: Gerencia con Tablero, Reportes y Sincronización', [b.inner_text() for b in vz.query_selector_all('#gerPanel [data-gt]')] == ['TABLERO', 'REPORTES', 'SINCRONIZACIÓN'])
    vz.click('#btCoord'); time.sleep(.5)
    check('Módulos: Coordinación y supervisión con Programador, Transitabilidad, Calidad, Auditoría y Reportes',
          'COORDINACIÓN Y SUPERVISIÓN DE LA LABOR' in txt().upper() and [b.inner_text() for b in vz.query_selector_all('#gerPanel [data-gt]')] == ['PROGRAMADOR DE POLINIZACIÓN', 'TRANSITABILIDAD', 'CALIDAD', 'AUDITORÍA', 'REPORTES'],
          [b.inner_text() for b in vz.query_selector_all('#gerPanel [data-gt]')])
    vz.click('[data-gt=transito]'); time.sleep(.4); T = txt()
    check('Transitabilidad por lote: entradas y salidas', 'TRANSITABILIDAD POR LOTE' in T.upper() and 'Poco transitable' in T and vz.evaluate("document.querySelectorAll('#trTabla tbody tr').length") == 2, re.sub(r'\s+', ' ', T)[:200])
    # Sincronización (módulo de análisis de datos)
    vz.click('#btDatos'); time.sleep(.3)
    check('Módulos: Análisis de datos con Sincronización', 'ANÁLISIS DE DATOS' in txt().upper() and [b.inner_text() for b in vz.query_selector_all('#gerPanel [data-gt]')] == ['SINCRONIZACIÓN'])
    vz.wait_for_function("!!GER.sync", timeout=15000); time.sleep(.4); T = txt()
    check('Sincronización: solo operarios activos (3)', vz.evaluate("GER.sync.filas.length") == 3, vz.evaluate("GER.sync.filas.map(x=>x.u)"))
    check('Sincronización: estados hoy / 6 días / sin envíos', 'Hoy' in T and '6 días sin sincronizar' in T and 'Sin envíos en 30 días' in T, re.sub(r'\s+', ' ', T)[:200])
    check('Sincronización: reconoce envíos antiguos por nombre (sin u:)', any(f['u'] == '1000000002' and f['n30'] == 1 for f in vz.evaluate("GER.sync.filas")))
    check('Sincronización: alerta de más de 2 días', 'operario(s) llevan más de 2 días' in T)
    # Calidad
    vz.click('#btCoord'); time.sleep(.3); vz.click('[data-gt=calidad]'); time.sleep(.4); T = txt()
    al = vz.evaluate("(()=>{const a=alertasCalidad();const c={};a.forEach(x=>c[x.m]=(c[x.m]||0)+1);return c})()")
    check('Calidad: detecta lejos, GPS, rápido y racha (sin «sin foto»)', al.get('lejos') == 1 and al.get('gps') == 1 and al.get('rapido', 0) >= 1 and al.get('racha') == 16 and 'foto' not in al, al)
    check('Calidad: % de alertas por operario y textos de registro', '% con alerta' in T and 'Registros de polinización' in T and 'iagnóstico' not in T)
    vz.select_option('#calTipo', 'lejos'); time.sleep(.3)
    n = vz.evaluate("[...document.querySelectorAll('#gerPanel [data-rev]')].length")
    check('Calidad: filtro por motivo', n == 1, n)
    check('Calidad: la alerta muestra el registro (1A + 1P)', '1A + 1P' in txt())
    vz.evaluate("document.querySelector('#gerPanel [data-rev]').click()"); time.sleep(.3)
    check('Calidad: marcar como revisada la oculta', vz.evaluate("[...document.querySelectorAll('#gerPanel [data-rev]')].length") == 0)
    # Auditoría
    vz.click('[data-gt=auditoria]'); time.sleep(.6)
    vz.fill('#audPct', '50'); vz.dispatch_event('#audPct', 'change'); vz.fill('#audMin', '2'); vz.dispatch_event('#audMin', 'change')
    vz.click('#audGen'); time.sleep(.6)
    m = vz.evaluate("GER.aud.muestra")
    ops = {x['original']['usuario'] for x in m['palmas']}
    check('Auditoría: muestra solo de operarios, por operario', len(m['palmas']) >= 4 and ops <= {'1000000001', '1000000002', '1000000003'} and len(ops) >= 2, (len(m['palmas']), ops))
    check('Auditoría: sin palmas repetidas', len({x['palma_id'] for x in m['palmas']}) == len(m['palmas']))
    check('Auditoría: el original lleva código, resumen y conteos', all(x['original'].get('codigo') and x['original'].get('resumen') and 'a' in x['original'] for x in m['palmas']), m['palmas'][0]['original'])
    vz.click('#audGuardar'); vz.wait_for_function("GER.aud.guardada", timeout=10000)
    check('Auditoría: se guarda en auditoria/ del repositorio de datos', EST['guardado'] and EST['guardado']['id'] == m['id'] and '/contents/auditoria/' + m['id'] in EST['puts'][0], EST['puts'][:1])
    vz.wait_for_function("GER.aud.lista&&GER.aud.lista.length", timeout=10000); time.sleep(.3)
    vz.click('#audVer'); vz.wait_for_function("!!GER.aud.res", timeout=15000); time.sleep(.3); T = txt()
    check('Auditoría: avance (2 auditadas) y concordancia 50 %', vz.evaluate("GER.aud.res.filas.filter(x=>x.hecha).length") == 2 and '50 %' in T and 'Concordancia en el código' in T, re.sub(r'\s+', ' ', T)[-300:])
    check('Auditoría: lista la diferencia', 'DIFERENCIAS (1)' in T.upper() and 'V: Palma con Avispas' in T)
    # Reportes
    vz.click('[data-gt=reportes]'); vz.wait_for_function("GER.reportes&&GER.reportes.semanales.length", timeout=10000); time.sleep(.3); T = txt()
    check('Reportes: lista semanas con PDF y Excel', '2026-S45' in T and 'PDF' in T and 'Excel' in T and 'Generar y enviar' in T)
    vz.click('#gerX'); check('Cerrar vuelve al mapa', vz.evaluate("document.querySelector('#gerPanel').hidden"))
    # ---- App: auditoría para supervisores (registro de polinización) ----
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errores.append('app: ' + str(e)[:200])); pg.on('dialog', lambda d: (print('     ALERTA:', d.message), d.dismiss()))
    pg.goto(BASE + '/index.html'); pg.wait_for_function("typeof panelAuditoria==='function'", timeout=30000); time.sleep(2)
    pal = EST['guardado']['palmas'][0]
    r = pg.evaluate("""async(pal)=>{try{ return await (async()=>{document.querySelector('#login').hidden=true;SES={u:'sup1',nombre:'Sara',rol:'supervisor'};S.cfg.gh={...S.cfg.gh,token:'tok',owner:'didpalmares',repo:'PolinizacionData',rama:'main'};
      await cargarAuditoria();menu();const tile=!!document.querySelector('#mAud');
      const j={id:'JA',labor:'polinizacion',estado:'activa',evaluador:'Sara',usuario:'sup1',inicio:new Date().toISOString(),seleccion:[{lote:pal.lote}],densidad:115,buffer:5,km:0,sync:'pendiente',
        transito:[{lote:String(pal.lote),entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};await dbPut('jornadas',j);S.jornada=j;
      S.idx.set(pal.palma_id,{type:'Feature',geometry:{type:'Point',coordinates:[pal.lng,pal.lat]},properties:{_id:pal.palma_id,_lote:pal.lote,_linea:pal.linea,_num:pal.palma}});
      S.gps={lat:pal.lat+0.00003,lng:pal.lng,acc:4,t:Date.now()};
      await panelAuditoria();const txt=document.querySelector('#hojaCuerpo').innerText;
      abrirPalma(pal.palma_id);const ficha=document.querySelector('#hojaCuerpo').innerText;
      await abrirFormulario({palma_id:pal.palma_id});const frm=document.querySelector('#frm');if(!frm)return {err:'sin formulario',h:document.querySelector('#hojaCuerpo').innerText.slice(0,200),toast:document.querySelector('#toast').textContent};
      const mas=frm.querySelector('[data-mas=a]');if(!mas)return {err:'sin botón A'};mas.click();mas.click();
      await guardarRegistro(frm);
      const reg=S.registros.find(x=>x.palma_id===pal.palma_id);
      return {tile,ciega:!txt.includes(pal.original.resumen||'@@')&&!txt.includes(pal.original.evaluador),cuenta:txt.toUpperCase().includes('PALMAS'),ficha:ficha.includes('Palma de la auditoría'),
        tag:reg&&reg.auditoria,plano:planos(reg).auditoria,a:reg&&reg.a,fuente:reg&&reg.fuente};})();}catch(e){return {err:e.message,stack:String(e.stack).slice(0,600)};}}""", pal)
    print('     app:', {k: v for k, v in r.items() if k in ('err', 'h', 'toast', 'stack')})
    check('App: menú «Auditoría» para supervisor', r.get('tile'))
    check('App: lista a ciegas (sin registro ni operario original)', r.get('ciega') and r.get('cuenta'))
    check('App: ficha de la palma avisa que es de auditoría', r.get('ficha'))
    check('App: el registro (2A, formulario) queda marcado con la muestra (también al sincronizar)', r.get('tag') == EST['guardado']['id'] and r.get('plano') == EST['guardado']['id'] and r.get('a') == 2 and r.get('fuente') == 'formulario', r)
    op = pg.evaluate("async()=>{SES={u:'op',nombre:'Op',rol:'operario'};AUD.m=null;await cargarAuditoria();menu();return !!document.querySelector('#mAud')}")
    check('App: un operario no ve la auditoría', not op)
    # Rol analista de datos: tiene los permisos de administrador (ve todos los módulos)
    rv = vz.evaluate("""()=>{SES={...SES,rol:'analista'};aplicarPermisosGer();const vis=['btGer','btCoord','btDatos'].filter(i=>!document.getElementById(i).hidden);
      alternarGerencia(true,'coord');const ab=GER.on&&GER.mod;alternarGerencia(false);SES={...SES,rol:'admin'};aplicarPermisosGer();
      return {vis,ab,vis2:['btGer','btCoord','btDatos'].filter(i=>!document.getElementById(i).hidden)};}""")
    check('Rol analista: ve todo, como administrador', rv['vis'] == ['btGer', 'btCoord', 'btDatos'] and rv['ab'] == 'coord' and rv['vis2'] == ['btGer', 'btCoord', 'btDatos'], rv)
    check('Sin errores de JavaScript', not errores, errores[:4])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
