package org.givingflow.mobile;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Matrix;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.print.PrintManager;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.WindowInsets;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.SslErrorHandler;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.net.http.SslError;
import android.widget.Button;
import android.widget.ImageView;
import android.content.res.ColorStateList;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.core.content.FileProvider;
import androidx.exifinterface.media.ExifInterface;
import com.google.zxing.integration.android.IntentIntegrator;
import com.google.zxing.integration.android.IntentResult;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int PHOTO_REQUEST = 2101, FILE_REQUEST = 2102, CAMERA_PERMISSION = 2103;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private LinearLayout root, content;
    private WebView web, printWeb;
    private TextView connection;
    private SharedPreferences preferences;
    private String server = "", photoRequestId = "", qrRequestId = "", pendingOperation = "";
    private File photoFile;
    private ValueCallback<Uri[]> fileCallback;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("givingflow", MODE_PRIVATE);
        server = preferences.getString("server", "");
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(Color.rgb(250,250,250));
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                v.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else v.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(dp(13),dp(3),dp(9),dp(3)); header.setBackgroundColor(Color.rgb(255,255,255));
        ImageView brand = new ImageView(this); brand.setImageResource(R.drawable.tfg_logo); brand.setContentDescription("THRIFT FOR GOOD"); brand.setScaleType(ImageView.ScaleType.FIT_CENTER); brand.setPadding(0,dp(10),dp(10),dp(10));
        header.addView(brand, new LinearLayout.LayoutParams(0,dp(48),1));
        connection = text("", 10, Color.rgb(12,115,118)); header.addView(connection);
        Button settings = new Button(this); settings.setText("Server"); settings.setBackgroundTintList(ColorStateList.valueOf(Color.rgb(233,247,247))); settings.setTextColor(Color.rgb(12,115,118)); settings.setTextSize(11); settings.setMinWidth(0); settings.setOnClickListener(v -> showSettings("")); header.addView(settings,new LinearLayout.LayoutParams(dp(77),dp(42)));
        root.addView(header);
        content = new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL); root.addView(content,new LinearLayout.LayoutParams(-1,0,1)); setContentView(root);
        if(state != null){photoRequestId=state.getString("photoRequestId",""); qrRequestId=state.getString("qrRequestId",""); String path=state.getString("photoPath",""); if(!path.isEmpty())photoFile=new File(path);}
        if(server.isEmpty())showSettings(""); else openWorkspace();
    }

    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    private TextView text(String value,int size,int color){TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(color);return v;}
    private void showSettings(String error) {
        if(!photoRequestId.isEmpty() || !qrRequestId.isEmpty()){Toast.makeText(this,"Finish camera capture first",Toast.LENGTH_SHORT).show();return;}
        if(web!=null){web.destroy();web=null;}
        content.removeAllViews(); connection.setText("PC connection ");
        ScrollView scroll = new ScrollView(this); LinearLayout form = new LinearLayout(this);form.setOrientation(1);form.setPadding(dp(24),dp(28),dp(24),dp(24));scroll.addView(form);content.addView(scroll);
        TextView title=text("Connect to your shop PC",24,Color.rgb(50,50,50));form.addView(title);
        TextView intro=text("Connect through the shop Wi-Fi or a connected NetBird private VPN. The app uses the PC’s existing donation database.",14,Color.rgb(98,98,98));intro.setPadding(0,dp(12),0,dp(22));form.addView(intro);
        form.addView(text("PC server address",12,Color.rgb(12,115,118)));
        EditText address=new EditText(this);address.setSingleLine(true);address.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);address.setText(server.isEmpty()?BuildConfig.DEFAULT_SERVER:server);address.setTextSize(16);form.addView(address,new LinearLayout.LayoutParams(-1,dp(56)));
        TextView status=text(error,13,Color.rgb(157,75,54));status.setPadding(0,dp(14),0,dp(14));form.addView(status);
        Button connect=new Button(this);connect.setText("Test connection & open workspace");connect.setBackgroundTintList(ColorStateList.valueOf(Color.rgb(241,86,42)));connect.setTextColor(Color.rgb(23,23,23));form.addView(connect,new LinearLayout.LayoutParams(-1,dp(56)));
        TextView help=text("Pilot: HTTP is supported on a trusted LAN or inside a connected private VPN. For NetBird, use the PC’s NetBird IP and keep NetBird connected on both devices. Sign in with the same staff account as on the PC. Camera and QR scanning use native Android controls.\n\nIf the connection fails: keep the PC awake, start Docker and the app, check the server address, NetBird access policy and PC firewall rule for TCP 8000. Use HTTPS with a trusted certificate for production.",12,Color.rgb(98,98,98));help.setPadding(0,dp(24),0,0);form.addView(help);
        connect.setOnClickListener(v -> {
            final String target;
            try {target=ServerPolicy.normalize(address.getText().toString());}
            catch(Exception e){status.setText(e.getMessage()==null?"Enter a complete PC address, for example http://192.168.70.5:8000":e.getMessage());return;}
            connect.setEnabled(false);status.setText("Checking PC and PostgreSQL…");
            worker.execute(() -> {
                String failure="";
                try {
                    HttpURLConnection http=(HttpURLConnection)new URL(target+"/api/health").openConnection();
                    http.setConnectTimeout(8000);http.setReadTimeout(8000);http.setInstanceFollowRedirects(false);
                    try {
                        if(http.getResponseCode()!=200)throw new Exception("The PC responded but its API is unavailable.");
                        try(InputStream input=http.getInputStream()){
                            ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int read;
                            while((read=input.read(buffer))!=-1){bytes.write(buffer,0,read);if(bytes.size()>65536)throw new Exception("Unexpected health response.");}
                            JSONObject body=new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
                            if(!"ok".equals(body.optString("status"))||!"postgresql".equals(body.optString("database")))throw new Exception("This server is not connected to PostgreSQL. Start the Docker application on the PC.");
                        }
                    } finally {http.disconnect();}
                } catch(Exception e){failure=e.getMessage()==null?"Could not reach the PC. Check Wi-Fi, server address and firewall.":e.getMessage();}
                final String result=failure;
                runOnUiThread(() -> {if(isFinishing())return;connect.setEnabled(true);if(!result.isEmpty()){status.setText("Connection failed: "+result);return;}server=target;preferences.edit().putString("server",server).apply();openWorkspace();});
            });
        });
    }

    private void openWorkspace() {
        content.removeAllViews(); connection.setText("PC connected ");
        web=new WebView(this);content.addView(web,new LinearLayout.LayoutParams(-1,-1));
        WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);settings.setAllowFileAccess(false);settings.setAllowContentAccess(true);settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);settings.setMediaPlaybackRequiresUserGesture(true);
        CookieManager.getInstance().setAcceptCookie(true);CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.addJavascriptInterface(new NativeBridge(),"GivingFlowAndroid");
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request){return !ServerPolicy.sameOrigin(server,request.getUrl().toString());}
            @Override public void onReceivedSslError(WebView view,SslErrorHandler handler,SslError error){handler.cancel();showSettings("The server’s HTTPS certificate is not trusted. Use a valid certificate or the local HTTP address for this test.");}
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error){if(request.isForMainFrame())showSettings("PC unavailable. Check that it is awake and the server is running.");}
            @Override public void onPageFinished(WebView view,String url){CookieManager.getInstance().flush();}
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){
                if(!trustedPage())return false;
                if(fileCallback!=null)fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent picker=new Intent(Intent.ACTION_OPEN_DOCUMENT);picker.setType("image/*");picker.addCategory(Intent.CATEGORY_OPENABLE);
                try{startActivityForResult(picker,FILE_REQUEST);}catch(Exception error){callback.onReceiveValue(null);fileCallback=null;}
                return true;
            }
        });
        web.loadUrl(server+"/");
    }

    private boolean trustedPage(){return web!=null&&ServerPolicy.sameOrigin(server,web.getUrl());}
    private boolean validId(String value){return value!=null&&value.matches("[A-Za-z0-9-]{1,80}");}
    private class NativeBridge {
        @JavascriptInterface public void takePhoto(String requestId){if(!validId(requestId))return;runOnUiThread(()->{if(!trustedPage())return;if(!photoRequestId.isEmpty()||!qrRequestId.isEmpty()){send("givingflow:photo",requestId,"error","Camera already in use");return;}photoRequestId=requestId;pendingOperation="photo";requestCamera();});}
        @JavascriptInterface public void scanQr(String requestId){if(!validId(requestId))return;runOnUiThread(()->{if(!trustedPage())return;if(!photoRequestId.isEmpty()||!qrRequestId.isEmpty()){send("givingflow:qr",requestId,"error","Camera already in use");return;}qrRequestId=requestId;pendingOperation="scan";requestCamera();});}
        @JavascriptInterface public void printLabels(String ids){runOnUiThread(()->{if(trustedPage()&&ids!=null&&ids.matches("[a-fA-F0-9,-]{1,3800}"))printLabelsNative(ids);});}
    }

    private void requestCamera(){if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{Manifest.permission.CAMERA},CAMERA_PERMISSION);}else startCameraOperation();}
    @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] results){super.onRequestPermissionsResult(requestCode,permissions,results);if(requestCode==CAMERA_PERMISSION){if(results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED)startCameraOperation();else failOperation("Camera permission was declined. Enable it in Android app permissions, or use the photo library / printed reference.");}}
    private void startCameraOperation(){
        if(pendingOperation.equals("scan")){
            try{new IntentIntegrator(this).setDesiredBarcodeFormats(IntentIntegrator.QR_CODE).setOrientationLocked(false).setBeepEnabled(false).setPrompt("Scan the Thrift for Good bag or item label").initiateScan();}
            catch(Exception error){failOperation("Could not open QR scanner.");}
            return;
        }
        try{
            File directory=new File(getCacheDir(),"camera");if(!directory.exists()&&!directory.mkdirs())throw new Exception();
            photoFile=File.createTempFile("item-",".jpg",directory);
            Uri uri=FileProvider.getUriForFile(this,getPackageName()+".files",photoFile);
            Intent camera=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);camera.putExtra(MediaStore.EXTRA_OUTPUT,uri);camera.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);camera.setClipData(ClipData.newRawUri("Item photo",uri));
            startActivityForResult(camera,PHOTO_REQUEST);
        }catch(Exception error){failOperation("No camera app is available, or the camera could not open.");}
    }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent result){
        super.onActivityResult(requestCode,resultCode,result);
        if(requestCode==FILE_REQUEST){if(fileCallback!=null){fileCallback.onReceiveValue(resultCode==RESULT_OK&&result!=null?new Uri[]{result.getData()}:null);fileCallback=null;}return;}
        if(requestCode==PHOTO_REQUEST){
            if(resultCode!=RESULT_OK||photoFile==null){failOperation("cancelled");return;}
            final File captured=photoFile;final String id=photoRequestId;photoFile=null;
            worker.execute(()->{
                try{
                    BitmapFactory.Options size=new BitmapFactory.Options();size.inJustDecodeBounds=true;BitmapFactory.decodeFile(captured.getPath(),size);
                    if(size.outWidth<1||size.outHeight<1)throw new Exception();
                    BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=1;
                    while(Math.max(size.outWidth,size.outHeight)/options.inSampleSize>2200)options.inSampleSize*=2;
                    Bitmap image=BitmapFactory.decodeFile(captured.getPath(),options);if(image==null)throw new Exception();
                    ExifInterface exif=new ExifInterface(captured);Matrix transform=new Matrix();
                    switch(exif.getAttributeInt(ExifInterface.TAG_ORIENTATION,ExifInterface.ORIENTATION_NORMAL)){
                        case ExifInterface.ORIENTATION_FLIP_HORIZONTAL:transform.setScale(-1,1);break;
                        case ExifInterface.ORIENTATION_ROTATE_180:transform.setRotate(180);break;
                        case ExifInterface.ORIENTATION_FLIP_VERTICAL:transform.setScale(1,-1);break;
                        case ExifInterface.ORIENTATION_TRANSPOSE:transform.setRotate(90);transform.postScale(-1,1);break;
                        case ExifInterface.ORIENTATION_ROTATE_90:transform.setRotate(90);break;
                        case ExifInterface.ORIENTATION_TRANSVERSE:transform.setRotate(270);transform.postScale(-1,1);break;
                        case ExifInterface.ORIENTATION_ROTATE_270:transform.setRotate(270);break;
                    }
                    Bitmap rotated=Bitmap.createBitmap(image,0,0,image.getWidth(),image.getHeight(),transform,true);
                    if(rotated!=image)image.recycle();
                    float scale=Math.min(1f,1600f/Math.max(rotated.getWidth(),rotated.getHeight()));
                    Bitmap resized=Bitmap.createScaledBitmap(rotated,Math.round(rotated.getWidth()*scale),Math.round(rotated.getHeight()*scale),true);if(resized!=rotated)rotated.recycle();
                    ByteArrayOutputStream bytes=new ByteArrayOutputStream();resized.compress(Bitmap.CompressFormat.JPEG,85,bytes);resized.recycle();
                    String base64=Base64.encodeToString(bytes.toByteArray(),Base64.NO_WRAP);
                    runOnUiThread(()->{send("givingflow:photo",id,"base64",base64);photoRequestId="";pendingOperation="";});
                }catch(Exception error){runOnUiThread(()->failOperation("Could not read this photo. Please retake it."));}
                finally{captured.delete();}
            });
            return;
        }
        IntentResult scanned=IntentIntegrator.parseActivityResult(requestCode,resultCode,result);
        if(scanned!=null){if(scanned.getContents()==null)failOperation("cancelled");else{send("givingflow:qr",qrRequestId,"value",scanned.getContents());qrRequestId="";pendingOperation="";}}
    }

    private void send(String event,String id,String key,String value){
        if(!trustedPage())return;
        try{JSONObject detail=new JSONObject();detail.put("requestId",id);detail.put(key,value);web.evaluateJavascript("window.dispatchEvent(new CustomEvent("+JSONObject.quote(event)+", {detail:"+detail+"}));",null);}catch(Exception ignored){}
    }
    private void failOperation(String message){if(!photoRequestId.isEmpty())send("givingflow:photo",photoRequestId,"error",message);if(!qrRequestId.isEmpty())send("givingflow:qr",qrRequestId,"error",message);if(photoFile!=null){photoFile.delete();photoFile=null;}photoRequestId="";qrRequestId="";pendingOperation="";}

    private void printLabelsNative(String ids){
        if(printWeb!=null)printWeb.destroy();
        printWeb=new WebView(this);printWeb.getSettings().setJavaScriptEnabled(false);
        printWeb.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){return !ServerPolicy.sameOrigin(server,request.getUrl().toString());}
            @Override public void onReceivedSslError(WebView v,SslErrorHandler h,SslError e){h.cancel();}
            @Override public void onPageFinished(WebView view,String url){if(ServerPolicy.sameOrigin(server,url)){PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);manager.print("Thrift for Good QR labels",view.createPrintDocumentAdapter("Thrift for Good labels"),null);}}
        });
        printWeb.loadUrl(server+"/api/labels?ids="+Uri.encode(ids));
    }
    @Override public void onBackPressed(){if(web!=null&&web.canGoBack())web.goBack();else new AlertDialog.Builder(this).setMessage("Close Thrift for Good?").setNegativeButton("Stay",null).setPositiveButton("Close",(d,w)->finish()).show();}
    @Override protected void onSaveInstanceState(Bundle out){super.onSaveInstanceState(out);out.putString("photoRequestId",photoRequestId);out.putString("qrRequestId",qrRequestId);if(photoFile!=null)out.putString("photoPath",photoFile.getPath());}
    @Override protected void onDestroy(){if(web!=null)web.destroy();if(printWeb!=null)printWeb.destroy();worker.shutdown();super.onDestroy();}
}
