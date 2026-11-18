"""Registro por voz y tarjetas NFC: frases («dos A una P», «balón», «erre», «deshacer», «repetir») → conteos de la palma
más cercana con fuente «voz»; lecturas NFC (texto «A», «pol:P») con fuente «nfc», antirrebote de 1,5 s por tarjeta,
retiro y nuevo toque, tarjeta desconocida y Web NFC simulado (botón «Activar NFC»)."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, BASE
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else BASE + '/index.html'
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)

# Web NFC simulado: NDEFReader.scan() deja el lector en window.__ndef para disparar lecturas.
INIT_NFC = """
window.NDEFReader=class{scan(){window.__ndef=this;return Promise.resolve();}write(m,o){window.__escrito={m,o:{overwrite:o&&o.overwrite}};return Promise.resolve();}};
window.__leerNdef=(txt,serial)=>window.__ndef&&window.__ndef.onreading({serialNumber:serial,message:{records:[{recordType:'text',encoding:'utf-8',data:new TextEncoder().encode(txt)}]}});
"""
errores = []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True, args=['--use-fake-ui-for-media-stream'])
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900}, permissions=['microphone'])
    ctx.add_init_script(INIT_VOZ + INIT_NFC)
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: (errores.append('DIALOGO: ' + d.message), d.dismiss()))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined'&&typeof sumarCodigo==='function'&&typeof nfcLeido==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      document.querySelector('#login').hidden=true;SES={u:'op1',nombre:'Operario Uno',rol:'operario'};
      const m=1/111320,f=(id,num,lat)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7,lat]},properties:{_id:id,_lote:'L1',_linea:1,_num:num,_existe:true}});
      S.palmas={type:'FeatureCollection',features:[f('P1',1,1.7),f('P2',2,1.7+40*m)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));
      if(typeof indexar==='function')try{indexar();}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),estado:'activa',seleccion:[],labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      await dbPut('jornadas',S.jornada);actualizarJornadaUI();
      window.__gps=n=>{S.gps={lat:1.7+n*m,lng:-78.7,acc:4,t:Date.now()};};__gps(1);}""")

    def reg(pid):
        return pg.evaluate(f"(()=>{{const r=S.hechos.get('{pid}');return r?{{a:r.a,p:r.p,b:r.b,cond:r.cond,f:(r.pasadas||[]).map(x=>x.f)}}:null}})()")
    def dichos(): return pg.evaluate("window.__dichos")
    def listo(t=10):
        fin = time.time() + t
        while time.time() < fin:
            if pg.evaluate("!RV.hablando&&!!window.__srOn&&RV.nh===0"): return True
            time.sleep(0.05)
        return False
    def decir(txt, t=10):
        """Dice la frase y espera la respuesta hablada de la app; devuelve lo último que dijo."""
        assert listo(), 'el micrófono no quedó escuchando'
        n0 = len(dichos())
        assert pg.evaluate(f"window.__hablar({txt!r})"), 'sin micrófono: ' + txt
        fin = time.time() + t
        while time.time() < fin and len(dichos()) <= n0: time.sleep(0.05)
        listo(); time.sleep(0.1)
        return dichos()[-1] if len(dichos()) > n0 else ''
    def esperar(cond_js, t=5):
        fin = time.time() + t
        while time.time() < fin:
            if pg.evaluate(cond_js): return True
            time.sleep(0.05)
        return False

    # ---------- Voz ----------
    check('Botón «Registro por voz» visible', pg.is_visible('#btDxVoz') and pg.get_attribute('#btDxVoz', 'aria-label') == 'Registro por voz')
    pg.click('#btDxVoz')
    esperar("window.__dichos.join(' ').includes('Registro por voz activado')")
    check('Activa y escucha', listo() and pg.evaluate("PV.on"), dichos()[-1:])
    d = decir('dos A una P')
    r = reg('P1')
    check('«dos A una P» → 2A + 1P', r and (r['a'], r['p'], r['b']) == (2, 1, 0), r)
    check('Fuente «voz» en cada pasada', r and r['f'] == ['voz'] * 3, r and r['f'])
    check('Confirma solo una vez con el estado final', '2 antesis, una post antesis' in d and sum('antesis' in x for x in dichos()[-2:]) == 1, d)
    d = decir('balón')
    check('«balón» → 1B', reg('P1')['b'] == 1, d)
    d = decir('erre')
    check('«erre» rechazada (la palma ya tiene inflorescencias)', reg('P1')['cond'] == '' and 'Deshaga' in d, d)
    d = decir('repetir')
    check('«repetir» repite la última confirmación', 'Deshaga' in d, d)
    d = decir('deshacer')
    check('«deshacer» quita el último registro (B)', (reg('P1')['a'], reg('P1')['p'], reg('P1')['b']) == (2, 1, 0) and 'Deshecho' in d, d)
    d = decir('pe')
    check('Letra dicha como palabra: «pe» → P', reg('P1')['p'] == 2, d)
    d = decir('3 a')
    check('Número en cifras: «3 a» → +3A', reg('P1')['a'] == 5, d)
    d = decir('post antesis un be')
    check('«post antesis un be» → +1P +1B (no confunde con A)', (reg('P1')['a'], reg('P1')['p'], reg('P1')['b']) == (5, 3, 1), (reg('P1'), d))
    n_antes = pg.evaluate("S.registros.length"); r0 = reg('P1')
    d = decir('hola qué tal')
    check('Frase sin código: no registra y avisa', reg('P1') == r0 and 'No entendí' in d, d)
    d = decir('once A')
    check('Más de diez no registra', reg('P1') == r0 and 'diez' in d, d)
    # La palma P2 (40 m) queda fuera del radio; al acercarse, V la marca y luego A se rechaza
    pg.evaluate("__gps(39.5)")
    d = decir('avispas')
    check('«avispas» → V en la palma más cercana', reg('P2') and reg('P2')['cond'] == 'V', (reg('P2'), d))
    d = decir('una A')
    check('A después de V: rechazada', reg('P2')['a'] == 0, d)
    # Mientras la app habla, el micrófono está en pausa: lo que «oiga» no se registra
    pg.evaluate("void decir('Prueba de pausa del micrófono con la palabra antesis')")
    esperar("RV.hablando")
    check('Micrófono en pausa mientras la app habla', pg.evaluate("!window.__srOn") and not pg.evaluate("window.__hablar('a')"))
    listo()
    pg.click('#btDxVoz'); time.sleep(0.3)
    check('Desactivar registro por voz', not pg.evaluate("PV.on") and not pg.evaluate("RV.on"))

    # ---------- NFC ----------
    pg.evaluate("__gps(1)")
    check('Web NFC sin permiso: muestra «Activar NFC»', pg.text_content('#polNfc') == 'Activar NFC', pg.text_content('#polNfc'))
    pg.click('#polNfc'); esperar("NFC.estado==='listo'")
    check('Tras tocar: «NFC listo»', pg.text_content('#polNfc') == 'NFC listo', pg.text_content('#polNfc'))
    a0 = reg('P1')['a']
    r1 = pg.evaluate("nfcLeido({texto:'A',id:'04AA'})")
    esperar(f"S.hechos.get('P1').a==={a0 + 1}")
    check('Tarjeta «A» suma 1A con fuente nfc', reg('P1')['a'] == a0 + 1 and reg('P1')['f'][-1] == 'nfc' and r1 == 'ok', (r1, reg('P1')))
    r2 = pg.evaluate("nfcLeido({texto:'A',id:'04AA'})"); time.sleep(0.4)
    check('Misma tarjeta sin retirarla (<1,5 s): ignorada', r2 == 'repetida' and reg('P1')['a'] == a0 + 1, r2)
    pg.evaluate("nfcRetirada({id:'04AA'})")
    r3 = pg.evaluate("nfcLeido({texto:'A',id:'04AA'})")
    esperar(f"S.hechos.get('P1').a==={a0 + 2}")
    check('Retirada y acercada de nuevo: cuenta otra vez', r3 == 'ok' and reg('P1')['a'] == a0 + 2, r3)
    p0 = reg('P1')['p']
    pg.evaluate("nfcLeido({texto:'pol:P',id:'04BB'})")
    esperar(f"S.hechos.get('P1').p==={p0 + 1}")
    check('Tarjeta «pol:P» suma 1P', reg('P1')['p'] == p0 + 1, reg('P1'))
    time.sleep(1.6)
    r4 = pg.evaluate("nfcLeido({texto:'pol:P',id:'04BB'})")
    esperar(f"S.hechos.get('P1').p==={p0 + 2}")
    check('Misma tarjeta después de 1,5 s: cuenta', r4 == 'ok' and reg('P1')['p'] == p0 + 2, r4)
    r_ant = reg('P1')
    r5 = pg.evaluate("nfcLeido({texto:'X',id:'04CC'})"); time.sleep(0.3)
    check('Tarjeta desconocida: no registra', r5 == 'desconocida' and reg('P1') == r_ant, r5)
    b0 = reg('P1')['b']
    pg.evaluate("__leerNdef('B','04:DD')")
    esperar(f"S.hechos.get('P1').b==={b0 + 1}")
    check('Web NFC: lectura de texto «B» suma 1B', reg('P1')['b'] == b0 + 1, reg('P1'))
    pg.evaluate("__leerNdef('B','04:DD')"); time.sleep(0.4)
    check('Web NFC: rebote de la misma tarjeta ignorado', reg('P1')['b'] == b0 + 1, reg('P1'))
    check('Interpretación: códigos de tarjeta', pg.evaluate("['A','a',' pol:V ','POL://r','AB','pol:X',''].map(codigoNfc)") == ['A', 'A', 'V', 'R', None, None, None])

    # ---------- Administración: grabar tarjetas ----------
    adm = ctx.new_page()
    adm.on('pageerror', lambda e: errores.append('admin: ' + str(e)))
    adm.goto(BASE + '/admin.html')
    adm.click('#tabs [data-t="nfc"]')
    check('Admin: pestaña «Grabar tarjetas NFC» con los 5 códigos', adm.is_visible('#nfc') and adm.locator('#nfcCods [data-c]').count() == 5
          and 'Inflorescencia en Antesis' in adm.text_content('#nfcCods') and adm.is_hidden('#nfcNo'))
    check('Admin: GRABAR deshabilitado hasta elegir código', adm.is_disabled('#nfcGrabar'))
    adm.click('#nfcCods [data-c="R"]'); adm.click('#nfcGrabar')
    adm.wait_for_function("document.querySelector('#nfcMsg').classList.contains('bien')", timeout=5000)
    esc = adm.evaluate("window.__escrito")
    check('Admin: graba un registro NDEF de texto «R»', esc and esc['m']['records'][0]['recordType'] == 'text' and esc['m']['records'][0]['data'] == 'R'
          and esc['o']['overwrite'] is True and 'Palma Rancho' in adm.text_content('#nfcMsg'), esc)
    sin = nav.new_context(service_workers='block')
    adm2 = sin.new_page(); adm2.goto(BASE + '/admin.html'); adm2.click('#tabs [data-t="nfc"]')
    check('Admin sin Web NFC (escritorio): aviso para usar Chrome en Android', adm2.is_visible('#nfcNo') and 'Android' in adm2.text_content('#nfcNo') and adm2.is_disabled('#nfcLeer'))
    sin.close()

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
