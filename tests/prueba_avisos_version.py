"""Avisos de versión nueva: la app web se actualiza sola si no hay jornada (y avisa con banner si la hay), sin recargas repetidas;
la APK nueva aparece en un banner (consulta cada 15 min con ETag: 304 no gasta el límite de GitHub) y al cerrarlo vuelve a las 4 h."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else (_os.environ.get('PRUEBAS_URL', 'http://127.0.0.1:8765').rstrip('/') + '/index.html')
errores = []
ok = True
API = {'n': 0, 'etag_recibido': [], 'tag': 'apk-1.0.9', 'web': None}

def check(nombre, cond, extra=''):
    global ok
    print(('OK   ' if cond else 'FALLA') + ' ' + nombre + (' · ' + str(extra) if extra != '' else ''))
    ok = ok and bool(cond)

def gh(route):
    API['n'] += 1
    inm = route.request.headers.get('if-none-match')
    API['etag_recibido'].append(inm)
    if inm == '"e1"' and API['tag'] == 'apk-1.0.9':
        route.fulfill(status=304, headers={'ETag': '"e1"', 'Access-Control-Allow-Origin': '*', 'Access-Control-Expose-Headers': 'ETag'}); return
    route.fulfill(status=200, content_type='application/json', headers={'ETag': '"e1"', 'Access-Control-Allow-Origin': '*', 'Access-Control-Expose-Headers': 'ETag'},
                  body=json.dumps({'tag_name': API['tag']}))

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900},
                          user_agent='Mozilla/5.0 (Linux; Android 14) Chrome/130 Mobile PolinizacionAPK/1 v1.0.3')
    ctx.add_init_script(INIT_VOZ)
    ctx.route('**/version.json*', lambda r: r.fulfill(status=200, content_type='application/json', body=json.dumps({'version': API['web'] or '00000000:0000'})))
    ctx.route('https://api.github.com/repos/didpalmares/Polinizacion/releases/latest', gh)
    ctx.route('https://api.github.com/repos/**/contents/**', lambda r: r.fulfill(status=404, body='{}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: d.dismiss())
    pg.add_init_script("window.__aplicar=0;")
    pg.goto(URL)
    pg.wait_for_function("typeof revisarNovedades==='function'", timeout=30000)
    time.sleep(6.5)  # deja pasar la revisión automática del arranque (a los 5 s)
    pg.evaluate("aplicarActualizacion=async()=>{window.__aplicar++;};localStorage.removeItem('sv_auto_act');localStorage.removeItem('sv_apk_ultima');")
    API['web'] = '29991231:2359'
    # Sin jornada: se actualiza sola
    pg.evaluate("buscarActualizacion(false)"); time.sleep(.5)
    check('Web sin jornada: se actualiza sola', pg.evaluate('window.__aplicar') == 1)
    pg.evaluate("buscarActualizacion(false)"); time.sleep(.5)
    check('Web: no repite la recarga automática (muestra banner)', pg.evaluate('window.__aplicar') == 1 and pg.is_visible('#bannerAct'))
    # Con jornada: banner, sin recargar
    pg.evaluate("localStorage.removeItem('sv_auto_act');document.querySelector('#bannerAct').hidden=true;S.jornada={id:'J',estado:'activa',seleccion:[]};buscarActualizacion(false)"); time.sleep(.5)
    check('Web con jornada: solo banner, no recarga', pg.evaluate('window.__aplicar') == 1 and pg.is_visible('#bannerAct'))
    pg.evaluate("S.jornada=null")
    # APK nueva: banner
    pg.evaluate("avisoApk()"); time.sleep(.6)
    check('APK 1.0.9 > 1.0.3: banner visible', pg.is_visible('#bannerApk') and '1.0.9' in pg.text_content('#bkTxt'), pg.text_content('#bkTxt'))
    n1 = API['n']
    pg.evaluate("avisoApk()"); time.sleep(.4)
    check('Antes de 15 min: no vuelve a consultar GitHub', API['n'] == n1)
    pg.evaluate("{const c=JSON.parse(localStorage.getItem('sv_apk_ultima'));c.t-=16*60000;localStorage.setItem('sv_apk_ultima',JSON.stringify(c));};avisoApk()"); time.sleep(.6)
    check('Después de 15 min: consulta con ETag (respuesta 304)', API['n'] == n1 + 1 and API['etag_recibido'][-1] == '"e1"' and pg.evaluate('APK.ultima') == '1.0.9', API['etag_recibido'][-1])
    pg.eval_on_selector('#bkNo', 'b=>b.click()'); time.sleep(.2)
    pg.evaluate("avisoApk()"); time.sleep(.4)
    check('Cerrado: no reaparece de inmediato', pg.is_hidden('#bannerApk'))
    pg.evaluate("localStorage.setItem('sv_apk_cerrado_1.0.9',String(Date.now()-5*3600e3));avisoApk()"); time.sleep(.4)
    check('Cerrado hace más de 4 h: reaparece', pg.is_visible('#bannerApk'))
    # Ya tiene la última APK: sin banner
    API['tag'] = 'apk-1.0.3'
    pg.evaluate("localStorage.removeItem('sv_apk_ultima');avisoApk()"); time.sleep(.6)
    check('Con la última APK: sin banner', pg.is_hidden('#bannerApk'))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
