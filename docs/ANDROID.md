# Test Thrift for Good on Android

For access from other shops or mobile data, follow [the NetBird PC and Android setup guide](NETBIRD.md). Version `0.3.1-test` (version code 3) supports NetBird's private VPN addresses; install the updated APK first.

## Install on your phone

The Android app uses the React workspace served by your PC, plus native Android photo capture, QR scanning and printing. Its data flow is:

**Android phone → PC FastAPI server → PC PostgreSQL database.**

The phone never connects directly to PostgreSQL. The PC and phone share exactly the same donors, bags, photos, item records and sales.

1. Keep the PC awake, with Docker Desktop and the GivingFlow containers running.
2. Connect the phone to the same local network as the PC. The PC can be connected by Ethernet and the phone by Wi-Fi, provided the router allows communication between them. Do not use an isolated guest Wi-Fi network.
3. On the phone, open **http://192.168.70.5:8000/android**. The page has the APK download and an installation QR code. From the PC you can also transfer [the test APK](../artifacts/GivingFlow-debug.apk) to the phone by USB.
4. Download and open **ThriftForGood-test.apk**. Android may ask you to allow this browser/file manager to install this app. Grant that installation permission for this test, then turn it off afterwards if desired. Keep Play Protect enabled; stop if the device blocks installation with a security warning instead of bypassing it.
5. Launch **THRIFT FOR GOOD**. It requires Android **8.0 or later**. The branded update uses the same package and signing certificate as the previous GivingFlow Test app, so installing it updates the existing app.
6. The PC address is prefilled as **http://192.168.70.5:8000**. Tap **Test connection & open workspace**. The app checks the PC API and PostgreSQL connection before saving the address.
7. Sign in with the same staff account used on the PC. The original fictional-demo credentials are `staff@givingflow.local` / `GivingFlow123!`, unless your existing account has been changed. No database password is included in the APK.

You can change the PC address later using the native **Server** button. The app remembers the selected address between launches. It does not work while the PC is off, and it does not queue offline changes.

## End-to-end test

1. In **Donations**, receive a named or anonymous donation on the phone. Confirm that it appears immediately on the PC after refreshing.
2. Print its bag QR label using Android’s Print / Save PDF dialog. Save a PDF or use a configured network printer; attach the label to the physical bag.
3. Send the bag to the warehouse. In the Sorting Room, tap **On the way**, choose the bag and tap **Scan this bag**. Android requests camera permission the first time. Scan the printed QR; the app receives the bag at the warehouse.
4. Choose **Sort an item**. Clothes are the default. Tap **Take photos** to launch the native camera, take a shot and confirm it. The image saves automatically against the original bag. Repeat for three clothing photos.
5. Complete the clothing fields and save. The new item and all three photos should be visible on the PC and under **People → Donors → the donor → the original bag**.
6. Print the item QR and add a second item to the same bag. Resale allows **only clothes, books, ornaments and jewellery**. Toys, shoes, hats, homeware, bags and Other remain available for the other routes, but cannot be sold or exported as resale.
7. Finish the bag after recording all contents. Scan an item QR to move it, send/return service work, record a customer-linked sale, donate it or dispose of it. Verify its journey and the original donor/bag link on both devices.

Native camera capture and QR scanning work over the configured local HTTP connection; they do not depend on browser getUserMedia or Google Play services. The QR decoder is bundled in the APK. The optional photo library uses Android’s document picker. Photos are compressed and rotated correctly before saving to the PC database.

The APK loads the workspace from the PC, so normal frontend/backend changes are available after refreshing the app. The native app itself needs reinstalling only when its Android code changes.

## PC connection setup

The prepared configuration uses the detected PC address `192.168.70.5`. `PUBLIC_BASE_URL` in `.env` is set to that address so newly printed labels work on phones. The firewall rule **GivingFlow-Phone-Test** allows only inbound **TCP 8000** to that local PC address from **LocalSubnet**. PostgreSQL stays bound to loopback port 55432 and is not opened to phones.

If the PC’s address changes, run this from an **Administrator PowerShell** in the project folder:

```powershell
.\scripts\Setup-AndroidTest.ps1 -ServerAddress YOUR-PC-IP -AllowFirewall
docker compose up -d
```

Then change the server address in the Android app. Reserve the PC’s IP address in your router for stable testing. Existing bag/item IDs are unchanged. Reprint labels if they contain an old hostname or `localhost`; scanning those old labels inside GivingFlow still resolves their record IDs, but opening them in a normal camera/browser uses the printed hostname.

### Connection troubleshooting

- On the phone, open `http://192.168.70.5:8000/api/health`. It should show `status: ok` and `database: postgresql`.
- If that page does not load, check the phone’s Wi-Fi, PC address, PC power, Docker status and router guest/client isolation. A VPN on either device may also block local access.
- Check server status on the PC with `docker compose ps` and `docker compose logs --tail 50 app`.
- The native Server button permits local HTTP addresses for testing and validates HTTPS certificates normally. It never ignores certificate errors. Use HTTPS and individual staff accounts before using real personal data outside a trusted pilot LAN.
- If `COOKIE_SECURE=true` is set, you must use HTTPS. The default local HTTP test uses `COOKIE_SECURE=false`.
- Camera permission can be managed in Android Settings → Apps → THRIFT FOR GOOD → Permissions. No broad storage permission is requested.
- If Android kills the app while its external camera is open, reopen the bag and retake that photo. Unsaved form drafts are not persisted across a killed app process.

To remove the phone-test network rule later, run as Administrator:

```powershell
Remove-NetFirewallRule -Name GivingFlow-Phone-Test
```

## Build another test APK

The source is under `android/`. The build uses official Temurin JDK and Android SDK tooling, with checksum verification on SDK tools and Gradle. No Android Studio installation is needed when building through Docker:

```powershell
docker build --build-arg ACCEPT_ANDROID_SDK_LICENSES=yes --target artifact --output type=local,dest=artifacts -f android/Dockerfile android
```

The flag accepts the [Android SDK license](https://developer.android.com/studio/terms). The output is `artifacts/GivingFlow-debug.apk` and its SHA-256 checksum. Native server-address policy tests run during the build, and `apksigner` verifies the resulting APK. The debug signing key is retained in a Docker build cache for subsequent builds on this PC. If that cache is removed, a new key may require uninstalling an older test app first; central PC records are unaffected. This is a debug-signed test build, not a Play Store release.

After rebuilding the APK, run `docker compose up -d --build` to update the download hosted on the PC.

References: [Android camera intents](https://developer.android.com/media/camera/camera-deprecated/photobasics), [ZXing Android Embedded](https://github.com/journeyapps/zxing-android-embedded), [Android print framework](https://developer.android.com/training/printing/html-docs).
