"""Mensajes de voz de inicio y fin de jornada con el nombre de pila del operario y el saludo según la hora."""
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

CASOS = {'CABEZAS ANGULO ANDREA ALBERTA': 'Andrea', 'DE LA CRUZ REDIN JAIME ALEXIS': 'Jaime', 'ANGULO VERONICA': 'Veronica',
         'RIASCOS WISNER': 'Wisner', 'LANDAZURI FRANCISCA': 'Francisca', 'BUILA FERRIN JOHN JAIRO': 'John', 'CASTILLO  FLOR ALICIA': 'Alicia', '': ''}

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    pg = nav.new_context(service_workers='block').new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("typeof msjInicio==='function'", timeout=30000)
    for n, esperado in CASOS.items():
        r = pg.evaluate("n=>nombrePila(n)", n)
        check(f'Nombre de pila de «{n}»', r == esperado, r)
    r = pg.evaluate("()=>{SES={u:'x',nombre:'CABEZAS ANGULO ANDREA ALBERTA',rol:'operario'};S.jornada=null;HORA.desfase=0;return [msjInicio(),msjFin(),saludoHora()]}")
    check('Inicio: saludo + nombre', r[0].startswith(r[2] + ', Andrea. Hoy inicia una nueva jornada.'), r[0][:70])
    check('Fin: gracias + nombre', r[1].startswith('Muchas gracias por su labor, Andrea.'), r[1])
    h = pg.evaluate("()=>{const out=[];for(const hh of [7,14,20]){const d=new Date();d.setHours(hh,0,0,0);HORA.desfase=d.getTime()-Date.now();out.push(saludoHora());}HORA.desfase=0;return out;}")
    check('Saludo según la hora (7 h, 14 h, 20 h)', h == ['Buenos días', 'Buenas tardes', 'Buenas noches'], h)
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
