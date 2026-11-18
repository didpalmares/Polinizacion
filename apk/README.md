# Polinización · APK Android

Aplicación Android (Capacitor 8) que abre la app publicada en https://didpalmares.github.io/Polinizacion/ y agrega:

- **Registro protegido del recorrido** (`RecorridoService.java`, `RecorridoPlugin.java` «Recorrido», `VigiaReceiver.java`): servicio de ubicación en primer plano que guarda cada punto en `files/recorrido/<jornada>.jsonl`; la App web los recupera con `puntos({jornada,desde})` aunque Android haya dormido la página. Una alarma exacta (`setAlarmClock`, cada 60 s) avisa con vibración, voz y notificación si pasa más de 1 minuto sin GPS y reanuda el servicio si Android lo cerró. Eventos (inicio, sin GPS, reinicios) en `<jornada>_eventos.jsonl`.
- GPS en segundo plano de respaldo para la App con APK antiguas (`@capacitor-community/background-geolocation`).
- Voz nativa de Android (`@capacitor-community/text-to-speech`).
- Permiso de notificaciones (`@capacitor/local-notifications`).
- Reconocimiento de voz sin conexión con **Vosk** (`VoskPlugin.java`, `com.alphacephei:vosk-android`) para el registro de polinización por voz (gramática limitada a A, P, B, R, V, números y comandos). El modelo de español (`vosk-model-small-es-0.42.zip`, ~40 MB) se descarga la primera vez que se activa desde la versión (Release) `vosk-es` de `didpalmares/Polinizacion`: hay que subirlo allí como recurso de esa versión.
- **Tarjetas NFC** (`NfcPlugin.java`, plugin «Nfc»): modo lector de Android con la app en primer plano; lee el texto NDEF de la tarjeta («A», «P», «B», «R», «V» o «pol:A») y lo entrega a la app (eventos `tarjeta` {texto, id} y `retirada` {id}). Permiso `NFC`; NFC no es obligatorio para instalar la APK.

Descarga (última versión): https://github.com/didpalmares/Polinizacion/releases/latest/download/Polinizacion.apk

La versión (`1.0.N`) se agrega al agente de usuario (`PolinizacionAPK/1 v1.0.N`) al compilar; la app la muestra en Menú → App Android y avisa cuando hay una más nueva en Releases.

Compilación: `.github/workflows/apk.yml` (GitHub Actions) en cada cambio dentro de `apk/`, firmada con los secretos
`POLINIZACION_KEYSTORE_B64` y `POLINIZACION_KEYSTORE_PASS`. Los cambios de la app web llegan a la APK sin recompilar.
