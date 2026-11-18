package co.palmasdetumaco.polinizacion;

import android.content.Context;
import android.content.Intent;
import android.location.Location;
import android.location.LocationManager;
import android.os.Build;
import android.os.SystemClock;
import android.provider.Settings;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Hora real sin internet: la última lectura del GPS trae la hora de los satélites (UTC).
 * gps() devuelve {ok, real, telefono, edadSeg}: «real» es la hora de los satélites llevada al momento actual con el reloj
 * interno del celular (elapsedRealtime, que no cambia aunque el usuario modifique la hora); «telefono» es la hora del celular.
 * reloj() devuelve {telefono, interno} para detectar cambios manuales de la hora durante la jornada.
 * abrirAjustesFecha() abre los ajustes de fecha y hora del celular.
 */
@CapacitorPlugin(name = "Hora")
public class HoraPlugin extends Plugin {

    @PluginMethod
    public void gps(PluginCall call) {
        JSObject r = new JSObject();
        long ahoraTel = System.currentTimeMillis();
        long ahoraInt = SystemClock.elapsedRealtime();
        r.put("telefono", ahoraTel);
        r.put("ok", false);
        try {
            LocationManager lm = (LocationManager) getContext().getSystemService(Context.LOCATION_SERVICE);
            Location l = lm != null ? lm.getLastKnownLocation(LocationManager.GPS_PROVIDER) : null;
            if (l != null && l.getTime() > 0 && Build.VERSION.SDK_INT >= 17) {
                long fixInt = l.getElapsedRealtimeNanos() / 1000000L;
                long edad = ahoraInt - fixInt;
                // la lectura debe ser de este encendido del celular (edad positiva) y de las últimas 12 horas
                if (fixInt > 0 && edad >= 0 && edad < 12L * 3600L * 1000L) {
                    r.put("ok", true);
                    r.put("real", l.getTime() + edad);
                    r.put("edadSeg", edad / 1000L);
                }
            }
        } catch (SecurityException e) {
            r.put("error", "sin permiso de ubicación");
        } catch (Exception e) {
            r.put("error", e.getMessage());
        }
        call.resolve(r);
    }

    @PluginMethod
    public void reloj(PluginCall call) {
        JSObject r = new JSObject();
        r.put("telefono", System.currentTimeMillis());
        r.put("interno", SystemClock.elapsedRealtime());
        call.resolve(r);
    }

    @PluginMethod
    public void abrirAjustesFecha(PluginCall call) {
        boolean ok;
        try {
            Intent i = new Intent(Settings.ACTION_DATE_SETTINGS);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(i);
            ok = true;
        } catch (Exception e) {
            ok = false;
        }
        JSObject r = new JSObject();
        r.put("abierto", ok);
        call.resolve(r);
    }
}
