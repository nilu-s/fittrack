package app.cronicl.mobile;

import android.Manifest;
import android.content.Intent;
import android.util.Base64;
import com.getcapacitor.*;
import com.getcapacitor.annotation.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import org.json.JSONObject;

@CapacitorPlugin(name = "CroniclNative", permissions = {
    @Permission(alias = "location", strings = { Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION })
})
public class CroniclNativePlugin extends Plugin {
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final GoogleLogin googleLogin = new GoogleLogin(this, network);
    @PluginMethod public void googleLogin(PluginCall call) { googleLogin.start(call); }
    @Override protected void handleOnDestroy() { googleLogin.cancel(); network.shutdown(); super.handleOnDestroy(); }
    @Override public void load() { NativeApi.origin = getConfig().getString("apiOrigin", "https://cronicl.invalid"); }
    @PluginMethod public void request(PluginCall call) {
        network.execute(() -> { try {
            String path = call.getString("path", "");
            String decoded = java.net.URI.create(path).getPath();
            if (decoded.startsWith("/api/native/google/") || decoded.startsWith("/api/native/login") || decoded.startsWith("/api/native/exchange")) { call.reject("Login requires the native module."); return; }
            String encoded = call.getString("bodyBase64");
            JSONObject response = NativeApi.request(getContext(), call.getString("path"), call.getString("method", "GET"), call.getObject("headers"), encoded == null ? null : Base64.decode(encoded, Base64.DEFAULT));
            call.resolve(new JSObject(response.toString()));
        } catch (Exception exception) { call.reject("API-Verbindung fehlgeschlagen."); } });
    }
    @PluginMethod public void clearSession(PluginCall call) {
        getContext().stopService(new Intent(getContext(), TravelLocationService.class));
        googleLogin.cancel();
        network.execute(() -> { NativeStore.clear(getContext()); googleLogin.clearProviderState(call); });
    }
    @PluginMethod public void startLocation(PluginCall call) {
        if (getPermissionState("location") != PermissionState.GRANTED) { requestPermissionForAlias("location", call, "locationPermission"); return; }
        beginLocation(call);
    }
    @PermissionCallback private void locationPermission(PluginCall call) {
        if (getPermissionState("location") != PermissionState.GRANTED) call.reject("Bitte den genauen Standort für die Begleitung erlauben.");
        else beginLocation(call);
    }
    private void beginLocation(PluginCall call) {
        try {
            String todo = UUID.fromString(call.getString("todoId")).toString();
            long expires = Instant.parse(call.getString("expiresAt")).toEpochMilli();
            if (expires <= System.currentTimeMillis() || expires > System.currentTimeMillis() + 24 * 3600000L || NativeStore.read(getContext()) == null) throw new IllegalArgumentException();
            Intent intent = new Intent(getContext(), TravelLocationService.class).putExtra("todo", todo).putExtra("expires", expires);
            getContext().startForegroundService(intent); call.resolve();
        } catch (Exception exception) { call.reject("Begleitung konnte nicht gestartet werden."); }
    }
    @PluginMethod public void stopLocation(PluginCall call) {
        getContext().stopService(new Intent(getContext(), TravelLocationService.class)); call.resolve();
    }
    @PluginMethod public void locationState(PluginCall call) {
        JSObject state = new JSObject(); state.put("active", TravelLocationService.todoId != null);
        state.put("todoId", TravelLocationService.todoId); call.resolve(state);
    }
}
