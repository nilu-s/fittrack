package app.cronicl.mobile;

import android.content.Context;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.io.InputStream;
import java.util.Iterator;
import org.json.JSONObject;

final class NativeApi {
    static String origin;
    static JSONObject request(Context context, String path, String method, JSONObject headers, byte[] body) throws Exception {
        return request(context, path, method, headers, body, true);
    }
    static JSONObject request(Context context, String path, String method, JSONObject headers, byte[] body, boolean authenticated) throws Exception {
        return send(context, path, method, headers, body, authenticated ? NativeStore.read(context) : null);
    }
    static void revokeCredential(Context context, String credential) {
        try { send(context, "/api/native/logout", "POST", null, null, credential); }
        catch (Exception ignored) { /* Offline credentials remain bounded by server expiry. */ }
    }
    private static JSONObject send(Context context, String path, String method, JSONObject headers, byte[] body, String credential) throws Exception {
        if (origin == null || !origin.startsWith("https://") || !path.startsWith("/api/") || path.contains("..") || path.contains("\\")) throw new IllegalArgumentException();
        URI base = new URI(origin);
        URI target = new URI(origin + path);
        if (!base.getHost().equals(target.getHost()) || target.getUserInfo() != null) throw new IllegalArgumentException();
        HttpURLConnection connection = (HttpURLConnection) target.toURL().openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(15000); connection.setReadTimeout(15000); connection.setRequestMethod(method);
        if (headers != null) for (Iterator<String> i = headers.keys(); i.hasNext();) {
            String name = i.next();
            if (name.equalsIgnoreCase("Content-Type") || name.equalsIgnoreCase("Accept")) connection.setRequestProperty(name, headers.getString(name));
        }
        if (credential != null) connection.setRequestProperty("Authorization", "Bearer " + credential);
        try {
            if (body != null) { connection.setDoOutput(true); connection.getOutputStream().write(body); }
            int status = connection.getResponseCode();
            InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
            if (stream != null) { byte[] buffer = new byte[8192]; int count; while ((count = stream.read(buffer)) != -1) bytes.write(buffer, 0, count); }
            String response = bytes.toString("UTF-8");
            if (stream != null) stream.close();
            return new JSONObject().put("status", status).put("body", response).put("contentType", connection.getContentType());
        } finally { connection.disconnect(); }
    }
}
