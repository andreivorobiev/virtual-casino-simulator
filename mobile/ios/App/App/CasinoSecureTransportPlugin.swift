import Foundation
import Security
import Capacitor

/// Rejects every HTTP redirect so native authentication never changes authority implicitly.
private final class CasinoNoRedirectDelegate: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

/// Owns native HTTPS and a this-device-only Keychain session record for issue #183.
@objc(CasinoSecureTransportPlugin)
public final class CasinoSecureTransportPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "CasinoSecureTransportPlugin"
    public let jsName = "CasinoSecureTransport"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "configure", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "request", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "probe", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "revokeAndClear", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "claimDeepLink", returnType: CAPPluginReturnPromise)
    ]
    private let service = "io.github.andreivorobiev.virtualcasino.mobile-session-v1"
    private let account = "active"
    private let maximumBodyBytes = 1_048_576
    private let lock = NSLock()
    private let sessionMutation = DispatchSemaphore(value: 1)

    @objc func configure(_ call: CAPPluginCall) {
        sessionMutation.wait()
        defer { sessionMutation.signal() }
        lock.lock()
        defer { lock.unlock() }
        do {
            let backend = try exactBackend(call.getString("backendOrigin") ?? "")
            let webView = try exactWebView(call.getString("webViewOrigin") ?? "")
            var record = try loadRecord()
            if record["backend_origin"] != nil || record["webview_origin"] != nil {
                if record["backend_origin"] as? String != backend || record["webview_origin"] as? String != webView { call.reject("MOBILE_NATIVE_ORIGIN_REBIND_REJECTED") } else { call.resolve() }
                return
            }
            record["backend_origin"] = backend
            record["webview_origin"] = webView
            record["vault_generation"] = record["vault_generation"] as? Int ?? record["generation"] as? Int ?? 0
            record.removeValue(forKey: "generation")
            try saveRecord(record)
            call.resolve()
        } catch {
            call.reject("MOBILE_NATIVE_CONFIGURATION_INVALID")
        }
    }

    @objc func request(_ call: CAPPluginCall) {
        Task {
            do {
                guard let expectedGeneration = call.getInt("generation"), expectedGeneration >= 0 else { throw VaultError.staleGeneration }
                let result = try await perform(path: call.getString("path") ?? "", method: call.getString("method") ?? "GET", headers: call.getObject("headers") ?? [:], body: call.getString("body") ?? "", expectedGeneration: expectedGeneration)
                call.resolve(result)
            } catch {
                call.reject("MOBILE_NATIVE_REQUEST_FAILED")
            }
        }
    }

    @objc func probe(_ call: CAPPluginCall) {
        Task {
            sessionMutation.wait()
            defer { sessionMutation.signal() }
            do {
                let record = try loadRecord()
                guard let token = record["token"] as? String, !token.isEmpty else {
                    call.resolve(["authenticated": false, "generation": record["vault_generation"] as? Int ?? 0, "status": 401])
                    return
                }
                let generation = record["vault_generation"] as? Int ?? 0
                let result = try await perform(path: "/api/v2/auth/mobile/session", method: "GET", headers: [:], body: "", expectedGeneration: generation, serializeSession: false)
                let status = result["status"] as? Int ?? 0
                guard [200, 401].contains(status) else { throw VaultError.invalidRecord }
                if status == 200 {
                    guard let storedSessionGeneration = record["session_generation"] as? Int, storedSessionGeneration >= 1, let body = result["body"] as? String, let bodyData = body.data(using: .utf8), let envelope = try JSONSerialization.jsonObject(with: bodyData) as? [String: Any], let payload = envelope["data"] as? [String: Any], payload["authenticated"] as? Bool == true, let session = payload["session"] as? [String: Any], let sessionGeneration = session["generation"] as? Int, sessionGeneration == storedSessionGeneration, let issuedAt = session["issued_at"] as? String, !issuedAt.isEmpty, let expiresAt = session["expires_at"] as? String, !expiresAt.isEmpty, session["status"] as? String == "active" else { throw VaultError.invalidEnvelope }
                }
                call.resolve(["authenticated": status == 200, "generation": result["generation"] as? Int ?? generation, "status": status])
            } catch {
                call.reject("MOBILE_NATIVE_SESSION_PROBE_FAILED")
            }
        }
    }

    @objc func revokeAndClear(_ call: CAPPluginCall) {
        Task {
            sessionMutation.wait()
            defer { sessionMutation.signal() }
            do {
                var record = try loadRecord()
                if let token = record["token"] as? String, !token.isEmpty {
                    let generation = record["vault_generation"] as? Int ?? 0
                    let result = try await perform(path: "/api/v2/auth/mobile/session/revoke", method: "POST", headers: [:], body: "{}", expectedGeneration: generation, serializeSession: false)
                    guard [200, 401].contains(result["status"] as? Int ?? 0) else { throw VaultError.invalidRecord }
                    record = try loadRecord()
                }
                if record["token"] != nil { try clearCredentials(&record) }
                call.resolve(["revoked": true, "cleared": true])
            } catch {
                call.reject("MOBILE_NATIVE_ACCOUNT_SWITCH_REVOKE_FAILED")
            }
        }
    }

    @objc func claimDeepLink(_ call: CAPPluginCall) {
        do {
            let fingerprint = call.getString("fingerprint") ?? ""
            guard fingerprint.range(of: "^[a-f0-9]{64}$", options: .regularExpression) != nil else { throw VaultError.invalidRecord }
            lock.lock()
            defer { lock.unlock() }
            var record = try loadRecord()
            var fingerprints = record["deep_link_fingerprints"] as? [String] ?? []
            guard !fingerprints.contains(fingerprint) else {
                call.resolve(["claimed": false])
                return
            }
            fingerprints = Array(fingerprints.suffix(63)) + [fingerprint]
            record["deep_link_fingerprints"] = fingerprints
            try saveRecord(record)
            call.resolve(["claimed": true])
        } catch {
            call.reject("MOBILE_NATIVE_DEEP_LINK_CLAIM_FAILED")
        }
    }

    private func perform(path: String, method: String, headers: JSObject, body: String, expectedGeneration: Int, serializeSession: Bool = true) async throws -> JSObject {
        if serializeSession { sessionMutation.wait() }
        defer { if serializeSession { sessionMutation.signal() } }
        lock.lock()
        let loadedRecord: [String: Any]
        do { loadedRecord = try loadRecord(); lock.unlock() } catch { lock.unlock(); throw error }
        var record = loadedRecord
        let vaultGeneration = record["vault_generation"] as? Int ?? 0
        guard expectedGeneration >= 0, expectedGeneration == vaultGeneration else { throw VaultError.staleGeneration }
        guard path.range(of: "^/api/(?:v1|v2)/[A-Za-z0-9_./?=&%+-]*$", options: .regularExpression) != nil, !path.contains("//") else { throw VaultError.invalidPath }
        let normalizedMethod = method.uppercased()
        guard ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"].contains(normalizedMethod) else { throw VaultError.invalidMethod }
        guard !["/api/v2/auth/login", "/api/v2/auth/guest"].contains(path) || (record["token"] as? String ?? "").isEmpty else { throw VaultError.staleGeneration }
        guard let backend = record["backend_origin"] as? String, let url = URL(string: backend + path), let webViewOrigin = record["webview_origin"] as? String else { throw VaultError.invalidRecord }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData, timeoutInterval: 15)
        request.httpMethod = normalizedMethod
        request.setValue(webViewOrigin, forHTTPHeaderField: "Origin")
        request.setValue("1", forHTTPHeaderField: "X-Casino-Mobile-Client")
        let publicHeaders = Set(["accept", "content-type", "idempotency-key"])
        for (name, value) in headers {
            let lower = name.lowercased()
            guard publicHeaders.contains(lower), let stringValue = value as? String else { throw VaultError.credentialHeader }
            request.setValue(stringValue, forHTTPHeaderField: name)
        }
        request.setValue("no-store", forHTTPHeaderField: "Cache-Control")
        if let token = record["token"] as? String, !token.isEmpty { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        if ["POST", "PUT", "PATCH", "DELETE"].contains(normalizedMethod), let csrf = record["csrf_token"] as? String, !csrf.isEmpty { request.setValue(csrf, forHTTPHeaderField: "X-CSRF-Token") }
        if let guestNonce = record["guest_browser_nonce"] as? String, !guestNonce.isEmpty { request.setValue(guestNonce, forHTTPHeaderField: "X-Guest-Browser-Nonce") }
        var requestBody = body
        if path == "/api/v2/auth/mobile/session/rotate" { requestBody = String(data: try JSONSerialization.data(withJSONObject: ["expected_generation": record["session_generation"] as? Int ?? -1]), encoding: .utf8) ?? "" }
        if !requestBody.isEmpty && ["POST", "PUT", "PATCH", "DELETE"].contains(normalizedMethod) {
            guard let bytes = requestBody.data(using: .utf8), bytes.count <= maximumBodyBytes else { throw VaultError.bodyTooLarge }
            request.httpBody = bytes
        }
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpCookieStorage = nil
        configuration.httpShouldSetCookies = false
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        let session = URLSession(configuration: configuration, delegate: CasinoNoRedirectDelegate(), delegateQueue: nil)
        defer { session.finishTasksAndInvalidate() }
        let (data, response) = try await session.data(for: request)
        guard data.count <= maximumBodyBytes, let http = response as? HTTPURLResponse else { throw VaultError.bodyTooLarge }
        guard !data.isEmpty, let envelopeObject = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw VaultError.invalidEnvelope }
        var envelope = envelopeObject
        let successStatus = (200..<300).contains(http.statusCode)
        guard !successStatus || (envelopeObject["ok"] as? Bool == true && envelopeObject["data"] is [String: Any]) else { throw VaultError.invalidEnvelope }
        let terminalSession = ["/api/v2/auth/logout", "/api/v2/auth/guest/end", "/api/v2/auth/mobile/session/revoke"].contains(path)
        if terminalSession && successStatus {
            let acknowledgement = path == "/api/v2/auth/logout" ? "logged_out" : (path == "/api/v2/auth/guest/end" ? "ended" : "revoked")
            guard (envelopeObject["data"] as? [String: Any])?[acknowledgement] as? Bool == true else { throw VaultError.invalidEnvelope }
        }
        let credentialIssuance = ["/api/v2/auth/login", "/api/v2/auth/guest", "/api/v2/auth/mobile/session/rotate"].contains(path) && successStatus
        var issuedSession = false
        if credentialIssuance, var payload = envelope["data"] as? [String: Any], var sessionBody = payload["session"] as? [String: Any] {
            let token = sessionBody.removeValue(forKey: "token") as? String
            let csrf = sessionBody.removeValue(forKey: "csrf_token") as? String
            guard let token, !token.isEmpty, let csrf, !csrf.isEmpty, let sessionId = sessionBody["session_id"] as? String, !sessionId.isEmpty, let sessionGeneration = sessionBody["generation"] as? Int, sessionGeneration >= 1 else { throw VaultError.invalidEnvelope }
            record["token"] = token
            record["csrf_token"] = csrf
            record["session_id"] = sessionId
            record["session_generation"] = sessionGeneration
            record["vault_generation"] = vaultGeneration + 1
            let userBody = payload["user"] as? [String: Any]
            record["account_id"] = userBody?["user_id"] as? String ?? payload["user_id"] as? String ?? record["account_id"]
            issuedSession = true
            payload["session"] = sessionBody
            envelope["data"] = payload
        }
        guard !credentialIssuance || issuedSession else { throw VaultError.invalidEnvelope }
        var issuedGuestNonce = false
        if credentialIssuance && path == "/api/v2/auth/guest", var payload = envelope["data"] as? [String: Any] {
            let guestNonce = payload.removeValue(forKey: "guest_browser_nonce") as? String
            if let guestNonce, !guestNonce.isEmpty { record["guest_browser_nonce"] = guestNonce; issuedGuestNonce = true }
            envelope["data"] = payload
        }
        guard path != "/api/v2/auth/guest" || !credentialIssuance || issuedGuestNonce else { throw VaultError.invalidEnvelope }
        _ = try rejectCredentialResidue(envelope, depth: 0, visited: 0)
        lock.lock()
        defer { lock.unlock() }
        let current = try loadRecord()
        guard (current["vault_generation"] as? Int ?? 0) == vaultGeneration else { throw VaultError.staleGeneration }
        if let fingerprints = current["deep_link_fingerprints"] { record["deep_link_fingerprints"] = fingerprints }
        if http.statusCode == 401 || (terminalSession && (200..<300).contains(http.statusCode)) { try clearCredentials(&record) } else if issuedSession { try saveRecord(record) }
        let sanitized = String(data: try JSONSerialization.data(withJSONObject: envelope), encoding: .utf8) ?? ""
        return ["status": http.statusCode, "headers": ["Content-Type": http.value(forHTTPHeaderField: "Content-Type") ?? "application/json"], "body": sanitized, "generation": record["vault_generation"] as? Int ?? 0, "sessionChanged": http.statusCode == 401 || issuedSession || (terminalSession && (200..<300).contains(http.statusCode))]
    }

    private func rejectCredentialResidue(_ value: Any, depth: Int, visited: Int) throws -> Int {
        guard depth <= 16, visited < 10000 else { throw VaultError.invalidEnvelope }
        var count = visited + 1
        if let object = value as? [String: Any] {
            for (name, child) in object {
                guard !["token", "csrf_token", "guest_browser_nonce"].contains(name) else { throw VaultError.invalidEnvelope }
                count = try rejectCredentialResidue(child, depth: depth + 1, visited: count)
            }
        } else if let array = value as? [Any] {
            for child in array { count = try rejectCredentialResidue(child, depth: depth + 1, visited: count) }
        }
        return count
    }

    private func exactBackend(_ value: String) throws -> String {
        guard value == "https://casino.tiltseven.com", let components = URLComponents(string: value), components.scheme == "https", components.host == "casino.tiltseven.com", components.port == nil, components.user == nil, components.password == nil, components.path.isEmpty, components.query == nil, components.fragment == nil else { throw VaultError.invalidOrigin }
        return components.url!.absoluteString
    }

    private func exactWebView(_ value: String) throws -> String {
        guard let components = URLComponents(string: value), ["https", "capacitor"].contains(components.scheme), components.host == "localhost", components.port == nil, components.user == nil, components.password == nil, components.path.isEmpty, components.query == nil, components.fragment == nil else { throw VaultError.invalidOrigin }
        return components.url!.absoluteString
    }

    private func clearCredentials(_ record: inout [String: Any]) throws {
        ["token", "csrf_token", "guest_browser_nonce", "account_id", "session_id", "session_generation"].forEach { record.removeValue(forKey: $0) }
        record["vault_generation"] = (record["vault_generation"] as? Int ?? 0) + 1
        try saveRecord(record)
    }

    private func loadRecord() throws -> [String: Any] {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account, kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound { return [:] }
        guard status == errSecSuccess, let data = item as? Data, let record = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw VaultError.invalidRecord }
        return record
    }

    private func saveRecord(_ record: [String: Any]) throws {
        let data = try JSONSerialization.data(withJSONObject: record)
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account]
        let attributes: [String: Any] = [kSecValueData as String: data, kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly, kSecAttrSynchronizable as String: false]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var inserted = query
            attributes.forEach { inserted[$0.key] = $0.value }
            guard SecItemAdd(inserted as CFDictionary, nil) == errSecSuccess else { throw VaultError.keychainFailure }
        } else if status != errSecSuccess { throw VaultError.keychainFailure }
    }

    private enum VaultError: Error {
        case invalidRecord, invalidEnvelope, staleGeneration, invalidPath, invalidMethod, credentialHeader, bodyTooLarge, invalidOrigin, keychainFailure
    }
}
