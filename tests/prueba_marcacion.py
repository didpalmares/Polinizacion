"""Marcación de palmas visitadas (pedido de campo: no se marcaban las palmas de las calles donde no se aplicaba nada).
Al entrar por GPS a un lote programado la app pregunta «¿Iniciar marcación?» (pantalla y voz); al aceptar pide la transitabilidad
(primera vez) y, con la marcación activa, cuentan las palmas del lote a <= 3,2 m del recorrido; sin marcación no cuenta el recorrido
(solo los registros); al salir del lote 90 s se finaliza sola; botón ▶ MARCAR y voz «iniciar / finalizar marcación»;
el recálculo (fin de jornada) da lo mismo que en vivo; la marcación queda en el reporte."""
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
    pg.wait_for_function("typeof vigilarLoteMarcacion==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Op',rol:'operario'};try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;
      const ky=111320,kx=ky*Math.cos(1.7*Math.PI/180),lat0=1.7,lng0=-78.7;window.__K={kx,ky,lat0,lng0};
      const rows=[];let id=1;
      for(let ln=1;ln<=3;ln++){const x=(ln-1)*8.7,off=(ln%2)?0:5;for(let n=0;n<12;n++){const y=10+off+n*10;rows.push([id++,ln,n+1,1,lng0+x/kx,lat0+y/ky]);}}
      const poli=[[lng0-10/kx,lat0],[lng0+30/kx,lat0],[lng0+30/kx,lat0+140/ky],[lng0-10/kx,lat0+140/ky],[lng0-10/kx,lat0]];
      S.lotes={type:'FeatureCollection',features:[{type:'Feature',properties:{_lote:'T1'},geometry:{type:'Polygon',coordinates:[poli]}}]};
      cajasLotes();LFEAT.clear();IDXV.clear();CARTO.lotes={T1:{n:rows.length}};cacheChunk.set('T1',rows);KX=0;
      S.palmas={type:'FeatureCollection',features:rows.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r[4],r[5]]},properties:{_id:String(r[0]),_lote:'T1',_linea:r[1],_num:r[2],_existe:true}}))};
      S.idx=new Map(S.palmas.features.map(f=>[f.properties._id,f]));try{indexar()}catch(e){}
      S.jornada={id:'JM',evaluador:'Op',estado:'activa',seleccion:[{lote:'T1'}],inicio:new Date().toISOString(),labor:'polinizacion',densidad:115,buffer:3.2,metodoVisita:'marcacion',bufferTerraza:8,
        transito:[],marcacion:[]};
      await dbPut('jornadas',S.jornada);VIS=nuevoEstadoVisita(115,3.2,'marcacion',8);TRACK.ultimo=null;TRACK.pts=[];actualizarJornadaUI();
      window.__T=Date.now();window.__pt=async(x,y,dt)=>{__T+=dt*1000;const g={lat:lat0+y/ky,lng:lng0+x/kx,acc:4,t:__T};S.gps={...g};await registrarPunto(g);};
    }""")
    check('Botón ▶ MARCAR visible en la barra', pg.is_visible('#polMarc') and 'MARCAR' in pg.text_content('#polMarc'))
    # Afuera del lote: no pregunta
    pg.evaluate("(async()=>{for(let k=0;k<4;k++)await __pt(1.5,-20-k*5,5);})()"); time.sleep(.4)
    check('Fuera del lote: no pregunta', pg.evaluate("document.querySelector('#hoja').classList.contains('oculto')"))
    # Entra al lote por la línea 1 (x=1,5 m): sin marcación todavía no cuenta
    pg.evaluate("(async()=>{for(const y of [5,9,13,17])await __pt(1.5,y,4);})()"); time.sleep(.6)
    check('Al entrar al lote programado: pregunta «¿Inicia la marcación?»', pg.is_visible('#cfSi') and 'Lote T1' in pg.text_content('#hojaTitulo') and 'marcación' in pg.text_content('#hojaCuerpo'), pg.text_content('#hojaTitulo'))
    check('Sin marcación: el recorrido no marca palmas', pg.evaluate("VIS.set.size") == 0)
    pg.eval_on_selector('#cfSi', 'b=>b.click()')
    pg.wait_for_selector('#hojaCuerpo [data-t="Transitable"]', timeout=5000)
    check('Al iniciar la marcación pide la transitabilidad (primera vez)', 'Transitabilidad' in pg.text_content('#hojaTitulo'))
    pg.eval_on_selector('#hojaCuerpo [data-t="Transitable"]', 'b=>b.click()'); time.sleep(.5)
    check('Marcación activa (botón «■ MARCANDO T1»)', pg.evaluate("!!marcActiva()&&marcActiva().lote==='T1'") and 'MARCANDO T1' in pg.text_content('#polMarc'))
    # Recorre la línea 1 a 1,5 m sin aplicar nada (4 m cada 4 s)
    pg.evaluate("(async()=>{for(let y=21;y<=125;y+=4)await __pt(1.5,y,4);})()"); time.sleep(1.2)
    ids = pg.evaluate("[...VIS.set].map(Number).sort((a,b)=>a-b)")
    check('Con marcación: cuentan las palmas de la línea 1 (a <= 3,2 m) desde que inicia, aunque no haya registros', ids == list(range(2, 13)), ids)
    check('La palma 1 (pasó antes de iniciar la marcación) no cuenta', 1 not in ids)
    check('No cuenta la línea vecina (a 7,2 m)', not any(13 <= i <= 24 for i in ids))
    # Sale del lote más de 90 s: se finaliza sola
    pg.evaluate("(async()=>{for(let k=0;k<6;k++)await __pt(1.5,150+k*5,20);})()"); time.sleep(.6)
    m = pg.evaluate("S.jornada.marcacion")
    check('Al salir del lote 90 s: la marcación se finaliza sola', len(m) == 1 and m[0]['fin_por'] == 'salida_lote' and not pg.evaluate("marcActiva()"), m)
    # Vuelve por la línea 3 sin marcación: no cuenta; registrar una palma sí
    pg.evaluate("MARC.preguntado.set('T1',Date.now())")   # ya le preguntaron hace poco: no vuelve a preguntar
    pg.evaluate("(async()=>{for(let y=125;y>=80;y-=4)await __pt(17.4+1.5,y,4);})()"); time.sleep(.8)
    check('Sin marcación (desplazamiento): no marca la línea 3', not any(25 <= i <= 36 for i in pg.evaluate("[...VIS.set].map(Number)")))
    check('Dentro del lote y preguntado hace poco: no vuelve a preguntar', pg.evaluate("document.querySelector('#hoja').classList.contains('oculto')"))
    # Botón: inicia y finaliza
    pg.eval_on_selector('#polMarc', 'b=>b.click()'); time.sleep(.5)
    check('Botón ▶ MARCAR: inicia (sin volver a pedir transitabilidad)', pg.evaluate("!!marcActiva()") and pg.evaluate("S.jornada.marcacion[1].inicio_por") == 'boton' and pg.evaluate("document.querySelector('#hoja').classList.contains('oculto')"))
    pg.evaluate("(async()=>{for(let y=78;y>=40;y-=4)await __pt(17.4+1.5,y,4);})()"); time.sleep(.8)
    l3 = [i for i in pg.evaluate("[...VIS.set].map(Number)") if 25 <= i <= 36]
    check('Con marcación por botón: marca la línea 3 desde ahí', len(l3) >= 3, sorted(l3))
    pg.eval_on_selector('#polMarc', 'b=>b.click()'); time.sleep(.4)
    check('Botón «■ MARCANDO»: finaliza', not pg.evaluate("marcActiva()") and pg.evaluate("S.jornada.marcacion[1].fin_por") == 'boton' and 'MARCAR' in pg.text_content('#polMarc'))
    # Vehículo / carrera (> 6 km/h): no marca
    pg.evaluate("marcActiva()||S.jornada.marcacion.push({lote:'T1',t0:tMarc(),inicio:new Date().toISOString(),inicio_por:'prueba',t1:null})")
    n0 = pg.evaluate("VIS.set.size")
    pg.evaluate("(async()=>{for(let y=125;y>=40;y-=20)await __pt(8.7+1,y,2);})()"); time.sleep(.6)
    check('A más de 6 km/h no marca', pg.evaluate("VIS.set.size") == n0)
    pg.evaluate("finalizarMarcacion('prueba',true)")
    # Voz
    check('Voz: «iniciar marcación» y «finalizar marcación»', pg.evaluate("interpretarVoz('iniciar marcación').cmd") == 'marcar_on' and pg.evaluate("interpretarVoz('finalizar la marcación').cmd") == 'marcar_off')
    # Recalcular como al finalizar: mismo resultado que en vivo
    r = pg.evaluate("""async()=>{const pts=TRACK.pts.map(p=>({...p}));const E=await calcularVisita(pts,115,3.2,'marcacion',true,true,S.jornada.seleccion,8,[],S.jornada.marcacion);
      return {vivo:[...VIS.set].sort(),recalc:[...E.set].sort(),res:resumenVisita(E,[]).metodo};}""")
    check('Recalcular (fin de jornada) da las mismas palmas que en vivo', r['vivo'] == r['recalc'] and r['res'] == 'marcacion', (len(r['vivo']), len(r['recalc'])))
    g = pg.evaluate("geoJornada(S.jornada,[],[],new Date().toISOString(),null).jornada.marcacion")
    check('El reporte de la jornada lleva la marcación por lote', len(g) == 3 and g[0]['lote'] == 'T1' and g[0]['fin_por'] == 'salida_lote', g[:1])
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
