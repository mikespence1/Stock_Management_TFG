// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TFGCore",
    products: [.library(name: "TFGCore", targets: ["TFGCore"])],
    targets: [
        .target(name: "TFGCore", path: "Sources/Core"),
        .testTarget(name: "TFGCoreTests", dependencies: ["TFGCore"], path: "Tests")
    ]
)
