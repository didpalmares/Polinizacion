"""Solo el Super administrador puede iniciar jornadas fuera de la plantación (pruebas): queda marcada como prueba y se
sincroniza en pruebas/jornadas/; los demás roles (operario, supervisor, administrador, analista) siguen bloqueados."""
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
    ctx.route('https://api.github.com/**', gh)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL)
    pg.wait_for_function("typeof motivoNoIniciar==='function'", timeout=30000)
    time.sleep(1.5)
    # Plantación de 1 km² alrededor de (1.70, -78.70); el operario está a ~5,5 km
    pg.evaluate("""()=>{S.plantacion={type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'Polygon',coordinates:[[[-78.705,1.695],[-78.695,1.695],[-78.695,1.705],[-78.705,1.705],[-78.705,1.695]]]}}]};
      S.gps={lat:1.75,lng:-78.70,acc:5,t:Date.now()};}""")
    for rol in ['operario', 'supervisor', 'admin', 'analista']:
        m = pg.evaluate(f"(()=>{{SES={{u:'x',nombre:'X',rol:'{rol}'}};return motivoNoIniciar();}})()")
        check(f'Rol {rol} fuera de la plantación: bloqueado', bool(m) and 'por fuera de la plantación' in m, (m or '')[:60])
    m = pg.evaluate("(()=>{SES={u:'jbuila',nombre:'BUILA',rol:'superadmin'};return motivoNoIniciar();})()")
    check('Super administrador fuera de la plantación: puede iniciar (prueba)', m is None and pg.evaluate("S.pruebaFuera&&S.pruebaFuera.motivo") == 'fuera_plantacion', pg.evaluate("S.pruebaFuera"))
    pg.evaluate("S.gps=null")
    check('Super administrador sin GPS: puede iniciar (prueba)', pg.evaluate("motivoNoIniciar()") is None and pg.evaluate("S.pruebaFuera.motivo") == 'sin_gps')
    pg.evaluate("S.gps={lat:1.70,lng:-78.70,acc:5,t:Date.now()}")
    check('Super administrador dentro de la plantación: jornada normal (no es prueba)', pg.evaluate("motivoNoIniciar()") is None and pg.evaluate("S.pruebaFuera") is None)
    # Iniciar de verdad fuera de la plantación y sincronizar: va a pruebas/jornadas/
    r = pg.evaluate("""async()=>{SES={u:'jbuila',nombre:'BUILA',rol:'superadmin'};S.cfg.gh={...S.cfg.gh,token:'tok'};S.gps={lat:1.75,lng:-78.70,acc:5,t:Date.now()};
      try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;
      await iniciarJornada([{lote:'L1'}],'BUILA');const j=S.jornada;const prueba=j&&j.prueba;
      j.fin=new Date().toISOString();j.estado='finalizada';j.sync='pendiente';await dbPut('jornadas',j);S.jornada=null;S.cfg.jornadaActiva=null;
      await sincronizar(true);return {prueba,toast:document.querySelector('#toast').textContent};}""")
    check('La jornada queda marcada como prueba', r['prueba'] and r['prueba']['motivo'] == 'fuera_plantacion' and r['prueba']['usuario'] == 'jbuila', r['prueba'])
    rutas = arboles[-1] if arboles else []
    check('Se sincroniza aparte, en pruebas/jornadas/', any(x.startswith('pruebas/jornadas/') for x in rutas) and not any(x.startswith('jornadas/') for x in rutas), rutas)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
