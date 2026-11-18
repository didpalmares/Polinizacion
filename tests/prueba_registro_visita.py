"""Toda palma con registro cuenta como visitada (en vivo y al recalcular la jornada) y la ficha de la palma dice «REGISTRAR PALMA»."""
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
    pg.wait_for_function("typeof visitarRegistro==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Op',rol:'operario'};try{ocultarSplash()}catch(e){}
      const ky=111320,kx=ky*Math.cos(1.7*Math.PI/180),lat0=1.7,lng0=-78.7;window.__K={kx,ky,lat0,lng0};
      const rows=[];let id=1;
      for(let ln=1;ln<=3;ln++){const x=(ln-1)*8.7,off=(ln%2)?0:5;for(let n=0;n<12;n++){const y=10+off+n*10;rows.push([id++,ln,n+1,1,lng0+x/kx,lat0+y/ky]);}}
      const poli=[[lng0-10/kx,lat0],[lng0+30/kx,lat0],[lng0+30/kx,lat0+140/ky],[lng0-10/kx,lat0+140/ky],[lng0-10/kx,lat0]];
      S.lotes={type:'FeatureCollection',features:[{type:'Feature',properties:{_lote:'T1'},geometry:{type:'Polygon',coordinates:[poli]}}]};
      cajasLotes();LFEAT.clear();IDXV.clear();CARTO.lotes={T1:{n:rows.length}};cacheChunk.set('T1',rows);KX=0;
      S.palmas={type:'FeatureCollection',features:rows.map(r=>({type:'Feature',geometry:{type:'Point',coordinates:[r[4],r[5]]},properties:{_id:String(r[0]),_lote:'T1',_linea:r[1],_num:r[2],_existe:true}}))};
      S.idx=new Map(S.palmas.features.map(f=>[f.properties._id,f]));try{indexar()}catch(e){}
      S.jornada={id:'J1',evaluador:'Op',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',densidad:115,buffer:5,metodoVisita:'calle',bufferTerraza:8,
        transito:[{lote:'T1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      VIS=nuevoEstadoVisita(115,5,'calle',8);actualizarJornadaUI();
      // Junto a la palma 13 (línea 2, palma 1: y=15 m, x=8,7 m), sin recorrido
      S.gps={lat:lat0+15/ky,lng:lng0+8.7/kx,acc:4,t:Date.now()};
    }""")
    check('Palma 13 no visitada antes de registrar', not pg.evaluate("VIS.set.has('13')"))
    pg.evaluate("sumarCodigo('A','boton')"); time.sleep(.6)
    check('Registrada en vivo: cuenta como visitada', pg.evaluate("VIS.set.has('13')") and pg.evaluate("(S.hechos.get('13')||{}).a") == 1)
    check('Contador de visitadas suma 1', pg.text_content('#pjVis').strip() in ('1',), pg.text_content('#pjVis'))
    # Recalcular la jornada sin recorrido: la registrada sigue como visitada (solo ella)
    r = pg.evaluate("""async()=>{const regs=S.registros.filter(r=>r.jornada_id==='J1');const E=await calcularVisita([],115,5,'calle',true,true,null,8,regs);
      return {ids:[...E.set],res:resumenVisita(E,regs).palmas_visitadas};}""")
    check('Al recalcular (fin / sincronización): la palma registrada es visitada', r['ids'] == ['13'] and r['res'] == 1, r)
    # Ficha de la palma: «REGISTRAR PALMA»
    pg.evaluate("abrirPalma('14')"); time.sleep(.3)
    txt = pg.text_content('#hojaCuerpo')
    check('Ficha de la palma: botón «REGISTRAR PALMA» (sin «diagnóstico»)', 'REGISTRAR PALMA' in txt and 'iagnóstic' not in txt, txt[:160])
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
