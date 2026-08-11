package io.github.andreivorobiev.virtualcasino;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Iterator;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import org.json.JSONArray;
import org.json.JSONObject;

/** Owns native HTTPS and an Android-Keystore encrypted session record for issue #183. */
@CapacitorPlugin(name = "CasinoSecureTransport")
public final class CasinoSecureTransportPlugin extends Plugin {
    private static final String KEY_ALIAS = "casino.mobile.session.v1";
    private static final String PREFS_NAME = "casino_mobile_vault";
    private static final String RECORD_KEY = "encrypted_record";
    private static final int MAX_BODY_BYTES = 1_048_576;
    private static final java.util.Set<String> PUBLIC_HEADERS = new java.util.HashSet<>(java.util.Arrays.asList("accept", "content-type", "idempotency-key"));

    @PluginMethod
    public synchronized void configure(PluginCall call) {
        try {
            String backend = exactBackend(call.getString("backendOrigin", ""));
            String webView = exactWebView(call.getString("webViewOrigin", ""));
            JSONObject record = loadRecord();
            if (record.has("backend_origin") || record.has("webview_origin")) {
                if (!backend.equals(record.optString("backend_origin")) || !webView.equals(record.optString("webview_origin"))) call.reject("MOBILE_NATIVE_ORIGIN_REBIND_REJECTED"); else call.resolve();
                return;
            }
            record.put("backend_origin", backend);
            record.put("webview_origin", webView);
            record.put("vault_generation", record.optInt("vault_generation", record.optInt("generation", 0)));
            record.remove("generation");
            saveRecord(record);
            call.resolve();
        } catch (Exception error) {
            call.reject("MOBILE_NATIVE_CONFIGURATION_INVALID");
        }
    }

    @PluginMethod
    public void request(PluginCall call) {
        bridge.executeOnThread(() -> {
            try {
                Object requestedGeneration = call.getData().opt("generation");
                if (!(requestedGeneration instanceof Number) || ((Number) requestedGeneration).intValue() < 0 || ((Number) requestedGeneration).doubleValue() != ((Number) requestedGeneration).intValue()) throw new IllegalArgumentException("generation required");
                JSONObject result = perform(call.getString("path", ""), call.getString("method", "GET"), call.getObject("headers", new JSObject()), call.getString("body", ""), ((Number) requestedGeneration).intValue());
                call.resolve(JSObject.fromJSONObject(result));
            } catch (Exception error) {
                call.reject("MOBILE_NATIVE_REQUEST_FAILED");
            }
        });
    }

    @PluginMethod
    public void probe(PluginCall call) {
        bridge.executeOnThread(() -> {
            synchronized (this) {
                try {
                JSONObject record = loadRecord();
                if (record.optString("token").isEmpty()) {
                    JSObject absent = new JSObject();
                    absent.put("authenticated", false);
                    absent.put("generation", record.optInt("vault_generation", 0));
                    absent.put("status", 401);
                    call.resolve(absent);
                    return;
                }
                JSONObject response = perform("/api/v2/auth/mobile/session", "GET", new JSObject(), "", record.optInt("vault_generation", 0));
                int status = response.getInt("status");
                if (status != 200 && status != 401) throw new IllegalStateException("probe rejected");
                if (status == 200) {
                    JSONObject probeEnvelope = new JSONObject(response.getString("body"));
                    JSONObject probeData = probeEnvelope.optJSONObject("data");
                    JSONObject probeSession = probeData == null ? null : probeData.optJSONObject("session");
                    Object probeGeneration = probeSession == null ? null : probeSession.opt("generation");
                    int storedSessionGeneration = record.optInt("session_generation", -1);
                    if (!Boolean.TRUE.equals(probeData == null ? null : probeData.opt("authenticated")) || !(probeGeneration instanceof Number) || storedSessionGeneration < 1 || ((Number) probeGeneration).intValue() != storedSessionGeneration || ((Number) probeGeneration).doubleValue() != ((Number) probeGeneration).intValue() || !(probeSession.opt("issued_at") instanceof String) || ((String) probeSession.opt("issued_at")).isEmpty() || !(probeSession.opt("expires_at") instanceof String) || ((String) probeSession.opt("expires_at")).isEmpty() || !"active".equals(probeSession.opt("status"))) throw new IllegalStateException("probe envelope invalid");
                }
                JSObject result = new JSObject();
                result.put("authenticated", status == 200);
                result.put("generation", response.getInt("generation"));
                result.put("status", status);
                call.resolve(result);
                } catch (Exception error) {
                    call.reject("MOBILE_NATIVE_SESSION_PROBE_FAILED");
                }
            }
        });
    }

