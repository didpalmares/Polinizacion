"""Vigilancia del lector NFC nativo (plugin simulado): se reinicia al iniciar la jornada, al volver a la app y solo si el lector quedó inactivo
(no se reinicia periódicamente ni tras la transitabilidad: cada reinicio lo apaga un instante); si el NFC del celular está apagado lo muestra; y una lectura sigue sumando."""
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
      window.__nfc={reinicios:0,iniciar:0,habilitado:true,activo:false,lis:{}};
      window.Capacitor=window.Capacitor||{};window.Capacitor.Plugins=window.Capacitor.Plugins||{};
      window.Capacitor.Plugins.Nfc={
        addListener:async(n,f)=>{__nfc.lis[n]=f;return {remove(){}};},
        estado:async()=>({disponible:true,habilitado:__nfc.habilitado,activo:__nfc.activo}),
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
    # Más de 60 s sin leer: la revisión periódica lo reinicia
    r2 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("NFC.ultLect=Date.now()-600000;__nfc.activo=true;asegurarNfc('revisar')"); time.sleep(.3)
    check('Lector activo sin lecturas en 10 min: NO reinicia', pg.evaluate("__nfc.reinicios") == r2)
    pg.evaluate("__nfc.activo=false;asegurarNfc('revisar')"); time.sleep(.3)
    check('Lector inactivo: la revisión lo reinicia', pg.evaluate("__nfc.reinicios") > r2)
    r3 = pg.evaluate("__nfc.reinicios")
    pg.evaluate("NFC.ultLect=Date.now();NFC.ultReinicio=Date.now();asegurarNfc('revisar')"); time.sleep(.3)
    check('Leyendo y reiniciado hace poco: no reinicia', pg.evaluate("__nfc.reinicios") == r3)
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
