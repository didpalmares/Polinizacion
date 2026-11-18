"""Bloqueo de pantalla del registro (modo campo): botón 🔒, capa negra que no deja tocar, NFC activo mientras está bloqueada,
desbloqueo manteniendo 2 s (un toque corto no desbloquea), volumen arriba (evento nativo simulado con alternarBloqueo)
y desbloqueo automático cuando hay que elegir la transitabilidad de un lote."""
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
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined' && typeof bloquearPantalla==='function'", timeout=30000)
    time.sleep(1.5)
    check('Sin jornada: botón 🔒 oculto', pg.is_hidden('#btBloq'))
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};try{ocultarSplash()}catch(e){}
      const m=1/111320,f=(id,lote,lat)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7,lat]},properties:{_id:id,_lote:lote,_linea:1,_num:id.slice(1),_existe:true}});
      S.palmas={type:'FeatureCollection',features:[f('P1','L1',1.7),f('Q1','L2',1.7+200*m)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));try{indexar()}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      await dbPut('jornadas',S.jornada);actualizarJornadaUI();window.__gps=n=>{S.gps={lat:1.7+n*m,lng:-78.7,acc:4,t:Date.now()};};__gps(1);pintarPolBar();
    }""")
    check('Con jornada: botón 🔒 visible', pg.is_visible('#btBloq'))
    pg.eval_on_selector('#btBloq', 'b=>b.click()'); time.sleep(.3)
    check('Bloquear: capa negra visible', pg.is_visible('#bloqueo') and pg.evaluate('BLOQ.on'))
    check('Bloquear: avisa por voz', 'Pantalla bloqueada' in ' '.join(pg.evaluate('window.__dichos')))
    # Un toque sobre el botón A (debajo de la capa) no registra nada
    box = pg.evaluate("(()=>{const r=document.querySelector('#polBar [data-c=A]').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
    pg.mouse.click(box[0], box[1]); time.sleep(.3)
    check('Bloqueada: los toques no registran', pg.evaluate("S.registros.length") == 0)
    # La tarjeta NFC sí registra con la pantalla bloqueada
    pg.evaluate("sumarCodigo('A','nfc')"); time.sleep(.3)
    check('Bloqueada: NFC registra 1A', pg.evaluate("(S.hechos.get('P1')||{}).a") == 1)
    check('Bloqueada: muestra el último registro', '1A' in pg.text_content('#bqUlt'), pg.text_content('#bqUlt'))
    # Toque corto en 🔓: sigue bloqueada
    b0 = pg.locator('#btDesbloq').bounding_box(); pg.mouse.click(b0['x'] + 20, b0['y'] + 10); time.sleep(.4)
    check('Toque corto en 🔓: sigue bloqueada', pg.evaluate('BLOQ.on'))
    # Mantener 2 s: desbloquea
    b = pg.locator('#btDesbloq').bounding_box()
    pg.mouse.move(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2); pg.mouse.down(); time.sleep(2.3); pg.mouse.up(); time.sleep(.3)
    check('Mantener 2 s en 🔓: desbloquea', not pg.evaluate('BLOQ.on') and pg.is_hidden('#bloqueo'))
    # Volumen arriba (evento nativo «volumenLargo» → alternarBloqueo)
    pg.evaluate('alternarBloqueo()'); time.sleep(.2)
    on1 = pg.evaluate('BLOQ.on')
    pg.evaluate('alternarBloqueo()'); time.sleep(.2)
    check('Volumen arriba 2 s: bloquea y desbloquea', on1 and not pg.evaluate('BLOQ.on'))
    # Bloqueada y entra a otro lote por NFC: se desbloquea para elegir la transitabilidad
    pg.evaluate('bloquearPantalla()'); time.sleep(.2)
    pg.evaluate("__gps(200);void(window.__p=sumarCodigo('P','nfc'))")
    pg.wait_for_selector('#hojaCuerpo [data-t="Transitable"]', timeout=5000)
    check('Cambio de lote: se desbloquea para la transitabilidad', not pg.evaluate('BLOQ.on'))
    pg.eval_on_selector('#hojaCuerpo [data-t="Poco transitable"]', 'b=>b.click()')
    pg.wait_for_selector('#hojaCuerpo [data-t="Transitable"]', timeout=5000)
    pg.eval_on_selector('#hojaCuerpo [data-t="Transitable"]', 'b=>b.click()')
    pg.evaluate('window.__p'); time.sleep(.3)
    check('Cambio de lote: Q1 = 1P', pg.evaluate("(S.hechos.get('Q1')||{}).p") == 1)
    # Al terminar la jornada se quita el bloqueo y el botón
    pg.evaluate('bloquearPantalla()'); time.sleep(.2)
    pg.evaluate('S.jornada=null;actualizarJornadaUI();'); time.sleep(.2)
    check('Sin jornada: se desbloquea y oculta 🔒', not pg.evaluate('BLOQ.on') and pg.is_hidden('#btBloq'))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