    @PluginMethod
    public void revokeAndClear(PluginCall call) {
        bridge.executeOnThread(() -> {
            try {
                synchronized (this) {
                    JSONObject record = loadRecord();
                    if (record.optString("token").isEmpty()) {
                        JSObject empty = new JSObject();
                        empty.put("revoked", true);
                        empty.put("cleared", true);
                        call.resolve(empty);
                        return;
                    }
                    JSONObject response = perform("/api/v2/auth/mobile/session/revoke", "POST", new JSObject(), "{}", record.optInt("vault_generation", 0));
                    if (response.getInt("status") != 200 && response.getInt("status") != 401) throw new IllegalStateException("revoke rejected");
                    JSObject result = new JSObject();
                    result.put("revoked", true);
                    result.put("cleared", true);
                    call.resolve(result);
                }
            } catch (Exception error) {
                call.reject("MOBILE_NATIVE_ACCOUNT_SWITCH_REVOKE_FAILED");
            }
        });
    }

    @PluginMethod
    public synchronized void claimDeepLink(PluginCall call) {
        try {
            String fingerprint = call.getString("fingerprint", "");
            if (!fingerprint.matches("^[a-f0-9]{64}$")) throw new IllegalArgumentException("invalid fingerprint");
            JSONObject record = loadRecord();
            JSONArray retained = record.optJSONArray("deep_link_fingerprints");
            if (retained == null) retained = new JSONArray();
            for (int index = 0; index < retained.length(); index += 1) {
                if (fingerprint.equals(retained.optString(index))) {
                    JSObject replay = new JSObject();
                    replay.put("claimed", false);
                    call.resolve(replay);
                    return;
                }
            }
            JSONArray bounded = new JSONArray();
            for (int index = Math.max(0, retained.length() - 63); index < retained.length(); index += 1) bounded.put(retained.getString(index));
            bounded.put(fingerprint);
            record.put("deep_link_fingerprints", bounded);
            saveRecord(record);
            JSObject result = new JSObject();
            result.put("claimed", true);
            call.resolve(result);
        } catch (Exception error) {
            call.reject("MOBILE_NATIVE_DEEP_LINK_CLAIM_FAILED");
        }
    }

