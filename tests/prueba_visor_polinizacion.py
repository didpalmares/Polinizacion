"""Visor · polinización de punta a punta: la App arma el GeoJSON de la jornada (el mismo que sincroniza) con A, P, B, R, V,
fuente, pasadas y transitabilidad; el visor lo lee de GitHub (simulado) y muestra colores y leyenda, ficha de la palma,
filtro por código, indicadores de Gerencia (🐝 Polinización), tabla por lote y transitabilidad por lote. Datos ficticios.

Uso: python tests/prueba_visor_polinizacion.py   (dirección base con PRUEBAS_URL; Edge con PW_CANAL=msedge)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, BASE
import sys, time, json, re
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)
HOY = date.today().isoformat()
COLORES = {'A': '#00c853', 'P': '#ffab00', 'B': '#d84315', 'R': '#8d6e63', 'V': '#e53935'}
NOMBRES = {'A': 'Inflorescencia en Antesis', 'P': 'Inflorescencia en Post-Antesis', 'B': 'Balón (Post-Antesis pasada)', 'R': 'Palma Rancho / Tapada', 'V': 'Palma con Avispas'}

# ---- 1. La App arma los GeoJSON de dos jornadas, como al sincronizar ----
ARMAR = """(hoy)=>{const t=h=>new Date(hoy+'T'+h+':00-05:00').toISOString();
  const reg=(jid,ev,pid,lote,lin,num,x,h,lat)=>completarPol({id:jid+'-'+pid,palma_id:pid,jornada_id:jid,evaluador:ev,labor:'polinizacion',a:x.a||0,p:x.p||0,b:x.b||0,cond:x.cond||'',
    fuente:x.f||'boton',pasadas:x.pas||[{c:x.cond||'A',f:x.f||'boton',t:t(h)}],lote,linea:lin,numero:num,lat,lng:-78.70,creado:t(h),fecha:hoy+' '+h,modificado:t(h),
    transitabilidad:x.tr||'Transitable',observaciones:x.obs||'',fotos:[],sync:'pendiente',gps_acc:4,dist_gps:2.5});
  const jor=(id,u,ev,ini,fin,transito,lotes)=>({id,labor:'polinizacion',evaluador:ev,usuario:u,inicio:t(ini),fin:t(fin),km:1.5,paradas:[],estado:'finalizada',
    visita:{palmas_visitadas:60,ha_recorridas:0.5,por_lote:lotes.map(l=>({lote:l,palmas_visitadas:30,ha:0.25}))},transito,secuencias:[],tiempos:null,seleccion:lotes.map(l=>({lote:l}))});
  const pas=[{c:'A',f:'boton',t:t('07:10')},{c:'A',f:'nfc',t:t('07:10')},{c:'P',f:'boton',t:t('07:11')},{c:'B',f:'boton',t:t('07:11')}];
  const J1=jor('J1','op1','GOMEZ PEREZ ANDRES','07:00','08:05',[{lote:'IT01',entrada:'Transitable',t_entrada:t('07:05'),salida:'Poco transitable',t_salida:t('08:00'),cierre:'boton'}],['IT01']);
  const R1=[reg('J1','GOMEZ PEREZ ANDRES','P101','IT01',3,1,{a:2,p:1,b:1,pas,obs:'Flor abierta'},'07:10',1.5000),
    reg('J1','GOMEZ PEREZ ANDRES','P102','IT01',3,2,{a:1,f:'nfc'},'07:12',1.5002),
    reg('J1','GOMEZ PEREZ ANDRES','P103','IT01',3,3,{cond:'R',f:'voz'},'07:14',1.5004),
    reg('J1','GOMEZ PEREZ ANDRES','P104','IT01',3,4,{b:2,f:'formulario'},'07:16',1.5006)];
  const J2=jor('J2','op2','LOPEZ DIAZ CARLOS','08:20','09:30',[{lote:'IT05',entrada:'Poco transitable',t_entrada:t('08:30'),salida:'Transitable',t_salida:t('08:50'),cierre:'boton'},
    {lote:'IT01',entrada:'Transitable',t_entrada:t('08:55'),salida:'',t_salida:''}],['IT05','IT01']);
  const R2=[reg('J2','LOPEZ DIAZ CARLOS','P201','IT05',1,1,{p:3,tr:'Poco transitable'},'08:31',1.5100),
    reg('J2','LOPEZ DIAZ CARLOS','P202','IT05',1,2,{cond:'V',tr:'Poco transitable'},'08:33',1.5102),
    reg('J2','LOPEZ DIAZ CARLOS','P203','IT05',1,3,{a:1,p:1,tr:'Poco transitable'},'08:35',1.5104),
    reg('J2','LOPEZ DIAZ CARLOS','P204','IT05',1,4,{a:1,p:2,tr:'Poco transitable'},'08:37',1.5106),
    reg('J2','LOPEZ DIAZ CARLOS','P102','IT01',3,2,{b:1},'09:00',1.5002)];
  const ahora=new Date().toISOString();
  return {g1:geoJornada(J1,R1,[],ahora,null),g2:geoJornada(J2,R2,[],ahora,null),plano:planos(R1[0]),csv:csvRegs(R1).split('\\r\\n')[0]};}"""
errores = []
EST = {}
def gh(route):
    u = route.request.url
    if '/contents/jornadas?' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps([{'type': 'dir', 'name': HOY, 'sha': 'dia1'}]))
    if u.endswith('/git/trees/dia1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps({'tree': [
        {'path': 'J1.geojson', 'type': 'blob', 'sha': 'g1'}, {'path': 'J2.geojson', 'type': 'blob', 'sha': 'g2'}]}))
    if u.endswith('/git/blobs/g1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g1']))
    if u.endswith('/git/blobs/g2'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g2']))
    route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 1400, 'height': 950}, accept_downloads=True, timezone_id='America/Bogota', locale='es-CO')
    ctx.route('https://api.github.com/**', gh)
    app = ctx.new_page(); app.on('pageerror', lambda e: errores.append('app: ' + str(e)[:200]))
    app.goto(BASE + '/index.html'); app.wait_for_function("typeof geoJornada==='function'&&typeof completarPol==='function'&&typeof S!=='undefined'", timeout=30000); time.sleep(1.5)
    r = app.evaluate(ARMAR, HOY)
    g1, g2 = r['g1'], r['g2']
    f101 = next(f for f in g1['features'] if f['properties'].get('palma_id') == 'P101')['properties']
    check('Sincronización: el punto lleva A, P, B, cond, inflorescencias, fuente, labor y pasadas',
          f101['a'] == 2 and f101['p'] == 1 and f101['b'] == 1 and f101['cond'] == '' and f101['inflorescencias'] == 4 and f101['fuente'] == 'boton'
          and f101['labor'] == 'polinizacion' and len(f101['pasadas']) == 4 and f101['n_pasadas'] == 4 and f101['nivel1'] == '2A + 1P + 1B', {k: f101.get(k) for k in ('a', 'p', 'b', 'cond', 'fuente', 'nivel1')})
    check('Sincronización: la jornada lleva la transitabilidad de cada lote y la labor',
          g1['jornada']['labor'] == 'polinizacion' and g1['jornada']['transito'][0]['salida'] == 'Poco transitable' and len(g2['jornada']['transito']) == 2, g1['jornada'].get('transito'))
    check('CSV de la App: columnas a, p, b, cond, inflorescencias, transitabilidad y fuente', all(c in r['csv'].split(';') for c in ['a', 'p', 'b', 'cond', 'inflorescencias', 'transitabilidad', 'fuente']), r['csv'][:120])
    # Importar en otro celular (historial): recupera los campos
    imp = app.evaluate("""async(g)=>{await importarJornadaGeo(g,null);const x=await dbGet('registros','J1-P101'),y=await dbGet('registros','J1-P103'),j=await dbGet('jornadas','J1');
      return {a:x.a,p:x.p,b:x.b,f:x.fuente,pas:(x.pasadas||[]).length,n1:x.n1,cond:y.cond,tr:(j.transito||[]).length};}""", g1)
    check('Importar la jornada (historial) recupera A, P, B, R, fuente, pasadas y transitabilidad', imp == {'a': 2, 'p': 1, 'b': 1, 'f': 'boton', 'pas': 4, 'n1': '2A + 1P + 1B', 'cond': 'R', 'tr': 1}, imp)
    # Registro sincronizado antes de esta versión (sin a, p, b): el visor lo lee del resumen
    f204 = next(f for f in g2['features'] if f['properties'].get('palma_id') == 'P204')['properties']
    for k in ('a', 'p', 'b', 'cond', 'inflorescencias', 'pasadas', 'n_pasadas'): f204.pop(k, None)
    EST['g1'], EST['g2'] = g1, g2

    # ---- 2. Visor ----
    vz = ctx.new_page(); vz.on('pageerror', lambda e: errores.append('visor: ' + str(e)[:200] + ' ' + (e.stack or '')[:300]))
    vz.goto(BASE + '/visor.html'); vz.wait_for_function("typeof alternarGerencia==='function'&&typeof cargar==='function'", timeout=30000); time.sleep(1)
    vz.evaluate("""async(hoy)=>{document.querySelector('#login').hidden=true;document.querySelector('#app').hidden=false;mapa.invalidateSize();window.chunkLote=async()=>[];
      SES={u:'admin1',nombre:'Admin',rol:'admin',token:'tok',repo:{owner:'didpalmares',repo:'PolinizacionData',rama:'main'}};ACCESO={usuarios:[]};aplicarPermisosGer();
      LOTES={type:'FeatureCollection',features:['IT01','IT05'].map((l,k)=>({type:'Feature',properties:{_lote:l},geometry:{type:'Polygon',coordinates:[[[-78.701,1.499+k*0.01],[-78.699,1.499+k*0.01],[-78.699,1.508+k*0.01],[-78.701,1.508+k*0.01],[-78.701,1.499+k*0.01]]]}}))};
      IND_LOTES={IT01:{n:500},IT05:{n:400}};opcionesLote();
      document.querySelector('#fDesde').value=hoy;document.querySelector('#fHasta').value=hoy;await cargar();}""", HOY)
    vz.wait_for_function("JOR.length===2", timeout=15000); time.sleep(.5)
    check('Visor: lee las 2 jornadas sincronizadas', vz.evaluate("JOR.map(j=>j.id).sort().join()") == 'J1,J2')
    # Leyenda
    ley = vz.inner_text('#leyenda')
    check('Leyenda: los 5 códigos con su nombre completo', all(f'{c}: {n}' in ley for c, n in NOMBRES.items()), ley[:200])
    check('Leyenda: sin enfermedades', 'Pudrición' not in ley and 'Enfermedad' not in ley)
    # Colores del mapa: último registro de cada palma
    col = vz.evaluate("(()=>{const o={};capaDiag.eachLayer(l=>{o[l.options.palma_id]=[l.options.codigo,l.options.fillColor];});return o;})()")
    esperado = {'P101': 'A', 'P102': 'B', 'P103': 'R', 'P104': 'B', 'P201': 'P', 'P202': 'V', 'P203': 'A', 'P204': 'A'}
    check('Mapa: una palma por marcador, color del código dominante del último registro', col == {k: [c, COLORES[c]] for k, c in esperado.items()}, col)
    # Ficha de la palma
    vz.evaluate("popupDiag(DIAGF.find(d=>d.palma_id==='P101'))"); time.sleep(.4)
    pop = vz.inner_text('.leaflet-popup-content')
    check('Ficha: resumen 2A + 1P + 1B', '2A + 1P + 1B' in pop, pop[:120])
    check('Ficha: cada conteo con su nombre completo', 'A: Inflorescencia en Antesis: 2' in pop and 'P: Inflorescencia en Post-Antesis: 1' in pop and 'B: Balón (Post-Antesis pasada): 1' in pop, pop)
    check('Ficha: operario, fecha y hora, transitabilidad, fuente y observación',
          'Operario: GOMEZ PEREZ ANDRES' in pop and f'Fecha y hora: {HOY} 07:10' in pop and 'Transitabilidad: Transitable' in pop and 'Fuente: Botón, Tarjeta NFC' in pop and 'Observación: Flor abierta' in pop, pop)
    check('Ficha: sin campos de enfermedad (cirugía, estado)', 'Cirugía' not in pop and 'Enfermedad' not in pop and 'Estado' not in pop)
    vz.evaluate("popupDiag(DIAGF.find(d=>d.palma_id==='P103'))"); time.sleep(.3)
    pop = vz.inner_text('.leaflet-popup-content')
    check('Ficha R: código y nombre, no se aplica, fuente Voz', 'R: Palma Rancho / Tapada' in pop and 'no se puede aplicar' in pop and 'Fuente: Voz' in pop, pop[:200])
    vz.evaluate("popupDiag(DIAGF.find(d=>d.palma_id==='P204'))"); time.sleep(.3)
    check('Ficha de un registro sin A, P, B (versión anterior): se lee del resumen', '1A + 2P' in vz.inner_text('.leaflet-popup-content'))
    vz.evaluate("mapa.closePopup()")
    # Panel: resumen y pestañas
    vz.click('nav.tabs [data-tab=resumen]'); time.sleep(.3)
    kp = vz.inner_text('#kpisPol')
    check('Resumen del visor: A 5 · P 7 · B 4 · % balón 25,0 % · R 1 · V 1', re.sub(r'\s+', ' ', kp).upper() == '5 A: INFLORESCENCIA EN ANTESIS 7 P: INFLORESCENCIA EN POST-ANTESIS 4 B: BALÓN (POST-ANTESIS PASADA) 25,0 % % BALÓN (B ÷ A+P+B) 1 PALMAS R: PALMA RANCHO / TAPADA 1 PALMAS V: PALMA CON AVISPAS', re.sub(r'\s+', ' ', kp))
    vz.click('nav.tabs [data-tab=diag]'); time.sleep(.3)
    T = vz.inner_text('#panel')
    check('Pestaña REGISTROS: 9 registros con código, transitabilidad y fuente', '9 registro(s)' in T and 'Tarjeta NFC' in T and 'Formulario' in T, T[:160])
    vz.click('nav.tabs [data-tab=lotes]'); time.sleep(.3)
    check('Pestaña LOTES: columnas A, P, B, % balón, R, V y sin PC', all(h in vz.inner_text('#tLot thead') for h in ['Palmas registradas', '% balón']) and 'PC' not in vz.inner_text('#tLot thead'))
    # Filtro por código (interfaz)
    vz.click('#filtros .ms[data-k=cod] .ms-bt'); time.sleep(.2)
    ops = vz.evaluate("[...document.querySelectorAll('#msL .ms-it span')].map(s=>s.innerText)")
    check('Filtro Código: A, P, B, R, V con su nombre', ops == [f'{c}: {n}' for c, n in NOMBRES.items()], ops)
    vz.click('#msL .solo[data-i="2"]'); time.sleep(.4)
    fb = vz.evaluate("({n:DIAGF.length,m:(()=>{const a=[];capaDiag.eachLayer(l=>a.push(l.options.palma_id));return a.sort().join();})(),bt:document.querySelector('#filtros .ms[data-k=cod] .ms-bt').innerText})")
    check('Filtro Código = B: 3 registros (P101, P104 y P102) y el botón dice B', fb == {'n': 3, 'm': 'P101,P102,P104', 'bt': 'B'}, fb)
    vz.evaluate("msSolo('cod','R');aplicarFiltros(false)"); time.sleep(.2)
    check('Filtro Código = R: solo la palma rancho', vz.evaluate("DIAGF.map(d=>d.palma_id).join()") == 'P103')
    vz.evaluate("msSolo('cod',null);aplicarFiltros(false)"); time.sleep(.2)
    check('Sin filtros de enfermedad en el visor', vz.evaluate("!document.querySelector('#filtros [data-k=n1]')&&!document.querySelector('#filtros [data-k=est]')&&Object.keys(FIL).join()") == 'prog,op,lote,cod')
    # Detalle de jornada: transitabilidad
    vz.evaluate("abrirDetalle(JOR.find(j=>j.id==='J2'))"); time.sleep(.4)
    det = vz.inner_text('#detalle')
    check('Detalle de la jornada: transitabilidad por lote y lote abierto', 'TRANSITABILIDAD POR LOTE' in det.upper() and 'Sin salida (lote abierto)' in det and 'Registros: 5' in det, det[-300:])
    vz.evaluate("cerrarDetalle()")

    # ---- 3. Gerencia · 🐝 Polinización ----
    vz.click('#btGer'); time.sleep(.5)
    T = vz.inner_text('#gerPanel')
    check('Gerencia: secciones Resumen, Polinización y Mapa de avance (sin Enfermedades)', '🐝 Polinización' in T and 'Mapa de avance de la polinización' in T and 'Enfermedades' not in T and 'censo' not in T.lower(), re.sub(r'\s+', ' ', T)[:200])
    check('Gerencia: filtro Código en la barra (sin enfermedad ni estado)', vz.evaluate("!!document.querySelector('#gerFil .ms[data-k=cod]')&&!document.querySelector('#gerFil .ms[data-k=n1]')&&!document.querySelector('#gerFil .ms[data-k=est]')"))
    check('Gerencia · Resumen: palmas registradas e inflorescencias', 'Palmas registradas' in T and 'Inflorescencias (A + P + B)' in T and 'Diagnósticos' not in T)
    vz.click('[data-tsub=pol]'); time.sleep(1)
    K = [re.sub(r'\s+', ' ', x) for x in vz.evaluate("[...document.querySelectorAll('#polKpis .ger-kpi')].map(k=>k.innerText)")]
    check('KPIs: 8 palmas registradas, A 5, P 7, B 4, % balón 25,0 %, R 1, V 1', K == ['8 Palmas registradas', '5 Total A: Inflorescencia en Antesis', '7 Total P: Inflorescencia en Post-Antesis', '4 Total B: Balón (Post-Antesis pasada)',
          '25,0 % % Balón = B ÷ (A + P + B)', '1 Palmas R: Palma Rancho / Tapada', '1 Palmas V: Palma con Avispas'], K)
    filas = vz.evaluate("[...document.querySelectorAll('#polLotes tbody tr')].map(t=>[...t.cells].map(c=>c.innerText.trim()))")
    check('Por lote: IT01 4 palmas, A 3, P 1, B 4, 50,0 %, R 1, V 0, entrada Transitable, salida Poco transitable (1 sin salida)',
          filas[0] == ['IT01', '—', '4', '3', '1', '4', '50,0 %', '1', '0', 'Transitable', 'Poco transitable 1 sin salida'], filas[0] if filas else filas)
    check('Por lote: IT05 4 palmas, A 2, P 6, B 0, 0,0 %, R 0, V 1, entrada Poco transitable, salida Transitable',
          len(filas) == 2 and filas[1] == ['IT05', '—', '4', '2', '6', '0', '0,0 %', '0', '1', 'Poco transitable', 'Transitable'], filas[1:] )
    bar = vz.evaluate("[...document.querySelectorAll('#polBarLote rect')].map(r=>r.dataset.lc)")
    check('Gráfico por lote: barras A/P/B apiladas', sorted(bar) == sorted(['IT01|A|3', 'IT01|P|1', 'IT01|B|4', 'IT05|A|2', 'IT05|P|6']), bar)
    sem = vz.evaluate("[...document.querySelectorAll('#polSemana rect')].map(r=>r.dataset.sc.split('|').slice(1).join(''))")
    check('Gráfico por semana: A 5, P 7, B 4 apiladas', sorted(sem) == ['A5', 'B4', 'P7'], sem)
    ops = vz.evaluate("[...document.querySelectorAll('#polOps tbody tr')].map(t=>[...t.cells].slice(0,5).map(c=>c.innerText.trim()))")
    check('Rendimiento por operario: palmas registradas, inflorescencias y palmas/día', ops == [['LOPEZ DIAZ CARLOS', '1', '5', '9', '5,0'], ['GOMEZ PEREZ ANDRES', '1', '4', '7', '4,0']], ops)
    rv = vz.evaluate("({n:GER.rvN,m:(()=>{const a=[];GER.rv.eachLayer(l=>{if(l.options&&l.options.codigo)a.push(l.options.codigo+l.options.fillColor);});return a.sort();})(),e:document.querySelector('#rvEstado').innerText})")
    check('Mapa de palmas R y V', rv['n'] == 2 and rv['m'] == ['R' + COLORES['R'], 'V' + COLORES['V']] and '1 palmas R' in rv['e'], rv)
    with vz.expect_download() as dl: vz.click('#xPolReg')
    ruta = dl.value.path(); cab = open(ruta, encoding='utf-8-sig').read().splitlines()
    cols = cab[0].split(';')
    check('CSV de registros: a, p, b, cond, inflorescencias, transitabilidad y fuente', all(c in cols for c in ['a', 'p', 'b', 'cond', 'inflorescencias', 'transitabilidad', 'fuente']) and len(cab) == 10, cols)
    fila = dict(zip(cols, next(l for l in cab[1:] if 'P101' in l).split(';')))
    check('CSV de registros: fila de P101', fila['a'] == '2' and fila['p'] == '1' and fila['b'] == '1' and fila['inflorescencias'] == '4' and fila['resumen'] == '2A + 1P + 1B' and fila['fuente'] == 'Botón, Tarjeta NFC', fila)
    # Filtro de código desde Gerencia
    vz.evaluate("msSolo('cod','V');aplicarFiltros(false)"); time.sleep(.5)
    K = [re.sub(r'\s+', ' ', x) for x in vz.evaluate("[...document.querySelectorAll('#polKpis .ger-kpi')].map(k=>k.innerText)")]
    check('Gerencia respeta el filtro Código (V: 1 palma, sin inflorescencias)', K[0] == '1 Palmas registradas' and K[4].startswith('—') and K[6].startswith('1 '), K)
    vz.evaluate("msSolo('cod',null);aplicarFiltros(false)"); time.sleep(.3)
    # Mapa de avance
    vz.click('[data-tsub=avance]'); time.sleep(1.2)
    check('Mapa de avance de la polinización (título)', 'AVANCE DE LA POLINIZACIÓN' in vz.inner_text('#avLeyenda').upper())
    # ---- 4. Coordinación y supervisión: transitabilidad ----
    vz.click('#btCoord'); time.sleep(.3)
    tabs = [b.inner_text() for b in vz.query_selector_all('#gerPanel [data-gt]')]
    check('Coordinación: pestaña TRANSITABILIDAD', 'TRANSITABILIDAD' in tabs and 'CALIDAD' in tabs and 'AUDITORÍA' in tabs, tabs)
    vz.click('[data-gt=transito]'); time.sleep(.4)
    T = vz.inner_text('#gerPanel')
    tr = vz.evaluate("[...document.querySelectorAll('#trTabla tbody tr')].map(t=>[...t.cells].map(c=>c.innerText.trim()))")
    check('Transitabilidad por lote: 3 entradas (lote, operario, entrada + hora, salida + hora, duración)',
          len(tr) == 3 and tr[0][1:] == ['IT01', 'GOMEZ PEREZ ANDRES', 'Transitable 07:05', 'Poco transitable 08:00', '0:55'] and tr[1][1:] == ['IT05', 'LOPEZ DIAZ CARLOS', 'Poco transitable 08:30', 'Transitable 08:50', '0:20'], tr)
    check('Transitabilidad: marca el lote abierto (sin salida)', tr[2][1] == 'IT01' and 'Sin salida' in tr[2][4] and tr[2][5] == '—' and '1 lote(s) quedaron abiertos' in T, tr[2] if len(tr) > 2 else T[:200])
    # Calidad y auditoría con el registro de polinización
    vz.click('[data-gt=calidad]'); time.sleep(.4); T = vz.inner_text('#gerPanel')
    check('Calidad: registros (sin «Sin foto» ni diagnósticos)', 'Registros de polinización' in T and 'Sin foto' not in T and 'iagnóstico' not in T, re.sub(r'\s+', ' ', T)[:200])
    vz.click('[data-gt=auditoria]'); time.sleep(.4); T = vz.inner_text('#gerPanel')
    check('Auditoría: textos de la polinización', 'registros de cada operario' in T and 'censador' not in T.lower())
    vz.click('#gerX')
    check('Sin errores de JavaScript', not errores, errores[:4])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
