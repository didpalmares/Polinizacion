# Pruebas automáticas

Pruebas de extremo a extremo con [Playwright](https://playwright.dev/python/) sobre la app compilada: app de campo, visor
(reproducción y Gerencia), administración (usuarios y formulario editable), registro por voz y tarjetas NFC, auditoría, límite de la
plantación, historial, APK, pantalla bloqueada, alertas y reportes, carga masiva, panel del día, ciclo de censo aprobado, planificación del censo,
y piloto de IA (servicio de IA simulado). GitHub se simula: las pruebas no leen ni escriben datos reales.

Se ejecutan solas en GitHub Actions (`.github/workflows/pruebas.yml`) con cada cambio en `src/` o `tests/`.

## Ejecutarlas en el computador

```bash
pip install playwright pillow openpyxl && python -m playwright install chromium
python src/build.py RUTA/node_modules src/marca
python -m http.server 8765 --bind 127.0.0.1
python tests/run_all.py            # todas
python tests/run_all.py gerencia   # solo las que contienen «gerencia»
```

En Windows se puede usar Edge en lugar de Chromium: `set PW_CANAL=msedge`.

Si la app se sirve en otra dirección, indíquela con `PRUEBAS_URL` (por ejemplo `PRUEBAS_URL=http://127.0.0.1:8799`);
sin ella se usa `http://127.0.0.1:8765`, la de GitHub Actions.

`prueba_visor_polinizacion.py` recorre la polinización de punta a punta: la App arma el GeoJSON de la jornada (A, P, B, R, V,
fuente, pasadas y transitabilidad de cada lote), el visor lo lee y se verifican colores, leyenda, ficha, filtro por código,
indicadores de Gerencia (🐝 Polinización), tabla por lote y transitabilidad por lote.

Los datos de las pruebas son ficticios (nombres, cédulas y el polígono de `fixtures/` no son reales).
