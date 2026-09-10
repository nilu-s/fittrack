package app.cronicl.mobile;

import android.content.Intent;
import android.content.MutableContextWrapper;
import android.os.CancellationSignal;
import android.util.Base64;
import androidx.core.content.ContextCompat;
import androidx.credentials.*;
import androidx.credentials.exceptions.*;
import com.getcapacitor.PluginCall;
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption;
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.concurrent.ExecutorService;
import org.json.JSONObject;

/** Tokens and the verifier never cross the JavaScript bridge. */
final class GoogleLogin {
    private final CroniclNativePlugin plugin;
    private final ExecutorService network;
    private CancellationSignal cancellation;
    private PluginCall pending;
    private long generation;

    GoogleLogin(CroniclNativePlugin plugin, ExecutorService network) {
        this.plugin = plugin; this.network = network;
    }

    synchronized void start(PluginCall call) {
        if (pending != null) { call.reject("Eine Anmeldung läuft bereits.", "LOGIN_BUSY"); return; }
        pending = call;
        long attempt = ++generation;
        network.execute(() -> {
            try {
                // A fresh login must never leave a previous account's local session active.
                try {
                    String previous = NativeStore.read(plugin.getContext());
                    if (previous != null) NativeApi.revokeCredential(plugin.getContext(), previous);
                } catch (Exception ignored) { /* An unreadable old vault must not prevent login. */ }
                plugin.getContext().stopService(new Intent(plugin.getContext(), TravelLocationService.class));
                NativeStore.clear(plugin.getContext());
                byte[] bytes = new byte[48]; new SecureRandom().nextBytes(bytes);
                String verifier = Base64.encodeToString(bytes, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
                String challenge = Base64.encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier.getBytes(StandardCharsets.UTF_8)), Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
                JSONObject started = post("/api/native/google/start", new JSONObject().put("challenge", challenge));
                plugin.getActivity().runOnUiThread(() -> openPicker(call, attempt, verifier, started));
            } catch (LoginFailure failure) { fail(call, attempt, failure.getMessage(), failure.code); }
            catch (Exception failure) { fail(call, attempt, "Anmeldung konnte nicht gestartet werden. Bitte Verbindung prüfen.", "LOGIN_NETWORK"); }
        });
    }

    private synchronized void openPicker(PluginCall call, long attempt, String verifier, JSONObject started) {
        if (attempt != generation) return;
        try {
            GetSignInWithGoogleOption option = new GetSignInWithGoogleOption.Builder(started.getString("client_id"))
                .setNonce(started.getString("nonce")).build();
            GetCredentialRequest request = new GetCredentialRequest.Builder().addCredentialOption(option).build();
            cancellation = new CancellationSignal();
            CredentialManager.create(plugin.getContext()).getCredentialAsync(
                new MutableContextWrapper(plugin.getActivity()), request, cancellation,
                ContextCompat.getMainExecutor(plugin.getContext()),
                new CredentialManagerCallback<GetCredentialResponse, GetCredentialException>() {
                    @Override public void onResult(GetCredentialResponse result) {
                        try {
                            Credential credential = result.getCredential();
                            if (!(credential instanceof CustomCredential) || !GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL.equals(credential.getType())) throw new IllegalArgumentException();
                            String token = GoogleIdTokenCredential.createFrom(credential.getData()).getIdToken();
                            network.execute(() -> complete(call, attempt, verifier, started, token));
                        } catch (Exception failure) { fail(call, attempt, "Google-Anmeldung konnte nicht gelesen werden.", "LOGIN_FAILED"); }
                    }
                    @Override public void onError(GetCredentialException error) {
                        boolean cancelled = error instanceof GetCredentialCancellationException;
                        fail(call, attempt, cancelled ? "Anmeldung abgebrochen." : "Google-Anmeldung nicht verfügbar. Bitte erneut versuchen.", cancelled ? "LOGIN_CANCELLED" : "LOGIN_FAILED");
                    }
                });
        } catch (Exception failure) { fail(call, attempt, "Google-Anmeldung nicht verfügbar.", "LOGIN_FAILED"); }
    }

    private void complete(PluginCall call, long attempt, String verifier, JSONObject started, String token) {
        synchronized (this) { if (attempt != generation) return; }
        String issued = null;
        try {
            JSONObject response = post("/api/native/google/exchange", new JSONObject()
                .put("login_id", started.getString("login_id")).put("verifier", verifier).put("id_token", token));
            String credential = response.getString("credential");
            issued = credential;
            synchronized (this) {
                if (attempt != generation) return;
                if (!credential.startsWith("crn2_")) throw new IllegalArgumentException();
                plugin.getContext().stopService(new Intent(plugin.getContext(), TravelLocationService.class));
                NativeStore.save(plugin.getContext(), credential);
                generation++; pending = null; cancellation = null; call.resolve();
                issued = null;
            }
        } catch (LoginFailure failure) { fail(call, attempt, failure.getMessage(), failure.code); }
        catch (Exception failure) { fail(call, attempt, "Anmeldung konnte nicht abgeschlossen werden. Bitte erneut versuchen.", "LOGIN_FAILED"); }
        finally { if (issued != null) NativeApi.revokeCredential(plugin.getContext(), issued); }
    }

    private JSONObject post(String path, JSONObject body) throws Exception {
        JSONObject response = NativeApi.request(plugin.getContext(), path, "POST", new JSONObject().put("Content-Type", "application/json"), body.toString().getBytes(StandardCharsets.UTF_8), false);
        int status = response.getInt("status");
        if (status == 403) throw new LoginFailure("Dieses Google-Konto ist für Cronicl nicht freigegeben.", "LOGIN_NOT_ALLOWED");
        if (status == 503) throw new LoginFailure("Die App-Anmeldung ist derzeit nicht verfügbar.", "LOGIN_UNAVAILABLE");
        if (status != 200) throw new LoginFailure("Anmeldung abgelaufen oder ungültig. Bitte erneut versuchen.", "LOGIN_FAILED");
        return new JSONObject(response.getString("body"));
    }

    private synchronized void fail(PluginCall call, long attempt, String message, String code) {
        if (attempt != generation || pending != call) return;
        generation++; pending = null; cancellation = null; call.reject(message, code);
    }

    synchronized void cancel() {
        generation++;
        if (cancellation != null) cancellation.cancel();
        if (pending != null) pending.reject("Anmeldung abgebrochen.", "LOGIN_CANCELLED");
        pending = null; cancellation = null;
    }

    void clearProviderState(PluginCall call) {
        try { CredentialManager.create(plugin.getContext()).clearCredentialStateAsync(new ClearCredentialStateRequest(), null,
            ContextCompat.getMainExecutor(plugin.getContext()), new CredentialManagerCallback<Void, ClearCredentialException>() {
                @Override public void onResult(Void ignored) { call.resolve(); }
                // Local logout must finish even if the provider is unavailable.
                @Override public void onError(ClearCredentialException error) { call.resolve(); }
            }); } catch (Exception ignored) { call.resolve(); }
    }

    private static class LoginFailure extends Exception {
        final String code;
        LoginFailure(String message, String code) { super(message); this.code = code; }
    }
}
