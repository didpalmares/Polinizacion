"""Vigilancia del lector NFC nativo (plugin simulado): se reinicia al iniciar la jornada, al volver a la app y si quedó inactivo; no tras la
transitabilidad. Validado en campo (lector «activo» que deja de leer tras 1-2 h): con APK anterior la app lo rearma tras 60 s sin lecturas;
con APK 1.0.10 el lector se rearma solo y la app vuelve a conectar la escucha si el lector leyó y no le llegó. Todo queda en nfc.eventos."""
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
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.goto(URL)
    pg.wait_for_function("typeof asegurarNfc==='function'", timeout=30000)
    time.sleep(1.5)
    # Plugin nativo simulado
    pg.evaluate("""()=>{
      window.__nfc={reinicios:0,iniciar:0,habilitado:true,activo:false,lis:{},adds:0,lecturas:undefined,rearmes:0};
      window.Capacitor=window.Capacitor||{};window.Capacitor.Plugins=window.Capacitor.Plugins||{};
      window.Capacitor.Plugins.Nfc={
        addListener:async(n,f)=>{__nfc.adds++;__nfc.lis[n]=f;return {remove(){}};},
        estado:async()=>({disponible:true,habilitado:__nfc.habilitado,activo:__nfc.activo,lecturas:__nfc.lecturas,rearmes:__nfc.rearmes,ecos:0,ultimaLectura:0}),
        iniciar:async()=>{__nfc.iniciar++;__nfc.activo=true;return {}},
        reiniciar:async()=>{__nfc.reinicios++;__nfc.activo=true;return {}},
        detener:async()=>{__nfc.activo=false;return {}}};
      nfcNativoDisponible=()=>true;
    }""")
    pg.evaluate("iniciarNfc(false)"); time.sleep(.3)
    check('Al abrir: NFC listo', pg.evaluate("NFC.estado") == 'listo' and pg.evaluate("NFC.modo") == 'nativo')
    r0 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};try{ocultarSplash()}catch(e){}
      const m=1/111320,f=(id,lote,lat)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7,lat]},properties:{_id:id,_lote:lote,_linea:1,_num:id.slice(1),_existe:true}});
      S.palmas={type:'FeatureCollection',features:[f('P1','L1',1.7)]};S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));try{indexar()}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',transito:[]};
      S.gps={lat:1.7+m,lng:-78.7,acc:4,t:Date.now()};actualizarJornadaUI();
    }"""); time.sleep(.4)
    check('Al iniciar la jornada: reinicia el lector', pg.evaluate("__nfc.reinicios") > r0, pg.evaluate("__nfc.reinicios"))
    # Primera tarjeta: pide transitabilidad; al cerrarla se reinicia el lector y la tarjeta suma
    r1 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("__nfc.lis.tarjeta({texto:'A',id:'01'})")
    pg.wait_for_selector('#hojaCuerpo [data-t="Transitable"]', timeout=5000)
    pg.eval_on_selector('#hojaCuerpo [data-t="Transitable"]', 'b=>b.click()'); time.sleep(.6)
    check('Tras elegir la transitabilidad: NO reinicia (evita apagar el lector justo al acercar la tarjeta)', pg.evaluate("__nfc.reinicios") == r1)
    check('La tarjeta A sumó 1A', pg.evaluate("(S.hechos.get('P1')||{}).a") == 1)
    # APK anterior: lector «activo» pero sin lecturas hace más de 60 s → la app lo rearma (lector dormido, caso de campo)
    r2 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("NFC.ultLect=Date.now()-600000;NFC.ultReinicio=0;__nfc.activo=true;asegurarNfc('revisar')"); time.sleep(.3)
    check('APK anterior, lector «activo» sin lecturas en 10 min: lo rearma', pg.evaluate("__nfc.reinicios") == r2 + 1)
    check('El rearme queda anotado en la jornada (nfc.eventos)', pg.evaluate("S.jornada.nfc.eventos.some(e=>e.tipo==='rearme_reposo')"))
    r2 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("asegurarNfc('revisar')"); time.sleep(.3)
    check('No lo rearma otra vez antes de 60 s', pg.evaluate("__nfc.reinicios") == r2)
    pg.evaluate("__nfc.activo=false;asegurarNfc('revisar')"); time.sleep(.3)
    check('Lector inactivo: la revisión lo reinicia', pg.evaluate("__nfc.reinicios") > r2)
    r3 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("NFC.ultLect=Date.now();NFC.ultReinicio=Date.now();asegurarNfc('revisar')"); time.sleep(.3)
    check('Leyendo y reiniciado hace poco: no reinicia', pg.evaluate("__nfc.reinicios") == r3)
    # APK 1.0.10: el lector se rearma solo (la app no lo rearma) y la app detecta lecturas que no le llegaron
    pg.evaluate("__nfc.lecturas=5;__nfc.rearmes=7;NFC.ultLect=Date.now()-600000;NFC.ultReinicio=0;NFC_VIGIA.base=null"); r4 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("asegurarNfc('revisar')"); time.sleep(.3)
    check('APK 1.0.10: la app no rearma (lo hace el lector nativo)', pg.evaluate("__nfc.reinicios") == r4 and pg.evaluate("S.jornada.nfc.rearmes_lector") == 7)
    a0 = pg.evaluate("__nfc.adds")
    pg.evaluate("__nfc.lecturas=8;asegurarNfc('revisar')"); time.sleep(.3)
    check('Lecturas que no llegaron (1.ª revisión): espera', pg.evaluate("__nfc.adds") == a0)
    pg.evaluate("asegurarNfc('revisar')"); time.sleep(.3)
    check('Lecturas que no llegaron (2.ª revisión): vuelve a conectar la escucha', pg.evaluate("__nfc.adds") == a0 + 2
          and pg.evaluate("S.jornada.nfc.eventos.some(e=>e.tipo==='escucha_reconectada'&&e.perdidas===3)"), pg.evaluate("S.jornada.nfc.eventos"))
    pg.evaluate("__nfc.lis.tarjeta({texto:'A',id:'01',t:Date.now()})"); time.sleep(.6)
    check('Tras reconectar: la tarjeta suma (2A)', pg.evaluate("(S.hechos.get('P1')||{}).a") == 2)
    pg.evaluate("__nfc.lecturas=9;asegurarNfc('revisar')"); time.sleep(.3); pg.evaluate("asegurarNfc('revisar')"); time.sleep(.3)
    check('Lecturas al día: no reconecta de más', pg.evaluate("__nfc.adds") == a0 + 2)
    pg.evaluate("__nfc.lecturas=undefined")
    # NFC apagado en el celular
    pg.evaluate("__nfc.habilitado=false;asegurarNfc('revisar')"); time.sleep(.3)
    check('NFC del celular apagado: lo muestra', pg.evaluate("NFC.estado") == 'apagado' and 'apagado' in pg.text_content('#polNfc'), pg.text_content('#polNfc'))
    pg.evaluate("__nfc.habilitado=true;asegurarNfc('volver')"); time.sleep(.3)
    check('Al volver con NFC encendido: listo otra vez', pg.evaluate("NFC.estado") == 'listo')
    # APK anterior sin «reiniciar»: usa iniciar
    pg.evaluate("delete Capacitor.Plugins.Nfc.reiniciar;__nfc.iniciar=0;asegurarNfc('jornada')"); time.sleep(.3)
    check('APK anterior (sin reiniciar): usa iniciar', pg.evaluate("__nfc.iniciar") >= 1 and pg.evaluate("NFC.estado") == 'listo')
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
