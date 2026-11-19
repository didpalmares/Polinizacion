"""Guardia de pantalla: con jornada la app pide al plugin nativo mostrarse encima del bloqueo y reencender la pantalla si el
operario la apaga; sigue activa aunque el supervisor libere el modo jornada; cada reencendido queda anotado en la jornada
(y en el reporte); si Android no deja reencender, avisa; al finalizar la jornada se apaga la guardia."""
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
    pg.wait_for_function("typeof aplicarGuardia==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""()=>{window.__g=[];window.__lis={};window.Capacitor=window.Capacitor||{};window.Capacitor.Plugins=window.Capacitor.Plugins||{};
      window.Capacitor.Plugins.Botones={fijar:async o=>({fijada:o.on}),pantallaCompleta:async()=>{},capturar:async()=>{},brillo:async()=>{},
        guardia:async o=>{__g.push(o.on);return {activa:o.on};},addListener:(ev,f)=>{__lis[ev]=f;return {remove(){}};}};
      SES={u:'op1',nombre:'Op',rol:'operario'};try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;
      S.jornada=null;actualizarJornadaUI();}"""); time.sleep(.4)
    check('Sin jornada: la guardia no se enciende', True not in pg.evaluate('__g'), pg.evaluate('__g'))
    pg.evaluate("""()=>{S.jornada={id:'J1',evaluador:'OP',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',transito:[]};
      actualizarJornadaUI();}"""); time.sleep(.5)
    check('Al iniciar la jornada: guardia encendida (app sobre el bloqueo y reencendido)', pg.evaluate('__g')[-1:] == [True], pg.evaluate('__g'))
    pg.evaluate("__lis.pantallaReencendida({ok:true,reencendidos:1})"); time.sleep(.3)
    check('Reencendido anotado en la jornada', pg.evaluate("S.jornada.pantalla_reencendida.length") == 1 and pg.evaluate("S.jornada.pantalla_reencendida[0].ok") is True)
    pg.evaluate("__lis.pantallaReencendida({ok:false,reencendidos:2})"); time.sleep(.3)
    check('Si Android no deja reencender: queda anotado y avisa', pg.evaluate("S.jornada.pantalla_reencendida[1].ok") is False and 'Encender la pantalla' in pg.evaluate("document.body.innerText"))
    pg.evaluate("MODO.libre=true;aplicarModoJornada(true)"); time.sleep(.3)
    check('Supervisor libera el modo jornada: la guardia sigue', pg.evaluate('__g')[-1] is True and pg.evaluate('__g').count(True) == 1)
    pr = pg.evaluate("(()=>{const g=geoJornada(S.jornada,[],[],new Date().toISOString(),null);const f=[g.jornada||{},g.properties||{},...(g.features||[]).map(x=>x.properties||{})].find(o=>o.pantalla_reencendida);return f?f.pantalla_reencendida:null;})()")
    check('El reporte de la jornada incluye los reencendidos', pr is not None and len(pr) == 2, pr)
    pg.evaluate("S.jornada=null;actualizarJornadaUI();"); time.sleep(.4)
    check('Al finalizar la jornada: guardia apagada', pg.evaluate('__g')[-1] is False, pg.evaluate('__g'))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
