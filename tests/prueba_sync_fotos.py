"""Sincronización de una jornada finalizada CON fotos (error «raiz is not defined» tras retirar los módulos):
envía jornadas/<fecha>/<id>.geojson y jornadas/<fecha>/<id>_fotos.zip en un commit y deja los registros sincronizados. GitHub simulado."""
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
    ctx = nav.new_context(service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: (errores.append('alert: ' + d.message), d.accept()))
    ctx.route('https://api.github.com/**', gh)
    pg.goto(URL)
    pg.wait_for_function("typeof sincronizar==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};S.cfg.gh={...S.cfg.gh,token:'tok-prueba'};
      const j={id:'JF1',evaluador:'Operario Uno',usuario:'op1',inicio:'2026-11-18T13:00:00.000Z',fin:'2026-11-18T15:00:00.000Z',estado:'finalizada',
        sync:'pendiente',labor:'polinizacion',seleccion:[],densidad:115,buffer:5,paradas:[],resumen_paradas:{},visita:{},secuencias:[],tiempos:{},
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:'2026-11-18T13:05:00.000Z',salida:'Poco transitable',t_salida:'2026-11-18T14:55:00.000Z'}]};
      await dbPut('jornadas',j);
      const buf=new Uint8Array([255,216,255,224,0,16,74,70,73,70]).buffer;
      await dbPut('fotos',{id:'F1',registro_id:'R1',buf,type:'image/jpeg'});
      const r={id:'R1',palma_id:'P1',jornada_id:'JF1',evaluador:'Operario Uno',labor:'polinizacion',a:2,p:1,b:0,cond:'',fotos:['F1'],sync:'pendiente',
        lote:'L1',linea:1,numero:1,lat:1.7,lng:-78.7,creado:'2026-11-18T13:10:00.000Z',fecha:'2026-11-18T08:10:00'};
      completarPol(r);await dbPut('registros',r);S.registros=await dbAll('registros');S.jornada=null;S.cfg.jornadaActiva=null;
      await sincronizar(true);
    }""")
    time.sleep(.5)
    rutas = arboles[0] if arboles else []
    check('Envía el geojson de la jornada', 'jornadas/2026-11-18/JF1.geojson' in rutas, rutas)
    check('Envía el zip de fotos en jornadas/<fecha>/', 'jornadas/2026-11-18/JF1_fotos.zip' in rutas, rutas)
    est = pg.evaluate("async()=>({j:(await dbGet('jornadas','JF1')).sync,r:(await dbGet('registros','R1')).sync,err:SYNC.error})")
    check('Jornada y registro quedan sincronizados, sin error', est['j'] == 'sincronizado' and est['r'] == 'sincronizado' and not est['err'], est)
    check('Sin errores de JavaScript ni alertas', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
