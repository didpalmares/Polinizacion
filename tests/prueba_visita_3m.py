"""Palmas visitadas en lotes lineales (polinización): una palma cuenta solo si el operario llega a ella
(a 3 m o menos de su línea y a 3 m o menos a lo largo). Siembra en triángulo: palmas cada 10 m, líneas a 8,7 m.
- Caminando pegado a la línea 2 (1 m): se marcan las palmas de la línea 2 y ninguna de las líneas 1 y 3.
- Caminando por el centro de la calle (4,35 m de cada línea): no se marca ninguna.
- Pasando solo 2 palmas (menos de 3): la calle no se confirma y no se marca nada."""
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
  const ky=111320,kx=ky*Math.cos(1.7*Math.PI/180),lat0=1.7,lng0=-78.7;window.__K={KX:kx,KY:ky,lat0,lng0};
  const rows=[];let id=1;
  for(let ln=1;ln<=3;ln++){const x=(ln-1)*8.7,off=(ln%2)?0:5;
    for(let n=0;n<12;n++){const y=10+off+n*10;rows.push([id++,ln,n+1,1,lng0+x/kx,lat0+y/ky]);}}
  const poli=[[lng0-10/kx,lat0],[lng0+30/kx,lat0],[lng0+30/kx,lat0+140/ky],[lng0-10/kx,lat0+140/ky],[lng0-10/kx,lat0]];
  S.lotes={type:'FeatureCollection',features:[{type:'Feature',properties:{_lote:'T1'},geometry:{type:'Polygon',coordinates:[poli]}}]};
  cajasLotes();LFEAT.clear();IDXV.clear();CARTO.lotes={T1:{n:rows.length}};cacheChunk.set('T1',rows);KX=0;
  window.__lineaDe=Object.fromEntries(rows.map(r=>[String(r[0]),r[1]]));
}"""

def caminar(pg, x, y0, y1):
    return pg.evaluate("""async([x,y0,y1])=>{const {KX,KY,lat0,lng0}=__K;const pts=[];let t=Date.now();
      for(let y=y0;y<=y1;y+=1){pts.push({lat:lat0+y/KY,lng:lng0+x/KX,t:(t+=1000),acc:4});}
      const E=await calcularVisita(pts,115,5,'calle',false,true,null,8);
      const por={1:0,2:0,3:0};for(const id of E.set)por[__lineaDe[id]]++;return por;}""", [x, y0, y1])

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block')
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("typeof calcularVisita==='function'", timeout=30000)
    time.sleep(1)
    pg.evaluate(PREP)
    r = caminar(pg, 8.7 + 1.0, 0, 135)
    check('Pegado a la línea 2 (1 m): marca sus 12 palmas', r['2'] == 12, r)
    check('Pegado a la línea 2: no marca las líneas 1 y 3 (a 7,7 m y 9,7 m)', r['1'] == 0 and r['3'] == 0, r)
    r = caminar(pg, 8.7 + 2.8, 0, 135)
    check('A 2,8 m de la línea 2: sigue marcando', r['2'] >= 11, r)
    r = caminar(pg, 8.7 / 2, 0, 135)
    check('Por el centro de la calle (4,35 m): no marca ninguna', sum(r.values()) == 0, r)
    r = caminar(pg, 8.7 + 1.0, 10, 30)
    check('Solo 2 palmas pasadas: la calle no se confirma', sum(r.values()) == 0, r)
    r = caminar(pg, 8.7 + 1.0, 10, 40)
    check('3 palmas pasadas: se confirma y cuenta 3', r['2'] == 3, r)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
