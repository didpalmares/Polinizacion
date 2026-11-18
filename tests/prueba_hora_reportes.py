"""Reportes en hora real: con el celular 20 min atrasado (medido), lo sincronizado sale corregido: jornada (inicio/fin/hh:mm),
recorrido, paradas, secuencias, registros guardados con hora del teléfono y pasadas; la carpeta va por la fecha real;
los registros ya guardados con hora real no se corren dos veces; «hora_fin» vuelve a ser hh:mm."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else (_os.environ.get('PRUEBAS_URL', 'http://127.0.0.1:8765').rstrip('/') + '/index.html')
errores, arboles = [], []
ok = True

def check(nombre, cond, extra=''):
    global ok
    print(('OK   ' if cond else 'FALLA') + ' ' + nombre + (' · ' + str(extra) if extra != '' else ''))
    ok = ok and bool(cond)

def gh(route):
    req = route.request
    if req.method == 'POST' and req.url.endswith('/git/trees'):
        arboles.append([t['path'] for t in json.loads(req.post_data)['tree']])
    route.fulfill(status=200, content_type='application/json', body=json.dumps({'sha': 'abc123', 'object': {'sha': 'base1'}, 'tree': {'sha': 'tree1'}}))

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', timezone_id='America/Bogota')
    ctx.route('https://api.github.com/**', gh)
    ctx.route('**/version.json*', lambda r: r.fulfill(status=200, content_type='application/json', body='{"version":"00000000:0000"}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: (errores.append('alert: ' + d.message), d.accept()))
    pg.goto(URL)
    pg.wait_for_function("typeof horaRealJornada==='function'", timeout=30000)
    time.sleep(1.5)
    r = pg.evaluate("""async()=>{
      HORA.desfase=null;HORA.fuente='';
      const T=Date.parse('2026-11-18T23:50:00-05:00'); // celular: 11:50 p. m. del 18; real (+20 min): 12:10 a. m. del 19
      const j={id:'JH1',evaluador:'Op',usuario:'op1',inicio:new Date(T).toISOString(),fin:new Date(T+3600000).toISOString(),estado:'finalizada',sync:'pendiente',labor:'polinizacion',
        hora:{fuente:'telefono',desfase_s:0},hora_fin:{fuente:'gps',desfase_s:1200},seleccion:[],densidad:115,buffer:5,
        paradas:[{n:1,inicio:T+600000,fin:T+900000,lat:1.7,lng:-78.7,duracion_min:5,tipo:'sin actividad'}],resumen_paradas:{},
        secuencias:[{tipo:'lote',lote:'L1',inicio:new Date(T).toISOString(),fin:new Date(T+1800000).toISOString(),hora_inicio:'23:50',hora_fin:'00:20',inicio_labor:new Date(T+60000).toISOString(),hora_inicio_labor:'23:51'}],
        visita:{t0_visita:new Date(T).toISOString(),palmas_visitadas:0,por_lote:[]},tiempos:{},transito:[]};
      const regs=[
        {id:'R1',palma_id:'P1',jornada_id:'JH1',lote:'L1',linea:1,numero:1,lat:1.7,lng:-78.7,labor:'polinizacion',a:1,p:0,b:0,cond:'',fotos:[],sync:'pendiente',
         creado:new Date(T+120000).toISOString(),creado_telefono:new Date(T+120000).toISOString(),fecha:'2026-11-18T23:52',hora_fuente:'telefono',desfase_hora_s:0,
         pasadas:[{c:'A',f:'boton',t:new Date(T+120000).toISOString()}]},
        {id:'R2',palma_id:'P2',jornada_id:'JH1',lote:'L1',linea:1,numero:2,lat:1.7,lng:-78.7,labor:'polinizacion',a:2,p:0,b:0,cond:'',fotos:[],sync:'pendiente',
         creado:new Date(T+1200000+300000).toISOString(),creado_telefono:new Date(T+300000).toISOString(),fecha:'2026-11-19T00:15',hora_fuente:'gps',desfase_hora_s:1200}];
      regs.forEach(x=>completarPol(x));
      const pts=[{j:'JH1',t:T,lat:1.7,lng:-78.7,acc:4},{j:'JH1',t:T+60000,lat:1.7001,lng:-78.7,acc:4}];
      const HR=horaRealJornada(j,regs,pts);const g=geoJornada(HR.j,HR.regs,HR.pts,new Date().toISOString(),null);
      const reg=id=>g.features.find(f=>f.properties.tipo==='diagnostico'&&f.properties.id===id).properties;
      const rec=g.features.find(f=>f.properties.tipo==='recorrido').properties;const par=g.features.find(f=>f.properties.tipo==='parada').properties;
      // sincronización real (carpeta por fecha real)
      await dbPut('jornadas',j);for(const x of regs)await dbPut('registros',x);for(const q of pts)await dbPut('track',{...q,id:'JH1-'+q.t});
      S.registros=await dbAll('registros');S.jornada=null;S.cfg.jornadaActiva=null;SES={u:'op1',nombre:'Op',rol:'operario'};S.cfg.gh={...S.cfg.gh,token:'tok'};
      await sincronizar(true);
      return {D:HR.D,jor:g.jornada,rec0:rec.tiempos[0],par:[par.hora_inicio,par.inicio],sec:g.jornada.secuencias[0],r1:reg('R1'),r2:reg('R2'),t0v:g.jornada.t0_visita};
    }""")
    j = r['jor']
    check('Desfase de la jornada: +20 min (medido con GPS al finalizar)', r['D'] == 1200000, r['D'])
    check('Jornada: inicio, fecha y hh:mm en hora real', j['fecha'] == '2026-11-19' and j['hora_inicio'] == '00:10' and j['hora_fin'] == '01:10', [j['fecha'], j['hora_inicio'], j['hora_fin']])
    check('«hora_fin» es hh:mm (no lo pisa el estado de la hora)', isinstance(j['hora_fin'], str) and j.get('hora_validacion_fin', {}).get('fuente') == 'gps', j.get('hora_validacion_fin'))
    check('Recorrido en hora real', r['rec0'].startswith('2026-11-19T05:10'), r['rec0'])
    check('Paradas en hora real', r['par'][0] == '00:20' and r['par'][1].startswith('2026-11-19T05:20'), r['par'])
    check('Secuencias en hora real', r['sec']['hora_inicio'] == '00:10' and r['sec']['hora_inicio_labor'] == '00:11', [r['sec']['hora_inicio'], r['sec']['hora_inicio_labor']])
    check('Registro con hora del teléfono: corregido (+20 min) y pasadas', r['r1']['fecha'] == '2026-11-19T00:12' and r['r1']['hora_fuente'] == 'corregida' and r['r1']['pasadas'][0]['t'].startswith('2026-11-19T05:12'), [r['r1']['fecha'], r['r1']['hora_fuente']])
    check('Registro ya en hora real (GPS): no se corre dos veces', r['r2']['fecha'] == '2026-11-19T00:15' and r['r2']['hora_fuente'] == 'gps', r['r2']['fecha'])
    check('Inicio de la visita en hora real', (r['t0v'] or '').startswith('2026-11-19T05:10'), r['t0v'])
    rutas = arboles[-1] if arboles else []
    check('Sincronización: carpeta por la fecha real (2026-11-19)', 'jornadas/2026-11-19/JH1.geojson' in rutas, rutas)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
