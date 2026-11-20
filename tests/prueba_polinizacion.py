"""Registro de polinización: botones A/P/B/R/V a la palma existente más cercana (10 m), combinaciones,
R y V solas, existencia 0 excluida, transitabilidad una sola vez al entrar a cada lote (nunca al salir) y deshacer. GitHub simulado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, BASE
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else BASE + '/index.html'
errores, dialogos = [], []
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
    pg.on('console', lambda m: m.type == 'error' and '404' not in m.text and errores.append('console: ' + m.text))
    pg.on('dialog', lambda d: (dialogos.append(d.message), d.accept()))
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined' && typeof sumarCodigo==='function' && !!document.querySelector('#polBar')", timeout=30000)
    time.sleep(1.5)

    # Dos lotes: L1 con palmas cada 9 m (la 3 es existencia 0) y L2 a 200 m.
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};
      const f=(id,lote,ln,num,lat,lng,existe=true)=>({type:'Feature',geometry:{type:'Point',coordinates:[lng,lat]},
        properties:{_id:id,_lote:lote,_linea:ln,_num:num,_existe:existe}});
      const m=1/111320;
      S.palmas={type:'FeatureCollection',features:[f('P1','L1',1,1,1.7,-78.7),f('P2','L1',1,2,1.7+9*m,-78.7),f('P3','L1',1,3,1.7+18*m,-78.7,false),
        f('Q1','L2',1,1,1.7+200*m,-78.7)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));
      if(typeof indexar==='function')try{indexar();}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),estado:'activa',seleccion:[],labor:'polinizacion'};
      await dbPut('jornadas',S.jornada);
      actualizarJornadaUI();
      window.__gps=(metrosN)=>{S.gps={lat:1.7+metrosN*m,lng:-78.7,acc:4,t:Date.now()};};
    }""")

    def tocar(c, transito=None):
        pg.evaluate(f"void(window.__p=sumarCodigo('{c}','boton'))")
        if transito:
            pg.wait_for_selector(f'#hojaCuerpo [data-t="{transito}"]', timeout=5000)
            pg.eval_on_selector(f'#hojaCuerpo [data-t="{transito}"]', 'b=>b.click()')
        pg.evaluate("window.__p")
        time.sleep(.15)

    def reg(pid):
        return pg.evaluate(f"(()=>{{const r=S.hechos.get('{pid}');return r?{{a:r.a,p:r.p,b:r.b,cond:r.cond,n1:r.n1,tr:r.transitabilidad,est:r.estado}}:null}})()")

    check('Barra visible con jornada activa', pg.is_visible('#polBar'))

    # Sin GPS no registra
    pg.evaluate("S.gps=null")
    tocar('A')
    check('Sin GPS: no registra', reg('P1') is None)

    # Junto a P1 (1 m): pide transitabilidad de entrada y suma
    pg.evaluate("__gps(1)")
    tocar('A', 'Poco transitable')
    tocar('A'); tocar('P'); tocar('B')
    r = reg('P1')
    check('P1 = 2A + 1P + 1B', r and (r['a'], r['p'], r['b']) == (2, 1, 1) and r['n1'] == '2A + 1P + 1B', r)
    check('Transitabilidad de entrada en el registro', r and r['tr'] == 'Poco transitable', r)
    tramo = pg.evaluate("S.jornada.transito")
    check('Tramo del lote L1 abierto', len(tramo) == 1 and tramo[0]['lote'] == 'L1' and tramo[0]['entrada'] == 'Poco transitable' and 'salida' not in tramo[0], tramo)

    # R no se combina con inflorescencias
    tocar('R')
    check('R rechazada si ya hay inflorescencias', reg('P1')['cond'] == '' and reg('P1')['a'] == 2)

    # Deshacer quita la última B
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Deshacer: P1 queda 2A + 1P', (reg('P1')['a'], reg('P1')['p'], reg('P1')['b']) == (2, 1, 0), reg('P1'))

    # P2 (a 9 m): V sola, y luego no acepta A
    pg.evaluate("__gps(9.5)")
    tocar('V'); tocar('A')
    r2 = reg('P2')
    check('P2 = V sola (no acepta A después)', r2 and r2['cond'] == 'V' and r2['a'] == 0 and r2['est'] == 'no_aplica', r2)

    # P3 existencia 0: con GPS encima, debe ir a la palma existente más cercana (P2), no a P3
    pg.evaluate("__gps(18)")
    tocar('B')
    check('Existencia 0 nunca se registra', reg('P3') is None)

    # Lejos de todo (100 m): no registra
    pg.evaluate("__gps(100)")
    n0 = pg.evaluate("S.registros.length")
    tocar('A')
    check('A más de 10 m de cualquier palma: no registra', pg.evaluate("S.registros.length") == n0)

    # Cambio de lote: NO pregunta salida de L1; pregunta solo la entrada a L2 (primera vez)
    pg.evaluate("__gps(200)")
    pg.evaluate("void(window.__p=sumarCodigo('A','nfc'))")
    pg.wait_for_selector('#hojaCuerpo [data-t="Transitable"]', timeout=5000)
    titulo2 = pg.text_content('#hojaTitulo')
    pg.eval_on_selector('#hojaCuerpo [data-t="Transitable"]', 'b=>b.click()')
    pg.evaluate("window.__p"); time.sleep(.2)
    tramo = pg.evaluate("S.jornada.transito")
    check('Cambio de lote: sin pregunta de salida de L1; una sola pregunta al entrar a L2', 'L2' in titulo2 and 'salida' not in titulo2.lower()
          and len(tramo) == 2 and 'salida' not in tramo[0] and tramo[1]['lote'] == 'L2' and tramo[1]['entrada'] == 'Transitable', tramo)
    check('Q1 = 1A (fuente NFC)', reg('Q1') and reg('Q1')['a'] == 1 and pg.evaluate("S.hechos.get('Q1').fuente") == 'nfc')

    # Formulario manual de la palma: existencia 0 bloqueada
    rg = pg.evaluate("reglaDiagnostico(S.idx.get('P3'))")
    check('Formulario: existencia 0 bloqueada', not rg['ok'] and 'existencia 0' in rg['motivo'], rg.get('motivo'))

    # Volver a un lote ya registrado: no vuelve a preguntar y usa la misma transitabilidad
    pg.evaluate("__gps(1)"); n0 = len(pg.evaluate("S.jornada.transito"))
    pg.evaluate("sumarCodigo('P','boton')"); time.sleep(.6)
    check('Volver a L1: no pregunta otra vez (una sola vez por lote)', pg.evaluate("document.querySelector('#hoja').classList.contains('oculto')") and reg('P1')['p'] == 2
          and len(pg.evaluate("S.jornada.transito")) == n0 and reg('P1')['tr'] == 'Poco transitable', pg.evaluate("S.jornada.transito"))
    check('Sin botón «Finalizar lote»', pg.evaluate("!document.querySelector('#polFin')"))

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
