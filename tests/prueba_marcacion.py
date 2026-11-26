"""Marcación de palmas visitadas (pedido de campo: no se marcaban las palmas de las calles donde no se aplicaba nada).
Al entrar por GPS al polígono de un lote programado: 1) la primera vez, transitabilidad; 2) marcación OBLIGATORIA (solo ▶ MARCAR o
decir «marcar»; si se cierra la ventana vuelve a aparecer). Con la marcación activa cuentan, igual que en terraza, todas las palmas del
lote a <= 3,2 m del recorrido (sin otras restricciones: ni velocidad), desde que entró al lote; sin marcación no cuenta el recorrido.
Al salir del lote 90 s se finaliza sola; al volver a entrar se pide otra vez la marcación (no la transitabilidad). Botón en la barra.
El recálculo (fin de jornada) da lo mismo que en vivo y la marcación queda en el reporte."""
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
    oculta = lambda: pg.evaluate("document.querySelector('#hoja').classList.contains('oculto')")
    check('Botón ▶ MARCAR visible en la barra', pg.is_visible('#polMarc') and 'MARCAR' in pg.text_content('#polMarc'))
    pg.evaluate("(async()=>{for(let k=0;k<4;k++)await __pt(1.5,-20-k*5,5);})()"); time.sleep(.4)
    check('Fuera del lote: no pregunta nada', oculta())
    # Entra al polígono (línea 1, x=1,5 m)
    pg.evaluate("(async()=>{for(const y of [5,9,13])await __pt(1.5,y,4);})()"); time.sleep(.6)
    check('Al entrar por primera vez al polígono: pide la transitabilidad', pg.is_visible('#hojaCuerpo [data-t="Transitable"]') and 'lote T1' in pg.text_content('#hojaTitulo'), pg.text_content('#hojaTitulo'))
    pg.eval_on_selector('#hojaCuerpo [data-t="Poco transitable"]', 'b=>b.click()'); time.sleep(.6)
    check('Luego la marcación: obligatoria (solo ▶ MARCAR, sin «Todavía no»)', pg.is_visible('#mkSi') and not pg.query_selector('#cfNo') and 'marcar' in pg.text_content('#hojaCuerpo'))
    check('Transitabilidad guardada al entrar (sin registros)', pg.evaluate("S.jornada.transito.length") == 1 and pg.evaluate("S.jornada.transito[0].entrada") == 'Poco transitable' and pg.evaluate("S.registros.length") == 0)
    pg.evaluate("cerrarHoja()"); time.sleep(.3)
    pg.evaluate("(async()=>{await __pt(1.5,17,4);})()"); time.sleep(.6)
    check('Si la cierra sin marcar: vuelve a aparecer', pg.is_visible('#mkSi') and pg.evaluate("S.jornada.transito.length") == 1)
    check('Sin marcación: el recorrido aún no marca', pg.evaluate("VIS.set.size") == 0)
    pg.eval_on_selector('#mkSi', 'b=>b.click()'); time.sleep(.6)
    check('▶ MARCAR: marcación activa (botón «■ MARCANDO T1»)', pg.evaluate("!!marcActiva()&&marcActiva().lote==='T1'") and 'MARCANDO T1' in pg.text_content('#polMarc') and oculta())
    check('Cuenta desde que entró al lote: la palma 1 (pasó mientras respondía) ya está marcada', pg.evaluate("VIS.set.has('1')"), pg.evaluate("[...VIS.set]"))
    pg.evaluate("(async()=>{for(let y=21;y<=125;y+=4)await __pt(1.5,y,4);})()"); time.sleep(1.2)
    ids = pg.evaluate("[...VIS.set].map(Number).sort((a,b)=>a-b)")
    check('Con marcación: las 12 palmas de la línea 1 (a <= 3,2 m) sin registros', ids == list(range(1, 13)), ids)
    check('No cuenta la línea vecina (a 7,2 m)', not any(13 <= i <= 24 for i in ids))
    # Sale 90 s: se finaliza sola
    pg.evaluate("(async()=>{for(let k=0;k<6;k++)await __pt(1.5,150+k*5,20);})()"); time.sleep(.6)
    m = pg.evaluate("S.jornada.marcacion")
    check('Al salir del lote 90 s: la marcación se finaliza sola', len(m) == 1 and m[0]['fin_por'] == 'salida_lote' and not pg.evaluate("marcActiva()"), m)
    # Vuelve a entrar (línea 3): pide la marcación otra vez, no la transitabilidad; responde por voz «marcar»
    pg.evaluate("(async()=>{for(let y=135;y>=123;y-=4)await __pt(17.4+1.5,y,4);})()"); time.sleep(.6)
    check('Al volver a entrar: pide marcar otra vez (sin transitabilidad)', pg.is_visible('#mkSi') and pg.evaluate("S.jornada.transito.length") == 1)
    check('Voz: «marcar» se entiende como iniciar marcación', pg.evaluate("interpretarVoz('marcar').cmd") == 'marcar_on' and pg.evaluate("interpretarVoz('finalizar marcación').cmd") == 'marcar_off'
          and pg.evaluate("interpretarVoz('dos a').items[0][0]") == 'A')
    pg.evaluate("MARC.porVoz=true;MARC.resolver(true)"); time.sleep(.6)
    check('Respondida por voz: marcación activa, iniciada por «voz»', pg.evaluate("!!marcActiva()") and pg.evaluate("S.jornada.marcacion[1].inicio_por") == 'voz' and oculta())
    # Sin restricción de velocidad (igual que terraza)
    pg.evaluate("(async()=>{for(let y=119;y>=40;y-=20)await __pt(17.4+1.5,y,2);})()"); time.sleep(.8)
    l3 = [i for i in pg.evaluate("[...VIS.set].map(Number)") if 25 <= i <= 36]
    check('Rápido (36 km/h simulado) también marca: sin otras restricciones', len(l3) >= 6, sorted(l3))
    # Botón: finaliza; dentro del lote no vuelve a preguntar
    pg.eval_on_selector('#polMarc', 'b=>b.click()'); time.sleep(.4)
    check('Botón «■ MARCANDO»: finaliza', not pg.evaluate("marcActiva()") and pg.evaluate("S.jornada.marcacion[1].fin_por") == 'boton')
    pg.evaluate("(async()=>{for(let y=40;y>=20;y-=4)await __pt(8.7+1,y,4);})()"); time.sleep(.6)
    check('Finalizada a mano dentro del lote: no vuelve a preguntar hasta salir y entrar', oculta())
    pg.eval_on_selector('#polMarc', 'b=>b.click()'); time.sleep(.4)
    check('Botón ▶ MARCAR: vuelve a iniciar', pg.evaluate("!!marcActiva()") and pg.evaluate("S.jornada.marcacion[2].inicio_por") == 'boton')
    pg.evaluate("finalizarMarcacion('prueba',true)")
    r = pg.evaluate("""async()=>{const pts=TRACK.pts.map(p=>({...p}));const E=await calcularVisita(pts,115,3.2,'marcacion',true,true,S.jornada.seleccion,8,[],S.jornada.marcacion);
      return {vivo:[...VIS.set].sort(),recalc:[...E.set].sort(),res:resumenVisita(E,[]).metodo};}""")
    check('Recalcular (fin de jornada) da las mismas palmas que en vivo', r['vivo'] == r['recalc'] and r['res'] == 'marcacion', (len(r['vivo']), len(r['recalc']), sorted(set(r['vivo']) ^ set(r['recalc']))))
    g = pg.evaluate("geoJornada(S.jornada,[],[],new Date().toISOString(),null).jornada.marcacion")
    check('El reporte de la jornada lleva la marcación por lote', len(g) == 3 and g[0]['fin_por'] == 'salida_lote' and g[1]['inicio_por'] == 'voz', [x['inicio_por'] for x in g])
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
