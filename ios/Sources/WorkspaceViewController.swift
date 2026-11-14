import AVFoundation
import UIKit
import WebKit

private final class ScriptMessageProxy: NSObject, WKScriptMessageHandler {
    weak var owner: WorkspaceViewController?
    init(owner: WorkspaceViewController) { self.owner = owner }
    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        owner?.receive(message)
    }
}

private final class NoRedirectDelegate: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

final class WorkspaceViewController: UIViewController, WKNavigationDelegate, WKUIDelegate,
                                     UIImagePickerControllerDelegate, UINavigationControllerDelegate, UITextFieldDelegate {
    private let turquoise = UIColor(red: 12/255, green: 115/255, blue: 118/255, alpha: 1)
    private let orange = UIColor(red: 241/255, green: 86/255, blue: 42/255, alpha: 1)
    private let content = UIView()
    private let serverButton = UIButton(type: .system)
    private let address = UITextField()
    private let connectButton = UIButton(type: .system)
    private let status = UILabel()
    private var server: URL?
    private var web: WKWebView?
    private var printWeb: WKWebView?
    private var pending: (event: String, id: String)?
    private var printTimer: Timer?
    private var checking = false
    private var connectionAttempt = UUID()
    private var healthSession: URLSession?
    private var downloads: [ObjectIdentifier: FileDownload] = [:]
    private let savedServerKey = "givingflow.server"

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .white
        let header = UIStackView()
        header.axis = .horizontal
        header.spacing = 14
        header.alignment = .center
        header.translatesAutoresizingMaskIntoConstraints = false
        header.isLayoutMarginsRelativeArrangement = true
        header.directionalLayoutMargins = NSDirectionalEdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 12)
        let logo = UIImageView(image: UIImage(named: "BrandLogo"))
        logo.contentMode = .scaleAspectFit
        logo.accessibilityLabel = "THRIFT FOR GOOD"
        logo.isAccessibilityElement = true
        logo.setContentHuggingPriority(.defaultHigh, for: .horizontal)
        let preferredLogoWidth = logo.widthAnchor.constraint(equalToConstant: 200)
        preferredLogoWidth.priority = .defaultHigh
        preferredLogoWidth.isActive = true
        logo.widthAnchor.constraint(lessThanOrEqualToConstant: 210).isActive = true
        serverButton.setTitle("Server", for: .normal)
        serverButton.tintColor = turquoise
        serverButton.setContentHuggingPriority(.required, for: .horizontal)
        serverButton.accessibilityIdentifier = "serverSettings"
        serverButton.addTarget(self, action: #selector(openSettings), for: .touchUpInside)
        header.addArrangedSubview(logo)
        header.addArrangedSubview(UIView())
        header.addArrangedSubview(serverButton)
        view.addSubview(header)
        content.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(content)
        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            header.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            header.heightAnchor.constraint(equalToConstant: 58),
            logo.heightAnchor.constraint(equalToConstant: 30),
            serverButton.widthAnchor.constraint(equalToConstant: 72),
            content.topAnchor.constraint(equalTo: header.bottomAnchor),
            content.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            content.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            content.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor)
        ])
        let isUITest = ProcessInfo.processInfo.arguments.contains("--uitesting")
        if !isUITest, let saved = UserDefaults.standard.string(forKey: savedServerKey),
           let url = try? ServerPolicy.normalize(saved) {
            server = url
            showWorkspace()
        } else {
            showConnection()
        }
    }

    @objc private func openSettings() {
        guard pending == nil, printWeb == nil, presentedViewController == nil else {
            showAlert("Finish the current camera or print action first.")
            return
        }
        showConnection()
    }

    private func label(_ text: String, style: UIFont.TextStyle = .body) -> UILabel {
        let label = UILabel()
        label.text = text
        label.numberOfLines = 0
        label.font = .preferredFont(forTextStyle: style)
        label.adjustsFontForContentSizeCategory = true
        label.textColor = UIColor(white: 0.20, alpha: 1)
        return label
    }

    private func showConnection(_ message: String = "") {
        connectionAttempt = UUID()
        healthSession?.invalidateAndCancel()
        healthSession = nil
        checking = false
        web?.configuration.userContentController.removeScriptMessageHandler(forName: "givingflow")
        web?.stopLoading()
        web?.removeFromSuperview()
        web = nil
        content.subviews.forEach { $0.removeFromSuperview() }
        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        content.addSubview(scroll)
        NSLayoutConstraint.activate([
            scroll.topAnchor.constraint(equalTo: content.topAnchor),
            scroll.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            scroll.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            scroll.trailingAnchor.constraint(equalTo: content.trailingAnchor)
        ])
        let form = UIStackView()
        form.axis = .vertical
        form.spacing = 18
        form.translatesAutoresizingMaskIntoConstraints = false
        scroll.addSubview(form)
        NSLayoutConstraint.activate([
            form.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor, constant: 24),
            form.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor, constant: -24),
            form.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor, constant: 24),
            form.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor, constant: -24),
            form.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor, constant: -48)
        ])
        form.addArrangedSubview(label("Connect to your shop PC", style: .title1))
        form.addArrangedSubview(label("Use the shop Wi-Fi or connect NetBird on this device and the PC. Photos and records save to the PC's existing database."))
        form.addArrangedSubview(label("PC server address", style: .subheadline))
        address.borderStyle = .roundedRect
        address.keyboardType = .URL
        address.autocorrectionType = .no
        address.autocapitalizationType = .none
        address.clearButtonMode = .whileEditing
        address.returnKeyType = .go
        address.delegate = self
        address.accessibilityIdentifier = "serverAddress"
        address.accessibilityLabel = "PC server address"
        address.text = server?.absoluteString
            ?? UserDefaults.standard.string(forKey: savedServerKey)
            ?? Bundle.main.object(forInfoDictionaryKey: "TFGDefaultServerURL") as? String
            ?? "http://100.88.75.17:8000"
        if ProcessInfo.processInfo.arguments.contains("--uitesting") { address.text = "" }
        address.heightAnchor.constraint(greaterThanOrEqualToConstant: 48).isActive = true
        form.addArrangedSubview(address)
        status.numberOfLines = 0
        status.textColor = UIColor(red: 0.63, green: 0.22, blue: 0.11, alpha: 1)
        status.font = .preferredFont(forTextStyle: .subheadline)
        status.accessibilityIdentifier = "connectionStatus"
        status.text = message
        form.addArrangedSubview(status)
        connectButton.setTitle("Test connection & open workspace", for: .normal)
        connectButton.backgroundColor = orange
        connectButton.setTitleColor(.black, for: .normal)
        connectButton.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        connectButton.titleLabel?.adjustsFontSizeToFitWidth = true
        connectButton.layer.cornerRadius = 8
        connectButton.accessibilityIdentifier = "connectServer"
        connectButton.isEnabled = true
        connectButton.removeTarget(nil, action: nil, for: .allEvents)
        connectButton.addTarget(self, action: #selector(testConnection), for: .touchUpInside)
        connectButton.heightAnchor.constraint(greaterThanOrEqualToConstant: 54).isActive = true
        form.addArrangedSubview(connectButton)
        form.addArrangedSubview(label("Keep NetBird connected for remote access. Use the same NetBird account or organisation as the PC. Sign in to the workspace with your separate staff account.", style: .footnote))
        form.addArrangedSubview(label("Allow Local Network and Camera when requested. This app needs a live PC connection and does not queue work offline. HTTP is for a trusted LAN or encrypted VPN pilot; use trusted HTTPS for production.", style: .footnote))
    }

    func textFieldShouldReturn(_ textField: UITextField) -> Bool { testConnection(); return false }

    @objc private func testConnection() {
        guard !checking else { return }
        let target: URL
        do { target = try ServerPolicy.normalize(address.text ?? "") }
        catch { status.text = error.localizedDescription; return }
        address.resignFirstResponder()
        checking = true
        connectButton.isEnabled = false
        status.text = "Checking PC and PostgreSQL..."
        let attempt = UUID()
        connectionAttempt = attempt
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 12
        configuration.timeoutIntervalForResource = 15
        configuration.httpShouldSetCookies = false
        let session = URLSession(configuration: configuration, delegate: NoRedirectDelegate(), delegateQueue: nil)
        healthSession = session
        let url = target.appendingPathComponent("api/health")
        session.dataTask(with: url) { [weak self] data, response, error in
            var failure: String?
            do {
                if let error = error { throw error }
                guard let response = response as? HTTPURLResponse, let data = data,
                      let finalURL = response.url, ServerPolicy.sameOrigin(target, finalURL)
                else { throw ConnectionError.unhealthyServer }
                try HealthCheck.validate(status: response.statusCode, data: data)
            } catch {
                failure = "Connection failed: \(error.localizedDescription)\nCheck NetBird, PC address, Docker, TCP 8000 access and iOS Local Network permission."
            }
            DispatchQueue.main.async {
                guard let self = self, self.connectionAttempt == attempt else { return }
                self.checking = false
                self.connectButton.isEnabled = true
                self.healthSession?.finishTasksAndInvalidate()
                self.healthSession = nil
                if let failure = failure { self.status.text = failure; return }
                self.server = target
                UserDefaults.standard.set(target.absoluteString, forKey: self.savedServerKey)
                self.showWorkspace()
            }
        }.resume()
    }

    private func showWorkspace() {
        guard let server = server else { showConnection(); return }
        content.subviews.forEach { $0.removeFromSuperview() }
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let source = """
        if (window.top === window) {
          Object.defineProperty(window, 'GivingFlowIOS', {value: Object.freeze({
            takePhoto: function(id) { window.webkit.messageHandlers.givingflow.postMessage({operation:'photo',requestId:id}); },
            scanQr: function(id) { window.webkit.messageHandlers.givingflow.postMessage({operation:'qr',requestId:id}); },
            printLabels: function(ids) { window.webkit.messageHandlers.givingflow.postMessage({operation:'print',ids:ids}); },
            shareFile: function(name,contents) { window.webkit.messageHandlers.givingflow.postMessage({operation:'share',filename:name,contents:contents}); }
          })});
        }
        """
        configuration.userContentController.addUserScript(WKUserScript(source: source, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        configuration.userContentController.add(ScriptMessageProxy(owner: self), name: "givingflow")
        let web = WKWebView(frame: .zero, configuration: configuration)
        web.translatesAutoresizingMaskIntoConstraints = false
        web.navigationDelegate = self
        web.uiDelegate = self
        web.allowsBackForwardNavigationGestures = true
        web.scrollView.keyboardDismissMode = .interactive
        content.addSubview(web)
        NSLayoutConstraint.activate([
            web.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            web.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            web.topAnchor.constraint(equalTo: content.topAnchor),
            web.bottomAnchor.constraint(equalTo: content.bottomAnchor)
        ])
        self.web = web
        web.load(URLRequest(url: server))
    }

    private func isTrusted(_ candidate: URL?) -> Bool {
        guard let server = server, let candidate = candidate else { return false }
        return ServerPolicy.sameOrigin(server, candidate)
    }

    fileprivate func receive(_ message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, message.webView === web,
              isTrusted(message.frameInfo.request.url), isTrusted(web?.url),
              let body = message.body as? [String: String], let operation = body["operation"]
        else { return }
        if operation == "share" {
            guard pending == nil, printWeb == nil, presentedViewController == nil else { return }
            shareFile(filename: body["filename"] ?? "", contents: body["contents"] ?? "")
            return
        }
        if operation == "print" {
            guard pending == nil else { showAlert("Finish the camera action first."); return }
            printLabels(body["ids"] ?? "")
            return
        }
        guard ["photo", "qr"].contains(operation), let id = body["requestId"],
              id.range(of: "^[A-Za-z0-9-]{1,80}$", options: .regularExpression) != nil else { return }
        let event = operation == "photo" ? "givingflow:photo" : "givingflow:qr"
        guard pending == nil, printWeb == nil, presentedViewController == nil else {
            emit(event, id: id, key: "error", value: "Camera or printer already in use")
            return
        }
        pending = (event, id)
        let authorized: (Bool) -> Void = { [weak self] allowed in
            DispatchQueue.main.async {
                guard let self = self, self.pending?.id == id else { return }
                guard allowed else {
                    self.finishNative(key: "error", value: "Camera permission was declined. Enable Camera in iOS Settings for Thrift for Good, or enter the printed reference.")
                    return
                }
                if operation == "photo" { self.takePhoto() } else { self.scanQR() }
            }
        }
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: authorized(true)
        case .notDetermined: AVCaptureDevice.requestAccess(for: .video, completionHandler: authorized)
        default: authorized(false)
        }
    }

    private func emit(_ event: String, id: String, key: String, value: String) {
        guard isTrusted(web?.url),
              let bytes = try? JSONSerialization.data(withJSONObject: ["requestId": id, key: value]),
              let json = String(data: bytes, encoding: .utf8),
              ["givingflow:photo", "givingflow:qr"].contains(event) else { return }
        web?.evaluateJavaScript("window.dispatchEvent(new CustomEvent('\(event)', {detail:\(json)}));", completionHandler: nil)
    }

    private func finishNative(key: String, value: String) {
        guard let request = pending else { return }
        pending = nil
        emit(request.event, id: request.id, key: key, value: value)
    }

    private func takePhoto() {
        guard UIImagePickerController.isSourceTypeAvailable(.camera) else {
            finishNative(key: "error", value: "No camera is available. Use the photo library on a physical device.")
            return
        }
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraCaptureMode = .photo
        picker.delegate = self
        picker.modalPresentationStyle = .fullScreen
        present(picker, animated: true)
    }

    func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
        picker.dismiss(animated: true) { [weak self] in self?.finishNative(key: "error", value: "cancelled") }
    }

    func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
        guard let image = info[.originalImage] as? UIImage, let id = pending?.id,
              image.size.width > 0, image.size.height > 0 else {
            picker.dismiss(animated: true) { [weak self] in self?.finishNative(key: "error", value: "Could not read the photo. Please retake it.") }
            return
        }
        picker.dismiss(animated: true) { [weak self] in
            DispatchQueue.global(qos: .userInitiated).async {
                let data: Data = autoreleasepool {
                    let scale = min(1, 1600 / max(image.size.width, image.size.height))
                    let size = CGSize(width: max(1, (image.size.width * scale).rounded()),
                                      height: max(1, (image.size.height * scale).rounded()))
                    let format = UIGraphicsImageRendererFormat()
                    format.scale = 1
                    format.opaque = true
                    return UIGraphicsImageRenderer(size: size, format: format).jpegData(withCompressionQuality: 0.85) { context in
                        UIColor.white.setFill()
                        context.fill(CGRect(origin: .zero, size: size))
                        image.draw(in: CGRect(origin: .zero, size: size))
                    }
                }
                DispatchQueue.main.async {
                    guard let self = self, self.pending?.id == id else { return }
                    self.finishNative(key: "base64", value: data.base64EncodedString())
                }
            }
        }
    }

    private func scanQR() {
        let scanner = QRScannerViewController()
        scanner.modalPresentationStyle = .fullScreen
        scanner.onResult = { [weak self] result in
            switch result {
            case .success(let value): self?.finishNative(key: "value", value: value)
            case .failure(let error): self?.finishNative(key: "error", value: error.localizedDescription)
            }
        }
        present(scanner, animated: true)
    }

    private func shareFile(filename: String, contents: String) {
        guard filename.range(of: "^[A-Za-z0-9][A-Za-z0-9._-]{0,159}\\.json$", options: .regularExpression) != nil,
              let data = contents.data(using: .utf8), data.count <= 1048576,
              (try? JSONSerialization.jsonObject(with: data)) != nil else {
            showAlert("The JSON export could not be prepared.")
            return
        }
        do {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let url = directory.appendingPathComponent(filename)
            try data.write(to: url, options: .atomic)
            presentShare(url)
        } catch { showAlert(error.localizedDescription) }
    }

    private func presentShare(_ url: URL) {
        guard presentedViewController == nil else {
            try? FileManager.default.removeItem(at: url.deletingLastPathComponent())
            return
        }
        let share = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        share.popoverPresentationController?.sourceView = serverButton
        share.popoverPresentationController?.sourceRect = serverButton.bounds
        share.completionWithItemsHandler = { _, _, _, _ in try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
        present(share, animated: true)
    }

    private func printLabels(_ ids: String) {
        guard let server = server, printWeb == nil else { return }
        do {
            let url = try ServerPolicy.labelURL(server: server, ids: ids)
            let configuration = WKWebViewConfiguration()
            configuration.websiteDataStore = .default()
            configuration.defaultWebpagePreferences.allowsContentJavaScript = false
            let printWeb = WKWebView(frame: CGRect(x: 0, y: 0, width: 794, height: 1123), configuration: configuration)
            printWeb.navigationDelegate = self
            self.printWeb = printWeb
            printTimer = Timer.scheduledTimer(withTimeInterval: 20, repeats: false) { [weak self] _ in
                guard let self = self, self.printWeb != nil else { return }
                self.clearPrint()
                self.showAlert("Labels could not load. Check the PC connection and sign in again if needed.")
            }
            printWeb.load(URLRequest(url: url))
        } catch { showAlert(error.localizedDescription) }
    }

    private func clearPrint() {
        printTimer?.invalidate()
        printTimer = nil
        printWeb?.stopLoading()
        printWeb = nil
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url, isTrusted(url) else { decisionHandler(.cancel); return }
        if action.targetFrame == nil {
            if url.path == "/api/labels",
               let ids = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first(where: { $0.name == "ids" })?.value {
                printLabels(ids)
            }
            decisionHandler(.cancel)
            return
        }
        decisionHandler(action.shouldPerformDownload ? .download : .allow)
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        guard isTrusted(response.response.url) else { decisionHandler(.cancel); return }
        if let http = response.response as? HTTPURLResponse, http.statusCode >= 400 {
            if webView === printWeb { clearPrint(); showAlert("Sign in to the workspace before printing labels.") }
            decisionHandler(.cancel)
            return
        }
        let attachment = (response.response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition")?.lowercased().contains("attachment") == true
        decisionHandler(attachment || !response.canShowMIMEType ? .download : .allow)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard webView === printWeb else { return }
        printTimer?.invalidate()
        printTimer = nil
        let controller = UIPrintInteractionController.shared
        let info = UIPrintInfo(dictionary: nil)
        info.jobName = "Thrift for Good QR labels"
        info.outputType = .general
        controller.printInfo = info
        controller.printFormatter = webView.viewPrintFormatter()
        let completion: UIPrintInteractionController.CompletionHandler = { [weak self] _, _, error in
            self?.clearPrint()
            if let error = error { self?.showAlert(error.localizedDescription) }
        }
        if UIDevice.current.userInterfaceIdiom == .pad {
            controller.present(from: serverButton.bounds, in: serverButton, animated: true, completionHandler: completion)
        } else { controller.present(animated: true, completionHandler: completion) }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        handleNavigationError(webView, error: error)
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        handleNavigationError(webView, error: error)
    }
    private func handleNavigationError(_ webView: WKWebView, error: Error) {
        guard (error as NSError).code != NSURLErrorCancelled else { return }
        if webView === printWeb { clearPrint(); showAlert(error.localizedDescription) }
        else { showConnection("PC unavailable: \(error.localizedDescription)\nCheck NetBird, PC power, Docker and Local Network permission.") }
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        if pending == nil { webView.reload() }
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { begin(download) }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { begin(download) }
    private func begin(_ download: WKDownload) {
        guard isTrusted(download.originalRequest?.url) else { download.cancel(nil); return }
        let key = ObjectIdentifier(download)
        let handler = FileDownload()
        handler.onFinish = { [weak self] result in
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.downloads.removeValue(forKey: key)
                switch result {
                case .success(let url):
                    self.presentShare(url)
                case .failure(let error): self.showAlert(error.localizedDescription)
                }
            }
        }
        downloads[key] = handler
        download.delegate = handler
    }

    private func showAlert(_ message: String) {
        guard presentedViewController == nil else { return }
        let alert = UIAlertController(title: "Thrift for Good", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }
}

private final class FileDownload: NSObject, WKDownloadDelegate {
    var onFinish: ((Result<URL, Error>) -> Void)?
    private var destination: URL?
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String,
                  completionHandler: @escaping (URL?) -> Void) {
        do {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let filename = (suggestedFilename as NSString).lastPathComponent
            let url = directory.appendingPathComponent(filename.isEmpty ? "ThriftForGood-export.json" : filename)
            destination = url
            completionHandler(url)
        } catch { completionHandler(nil); onFinish?(.failure(error)) }
    }
    func downloadDidFinish(_ download: WKDownload) {
        if let destination = destination { onFinish?(.success(destination)) }
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        if let destination = destination { try? FileManager.default.removeItem(at: destination.deletingLastPathComponent()) }
        onFinish?(.failure(error))
    }
    func download(_ download: WKDownload, willPerformHTTPRedirection response: HTTPURLResponse,
                  newRequest request: URLRequest, decisionHandler: @escaping (WKDownload.RedirectPolicy) -> Void) {
        if let original = download.originalRequest?.url, let target = request.url, ServerPolicy.sameOrigin(original, target) {
            decisionHandler(.allow)
        } else { decisionHandler(.cancel) }
    }
}
