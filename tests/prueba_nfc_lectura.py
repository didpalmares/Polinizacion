"""Lectura NFC más robusta: dos pasadas seguidas de la misma tarjeta (A, A) cuentan 2 sin depender de detectar el retiro;
un rebote (< 0,45 s) se ignora; lectura fallida y tarjeta en blanco avisan con un mensaje claro y no registran;
el conteo de lecturas queda en la jornada."""
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
    pg.wait_for_function("typeof nfcLeido==='function' && typeof statsNfc==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{SES={u:'op1',nombre:'Op',rol:'operario'};const m=1/111320;
      const f={type:'Feature',geometry:{type:'Point',coordinates:[-78.7,1.7]},properties:{_id:'P1',_lote:'L1',_linea:1,_num:1,_existe:true}};
      S.palmas={type:'FeatureCollection',features:[f]};S.idx=new Map([['P1',f]]);
      S.jornada={id:'J1',evaluador:'Op',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      S.gps={lat:1.7+m,lng:-78.7,acc:4,t:Date.now()};NFC.ult=null;actualizarJornadaUI();}""")
    a = pg.evaluate("nfcLeido({texto:'A',id:'0A'})"); time.sleep(.6)
    b = pg.evaluate("nfcLeido({texto:'A',id:'0A'})"); time.sleep(.6)
    check('A, A con 0,6 s entre pasadas: cuenta 2 (sin depender del retiro)', a == 'ok' and b == 'ok' and pg.evaluate("(S.hechos.get('P1')||{}).a") == 2, (a, b))
    c = pg.evaluate("nfcLeido({texto:'A',id:'0A'})")
    d = pg.evaluate("nfcLeido({texto:'A',id:'0A'})"); time.sleep(.6)
    check('Rebote (< 0,45 s): se ignora', c == 'ok' and d == 'repetida' and pg.evaluate("(S.hechos.get('P1')||{}).a") == 3, (c, d))
    e = pg.evaluate("nfcLeido({texto:'',id:'0B',motivo:'lectura'})"); time.sleep(.2)
    check('Lectura fallida: avisa «No se leyó bien…» y no registra', e == 'fallida' and 'No se leyó bien' in pg.text_content('#toast'), pg.text_content('#toast'))
    f2 = pg.evaluate("nfcLeido({texto:'',id:'0B',motivo:'lectura'})")
    check('Tras una lectura fallida, la misma tarjeta se puede volver a leer de inmediato', f2 == 'fallida')
    g = pg.evaluate("nfcLeido({texto:'',id:'0C',motivo:'sin_ndef'})"); time.sleep(.2)
    check('Tarjeta en blanco: avisa que hay que grabarla', g == 'desconocida' and 'en blanco' in pg.text_content('#toast'), pg.text_content('#toast'))
    s = pg.evaluate("S.jornada.nfc")
    check('Conteo de lecturas en la jornada', s and s['ok'] == 3 and s['repetidas'] == 1 and s['fallidas'] == 2 and s['en_blanco'] == 1 and s['lecturas'] == 7, s)
    gj = pg.evaluate("geoJornada(S.jornada,[],[],new Date().toISOString(),null).jornada.nfc")
    check('El conteo NFC se sincroniza con la jornada', gj and gj['ok'] == 3, gj)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
