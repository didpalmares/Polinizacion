"""Líneas de borde (primera/última del lote) y esquinas trabajadas como UNA sola línea:
- Desde fuera del lote (4 m de la línea 1, 3 m fuera del polígono), despacio: cuenta solo la línea 1.
- Igual, pero sobre un sendero que bordea el lote: también cuenta la línea 1 (se trabaja desde el sendero).
- De paso (rápido) por fuera del lote o por el sendero del borde: no cuenta.
- Lejos del lote (12 m fuera): no cuenta.
- Calle interna (dos líneas) sobre un sendero: sigue sin contar.
- Esquina: tramo final de la línea 4 donde la línea 3 ya terminó: cuenta la línea 4."""
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

# Líneas 1..4 (x = 0, 8.7, 17.4, 26.1); la línea 3 es corta (6 palmas) para formar una esquina; polígono ajustado: x de -1 a 27.
PREP = """()=>{
  const ky=111320,kx=ky*Math.cos(1.7*Math.PI/180),lat0=1.7,lng0=-78.7;window.__K={kx,ky,lat0,lng0};
  const rows=[];let id=1;
  for(let ln=1;ln<=4;ln++){const x=(ln-1)*8.7,off=(ln%2)?0:5,n=(ln===3)?6:12;for(let k=0;k<n;k++){const y=10+off+k*10;rows.push([id++,ln,k+1,1,lng0+x/kx,lat0+y/ky]);}}
  const poli=[[lng0-1/kx,lat0],[lng0+27/kx,lat0],[lng0+27/kx,lat0+140/ky],[lng0-1/kx,lat0+140/ky],[lng0-1/kx,lat0]];
  S.lotes={type:'FeatureCollection',features:[{type:'Feature',properties:{_lote:'T1'},geometry:{type:'Polygon',coordinates:[poli]}}]};
  cajasLotes();LFEAT.clear();LMET.clear();IDXV.clear();CARTO.lotes={T1:{n:rows.length}};cacheChunk.set('T1',rows);KX=0;
  window.__lineaDe=Object.fromEntries(rows.map(r=>[String(r[0]),r[1]]));VIAS.gj=null;SEND_IDX=null;
  window.__sendero=x=>{VIAS.gj={type:'FeatureCollection',features:[{type:'Feature',properties:{tipo:'sendero_principal'},geometry:{type:'LineString',coordinates:[[lng0+x/kx,lat0-5/ky],[lng0+x/kx,lat0+150/ky]]}}]};SEND_IDX=null;};
}"""

CAMINAR = """async([x,y0,y1,paso])=>{const {kx,ky,lat0,lng0}=__K;const pts=[];let t=1.8e12;
  for(let y=y0;y<=y1;y+=1)pts.push({lat:lat0+y/ky,lng:lng0+x/kx,t:(t+=paso*1000),acc:4});
  const E=await calcularVisita(pts,115,5,'calle',false,true,null,8,[]);
  const por={1:0,2:0,3:0,4:0};for(const id of E.set)por[__lineaDe[id]]++;return por;}"""

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    pg = nav.new_context(service_workers='block').new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("typeof enSendero==='function' && typeof BORDE_M!=='undefined'", timeout=30000)
    time.sleep(1)
    pg.evaluate(PREP)
    c = lambda x, y0=0, y1=135, paso=2: pg.evaluate(CAMINAR, [x, y0, y1, paso])
    r = c(-4)
    check('Borde desde fuera del lote (3 m fuera), despacio: cuenta solo la línea 1', r['1'] >= 11 and r['2'] == 0, r)
    pg.evaluate("__sendero(-4)")
    r = c(-4)
    check('Borde desde el sendero que bordea el lote, despacio: cuenta la línea 1', r['1'] >= 11 and r['2'] == 0, r)
    r = c(-4, paso=0.8)
    check('Sendero del borde de paso (4,5 km/h): no cuenta', sum(r.values()) == 0, r)
    pg.evaluate("VIAS.gj=null;SEND_IDX=null;")
    r = c(-4, paso=0.8)
    check('Fuera del lote de paso (4,5 km/h): no cuenta', sum(r.values()) == 0, r)
    r = c(-13)
    check('Lejos del lote (12 m fuera): no cuenta', sum(r.values()) == 0, r)
    pg.evaluate("__sendero(4.35)")
    r = c(4.35)
    check('Calle interna 1–2 sobre un sendero: no cuenta', r['1'] == 0 and r['2'] == 0, r)
    pg.evaluate("VIAS.gj=null;SEND_IDX=null;")
    r = c(26.1 - 3, 80, 135)
    check('Esquina: tramo final de la línea 4 sin línea 3 al lado: cuenta la línea 4', r['4'] >= 5, r)
    r = c(4.35)
    check('Calle interna 1–2 despacio (sin sendero): sigue contando las dos líneas', r['1'] >= 11 and r['2'] >= 11, r)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
