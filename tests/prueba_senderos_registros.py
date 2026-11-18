"""Palmas visitadas en lotes lineales (polinización), calle con ambas líneas:
- Calle trabajada CON un registro en ella: cuenta las dos líneas.  SIN registros: no cuenta (va de paso).
- Sobre un sendero o vía (a 6 m o menos de su eje): no cuenta aunque haya registros.
- Quedarse 3 min quieto polinizando una palma no descarta la calle (antes se perdía a los 90 s).
- En vivo: al registrar una palma, la calle que ya se recorría se confirma.
Siembra en triángulo: palmas cada 10 m, líneas a 8,7 m; el operario camina por el centro de la calle 1–2."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL
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

PREP = """()=>{
  const ky=111320,kx=ky*Math.cos(1.7*Math.PI/180),lat0=1.7,lng0=-78.7;window.__K={kx,ky,lat0,lng0};
  const rows=[];let id=1;
  for(let ln=1;ln<=4;ln++){const x=(ln-1)*8.7,off=(ln%2)?0:5;for(let n=0;n<12;n++){const y=10+off+n*10;rows.push([id++,ln,n+1,1,lng0+x/kx,lat0+y/ky]);}}
  const poli=[[lng0-10/kx,lat0],[lng0+40/kx,lat0],[lng0+40/kx,lat0+140/ky],[lng0-10/kx,lat0+140/ky],[lng0-10/kx,lat0]];
  S.lotes={type:'FeatureCollection',features:[{type:'Feature',properties:{_lote:'T1'},geometry:{type:'Polygon',coordinates:[poli]}}]};
  cajasLotes();LFEAT.clear();IDXV.clear();CARTO.lotes={T1:{n:rows.length}};cacheChunk.set('T1',rows);KX=0;
  window.__lineaDe=Object.fromEntries(rows.map(r=>[String(r[0]),r[1]]));VIAS.gj=null;
}"""

CAMINAR = """async([x,y0,y1,regs,quieto])=>{const {kx,ky,lat0,lng0}=__K;const pts=[];let t=1.8e12;
  for(let y=y0;y<=y1;y+=1){pts.push({lat:lat0+y/ky,lng:lng0+x/kx,t:(t+=1000),acc:4});
    if(quieto&&y===quieto)for(let s=0;s<180;s+=2)pts.push({lat:lat0+y/ky,lng:lng0+x/kx,t:(t+=2000),acc:4});}
  const R=(regs||[]).map(([ln,num])=>({lote:'T1',linea:ln,numero:num,palma_id:String((ln-1)*12+num),labor:'polinizacion',creado:new Date(1.8e12).toISOString()}));
  const E=await calcularVisita(pts,115,5,'calle',false,true,null,8,R);
  const por={1:0,2:0,3:0,4:0};for(const id of E.set)por[__lineaDe[id]]++;return por;}"""

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("typeof calleConRegistro==='function' && typeof enSendero==='function'", timeout=30000)
    time.sleep(1)
    pg.evaluate(PREP)
    c = lambda x, y0, y1, regs=None, quieto=None: pg.evaluate(CAMINAR, [x, y0, y1, regs or [], quieto])
    r = c(4.35, 0, 135)
    check('Calle 1–2 recorrida SIN registros: no cuenta (va de paso)', sum(r.values()) == 0, r)
    r = c(4.35, 0, 135, [[1, 5]])
    check('Calle 1–2 CON un registro (línea 1): cuenta las dos líneas', r['1'] >= 11 and r['2'] >= 11 and r['3'] == 0, r)
    r = c(4.35, 0, 135, [[3, 5]])
    check('Registro en otra calle (línea 3): la calle 1–2 no cuenta', r['1'] == 0 and r['2'] == 0, r)
    r = c(4.35, 0, 135, [[2, 6]], 40)
    check('Quieto 3 min en una palma (con registro): la calle sigue y cuenta', r['1'] >= 11 and r['2'] >= 11, r)
    # Sendero por la calle 1–2
    pg.evaluate("""()=>{const {kx,ky,lat0,lng0}=__K;VIAS.gj={type:'FeatureCollection',features:[{type:'Feature',properties:{tipo:'sendero_principal'},
      geometry:{type:'LineString',coordinates:[[lng0+4.35/kx,lat0-5/ky],[lng0+4.35/kx,lat0+150/ky]]}}]};SEND_IDX=null;}""")
    r = c(4.35, 0, 135, [[1, 5], [2, 6]])
    check('Sobre un sendero (calle 1–2): solo cuentan las 2 palmas registradas, no la calle', r['1'] == 1 and r['2'] == 1, r)
    r = c(4.35 + 8.7 * 2, 0, 135, [[3, 5]])
    check('Calle 3–4 (a 17 m del sendero) con registro: sí cuenta', r['3'] >= 11 and r['4'] >= 11, r)
    pg.evaluate("VIAS.gj=null;SEND_IDX=null;")
    # En vivo: recorre la calle sin registro y luego registra → se confirma
    r = pg.evaluate("""async()=>{const {kx,ky,lat0,lng0}=__K;const E=nuevoEstadoVisita(115,5,'calle',8);let t=1.8e12;
      for(let y=0;y<=60;y++)await visitarTramo(E,{lat:lat0+y/ky,lng:lng0+4.35/kx,t:(t+=1000),acc:4});
      const antes=E.set.size;
      await visitarRegistro(E,{lote:'T1',linea:1,numero:3,palma_id:'3',labor:'polinizacion',creado:new Date(t).toISOString()});
      return {antes,despues:E.set.size};}""")
    check('En vivo: sin registro no cuenta; al registrar, la calle recorrida se confirma', r['antes'] == 0 and r['despues'] >= 8, r)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
