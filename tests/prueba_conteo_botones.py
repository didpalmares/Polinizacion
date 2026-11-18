"""Cantidades sobre los botones A, P y B (y ✓ sobre R o V) de la palma que se está trabajando (la más cercana)."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ
import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else (_os.environ.get('PRUEBAS_URL', 'http://127.0.0.1:8765').rstrip('/') + '/index.html')
errores = []
ok = True

def check(nombre, cond, extra=''):
    global ok
    print(('OK   ' if cond else 'FALLA') + ' ' + nombre + (' · ' + str(extra) if extra != '' else ''))
    ok = ok and bool(cond)

def badges(pg):
    return pg.evaluate("Object.fromEntries([...document.querySelectorAll('#polBar [data-c]')].map(b=>{const i=b.querySelector('.pol-n');return [b.dataset.c,i&&!i.hidden?i.textContent:'']}))")

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    ctx.add_init_script(INIT_VOZ)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined' && typeof sumarCodigo==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};try{ocultarSplash()}catch(e){}
      const m=1/111320,f=(id,lat)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7,lat]},properties:{_id:id,_lote:'L1',_linea:1,_num:id.slice(1),_existe:true}});
      S.palmas={type:'FeatureCollection',features:[f('P1',1.7),f('P2',1.7+9*m)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));try{indexar()}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      await dbPut('jornadas',S.jornada);actualizarJornadaUI();window.__gps=n=>{S.gps={lat:1.7+n*m,lng:-78.7,acc:4,t:Date.now()};};__gps(1);pintarPolBar();
    }""")
    check('Palma sin registro: botones sin número', badges(pg) == {'A': '', 'P': '', 'B': '', 'R': '', 'V': ''}, badges(pg))
    for c in 'AAPB':
        pg.evaluate(f"sumarCodigo('{c}','boton')"); time.sleep(.15)
    check('P1 con 2A + 1P + 1B: A=2, P=1, B=1', badges(pg) == {'A': '2', 'P': '1', 'B': '1', 'R': '', 'V': ''}, badges(pg))
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Deshacer: B vuelve a vacío', badges(pg) == {'A': '2', 'P': '1', 'B': '', 'R': '', 'V': ''}, badges(pg))
    pg.evaluate("__gps(9.5);pintarPolBar()")
    check('Al pasar a P2 (sin registro): se limpian', badges(pg) == {'A': '', 'P': '', 'B': '', 'R': '', 'V': ''}, badges(pg))
    pg.evaluate("sumarCodigo('V','boton')"); time.sleep(.2)
    check('P2 con V: ✓ sobre V', badges(pg)['V'] == '✓' and badges(pg)['A'] == '', badges(pg))
    pg.evaluate("__gps(1);pintarPolBar()")
    check('Al volver a P1: muestra otra vez 2 y 1', badges(pg) == {'A': '2', 'P': '1', 'B': '', 'R': '', 'V': ''}, badges(pg))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
