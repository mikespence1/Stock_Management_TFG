package org.givingflow.mobile;

import java.net.URI;
import java.util.Locale;

/** Only explicitly configured origins are opened with the native bridge. */
public final class ServerPolicy {
    private ServerPolicy() {}

    public static String normalize(String input) {
        try {
            URI uri = new URI(input.trim());
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
            String host = uri.getHost();
            if ((!scheme.equals("http") && !scheme.equals("https")) || host == null || uri.getUserInfo() != null
                    || uri.getQuery() != null || uri.getFragment() != null || uri.getPort() > 65535 || uri.getPort() == 0
                    || (uri.getPath() != null && !uri.getPath().isEmpty() && !uri.getPath().equals("/"))) {
                throw new IllegalArgumentException();
            }
            if (scheme.equals("http") && !isLocalHost(host)) {
                throw new IllegalArgumentException("HTTP testing is limited to a local PC address. Use HTTPS for an internet server.");
            }
            return new URI(scheme, null, host.toLowerCase(Locale.ROOT), uri.getPort(), null, null, null).toString();
        } catch (IllegalArgumentException error) {
            throw error;
        } catch (Exception error) {
            throw new IllegalArgumentException("Enter a server address such as http://192.168.70.5:8000");
        }
    }

    public static boolean sameOrigin(String server, String target) {
        try {
            URI a = new URI(server), b = new URI(target);
            return a.getHost() != null && b.getHost() != null && a.getScheme().equalsIgnoreCase(b.getScheme())
                    && a.getHost().equalsIgnoreCase(b.getHost()) && port(a) == port(b) && b.getUserInfo() == null;
        } catch (Exception error) { return false; }
    }

    private static int port(URI uri) { return uri.getPort() == -1 ? ("https".equals(uri.getScheme()) ? 443 : 80) : uri.getPort(); }

    private static boolean isLocalHost(String host) {
        host = host.toLowerCase(Locale.ROOT);
        if (host.equals("localhost") || host.equals("[::1]") || host.equals("::1") || host.endsWith(".local") || host.endsWith(".lan")) return true;
        if (host.matches("[a-z][a-z0-9-]*")) return true;
        String[] parts = host.split("\\.");
        if (parts.length != 4) return false;
        try {
            int a = Integer.parseInt(parts[0]), b = Integer.parseInt(parts[1]);
            for (String part : parts) { int v = Integer.parseInt(part); if(v < 0 || v > 255) return false; }
            return a == 10 || a == 127 || (a == 192 && b == 168) || (a == 172 && b >= 16 && b <= 31);
        } catch (NumberFormatException e) { return false; }
    }
}
