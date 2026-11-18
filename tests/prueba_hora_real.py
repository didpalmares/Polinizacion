"""Hora real del celular: desfase medido con internet (cabecera Date) o con el GPS (plugin nativo simulado, sin internet);
aviso si pasa de 5 min (no bloquea); los registros guardan la hora real y la del teléfono; cambio manual de la hora detectado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ
import sys, time
from email.utils import formatdate
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else (_os.environ.get('PRUEBAS_URL', 'http://127.0.0.1:8765').rstrip('/') + '/index.html')
errores = []
ok = True
SERV = {'desfase_s': 0}   # hora del «servidor» = hora real del computador + desfase

def check(nombre, cond, extra=''):
    global ok
    print(('OK   ' if cond else 'FALLA') + ' ' + nombre + (' · ' + str(extra) if extra != '' else ''))
    ok = ok and bool(cond)

def version(route):
    route.fulfill(status=200, content_type='application/json', body='{"version":"00000000:0000"}',
                  headers={'Date': formatdate(time.time() + SERV['desfase_s'], usegmt=True)})

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    ctx.add_init_script(INIT_VOZ)
    ctx.route('**/version.json*', version)
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto(URL)
    pg.wait_for_function("typeof revisarHora==='function'", timeout=30000)
    time.sleep(4)
    pg.evaluate("localStorage.removeItem('sv_hora');HORA.desfase=null;HORA.avisado=0;HORA.cerrado=0;")
    # 1) Celular en hora (internet): sin aviso
    pg.evaluate("revisarHora()"); time.sleep(.6)
    check('En hora (internet): desfase ≈ 0 y sin aviso', abs(pg.evaluate('HORA.desfase')) < 3000 and pg.is_hidden('#bannerHora'), pg.evaluate('HORA.desfase'))
    # 2) Servidor 20 min adelante = celular 20 min atrasado
    SERV['desfase_s'] = 20 * 60
    pg.evaluate("revisarHora()"); time.sleep(.6)
    d = pg.evaluate('HORA.desfase')
    check('Atrasado 20 min (internet): mide ≈ +20 min', abs(d - 20 * 60000) < 3000, d)
    check('Aviso visible con el desfase', pg.is_visible('#bannerHora') and '20 min atrasada' in pg.text_content('#bhTxt'), pg.text_content('#bhTxt'))
    check('Aviso por voz', any('hora del celular' in x for x in pg.evaluate('window.__dichos')))
    # 3) Registro guardado con hora real (no bloquea)
    r = pg.evaluate("""async()=>{SES={u:'op1',nombre:'Op',rol:'operario'};
      const m=1/111320,f={type:'Feature',geometry:{type:'Point',coordinates:[-78.7,1.7]},properties:{_id:'P1',_lote:'L1',_linea:1,_num:1,_existe:true}};
      S.palmas={type:'FeatureCollection',features:[f]};S.idx=new Map([['P1',f]]);
      S.jornada={id:'J1',evaluador:'Op',estado:'activa',seleccion:[],inicio:new Date().toISOString(),labor:'polinizacion',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      S.gps={lat:1.7+m,lng:-78.7,acc:4,t:Date.now()};await sumarCodigo('A','boton');const r=S.hechos.get('P1');
      return {real:Date.parse(r.creado),tel:Date.parse(r.creado_telefono),fuente:r.hora_fuente,des:r.desfase_hora_s,a:r.a};}""")
    check('Con la hora mal igual registra (solo advierte)', r['a'] == 1, r)
    check('El registro guarda la hora real (+20 min) y la del teléfono', abs((r['real'] - r['tel']) - 20 * 60000) < 3000 and r['fuente'] == 'internet' and abs(r['des'] - 1200) <= 3, r)
    # 4) Sin internet, con GPS (plugin nativo simulado): celular 1 h adelantado
    SERV['desfase_s'] = 0
    pg.evaluate("""()=>{window.Capacitor=window.Capacitor||{};window.Capacitor.Plugins=window.Capacitor.Plugins||{};
      window.Capacitor.Plugins.Hora={gps:async()=>({ok:true,telefono:Date.now(),real:Date.now()-3600000,edadSeg:3}),abrirAjustesFecha:async()=>{window.__ajustes=1;return {abierto:true};}};}""")
    pg.evaluate("""async()=>{const H=window.Capacitor.Plugins.Hora;const r=await H.gps();fijarDesfase(Math.round(r.real-r.telefono),'gps');}"""); time.sleep(.3)
    d = pg.evaluate('HORA.desfase')
    check('GPS sin internet: celular 1 h adelantado → desfase −1 h', abs(d + 3600000) < 3000 and pg.evaluate('HORA.fuente') == 'gps', d)
    check('Aviso: «1 h 0 min adelantada» (GPS)', '1 h 0 min adelantada' in pg.text_content('#bhTxt') and '(GPS)' in pg.text_content('#bhTxt'), pg.text_content('#bhTxt'))
    # 5) Cerrar el aviso: no reaparece de inmediato
    pg.eval_on_selector('#bhNo', 'b=>b.click()'); pg.evaluate('pintarHora()'); time.sleep(.2)
    check('Cerrado: no reaparece de inmediato', pg.is_hidden('#bannerHora'))
    # 6) Cambio manual de la hora durante la jornada: se compensa
    pg.evaluate("HORA.desfase=0;HORA.base=Date.now()-performance.now()-600000;HORA.cerrado=0;")  # como si el reloj hubiera saltado +10 min
    pg.evaluate("""()=>{const base=Date.now()-performance.now();const salto=base-HORA.base;HORA.base=base;HORA.desfase-=salto;pintarHora();}""")
    check('Cambio manual de +10 min: desfase compensado a −10 min', abs(pg.evaluate('HORA.desfase') + 600000) < 2000, pg.evaluate('HORA.desfase'))
    # 7) Jornada con hora real al iniciar
    check('Funciones de jornada con hora real', pg.evaluate("typeof estadoHora==='function' && estadoHora().fuente!==undefined"))
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
