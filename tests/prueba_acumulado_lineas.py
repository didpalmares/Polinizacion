"""Al finalizar la jornada: tabla «Acumulado por línea de cada lote» con la cantidad de cada etiqueta (A, P, B, R, V),
palmas registradas y visitadas por línea, total por lote y total de la jornada; queda guardada en el reporte (acumulado_lineas)."""
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
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL)
    pg.wait_for_function("typeof acumuladoLineas==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{try{ocultarSplash()}catch(e){}document.querySelector('#login').hidden=true;SES={u:'op1',nombre:'OPERARIO UNO',rol:'operario'};
      const m=1/111320,feats=[];
      // Lote L1: líneas 1 y 2 (3 palmas c/u); lote L2: línea 5 (2 palmas)
      const mk=(id,l,ln,n,x,y)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7+x*m,1.7+y*m]},properties:{_id:id,_lote:l,_linea:String(ln),_num:String(n),_existe:true}});
      for(let n=1;n<=3;n++){feats.push(mk('a'+n,'L1',1,n,0,n*9));feats.push(mk('b'+n,'L1',2,n,9,n*9));}
      for(let n=1;n<=2;n++)feats.push(mk('c'+n,'L2',5,n,200,n*9));
      S.palmas={type:'FeatureCollection',features:feats};indexar();
      S.jornada={id:'JAC',evaluador:'OPERARIO UNO',estado:'activa',seleccion:[{lote:'L1'},{lote:'L2'}],inicio:new Date(Date.now()-3600e3).toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'Transitable',t_salida:new Date().toISOString()}]};
      const reg=(f,o)=>{const r=nuevoRegistroPol(f);Object.assign(r,o);completarPol(r);r.jornada_id='JAC';S.registros.push(r);S.hechos.set(f.properties._id,r);return r;};
      const F=id=>S.idx.get(id);
      reg(F('a1'),{a:2,p:1});reg(F('a2'),{b:1});reg(F('a3'),{cond:'R'});
      reg(F('b1'),{a:1,p:1,b:1});reg(F('b2'),{cond:'V'});
      reg(F('c1'),{p:3});
      for(const r of S.registros)await dbPut('registros',r);await dbPut('jornadas',S.jornada);}""")
    filas = pg.evaluate("acumuladoLineas(S.registros.filter(r=>r.jornada_id==='JAC'),{por_lote:[{lote:'L1',ids_palmas_visitadas:['a1','a2','a3','b1','b2','b3']},{lote:'L2',ids_palmas_visitadas:['c1']}]})")
    d = {(f['lote'], f['linea']): f for f in filas}
    check('Tres líneas en orden (L1-1, L1-2, L2-5)', [(f['lote'], f['linea']) for f in filas] == [('L1', '1'), ('L1', '2'), ('L2', '5')], [(f['lote'], f['linea']) for f in filas])
    x = d[('L1', '1')]
    check('L1 línea 1: A2 P1 B1 R1 V0 · 3 palmas', (x['A'], x['P'], x['B'], x['R'], x['V'], x['palmas']) == (2, 1, 1, 1, 0, 3), x)
    x = d[('L1', '2')]
    check('L1 línea 2: A1 P1 B1 V1 · 2 palmas · 3 visitadas', (x['A'], x['P'], x['B'], x['R'], x['V'], x['palmas'], x['visitadas']) == (1, 1, 1, 0, 1, 2, 3), x)
    x = d[('L2', '5')]
    check('L2 línea 5: P3 · 1 palma', (x['P'], x['palmas'], x['visitadas']) == (3, 1, 1), x)
    pg.evaluate("finalizarJornada()"); time.sleep(4)
    tx = pg.evaluate("(document.querySelector('#tabAcum')||{}).innerText||''")
    check('Al finalizar: se muestra la tabla de acumulado por línea', 'Total lote L1' in tx and 'Total lote L2' in tx and 'TOTAL JORNADA' in tx, tx[:200])
    tot = pg.evaluate("[...document.querySelectorAll('#tabAcum tbody tr')].pop().innerText")
    check('Total jornada: A3 P5 B2 R1 V1 · 6 palmas', tot.split('\t')[1:7] == ['3', '5', '2', '1', '1', '6'], tot)
    j = pg.evaluate("(async()=>{const j=await dbGet('jornadas','JAC');return geoJornada(j,S.registros.filter(r=>r.jornada_id==='JAC'),[],new Date().toISOString(),null).jornada.acumulado_lineas;})()")
    check('El reporte de la jornada guarda el acumulado por línea', isinstance(j, list) and len(j) == 3, j and len(j))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
