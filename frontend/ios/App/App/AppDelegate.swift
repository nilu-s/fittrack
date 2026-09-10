import UIKit
import Capacitor
import CoreLocation
import Security

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        NotificationCenter.default.post(name: .capacitorDidRegisterForRemoteNotifications, object: deviceToken)
    }
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        NotificationCenter.default.post(name: .capacitorDidFailToRegisterForRemoteNotifications, object: error)
    }

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Override point for customization after application launch.
        return true
    }

    func applicationWillResignActive(_ application: UIApplication) {
        // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
        // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
        // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ application: UIApplication,
                     configurationForConnecting connectingSceneSession: UISceneSession,
                     options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        let config = UISceneConfiguration(name: "Default Configuration",
                                          sessionRole: connectingSceneSession.role)
        config.delegateClass = SceneDelegate.self
        return config
    }
}

class CroniclViewController: CAPBridgeViewController {
    override func capacitorDidLoad() { bridge?.registerPluginInstance(CroniclNativePlugin()) }
}

private enum SessionVault {
    static let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: "app.cronicl.native", kSecAttrAccount as String: "session"]
    static func read() -> String? {
        var search = query; search[kSecReturnData as String] = true
        var result: CFTypeRef?
        guard SecItemCopyMatching(search as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func save(_ credential: String) throws {
        clear()
        var entry = query; entry[kSecValueData as String] = Data(credential.utf8)
        entry[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        guard SecItemAdd(entry as CFDictionary, nil) == errSecSuccess else { throw NativeFailure.failed }
    }
    static func clear() { SecItemDelete(query as CFDictionary) }
}

private enum NativeFailure: Error { case failed }

/** Redirects never carry a native bearer credential to another host. */
private class NativeHTTP: NSObject, URLSessionTaskDelegate {
    static let shared = NativeHTTP()
    var origin = "https://cronicl.invalid"
    lazy var session = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: nil)
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
    func send(path: String, method: String = "GET", headers: [String: String] = [:], body: Data? = nil,
              completion: @escaping (Result<[String: Any], Error>) -> Void) {
        guard path.hasPrefix("/api/"), !path.contains(".."), !path.contains("\\"),
              let base = URL(string: origin), base.scheme == "https", let url = URL(string: origin + path),
              url.host == base.host, url.user == nil else { completion(.failure(NativeFailure.failed)); return }
        var request = URLRequest(url: url); request.httpMethod = method; request.httpBody = body; request.timeoutInterval = 15
        for (key, value) in headers where ["content-type", "accept"].contains(key.lowercased()) { request.setValue(value, forHTTPHeaderField: key) }
        if let token = SessionVault.read() { request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization") }
        session.dataTask(with: request) { data, response, error in
            guard error == nil, let response = response as? HTTPURLResponse else { completion(.failure(NativeFailure.failed)); return }
            completion(.success(["status": response.statusCode, "body": String(data: data ?? Data(), encoding: .utf8) ?? "",
                "contentType": response.value(forHTTPHeaderField: "Content-Type") ?? "application/json"]))
        }.resume()
    }
}

@objc(CroniclNativePlugin)
public class CroniclNativePlugin: CAPPlugin, CAPBridgedPlugin, CLLocationManagerDelegate {
    public let identifier = "CroniclNativePlugin"
    public let jsName = "CroniclNative"
    public let pluginMethods: [CAPPluginMethod] = ["request", "exchange", "clearSession", "startLocation", "stopLocation", "locationState"].map { CAPPluginMethod(name: $0, returnType: CAPPluginReturnPromise) }
    private let locations = CLLocationManager()
    private var todoID: String?
    private var expiresAt: Date?
    private var expiryTimer: Timer?
    private var pendingStart: CAPPluginCall?
    private var lastUpload = Date.distantPast

    public override func load() {
        NativeHTTP.shared.origin = getConfig().getString("apiOrigin") ?? "https://cronicl.invalid"
        locations.delegate = self
        locations.desiredAccuracy = kCLLocationAccuracyHundredMeters
        locations.distanceFilter = 100
        locations.allowsBackgroundLocationUpdates = true
        locations.showsBackgroundLocationIndicator = true
        locations.pausesLocationUpdatesAutomatically = false
    }
    @objc func request(_ call: CAPPluginCall) {
        guard let path = call.getString("path") else { call.reject("Ungültige Anfrage."); return }
        let decoded = path.removingPercentEncoding ?? path
        guard !decoded.hasPrefix("/api/native/google/"), !decoded.hasPrefix("/api/native/login"),
              !decoded.hasPrefix("/api/native/exchange") else { call.reject("Login requires the native module."); return }
        let headers = call.getObject("headers") as? [String: String] ?? [:]
        NativeHTTP.shared.send(path: path, method: call.getString("method") ?? "GET", headers: headers,
            body: call.getString("bodyBase64").flatMap { Data(base64Encoded: $0) }) { result in
            switch result { case .success(let response): call.resolve(response); case .failure: call.reject("API-Verbindung fehlgeschlagen.") }
        }
    }
    @objc func exchange(_ call: CAPPluginCall) {
        guard let id = call.getString("loginId"), let verifier = call.getString("verifier"),
              let body = try? JSONSerialization.data(withJSONObject: ["login_id": id, "verifier": verifier]) else { call.reject("Ungültige Anmeldung."); return }
        NativeHTTP.shared.send(path: "/api/native/exchange", method: "POST", headers: ["Content-Type": "application/json"], body: body) { result in
            guard case .success(let response) = result, response["status"] as? Int == 200,
                let text = response["body"] as? String, let data = text.data(using: .utf8),
                let payload = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
                let credential = payload["credential"] as? String else { call.reject("Anmeldung noch nicht abgeschlossen oder abgelaufen."); return }
            do { try SessionVault.save(credential); call.resolve() } catch { call.reject("Sitzung konnte nicht sicher gespeichert werden.") }
        }
    }
    @objc func clearSession(_ call: CAPPluginCall) {
        DispatchQueue.main.async { self.stop(); SessionVault.clear(); call.resolve() }
    }
    @objc func startLocation(_ call: CAPPluginCall) {
        DispatchQueue.main.async {
            let format = ISO8601DateFormatter(); format.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            guard let id = call.getString("todoId"), UUID(uuidString: id) != nil,
                  let value = call.getString("expiresAt"), let expires = format.date(from: value) ?? ISO8601DateFormatter().date(from: value),
                  expires > Date(), expires.timeIntervalSinceNow <= 86400, SessionVault.read() != nil else { call.reject("Ungültige Begleitung."); return }
            self.todoID = id; self.expiresAt = expires; self.pendingStart = call
            if self.locations.authorizationStatus == .notDetermined { self.locations.requestWhenInUseAuthorization() }
            else { self.activateIfAuthorized() }
        }
    }
    private func activateIfAuthorized() {
        guard let call = pendingStart else { return }
        switch locations.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            locations.startUpdatingLocation()
            expiryTimer?.invalidate()
            expiryTimer = Timer.scheduledTimer(withTimeInterval: max(1, expiresAt?.timeIntervalSinceNow ?? 1), repeats: false) { [weak self] _ in self?.stop() }
            pendingStart = nil; call.resolve()
        case .denied, .restricted:
            pendingStart = nil; todoID = nil; expiresAt = nil; call.reject("Bitte den Standort in den Einstellungen erlauben.")
        default: break
        }
    }
    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        activateIfAuthorized()
        if manager.authorizationStatus == .denied || manager.authorizationStatus == .restricted { stop() }
    }
    public func locationManager(_ manager: CLLocationManager, didUpdateLocations values: [CLLocation]) {
        guard let id = todoID, let expires = expiresAt, expires > Date() else { stop(); return }
        guard let fix = values.last, fix.horizontalAccuracy >= 0, fix.horizontalAccuracy <= 200,
              Date().timeIntervalSince(fix.timestamp) <= 120, Date().timeIntervalSince(lastUpload) >= 60 else { return }
        lastUpload = Date()
        let payload: [String: Any] = ["latitude": fix.coordinate.latitude, "longitude": fix.coordinate.longitude,
            "accuracy": fix.horizontalAccuracy, "measured_at": ISO8601DateFormatter().string(from: fix.timestamp)]
        guard let body = try? JSONSerialization.data(withJSONObject: payload) else { return }
        NativeHTTP.shared.send(path: "/api/travel/\(id)/location", method: "POST", headers: ["Content-Type": "application/json"], body: body) { [weak self] result in
            if case .success(let response) = result, let status = response["status"] as? Int, [401,403,404,409].contains(status) {
                DispatchQueue.main.async { self?.stop() }
            }
        }
    }
    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if (error as? CLError)?.code == .denied { stop() }
    }
    private func stop() {
        let id = todoID; todoID = nil; expiresAt = nil
        locations.stopUpdatingLocation(); expiryTimer?.invalidate(); expiryTimer = nil
        if let id = id { NativeHTTP.shared.send(path: "/api/travel/\(id)/pause", method: "POST") { _ in } }
    }
    @objc func stopLocation(_ call: CAPPluginCall) { DispatchQueue.main.async { self.stop(); call.resolve() } }
    @objc func locationState(_ call: CAPPluginCall) {
        DispatchQueue.main.async {
            var state: [String: Any] = ["active": self.todoID != nil && (self.expiresAt ?? .distantPast) > Date()]
            if let id = self.todoID { state["todoId"] = id }
            call.resolve(state)
        }
    }
}
