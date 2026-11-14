import AVFoundation
import UIKit

final class QRScannerViewController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
    private let session = AVCaptureSession()
    private let captureQueue = DispatchQueue(label: "org.givingflow.qr")
    private var preview: AVCaptureVideoPreviewLayer?
    private var configured = false
    private var finished = false
    var onResult: ((Result<String, Error>) -> Void)?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        let preview = AVCaptureVideoPreviewLayer(session: session)
        preview.videoGravity = .resizeAspectFill
        view.layer.addSublayer(preview)
        self.preview = preview

        let controls = UIStackView()
        controls.axis = .vertical
        controls.spacing = 16
        controls.alignment = .center
        controls.translatesAutoresizingMaskIntoConstraints = false
        let title = UILabel()
        title.text = "Scan the bag or item QR label"
        title.textColor = .white
        title.font = .preferredFont(forTextStyle: .headline)
        title.textAlignment = .center
        title.numberOfLines = 0
        let cancel = UIButton(type: .system)
        cancel.setTitle("Cancel scanning", for: .normal)
        cancel.tintColor = .white
        cancel.backgroundColor = UIColor.black.withAlphaComponent(0.65)
        cancel.layer.cornerRadius = 8
        cancel.contentEdgeInsets = UIEdgeInsets(top: 12, left: 24, bottom: 12, right: 24)
        cancel.addTarget(self, action: #selector(cancelScan), for: .touchUpInside)
        controls.addArrangedSubview(title)
        controls.addArrangedSubview(cancel)
        view.addSubview(controls)
        NSLayoutConstraint.activate([
            controls.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 24),
            controls.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -24),
            controls.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24)
        ])
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        captureQueue.async { [weak self] in self?.startCapture() }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        captureQueue.async { [weak self] in self?.session.stopRunning() }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        preview?.frame = view.bounds
        if let orientation = view.window?.windowScene?.interfaceOrientation {
            switch orientation {
            case .landscapeLeft: preview?.connection?.videoOrientation = .landscapeLeft
            case .landscapeRight: preview?.connection?.videoOrientation = .landscapeRight
            case .portraitUpsideDown: preview?.connection?.videoOrientation = .portraitUpsideDown
            default: preview?.connection?.videoOrientation = .portrait
            }
        }
    }

    private func startCapture() {
        do {
            if !configured {
                guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back)
                        ?? AVCaptureDevice.default(for: .video) else { throw ScanError.unavailable }
                let input = try AVCaptureDeviceInput(device: camera)
                let output = AVCaptureMetadataOutput()
                session.beginConfiguration()
                guard session.canAddInput(input), session.canAddOutput(output) else {
                    session.commitConfiguration()
                    throw ScanError.unavailable
                }
                session.addInput(input)
                session.addOutput(output)
                output.setMetadataObjectsDelegate(self, queue: .main)
                guard output.availableMetadataObjectTypes.contains(.qr) else {
                    session.commitConfiguration()
                    throw ScanError.unavailable
                }
                output.metadataObjectTypes = [.qr]
                session.commitConfiguration()
                configured = true
            }
            session.startRunning()
        } catch {
            DispatchQueue.main.async { [weak self] in self?.finish(.failure(error)) }
        }
    }

    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput objects: [AVMetadataObject], from connection: AVCaptureConnection) {
        guard let value = objects.compactMap({ ($0 as? AVMetadataMachineReadableCodeObject)?.stringValue }).first,
              !value.isEmpty, value.utf8.count <= 8192 else { return }
        finish(.success(value))
    }

    @objc private func cancelScan() { finish(.failure(ScanError.cancelled)) }

    private func finish(_ result: Result<String, Error>) {
        guard !finished else { return }
        finished = true
        captureQueue.async { [weak self] in self?.session.stopRunning() }
        dismiss(animated: true) { [weak self] in self?.onResult?(result) }
    }
}

enum ScanError: LocalizedError {
    case cancelled, unavailable
    var errorDescription: String? {
        self == .cancelled ? "cancelled" : "The QR camera could not start. Enter the printed reference instead."
    }
}
