package co.palmasdetumaco.polinizacion;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.nfc.NdefMessage;
import android.nfc.NdefRecord;
import android.nfc.NfcAdapter;
import android.nfc.Tag;
import android.nfc.tech.Ndef;
import android.nfc.tech.NdefFormatable;
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
    // Las tarjetas son NFC-A (NTAG / MIFARE): buscar solo A y B hace la detección más rápida y estable que buscar todas las tecnologías.
    private static final int BANDERAS = NfcAdapter.FLAG_READER_NFC_A | NfcAdapter.FLAG_READER_NFC_B
            | NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS;
    private volatile boolean activo = false;
    // Grabación pendiente: la próxima tarjeta que se acerque se graba con este código (texto + marca de la app)
    private volatile PluginCall grabarCall = null;
    private volatile String grabarTexto = null;

    @Override
    public void load() {
        try { procesarIntento(getActivity().getIntent()); } catch (Exception ignored) { }
    }

    /** La app se abrió (o volvió al frente) porque se acercó una tarjeta con la app cerrada o en segundo plano. */
    @Override
    protected void handleOnNewIntent(Intent intent) {
        super.handleOnNewIntent(intent);
        procesarIntento(intent);
    }

    private void procesarIntento(Intent intent) {
        if (intent == null) return;
        String accion = intent.getAction();
        if (!NfcAdapter.ACTION_NDEF_DISCOVERED.equals(accion) && !NfcAdapter.ACTION_TAG_DISCOVERED.equals(accion)
                && !NfcAdapter.ACTION_TECH_DISCOVERED.equals(accion)) return;
        Tag tag = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG);
        intent.setAction(null); // no volver a procesarla si la actividad se recrea
        if (tag != null) entregar(tag, true);
    }

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

    /** Graba la próxima tarjeta que se acerque con un registro de texto (A, P, B, R o V) y la marca de Android de la app (AAR).
     *  Responde {ok, id} con el número único de la tarjeta, o un error. cancelarGrabacion() la anula. */
    @PluginMethod
    public void grabar(PluginCall call) {
        String texto = call.getString("texto", "");
        if (texto == null || texto.trim().isEmpty()) { call.reject("Falta el código a grabar."); return; }
        if (adaptador() == null) { call.reject("Este celular no tiene NFC."); return; }
        if (grabarCall != null) { try { grabarCall.reject("Reemplazada por otra grabación."); } catch (Exception ignored) { } }
        grabarTexto = texto.trim();
        grabarCall = call;
        activo = true;
        encender();
    }

    @PluginMethod
    public void cancelarGrabacion(PluginCall call) {
        PluginCall g = grabarCall; grabarCall = null; grabarTexto = null;
        if (g != null) { try { g.reject("Cancelada."); } catch (Exception ignored) { } }
        call.resolve();
    }

    private void escribir(Tag tag) {
        PluginCall g = grabarCall; String texto = grabarTexto;
        grabarCall = null; grabarTexto = null;
        if (g == null) return;
        try {
            NdefMessage msg = new NdefMessage(new NdefRecord[]{
                    NdefRecord.createTextRecord("es", texto),
                    NdefRecord.createApplicationRecord(getContext().getPackageName())});
            Ndef ndef = Ndef.get(tag);
            if (ndef != null) {
                try {
                    ndef.connect();
                    if (!ndef.isWritable()) throw new Exception("La tarjeta está bloqueada contra escritura.");
                    if (ndef.getMaxSize() < msg.toByteArray().length) msg = new NdefMessage(new NdefRecord[]{NdefRecord.createTextRecord("es", texto)});
                    ndef.writeNdefMessage(msg);
                } finally { try { ndef.close(); } catch (Exception ignored) { } }
            } else {
                NdefFormatable f = NdefFormatable.get(tag);
                if (f == null) throw new Exception("Esta tarjeta no admite NDEF. Use tarjetas NTAG213/215/216.");
                try { f.connect(); f.format(msg); } finally { try { f.close(); } catch (Exception ignored) { } }
            }
            vibrar(new long[]{0, 150});
            JSObject r = new JSObject(); r.put("ok", true); r.put("id", hex(tag.getId())); r.put("texto", texto);
            g.resolve(r);
        } catch (Exception e) {
            vibrar(new long[]{0, 60, 80, 60, 80, 60});
            g.reject(e.getMessage() != null ? e.getMessage() : "No se pudo grabar. Acerque la tarjeta y déjela quieta.");
        }
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
                extras.putInt(NfcAdapter.EXTRA_READER_PRESENCE_CHECK_DELAY, 250);
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

    /** Hilo del lector NFC de Android: una llamada por cada vez que se acerca una tarjeta.
     *  Android solo vuelve a llamar con la misma tarjeta cuando se retira y se acerca de nuevo, así que no hace falta vigilarla:
     *  se lee, se cierra la conexión de inmediato (para no bloquear la siguiente tarjeta) y se vibra para confirmar la lectura. */
    @Override
    public void onTagDiscovered(Tag tag) { entregar(tag, false); }

    private void entregar(Tag tag, boolean retener) {
        if (grabarCall != null && !retener) { escribir(tag); return; } // modo grabar: esta tarjeta se graba, no se registra
        final String id = hex(tag.getId());
        String texto = "";
        String motivo = "";
        Ndef ndef = Ndef.get(tag);
        if (ndef == null) {
            motivo = "sin_ndef"; // tarjeta sin formato NDEF (en blanco o de otro sistema)
        } else {
            try {
                NdefMessage m = ndef.getCachedNdefMessage();
                texto = leer(m);
                for (int i = 0; texto.isEmpty() && i < 4; i++) { // la tarjeta pasó rápido o quedó en el borde de la antena
                    try {
                        if (!ndef.isConnected()) ndef.connect();
                        texto = leer(ndef.getNdefMessage());
                    } catch (Exception e) {
                        try { Thread.sleep(60); } catch (InterruptedException ignored) { }
                    }
                }
                if (texto.isEmpty()) motivo = "lectura";
            } finally {
                try { ndef.close(); } catch (Exception ignored) { }
            }
        }
        vibrar(texto.isEmpty() ? new long[]{0, 40, 60, 40} : new long[]{0, 35});
        JSObject r = new JSObject();
        r.put("texto", texto);
        r.put("id", id);
        r.put("motivo", motivo);
        r.put("t", System.currentTimeMillis());
        r.put("abrioApp", retener);
        notifyListeners("tarjeta", r, retener); // si la abrió la tarjeta, se guarda hasta que la app esté escuchando
    }

    private void vibrar(long[] patron) {
        try {
            android.os.Vibrator v = (android.os.Vibrator) getContext().getSystemService(android.content.Context.VIBRATOR_SERVICE);
            if (v == null) return;
            if (android.os.Build.VERSION.SDK_INT >= 26) v.vibrate(android.os.VibrationEffect.createWaveform(patron, -1));
            else v.vibrate(patron, -1);
        } catch (Exception ignored) { }
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
