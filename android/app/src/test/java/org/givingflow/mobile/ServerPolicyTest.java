package org.givingflow.mobile;
import org.junit.Test;
import static org.junit.Assert.*;

public class ServerPolicyTest {
    @Test public void acceptsLocalPcAndStripsTrailingSlash(){assertEquals("http://192.168.70.5:8000",ServerPolicy.normalize(" http://192.168.70.5:8000/ "));}
    @Test public void allowsUsbAndEmulatorAddresses(){assertEquals("http://127.0.0.1:8000",ServerPolicy.normalize("http://127.0.0.1:8000"));assertEquals("http://10.0.2.2:8000",ServerPolicy.normalize("http://10.0.2.2:8000"));}
    @Test public void blocksExternalAndDifferentPorts(){assertFalse(ServerPolicy.sameOrigin("http://192.168.70.5:8000","https://evil.example/"));assertFalse(ServerPolicy.sameOrigin("http://192.168.70.5:8000","http://192.168.70.5:5432/"));assertTrue(ServerPolicy.sameOrigin("http://192.168.70.5:8000","http://192.168.70.5:8000/api/labels"));}
    @Test(expected=IllegalArgumentException.class) public void rejectsPublicCleartext(){ServerPolicy.normalize("http://example.com:8000");}
    @Test(expected=IllegalArgumentException.class) public void rejectsCredentials(){ServerPolicy.normalize("http://user:password@192.168.70.5:8000");}
    @Test(expected=IllegalArgumentException.class) public void rejectsFileUrls(){ServerPolicy.normalize("file:///etc/passwd");}
    @Test(expected=IllegalArgumentException.class) public void rejectsPaths(){ServerPolicy.normalize("http://192.168.70.5:8000/other");}
}
