"""Grabar tarjetas NFC desde la app: solo administrador, analista de datos y super administrador ven «Grabar tarjetas NFC»;
al grabar (lector nativo simulado) la app aprende el número único con el código nuevo (una tarjeta regrabada no cuenta con el
código viejo); «Verificar tarjeta» muestra el código sin registrar nada."""
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
    pg.wait_for_function("typeof panelGrabarNfc==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""()=>{try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;
      localStorage.setItem('pol_nfc_uid',JSON.stringify({'04CAFE':'A'}));NFC.uids=null;
      window.__g=[];window.Capacitor=window.Capacitor||{};window.Capacitor.Plugins=window.Capacitor.Plugins||{};
      window.Capacitor.Plugins.Nfc={addListener:async()=>({remove(){}}),estado:async()=>({disponible:true,habilitado:true,activo:true}),iniciar:async()=>({}),reiniciar:async()=>({}),
        grabar:async o=>{__g.push(o.texto);await new Promise(r=>setTimeout(r,300));return {ok:true,id:'04CAFE',texto:o.texto};},cancelarGrabacion:async()=>{}};
      nfcNativoDisponible=()=>true;NFC.modo='nativo';NFC.estado='listo';}""")
    for rol, debe in [('operario', False), ('supervisor', False), ('admin', True), ('analista', True), ('superadmin', True)]:
        tiene = pg.evaluate(f"(()=>{{SES={{u:'x',nombre:'X',rol:'{rol}'}};menu();const r=!!document.querySelector('#mNfcG');cerrarHoja();return r;}})()")
        time.sleep(.2)
        check(f'Rol {rol}: {"ve" if debe else "no ve"} «Grabar tarjetas NFC»', tiene == debe)
    pg.evaluate("SES={u:'adm',nombre:'ADMIN',rol:'admin'};panelGrabarNfc()"); time.sleep(.3)
    check('Panel con los 5 códigos y su nombre completo', pg.evaluate("[...document.querySelectorAll('#grbCods [data-g]')].map(b=>b.textContent).join('|')").count('|') == 4
          and 'Inflorescencia en Post-Antesis' in pg.text_content('#grbCods'))
    pg.eval_on_selector('#grbCods [data-g="P"]', 'b=>b.click()')
    pg.eval_on_selector('#grbOk', 'b=>b.click()'); time.sleep(1)
    check('Grabar P: llama al lector nativo y confirma', pg.evaluate('__g') == ['P'] and 'grabada con P' in pg.text_content('#grbMsg'), pg.text_content('#grbMsg'))
    check('Regrabada (A → P): la app aprende el código nuevo de inmediato', pg.evaluate("uidsNfc()['04CAFE']") == 'P')
    pg.eval_on_selector('#grbVer', 'b=>b.click()'); time.sleep(.3)
    r = pg.evaluate("nfcLeido({texto:'P',id:'04CAFE'})"); time.sleep(.3)
    check('Verificar: muestra el código y no registra', r == 'verificada' and 'Esta tarjeta es P' in pg.text_content('#grbMsg') and pg.evaluate("S.registros.length") == 0, pg.text_content('#grbMsg'))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
