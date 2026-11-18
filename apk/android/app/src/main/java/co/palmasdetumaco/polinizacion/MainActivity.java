package co.palmasdetumaco.polinizacion;

import android.os.Bundle;
import android.view.KeyEvent;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(EnergiaPlugin.class); // batería y bloqueo de pantalla (registro del recorrido en segundo plano)
        registerPlugin(VoskPlugin.class); // reconocimiento de voz sin conexión (registro por voz)
        registerPlugin(RecorridoPlugin.class); // GPS nativo del recorrido: puntos guardados en el celular y vigilancia cada minuto
        registerPlugin(NfcPlugin.class); // tarjetas NFC del registro de polinización (A, P, B, R, V)
        registerPlugin(HoraPlugin.class); // hora real con el GPS (sin internet) y acceso a los ajustes de fecha y hora
        registerPlugin(BotonesPlugin.class); // volumen arriba (2 s) para bloquear / desbloquear la pantalla y brillo mínimo
        super.onCreate(savedInstanceState);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (BotonesPlugin.tecla(event)) return true;
        return super.dispatchKeyEvent(event);
    }
}
