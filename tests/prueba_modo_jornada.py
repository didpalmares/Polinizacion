"""Modo jornada: sin jornada todo visible; con jornada solo los botones de la labor, la app se fija y queda a pantalla
completa (plugin nativo simulado); el supervisor libera con su usuario (un operario no puede); 📌 vuelve a modo jornada;
al finalizar la jornada se suelta todo. Además, dos tarjetazos con 1 s de diferencia cuentan 2."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ
import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else (_os.environ.get('PRUEBAS_URL', 'http://127.0.0.1:8765').rstrip('/') + '/index.html')
errores = []
ok = True
OCULTOS = ['#btUbic', '#btCercana', '#btBD', '#btMenu', '#btLeyenda', '#btVoz', '#btSeguir']

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
    pg.wait_for_function("typeof aplicarModoJornada==='function'", timeout=30000)
    time.sleep(1.5)
    # Paquete de acceso de prueba (cifrado real) con un supervisor y un operario; plugin nativo «Botones» simulado
    pg.evaluate("""async()=>{
      const enc=new TextEncoder(),b64=u=>btoa(String.fromCharCode(...new Uint8Array(u)));
      const dkRaw=crypto.getRandomValues(new Uint8Array(32));const dk=await crypto.subtle.importKey('raw',dkRaw,{name:'AES-GCM'},false,['encrypt']);
      const cif=async(k,datos)=>{const iv=crypto.getRandomValues(new Uint8Array(12));return {iv:b64(iv),ct:b64(await crypto.subtle.encrypt({name:'AES-GCM',iv},k,datos))};};
      const usuario=async(u,clave,meta)=>{const salt=crypto.getRandomValues(new Uint8Array(16));
        const base=await crypto.subtle.importKey('raw',enc.encode(clave),'PBKDF2',false,['deriveKey']);
        const kek=await crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:1000,hash:'SHA-256'},base,{name:'AES-GCM',length:256},false,['encrypt']);
        const w=await cif(kek,dkRaw);return {u,salt:b64(salt),iv:w.iv,ct:w.ct,meta:await cif(dk,enc.encode(JSON.stringify(meta)))};};
      ACCESO={kdf:{iter:1000},usuarios:[await usuario('sup1','clave1234',{nombre:'SUPERVISOR UNO',rol:'supervisor'}),await usuario('op9','clave1234',{nombre:'OPERARIO NUEVE',rol:'operario'})]};
      window.__nat=[];window.Capacitor=window.Capacitor||{};window.Capacitor.Plugins=window.Capacitor.Plugins||{};
      window.Capacitor.Plugins.Botones={fijar:async o=>{__nat.push('fijar:'+o.on);return {fijada:o.on};},pantallaCompleta:async o=>{__nat.push('pc:'+o.on);},capturar:async()=>{},brillo:async()=>{}};
      SES={u:'op1',nombre:'Op',rol:'operario'};try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;}""")
    vis = lambda sel: pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}');return !!e&&getComputedStyle(e).display!=='none'&&!e.hidden}})()")
    pg.evaluate("S.jornada=null;actualizarJornadaUI();"); time.sleep(.3)
    check('Sin jornada: todos los botones visibles', all(vis(s) for s in ['#btUbic', '#btCercana', '#btBD', '#btMenu', '#btJornada']) and not pg.evaluate("document.body.classList.contains('modo-jornada')"))
    pg.evaluate("""()=>{const m=1/111320,f={type:'Feature',geometry:{type:'Point',coordinates:[-78.7,1.7]},properties:{_id:'P1',_lote:'L1',_linea:1,_num:1,_existe:true}};
      S.palmas={type:'FeatureCollection',features:[f]};S.idx=new Map([['P1',f]]);
      S.jornada={id:'J1',evaluador:'ANDREA CABEZAS',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      S.gps={lat:1.7+m,lng:-78.7,acc:4,t:Date.now()};actualizarJornadaUI();}"""); time.sleep(.5)
    check('Con jornada: se ocultan menú, datos, cercana, ubicación, leyenda, guía de voz y Fija', not any(vis(s) for s in OCULTOS), [s for s in OCULTOS if vis(s)])
    check('Con jornada: siguen JORNADA, barra A/P/B/R/V, micrófono y candado', vis('#btJornada') and vis('#polBar') and vis('#btBloq'))
    check('Con jornada: la app se fija y queda a pantalla completa', 'fijar:True' in [x.replace('true', 'True') for x in pg.evaluate('__nat')] and 'pc:true' in pg.evaluate('__nat'), pg.evaluate('__nat'))
    # Dos tarjetazos con 1 s de diferencia
    pg.evaluate("NFC.ult=null;nfcLeido({texto:'A',id:'0A'})"); time.sleep(1.0)
    pg.evaluate("nfcLeido({texto:'A',id:'0A'})"); time.sleep(.6)
    check('Dos tarjetazos con 1 s de diferencia: cuentan 2', pg.evaluate("(S.hechos.get('P1')||{}).a") == 2)
    # Operario intenta desbloquear: no puede
    pg.evaluate("accesoSupervisor()"); time.sleep(.3)
    pg.fill('#supU', 'op9'); pg.fill('#supC', 'clave1234'); pg.eval_on_selector('#frmSup', 'f=>f.requestSubmit()'); time.sleep(1.2)
    check('Un operario no puede desbloquear', pg.is_visible('#supMsg') and 'supervisor' in pg.text_content('#supMsg') and pg.evaluate("document.body.classList.contains('modo-jornada')"), pg.text_content('#supMsg'))
    pg.fill('#supU', 'sup1'); pg.fill('#supC', 'mala'); pg.eval_on_selector('#frmSup', 'f=>f.requestSubmit()'); time.sleep(1.2)
    check('Contraseña errada: no desbloquea', 'incorrectos' in pg.text_content('#supMsg'))
    pg.evaluate("__nat.length=0"); pg.fill('#supC', 'clave1234'); pg.eval_on_selector('#frmSup', 'f=>f.requestSubmit()'); time.sleep(1.2)
    check('Supervisor: desbloquea, suelta la app y muestra todo', not pg.evaluate("document.body.classList.contains('modo-jornada')") and vis('#btMenu') and 'fijar:false' in pg.evaluate('__nat') and vis('#btModoJ'), pg.evaluate('__nat'))
    check('La jornada sigue activa y queda anotado quién desbloqueó', pg.evaluate("!!S.jornada && S.jornada.desbloqueos[0].usuario") == 'sup1')
    pg.evaluate("__nat.length=0"); pg.eval_on_selector('#btModoJ', 'b=>b.click()'); time.sleep(.4)
    check('📌 vuelve a modo jornada (fija la app otra vez)', pg.evaluate("document.body.classList.contains('modo-jornada')") and 'fijar:true' in pg.evaluate('__nat') and not vis('#btMenu'))
    pg.evaluate("__nat.length=0;S.jornada=null;actualizarJornadaUI();"); time.sleep(.4)
    check('Al finalizar la jornada: se suelta la app y vuelven los botones', not pg.evaluate("document.body.classList.contains('modo-jornada')") and 'fijar:false' in pg.evaluate('__nat') and vis('#btMenu'))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
