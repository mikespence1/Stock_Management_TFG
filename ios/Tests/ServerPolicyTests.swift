import Foundation
import XCTest
#if SWIFT_PACKAGE
@testable import TFGCore
#else
@testable import ThriftForGood
#endif

final class ServerPolicyTests: XCTestCase {
    func testConnectsToLANAndNetBirdWithoutChangingThePort() throws {
        for address in ["http://192.168.70.5:8000", "http://10.0.0.2:8000", "http://172.16.0.1:8000",
                        "http://100.64.0.0:8000", "http://100.88.75.17:8000", "http://100.127.255.255:8000"] {
            XCTAssertEqual(try ServerPolicy.normalize(" \(address)/ ").absoluteString, address)
        }
    }

    func testAcceptsTrustedHTTPSAndLocalHostNames() throws {
        for address in ["https://stock.example.org", "http://shop-pc.local:8000", "http://localhost:8000", "http://127.0.0.1:8000"] {
            XCTAssertEqual(try ServerPolicy.normalize(address).absoluteString, address)
        }
    }

    func testRejectsPublicHTTPAndAddressesOutsideTheVPNRange() {
        for address in ["http://example.org", "http://8.8.8.8:8000", "http://100.63.255.255:8000",
                        "http://100.128.0.0:8000", "http://100.88.75.256:8000", "http://010.0.0.1:8000"] {
            XCTAssertThrowsError(try ServerPolicy.normalize(address), address)
        }
    }

    func testRejectsCredentialsQueriesPathsAndUnsupportedSchemes() {
        for address in ["file:///tmp/test", "javascript:alert(1)", "ftp://192.168.1.1",
                        "http://staff:secret@192.168.1.1", "http://192.168.1.1/api",
                        "http://192.168.1.1?x=1", "http://192.168.1.1#fragment",
                        "http://192.168.1.1:0", "http://192.168.1.1:65536", "http://"] {
            XCTAssertThrowsError(try ServerPolicy.normalize(address), address)
        }
    }

    func testBridgeOriginRequiresSameSchemeHostAndPort() throws {
        let server = try ServerPolicy.normalize("https://stock.example.org")
        XCTAssertTrue(ServerPolicy.sameOrigin(server, URL(string: "https://STOCK.example.org:443/api/labels")!))
        for address in ["http://stock.example.org", "https://stock.example.org:8000",
                        "https://other.example.org", "https://stock.example.org.evil.test",
                        "https://user@stock.example.org"] {
            XCTAssertFalse(ServerPolicy.sameOrigin(server, URL(string: address)!))
        }
    }

    func testLabelPrintingPreservesRecordIDsAndRestrictsInput() throws {
        let server = try ServerPolicy.normalize("http://100.88.75.17:8000")
        let ids = "a8a3e99c-5b03-4bb1-bf48-cece0520f390,7ecf026d-a8fb-4f84-bd02-8c1afddcc344"
        let url = try ServerPolicy.labelURL(server: server, ids: ids)
        XCTAssertTrue(ServerPolicy.sameOrigin(server, url))
        XCTAssertEqual(url.path, "/api/labels")
        XCTAssertEqual(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first?.value, ids)
        for value in ["", "not-a-record", ids + ",", "../api/health", String(repeating: ids + ",", count: 101)] {
            XCTAssertThrowsError(try ServerPolicy.labelURL(server: server, ids: value))
        }
    }

    func testHealthCheckRequiresTheActualPostgreSQLApplication() throws {
        try HealthCheck.validate(status: 200, data: Data(#"{"status":"ok","database":"postgresql"}"#.utf8))
        for (status, body) in [
            (200, #"{"status":"ok","database":"sqlite"}"#),
            (200, #"{"status":"error","database":"postgresql"}"#),
            (302, #"{"status":"ok","database":"postgresql"}"#),
            (500, #"{"status":"ok","database":"postgresql"}"#),
            (200, "<html>sign in</html>")
        ] {
            XCTAssertThrowsError(try HealthCheck.validate(status: status, data: Data(body.utf8)))
        }
        XCTAssertThrowsError(try HealthCheck.validate(status: 200, data: Data(repeating: 32, count: 65537)))
    }
}
