"""Finalizar la jornada SIEMPRE (caso de campo: «no deja finalizar»): confirmación dentro de la app (no el confirm() nativo);
«Seguir trabajando» no finaliza; si el registro nativo del recorrido se queda colgado y el cálculo de palmas visitadas falla, la
jornada igual se finaliza, se guarda y anota los pasos fallidos; VOLUMEN ABAJO 10 s (evento nativo simulado) finaliza sin preguntar."""
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

PREP = """async(id)=>{try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;SES={u:'op1',nombre:'ANGULO ORDOÑEZ MELISSA',rol:'operario'};
  const m=1/111320,mk=(i,l,ln,x,y)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7+x*m,1.7+y*m]},properties:{_id:i,_lote:l,_linea:String(ln),_num:'1',_existe:true}});
  S.palmas={type:'FeatureCollection',features:[mk('a1','GU06',1,0,0),mk('a2','GU06',2,9,0),mk('c1','RI02',0,300,0)]};indexar();
  S.jornada={id,evaluador:'ANGULO ORDOÑEZ MELISSA',estado:'activa',seleccion:[{lote:'GU06'},{lote:'RI02'}],inicio:new Date(Date.now()-6*3600e3).toISOString(),labor:'polinizacion',transito:[]};
  S.registros=S.registros.filter(r=>r.jornada_id!==id);
  const r=nuevoRegistroPol(S.idx.get('a1'));Object.assign(r,{a:2});completarPol(r);r.jornada_id=id;S.registros.push(r);S.hechos.set('a1',r);await dbPut('registros',r);
  await dbPut('jornadas',S.jornada);S.cfg.jornadaActiva=id;actualizarJornadaUI();}"""

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    ctx.add_init_script(INIT_VOZ)
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    dialogos = []
    pg.on('dialog', lambda d: (dialogos.append(d.message), d.dismiss()))
    pg.goto(URL)
    pg.wait_for_function("typeof finalizarJornada==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate(PREP, 'J1'); time.sleep(.3)
    # 1) Confirmación dentro de la app; «Seguir trabajando» no finaliza
    pg.evaluate("void(window.__f=finalizarJornada())"); time.sleep(.4)
    check('Pide confirmar dentro de la app (sin diálogo nativo)', pg.is_visible('#cfSi') and not dialogos and 'Finalizar la jornada' in pg.text_content('#hojaTitulo'), dialogos)
    pg.eval_on_selector('#cfNo', 'b=>b.click()'); time.sleep(.4)
    check('«Seguir trabajando»: la jornada sigue activa', pg.evaluate("!!S.jornada&&S.jornada.estado==='activa'"))
    # 2) Registro nativo colgado + cálculo que falla: igual finaliza
    pg.evaluate("""()=>{FIN.escala=0.01;window.__cr=cerrarRecorrido;cerrarRecorrido=()=>new Promise(()=>{});window.__cv=calcularVisita;calcularVisita=async()=>{throw new Error('falla simulada');};}""")
    pg.evaluate("void(window.__f=finalizarJornada())"); time.sleep(.4)
    pg.eval_on_selector('#cfSi', 'b=>b.click()')
    pg.wait_for_function("document.querySelector('#hojaTitulo').textContent==='Jornada finalizada'", timeout=15000)
    j = pg.evaluate("(async()=>await dbGet('jornadas','J1'))()")
    check('Con el registro colgado y el cálculo fallando: la jornada queda finalizada y guardada', j['estado'] == 'finalizada' and pg.evaluate("S.jornada") is None, j['estado'])
    pasos = [e['paso'] for e in j.get('errores_cierre') or []]
    check('Anota los pasos que fallaron', 'cerrar_recorrido' in pasos and 'palmas_visitadas' in pasos, pasos)
    check('Muestra el aviso y el resumen (acumulado por línea)', 'Algunos cálculos no se completaron' in pg.text_content('#hojaCuerpo') and pg.is_visible('#tabAcum'))
    check('El reporte incluye errores_cierre', pg.evaluate("(async()=>{const j=await dbGet('jornadas','J1');return geoJornada(j,[],[],new Date().toISOString(),null).jornada.errores_cierre.length;})()") == 2)
    pg.evaluate("cerrarRecorrido=__cr;calcularVisita=__cv;FIN.escala=1;cerrarHoja()")
    # 3) VOLUMEN ABAJO 10 s (evento del plugin nativo): finaliza sin preguntar
    pg.evaluate(PREP, 'J2'); time.sleep(.3)
    pg.evaluate("finalizarPorVolumen()")
    pg.wait_for_function("document.querySelector('#hojaTitulo').textContent==='Jornada finalizada'", timeout=15000)
    j2 = pg.evaluate("(async()=>await dbGet('jornadas','J2'))()")
    check('Volumen abajo 10 s: finaliza sin confirmar', j2['estado'] == 'finalizada' and j2['cierre']['modo'] == 'volumen_abajo' and not (j2.get('errores_cierre')), j2.get('cierre'))
    check('Volumen abajo sin jornada: no hace nada', pg.evaluate("(async()=>{await finalizarPorVolumen();return S.jornada===null})()"))
    check('Sin diálogos nativos y sin errores de JavaScript', not dialogos and not errores, (dialogos, errores[:3]))
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