    private synchronized JSONObject perform(String path, String method, JSObject publicHeaders, String body, int expectedGeneration) throws Exception {
        JSONObject record = loadRecord();
        int vaultGeneration = record.optInt("vault_generation", 0);
        if (expectedGeneration < 0 || expectedGeneration != vaultGeneration) throw new IllegalStateException("stale generation");
        if (!path.matches("^/api/(?:v1|v2)/[A-Za-z0-9_./?=&%+-]*$") || path.contains("//")) throw new IllegalArgumentException("invalid path");
        String normalizedMethod = method.toUpperCase();
        if (!normalizedMethod.matches("GET|POST|PUT|PATCH|DELETE|HEAD")) throw new IllegalArgumentException("invalid method");
        if (("/api/v2/auth/login".equals(path) || "/api/v2/auth/guest".equals(path)) && !record.optString("token").isEmpty()) throw new IllegalStateException("active session replacement rejected");
        URL url = new URL(record.getString("backend_origin") + path);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        try {
        connection.setInstanceFollowRedirects(false);
        connection.setUseCaches(false);
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(15000);
        connection.setRequestMethod(normalizedMethod);
        connection.setRequestProperty("Origin", record.getString("webview_origin"));
        connection.setRequestProperty("X-Casino-Mobile-Client", "1");
        Iterator<String> headerNames = publicHeaders.keys();
        while (headerNames.hasNext()) {
            String name = headerNames.next();
            String lower = name.toLowerCase();
            if (!PUBLIC_HEADERS.contains(lower)) throw new IllegalArgumentException("unowned header");
            connection.setRequestProperty(name, publicHeaders.getString(name));
        }
        connection.setRequestProperty("Cache-Control", "no-store");
        String token = record.optString("token");
        String csrf = record.optString("csrf_token");
        if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
        if (!csrf.isEmpty() && normalizedMethod.matches("POST|PUT|PATCH|DELETE")) connection.setRequestProperty("X-CSRF-Token", csrf);
        String guestNonce = record.optString("guest_browser_nonce");
        if (!guestNonce.isEmpty()) connection.setRequestProperty("X-Guest-Browser-Nonce", guestNonce);
        if ("/api/v2/auth/mobile/session/rotate".equals(path)) body = new JSONObject().put("expected_generation", record.optInt("session_generation", -1)).toString();
        if (!body.isEmpty() && normalizedMethod.matches("POST|PUT|PATCH|DELETE")) {
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            if (bytes.length > MAX_BODY_BYTES) throw new IllegalArgumentException("body too large");
            connection.setDoOutput(true);
            try (OutputStream output = connection.getOutputStream()) { output.write(bytes); }
        }
        int status = connection.getResponseCode();
        InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
        String responseBody = readBounded(stream);
        if (responseBody.isEmpty()) throw new IllegalStateException("empty API response");
        JSONObject envelope = new JSONObject(responseBody);
        JSONObject data = envelope.optJSONObject("data");
        boolean successStatus = status >= 200 && status < 300;
        if (successStatus && (!Boolean.TRUE.equals(envelope.opt("ok")) || data == null)) throw new IllegalStateException("success envelope invalid");
        boolean terminalSession = "/api/v2/auth/logout".equals(path) || "/api/v2/auth/guest/end".equals(path) || "/api/v2/auth/mobile/session/revoke".equals(path);
        if (terminalSession && successStatus) {
            String acknowledgement = "/api/v2/auth/logout".equals(path) ? "logged_out" : ("/api/v2/auth/guest/end".equals(path) ? "ended" : "revoked");
            if (!Boolean.TRUE.equals(data.opt(acknowledgement))) throw new IllegalStateException("terminal acknowledgement invalid");
        }
        boolean credentialIssuance = ("/api/v2/auth/login".equals(path) || "/api/v2/auth/guest".equals(path) || "/api/v2/auth/mobile/session/rotate".equals(path)) && successStatus;
        JSONObject session = data == null ? null : data.optJSONObject("session");
        boolean issuedSession = false;
        if (credentialIssuance && session != null) {
            Object issuedToken = session.remove("token");
            Object issuedCsrf = session.remove("csrf_token");
            Object issuedSessionId = session.opt("session_id");
            Object issuedGeneration = session.opt("generation");
            if (!(issuedToken instanceof String) || ((String) issuedToken).isEmpty() || !(issuedCsrf instanceof String) || ((String) issuedCsrf).isEmpty() || !(issuedSessionId instanceof String) || ((String) issuedSessionId).isEmpty() || !(issuedGeneration instanceof Number) || ((Number) issuedGeneration).intValue() < 1 || ((Number) issuedGeneration).doubleValue() != ((Number) issuedGeneration).intValue()) throw new IllegalStateException("issuance invalid");
            record.put("token", issuedToken);
            record.put("csrf_token", issuedCsrf);
            record.put("session_id", issuedSessionId);
            record.put("session_generation", ((Number) issuedGeneration).intValue());
            record.put("vault_generation", vaultGeneration + 1);
            JSONObject user = data.optJSONObject("user");
            String accountId = user == null ? data.optString("user_id") : user.optString("user_id");
            if (!accountId.isEmpty()) record.put("account_id", accountId);
            issuedSession = true;
        }
        if (credentialIssuance && !issuedSession) throw new IllegalStateException("issuance invalid");
        String issuedGuestNonce = "";
        if (credentialIssuance && "/api/v2/auth/guest".equals(path) && data != null) {
            Object guestNonceValue = data.remove("guest_browser_nonce");
            issuedGuestNonce = guestNonceValue instanceof String ? (String) guestNonceValue : "";
            if (!issuedGuestNonce.isEmpty()) record.put("guest_browser_nonce", issuedGuestNonce);
        }
        if ("/api/v2/auth/guest".equals(path) && credentialIssuance && issuedGuestNonce.isEmpty()) throw new IllegalStateException("guest issuance invalid");
        rejectCredentialResidue(envelope, 0, new int[] {0});
        if (status == 401 || (terminalSession && status >= 200 && status < 300)) clearCredentials(record); else if (issuedSession) saveRecord(record);
        JSObject headers = new JSObject();
        String contentType = connection.getHeaderField("Content-Type");
        if (contentType != null) headers.put("Content-Type", contentType);
        JSONObject result = new JSONObject();
        result.put("status", status);
        result.put("headers", headers);
        result.put("body", envelope.length() == 0 ? responseBody : envelope.toString());
        result.put("generation", loadRecord().optInt("vault_generation", 0));
        result.put("sessionChanged", status == 401 || issuedSession || (terminalSession && status >= 200 && status < 300));
        return result;
        } finally {
            connection.disconnect();
        }
    }

