package app.cronicl.mobile;

import android.app.*;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.location.*;
import android.os.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import org.json.JSONObject;

/** User-started, bounded foreground session; intentionally no boot receiver. */
public class TravelLocationService extends Service implements LocationListener {
    static volatile String todoId;
    private long expires;
    private long lastUpload;
    private LocationManager manager;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null || "stop".equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        todoId = intent.getStringExtra("todo"); expires = intent.getLongExtra("expires", 0);
        if (todoId == null || expires <= System.currentTimeMillis()) { stopSelf(); return START_NOT_STICKY; }
        NotificationManager notifications = getSystemService(NotificationManager.class);
        notifications.createNotificationChannel(new NotificationChannel("travel_location", "Aktive Anreisebegleitung", NotificationManager.IMPORTANCE_LOW));
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, TravelLocationService.class).setAction("stop"), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent open = PendingIntent.getActivity(this, 2, new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        Notification notification = new Notification.Builder(this, "travel_location").setContentTitle("Cronicl · Anreisebegleitung")
            .setContentText("Standort wird für deine Anreise aktualisiert.").setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true).setContentIntent(open).addAction(new Notification.Action.Builder(null, "Beenden", stop).build()).build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(42, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);
        else startForeground(42, notification);
        manager = getSystemService(LocationManager.class);
        try {
            manager.removeUpdates(this);
            for (String provider : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER})
                if (manager.isProviderEnabled(provider)) manager.requestLocationUpdates(provider, 60000, 100, this, Looper.getMainLooper());
        } catch (SecurityException exception) { stopSelf(); }
        handler.removeCallbacksAndMessages(null);
        handler.postDelayed(this::stopSelf, Math.max(1, expires - System.currentTimeMillis()));
        return START_NOT_STICKY;
    }
    @Override public void onLocationChanged(Location location) {
        long now = System.currentTimeMillis();
        if (now >= expires) { stopSelf(); return; }
        if (!location.hasAccuracy() || location.getAccuracy() > 200 || now - location.getTime() > 120000 || now - lastUpload < 60000) return;
        lastUpload = now;
        final String todo = todoId;
        network.execute(() -> { try {
            if (todo == null || !todo.equals(todoId) || System.currentTimeMillis() >= expires) return;
            JSONObject fix = new JSONObject().put("latitude", location.getLatitude()).put("longitude", location.getLongitude())
                .put("accuracy", location.getAccuracy()).put("measured_at", Instant.ofEpochMilli(location.getTime()).toString());
            JSONObject result = NativeApi.request(this, "/api/travel/" + todo + "/location", "POST", new JSONObject().put("Content-Type", "application/json"), fix.toString().getBytes(StandardCharsets.UTF_8));
            int status = result.getInt("status");
            if (status == 401 || status == 403 || status == 404 || status == 409) handler.post(this::stopSelf);
        } catch (Exception exception) { /* No persistent queue: an old fix is not replayed later. */ } });
    }
    @Override public void onDestroy() {
        String stoppedTodo = todoId; todoId = null;
        handler.removeCallbacksAndMessages(null);
        if (manager != null) manager.removeUpdates(this);
        // Best effort pause; local stop is immediate even without connectivity.
        if (stoppedTodo != null) network.execute(() -> { try {
            NativeApi.request(this, "/api/travel/" + stoppedTodo + "/pause", "POST", null, null);
        } catch (Exception ignored) {} });
        network.shutdown(); super.onDestroy();
    }
    @Override public void onProviderDisabled(String provider) {}
    @Override public void onProviderEnabled(String provider) {}
    @Override public void onStatusChanged(String provider, int status, Bundle extras) {}
}
