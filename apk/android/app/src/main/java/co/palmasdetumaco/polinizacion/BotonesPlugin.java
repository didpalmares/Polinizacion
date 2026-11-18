package co.palmasdetumaco.polinizacion;

import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.app.ActivityManager;
import android.content.Context;
import android.os.Build;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Botón físico y brillo para el bloqueo de pantalla del registro de polinización.
 * - Mientras la app lo pide (jornada activa), el botón VOLUMEN ARRIBA no cambia el volumen:
 *   mantenerlo presionado 2 segundos emite el evento «volumenLargo» (bloquear / desbloquear la pantalla).
 * - brillo({nivel}) baja el brillo de la ventana (0.01 = mínimo) o lo devuelve al del sistema (-1)
 *   y mantiene la pantalla encendida mientras está bloqueada (el NFC solo lee con la pantalla encendida).
 */
@CapacitorPlugin(name = "Botones")
public class BotonesPlugin extends Plugin {
    static BotonesPlugin instancia;
    static volatile boolean capturar = false;
    static volatile boolean jornada = false; // pantalla encendida durante la jornada (el NFC solo lee con la pantalla encendida)
    private static final long LARGO_MS = 2000L;
    private final Handler h = new Handler(Looper.getMainLooper());
    private boolean presionado = false;
    private final Runnable largo = () -> {
        if (presionado) notifyListeners("volumenLargo", new JSObject());
    };

    @Override
    public void load() { instancia = this; }

    /** Llamado desde MainActivity.dispatchKeyEvent. Devuelve true si la tecla se consumió. */
    static boolean tecla(KeyEvent e) {
        BotonesPlugin p = instancia;
        if (p == null || !capturar || e.getKeyCode() != KeyEvent.KEYCODE_VOLUME_UP) return false;
        if (e.getAction() == KeyEvent.ACTION_DOWN) {
            if (e.getRepeatCount() == 0 && !p.presionado) {
                p.presionado = true;
                p.h.removeCallbacks(p.largo);
                p.h.postDelayed(p.largo, LARGO_MS);
            }
        } else if (e.getAction() == KeyEvent.ACTION_UP) {
            p.presionado = false;
            p.h.removeCallbacks(p.largo);
        }
        return true;
    }

    @PluginMethod
    public void capturar(PluginCall call) {
        capturar = call.getBoolean("on", false);
        if (!capturar) { presionado = false; h.removeCallbacks(largo); }
        call.resolve();
    }

    /** Fija la app en la pantalla (función «Fijar aplicación» de Android): no se puede ir a Inicio ni a Recientes ni abrir otra app.
     *  La primera vez Android pide confirmar. Para soltarla hace falta Atrás + Recientes (y el PIN si el celular lo pide). */
    @PluginMethod
    public void fijar(PluginCall call) {
        final boolean on = call.getBoolean("on", false);
        getActivity().runOnUiThread(() -> {
            try {
                if (on) { if (!fijada()) getActivity().startLockTask(); }
                else if (fijada()) getActivity().stopLockTask();
                JSObject r = new JSObject(); r.put("fijada", fijada()); call.resolve(r);
            } catch (Exception e) { call.reject(e.getMessage()); }
        });
    }

    @PluginMethod
    public void estadoFijado(PluginCall call) { JSObject r = new JSObject(); r.put("fijada", fijada()); call.resolve(r); }

    private boolean fijada() {
        try {
            ActivityManager am = (ActivityManager) getContext().getSystemService(Context.ACTIVITY_SERVICE);
            if (Build.VERSION.SDK_INT >= 23) return am.getLockTaskModeState() != ActivityManager.LOCK_TASK_MODE_NONE;
            return am.isInLockTaskMode();
        } catch (Exception e) { return false; }
    }

    /** Pantalla completa: oculta la barra de estado y la de navegación (reaparecen un momento deslizando desde el borde). */
    @PluginMethod
    public void pantallaCompleta(PluginCall call) {
        final boolean on = call.getBoolean("on", false);
        getActivity().runOnUiThread(() -> {
            try {
                Window w = getActivity().getWindow();
                jornada = on;
                if (on) w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                else w.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                if (Build.VERSION.SDK_INT >= 30) {
                    WindowInsetsController c = w.getInsetsController();
                    if (c != null) {
                        if (on) { c.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                            c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE); }
                        else c.show(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                    }
                } else {
                    View d = w.getDecorView();
                    d.setSystemUiVisibility(on ? (View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE) : View.SYSTEM_UI_FLAG_VISIBLE);
                }
                call.resolve();
            } catch (Exception e) { call.reject(e.getMessage()); }
        });
    }

    @PluginMethod
    public void brillo(PluginCall call) {
        final double nivel = call.getDouble("nivel", -1.0);
        getActivity().runOnUiThread(() -> {
            try {
                Window w = getActivity().getWindow();
                WindowManager.LayoutParams lp = w.getAttributes();
                if (nivel < 0) {
                    lp.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
                    if (!jornada) w.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); // en jornada la pantalla sigue encendida
                } else {
                    lp.screenBrightness = (float) Math.max(0.01, Math.min(1.0, nivel));
                    w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                }
                w.setAttributes(lp);
                call.resolve();
            } catch (Exception e) {
                call.reject(e.getMessage());
            }
        });
    }
}
