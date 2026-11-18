package co.palmasdetumaco.polinizacion;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.nfc.NdefMessage;
import android.nfc.NdefRecord;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.nfc.tech.Ndef;
import android.os.Bundle;
import android.provider.Settings;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Tarjetas NFC del registro de polinización (texto «A», «P», «B», «R» o «V»; también «pol:A»).
 * Usa el modo lector de Android (enableReaderMode) solo mientras la app está en primer plano: así Android no abre
 * otra aplicación al acercar la tarjeta ni suena su pitido (la app confirma con su propio pitido y voz).
 * - estado(): {disponible, habilitado, activo}
 * - iniciar(), detener(), abrirAjustes()
 * Eventos: "tarjeta" {texto, id} al acercar una tarjeta; "retirada" {id} cuando se aleja (la app ignora la misma
 * tarjeta leída de nuevo antes de 1,5 s, salvo que se haya retirado y vuelto a acercar).
 */
@CapacitorPlugin(name = "Nfc")
public class NfcPlugin extends Plugin implements NfcAdapter.ReaderCallback {
    private static final int BANDERAS = NfcAdapter.FLAG_READER_NFC_A | NfcAdapter.FLAG_READER_NFC_B
            | NfcAdapter.FLAG_READER_NFC_F | NfcAdapter.FLAG_READER_NFC_V | NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS;
    private static final long VIGILAR_MAX_MS = 60000L;
    private volatile boolean activo = false;

    private NfcAdapter adaptador() {
        try { return NfcAdapter.getDefaultAdapter(getContext()); } catch (Exception e) { return null; }
    }

    private JSObject estadoObj() {
        NfcAdapter a = adaptador();
        JSObject r = new JSObject();
        r.put("disponible", a != null);
        r.put("habilitado", a != null && a.isEnabled());
        r.put("activo", activo);
        return r;
    }

    @PluginMethod
    public void estado(PluginCall call) { call.resolve(estadoObj()); }

    @PluginMethod
    public void iniciar(PluginCall call) {
        if (adaptador() == null) { call.reject("Este celular no tiene NFC."); return; }
        activo = true;
        encender();
        call.resolve(estadoObj());
    }

    /** Apaga y vuelve a encender el modo lector (al iniciar la jornada, al volver a la app y cada cierto tiempo):
     *  recupera el lector cuando Android lo dejó inactivo tras un permiso, un diálogo o la pantalla de ajustes. */
    @PluginMethod
    public void reiniciar(PluginCall call) {
        if (adaptador() == null) { call.reject("Este celular no tiene NFC."); return; }
        activo = true;
        apagar();
        final Activity act = getActivity();
        if (act != null) act.getWindow().getDecorView().postDelayed(this::encender, 250);
        else encender();
        call.resolve(estadoObj());
    }

    @PluginMethod
    public void detener(PluginCall call) {
        activo = false;
        apagar();
        call.resolve(estadoObj());
    }

    @PluginMethod
    public void abrirAjustes(PluginCall call) {
        boolean ok = abrir(new Intent(Settings.ACTION_NFC_SETTINGS));
        if (!ok) ok = abrir(new Intent(Settings.ACTION_WIRELESS_SETTINGS));
        JSObject r = new JSObject(); r.put("abierto", ok); call.resolve(r);
    }