    private void rejectCredentialResidue(Object value, int depth, int[] visited) throws Exception {
        if (depth > 16 || ++visited[0] > 10000) throw new IllegalStateException("response shape invalid");
        if (value instanceof JSONObject) {
            JSONObject object = (JSONObject) value;
            Iterator<String> names = object.keys();
            while (names.hasNext()) {
                String name = names.next();
                if ("token".equals(name) || "csrf_token".equals(name) || "guest_browser_nonce".equals(name)) throw new IllegalStateException("credential residue");
                rejectCredentialResidue(object.get(name), depth + 1, visited);
            }
        } else if (value instanceof JSONArray) {
            JSONArray array = (JSONArray) value;
            for (int index = 0; index < array.length(); index += 1) rejectCredentialResidue(array.get(index), depth + 1, visited);
        }
    }

    private String readBounded(InputStream stream) throws Exception {
        if (stream == null) return "";
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int total = 0;
        int count;
        while ((count = stream.read(buffer)) != -1) {
            total += count;
            if (total > MAX_BODY_BYTES) throw new IllegalStateException("response too large");
            output.write(buffer, 0, count);
        }
        return output.toString(StandardCharsets.UTF_8.name());
    }

    private String exactBackend(String value) throws Exception {
        URI uri = new URI(value);
        if (!"https://casino.tiltseven.com".equals(value) || !"https".equals(uri.getScheme()) || !"casino.tiltseven.com".equals(uri.getHost()) || uri.getUserInfo() != null || uri.getPort() != -1 || uri.getPath() == null || !uri.getPath().isEmpty() || uri.getQuery() != null || uri.getFragment() != null) throw new IllegalArgumentException("backend");
        return uri.toString();
    }

    private String exactWebView(String value) throws Exception {
        URI uri = new URI(value);
        if (!("https".equals(uri.getScheme()) || "capacitor".equals(uri.getScheme())) || !"localhost".equals(uri.getHost()) || uri.getUserInfo() != null || uri.getPort() != -1 || (uri.getPath() != null && !uri.getPath().isEmpty()) || uri.getQuery() != null || uri.getFragment() != null) throw new IllegalArgumentException("webview");
        return uri.toString();
    }

    private synchronized void clearCredentials(JSONObject record) throws Exception {
        record.remove("token");
        record.remove("csrf_token");
        record.remove("guest_browser_nonce");
        record.remove("account_id");
        record.remove("session_id");
        record.remove("session_generation");
        record.put("vault_generation", record.optInt("vault_generation", 0) + 1);
        saveRecord(record);
    }

    private SharedPreferences preferences() {
        return getContext().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    private SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return ((KeyStore.SecretKeyEntry) store.getEntry(KEY_ALIAS, null)).getSecretKey();
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build());
        return generator.generateKey();
    }

    private synchronized JSONObject loadRecord() throws Exception {
        String encoded = preferences().getString(RECORD_KEY, "");
        if (encoded.isEmpty()) return new JSONObject();
        byte[] packed = Base64.decode(encoded, Base64.NO_WRAP);
        if (packed.length < 13) throw new IllegalStateException("vault record invalid");
        byte[] iv = new byte[12];
        byte[] ciphertext = new byte[packed.length - 12];
        System.arraycopy(packed, 0, iv, 0, 12);
        System.arraycopy(packed, 12, ciphertext, 0, ciphertext.length);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, iv));
        return new JSONObject(new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8));
    }

    private synchronized void saveRecord(JSONObject record) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key());
        byte[] ciphertext = cipher.doFinal(record.toString().getBytes(StandardCharsets.UTF_8));
        byte[] iv = cipher.getIV();
        byte[] packed = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, packed, 0, iv.length);
        System.arraycopy(ciphertext, 0, packed, iv.length, ciphertext.length);
        if (!preferences().edit().putString(RECORD_KEY, Base64.encodeToString(packed, Base64.NO_WRAP)).commit()) throw new IllegalStateException("vault commit failed");
    }
}
