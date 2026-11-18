"""NFC «súper»: la app aprende cada tarjeta por su número único (UID) con la primera lectura completa; después, si el contenido
no alcanza a leerse (pasada muy rápida), el número basta para registrar. Una tarjeta desconocida sin contenido sigue avisando;
una tarjeta regrabada actualiza su código con la siguiente lectura completa."""
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

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    ctx.add_init_script(INIT_VOZ)
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("typeof uidsNfc==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""()=>{localStorage.removeItem('pol_nfc_uid');NFC.uids=null;SES={u:'op1',nombre:'Op',rol:'operario'};const m=1/111320;
      const f={type:'Feature',geometry:{type:'Point',coordinates:[-78.7,1.7]},properties:{_id:'P1',_lote:'L1',_linea:1,_num:1,_existe:true}};
      S.palmas={type:'FeatureCollection',features:[f]};S.idx=new Map([['P1',f]]);
      S.jornada={id:'J1',evaluador:'Op',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      S.gps={lat:1.7+m,lng:-78.7,acc:4,t:Date.now()};NFC.ult=null;actualizarJornadaUI();}""")
    a = lambda: pg.evaluate("(S.hechos.get('P1')||{}).a||0")
    r = pg.evaluate("nfcLeido({texto:'',id:'04A1B2',motivo:'lectura'})"); time.sleep(.6)
    check('Tarjeta nunca leída y sin contenido: avisa y no registra', r == 'fallida' and a() == 0, r)
    r = pg.evaluate("nfcLeido({texto:'A',id:'04A1B2'})"); time.sleep(.6)
    check('Primera lectura completa: registra 1A y aprende la tarjeta', r == 'ok' and a() == 1 and pg.evaluate("uidsNfc()['04A1B2']") == 'A', pg.evaluate("uidsNfc()"))
    r = pg.evaluate("nfcLeido({texto:'',id:'04A1B2',motivo:'lectura'})"); time.sleep(.6)
    check('Pasada rápida sin contenido: el número único basta (2A)', r == 'ok' and a() == 2, r)
    check('Conteo «por número único»', pg.evaluate("S.jornada.nfc.por_uid") == 1)
    check('Lo aprendido queda guardado en el celular', pg.evaluate("JSON.parse(localStorage.getItem('pol_nfc_uid'))['04A1B2']") == 'A')
    pg.evaluate("nfcLeido({texto:'P',id:'04A1B2'})"); time.sleep(.6)
    check('Tarjeta regrabada como P: se actualiza con la lectura completa', pg.evaluate("uidsNfc()['04A1B2']") == 'P' and pg.evaluate("(S.hechos.get('P1')||{}).p") == 1)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