    private boolean abrir(Intent i) {
        try {
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(i);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private void encender() {
        final Activity act = getActivity();
        final NfcAdapter a = adaptador();
        if (act == null || a == null || !activo) return;
        final NfcPlugin yo = this;
        act.runOnUiThread(() -> {
            try {
                Bundle extras = new Bundle();
                extras.putInt(NfcAdapter.EXTRA_READER_PRESENCE_CHECK_DELAY, 500);
                a.enableReaderMode(act, yo, BANDERAS, extras);
            } catch (Exception ignored) { } // la actividad no está en primer plano: se activa en handleOnResume
        });
    }

    private void apagar() {
        final Activity act = getActivity();
        final NfcAdapter a = adaptador();
        if (act == null || a == null) return;
        act.runOnUiThread(() -> {
            try { a.disableReaderMode(act); } catch (Exception ignored) { }
        });
    }

    @Override
    protected void handleOnResume() {
        super.handleOnResume();
        if (activo) encender();
    }

    @Override
    protected void handleOnPause() {
        if (activo) apagar();
        super.handleOnPause();
    }

    /** Hilo del lector NFC de Android: una llamada por cada vez que se acerca una tarjeta. */
    @Override
    public void onTagDiscovered(Tag tag) {
        final String id = hex(tag.getId());
        final Ndef ndef = Ndef.get(tag);
        String texto = "";
        if (ndef != null) {
            NdefMessage m = ndef.getCachedNdefMessage();
            texto = leer(m);
            // Si la tarjeta pasó rápido o quedó en el borde de la antena, se reintenta la lectura hasta 4 veces
            for (int i = 0; texto.isEmpty() && i < 4; i++) {
                try {
                    if (!ndef.isConnected()) ndef.connect();
                    texto = leer(ndef.getNdefMessage());
                } catch (Exception e) {
                    try { Thread.sleep(80); } catch (InterruptedException ignored) { }
                }
            }
        }
        JSObject r = new JSObject();
        r.put("texto", texto);
        r.put("id", id);
        notifyListeners("tarjeta", r);
        if (ndef != null) vigilarRetiro(ndef, id);
    }

    /** Lee la tarjeta cada 200 ms hasta que deja de responder (se retiró) y entonces avisa con "retirada". */
    private void vigilarRetiro(final Ndef ndef, final String id) {
        new Thread(() -> {
            try {
                if (!ndef.isConnected()) ndef.connect();
                long fin = System.currentTimeMillis() + VIGILAR_MAX_MS;
                while (System.currentTimeMillis() < fin) {
                    Thread.sleep(300);
                    ndef.getNdefMessage(); // lanza una excepción cuando la tarjeta ya no está
                }
            } catch (Exception ignored) {
                // tarjeta retirada (o error de lectura): se trata como retiro
            } finally {
                try { ndef.close(); } catch (Exception ignored) { }
            }
            JSObject r = new JSObject();
            r.put("id", id);
            notifyListeners("retirada", r);
        }, "nfc-retiro").start();
    }

    private static String leer(NdefMessage m) {
        if (m == null) return "";
        for (NdefRecord rec : m.getRecords()) {
            String t = textoDe(rec);
            if (t != null && !t.trim().isEmpty()) return t.trim();
        }
        return "";
    }

    private static String textoDe(NdefRecord rec) {
        try {
            short tnf = rec.getTnf();
            byte[] tipo = rec.getType();
            byte[] p = rec.getPayload();
            if (p == null) return null;
            if (tnf == NdefRecord.TNF_WELL_KNOWN && Arrays.equals(tipo, NdefRecord.RTD_TEXT)) {
                if (p.length == 0) return null;
                int largoIdioma = p[0] & 0x3F;
                Charset cs = (p[0] & 0x80) == 0 ? StandardCharsets.UTF_8 : StandardCharsets.UTF_16;
                if (1 + largoIdioma > p.length) return null;
                return new String(p, 1 + largoIdioma, p.length - 1 - largoIdioma, cs);
            }
            if ((tnf == NdefRecord.TNF_WELL_KNOWN && Arrays.equals(tipo, NdefRecord.RTD_URI)) || tnf == NdefRecord.TNF_ABSOLUTE_URI) {
                Uri u = rec.toUri();
                return u != null ? u.toString() : new String(p, StandardCharsets.UTF_8);
            }
            if (tnf == NdefRecord.TNF_MIME_MEDIA && new String(tipo, StandardCharsets.US_ASCII).toLowerCase().startsWith("text/")) {
                return new String(p, StandardCharsets.UTF_8);
            }
        } catch (Exception ignored) { }
        return null;
    }

    private static String hex(byte[] b) {
        if (b == null) return "";
        StringBuilder s = new StringBuilder();
        for (byte x : b) s.append(String.format("%02X", x));
        return s.toString();
    }
}
