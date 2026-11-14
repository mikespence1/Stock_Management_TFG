import Foundation

public enum ConnectionError: LocalizedError {
    case invalidAddress, insecureAddress, unhealthyServer, wrongDatabase, invalidLabels

    public var errorDescription: String? {
        switch self {
        case .invalidAddress:
            return "Enter a complete PC address, such as http://100.88.75.17:8000, without a path, login or query."
        case .insecureAddress:
            return "HTTP is limited to a local PC or private VPN address. Use trusted HTTPS for an internet server."
        case .unhealthyServer:
            return "The PC responded, but its application is not ready. Start Docker and check /api/health."
        case .wrongDatabase:
            return "This server is not connected to PostgreSQL. Use the Docker application on your PC."
        case .invalidLabels:
            return "Select valid bag or item labels before printing."
        }
    }
}

public enum ServerPolicy {
    public static func normalize(_ input: String) throws -> URL {
        guard var parts = URLComponents(string: input.trimmingCharacters(in: .whitespacesAndNewlines)),
              let scheme = parts.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              let host = parts.host?.lowercased(), !host.isEmpty,
              parts.user == nil, parts.password == nil,
              parts.query == nil, parts.fragment == nil,
              parts.path.isEmpty || parts.path == "/",
              parts.port == nil || (1...65535).contains(parts.port!)
        else { throw ConnectionError.invalidAddress }
        if scheme == "http" && !isPrivateHost(host) { throw ConnectionError.insecureAddress }
        parts.scheme = scheme
        parts.host = host
        parts.path = ""
        guard let url = parts.url else { throw ConnectionError.invalidAddress }
        return url
    }

    public static func sameOrigin(_ first: URL, _ second: URL) -> Bool {
        guard let a = URLComponents(url: first, resolvingAgainstBaseURL: false),
              let b = URLComponents(url: second, resolvingAgainstBaseURL: false),
              let hostA = a.host?.lowercased(), let hostB = b.host?.lowercased(),
              a.user == nil, a.password == nil, b.user == nil, b.password == nil
        else { return false }
        let schemeA = a.scheme?.lowercased(), schemeB = b.scheme?.lowercased()
        return schemeA == schemeB && hostA == hostB
            && (a.port ?? (schemeA == "https" ? 443 : 80)) == (b.port ?? (schemeB == "https" ? 443 : 80))
    }

    private static func isPrivateHost(_ host: String) -> Bool {
        if ["localhost", "::1", "[::1]"].contains(host) { return true }
        if host.hasSuffix(".local") || host.hasSuffix(".lan") { return true }
        if host.range(of: "^[a-z][a-z0-9-]*$", options: .regularExpression) != nil { return true }
        let pieces = host.split(separator: ".", omittingEmptySubsequences: false)
        guard pieces.count == 4 else { return false }
        var octets: [Int] = []
        for piece in pieces {
            guard !piece.isEmpty, piece.utf8.allSatisfy({ (48...57).contains($0) }),
                  piece.count == 1 || piece.first != "0",
                  let value = Int(piece), (0...255).contains(value)
            else { return false }
            octets.append(value)
        }
        return octets[0] == 10 || octets[0] == 127
            || (octets[0] == 192 && octets[1] == 168)
            || (octets[0] == 172 && (16...31).contains(octets[1]))
            || (octets[0] == 100 && (64...127).contains(octets[1]))
    }

    public static func labelURL(server: URL, ids: String) throws -> URL {
        let labels = ids.split(separator: ",", omittingEmptySubsequences: false)
        guard (1...100).contains(labels.count),
              labels.allSatisfy({ UUID(uuidString: String($0)) != nil }),
              var parts = URLComponents(url: server, resolvingAgainstBaseURL: false)
        else { throw ConnectionError.invalidLabels }
        parts.path = "/api/labels"
        parts.queryItems = [URLQueryItem(name: "ids", value: ids)]
        guard let url = parts.url else { throw ConnectionError.invalidLabels }
        return url
    }
}

public enum HealthCheck {
    public static func validate(status: Int, data: Data) throws {
        guard status == 200, data.count <= 65536,
              let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              body["status"] as? String == "ok"
        else { throw ConnectionError.unhealthyServer }
        guard body["database"] as? String == "postgresql" else { throw ConnectionError.wrongDatabase }
    }
}
