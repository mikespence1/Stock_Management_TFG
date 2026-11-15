# Thrift for Good on iPhone and iPad

The native iOS app is under ios/. It supports **iOS/iPadOS 16 and later**, using the same PC, staff account, PostgreSQL records and photographs as the browser and Android app.

It includes:

- The official Thrift for Good logo and turquoise/orange palette.
- A saved PC connection, checked against /api/health before opening.
- Native camera photographs, resized to JPEG and saved through the existing form to the original donation.
- Native QR scanning for bags and individual items.
- The iOS label print dialog with AirPrint and PDF sharing.
- The system share sheet for downloads such as Shopify draft JSON.
- The full staff workspace for intake, sorting, inventory, sales, people, causes and history.

The app does not contain database credentials, connect directly to PostgreSQL, create its own inventory database or queue changes offline.

## What is ready, and what still requires Apple

The project includes a shared Xcode scheme, app icon, launch screen, permission descriptions, required-reason privacy manifest, native source and tests. It does **not** contain an Apple signing certificate, provisioning profile or signed IPA.

An Android APK cannot be installed on iOS. A source ZIP or unsigned build is also not an installable iPhone app. Build with Apple's SDK and sign for the chosen installation method.

| Situation | Installation path |
| --- | --- |
| Mac with Xcode and an iPhone/iPad | An ordinary Apple Account enables a free Personal Team for limited testing. Its device provisioning expires after 7 days and needs rebuilding/reinstalling; this is not staff distribution. |
| Staff beta testing | Apple Developer Program membership, signed upload to App Store Connect and TestFlight invitations. Builds expire after 90 days; external testing may require Beta App Review. |
| Limited set of known devices | Register devices in your developer account and export an Ad Hoc signed build for them. |
| Ongoing organisation deployment | Discuss Custom Apps through Apple Business Manager/MDM with your Apple administrator. |

A paid Developer Program membership is normally needed for TestFlight and Ad Hoc distribution. Eligible nonprofits can apply for Apple's membership fee waiver; Apple decides eligibility.

## Install using a Mac and Xcode

1. Copy/clone the **ios-native-app** branch onto a Mac with current Xcode. Until this work is merged, the repository's main branch does not contain the iOS project. On GitHub, select that branch before using **Code -> Download ZIP**.
2. Open ios/ThriftForGood.xcodeproj and select the **ThriftForGood** scheme.
3. Select the application target, then **Signing & Capabilities**.
4. Choose your Apple development **Team** and automatic signing. Replace org.givingflow.mobile with your organisation's registered identifier if needed.
5. Connect an iPhone/iPad. Complete its trust and Developer Mode steps when Xcode requests them.
6. Select that physical device as the run destination and choose **Product -> Run**.
7. Allow **Local Network** when first requested, and **Camera** when photographing or scanning.

Do not commit Apple passwords, private keys, certificates or provisioning profiles. Xcode manages signing through your selected team.

For simulator testing without a signing account, select an iPhone/iPad simulator and Run. Simulators do not provide a physical camera or a real NetBird connection; device testing remains necessary.

## Connect through NetBird

1. Install [NetBird for iOS](https://docs.netbird.io/get-started/install/ios) from the App Store.
2. Connect using the **same NetBird account and sign-in method** as your PC, or an invited user in the same organisation.
3. Confirm both devices appear in the **web dashboard** at [app.netbird.io](https://app.netbird.io/). The default desktop view hides the peer list; Advanced view can show it.
4. Add the iPhone/iPad to the authorised device group. Its policy must allow connection to the PC on **TCP 8000**.
5. If Windows Firewall allows only the Android peer's IP, add a rule for the iPhone/iPad's actual NetBird IP. Use the narrow rule in [the NetBird guide](NETBIRD.md). Do not open PostgreSQL ports.
6. Keep NetBird connected on both devices.
7. In Safari on the iPhone/iPad, open http://100.88.75.17:8000/api/health. This is the PC address observed during setup; check the dashboard if it changes. Expect status: ok and database: postgresql.
8. Open **THRIFT FOR GOOD**. Enter **http://100.88.75.17:8000** and tap **Test connection & open workspace**.
9. Sign in with the existing **Thrift for Good staff account**. This is separate from NetBird authentication.

The current PC address is prefilled and can be changed using **Server**. Use the PC's address, not the iPhone's. Do not append /api or /android.

On shop Wi-Fi, the reachable LAN address can also be used, currently http://192.168.70.5:8000. Keep one stable PUBLIC_BASE_URL for new QR labels; use the NetBird address for access across sites. Reprint older labels whose embedded links need to change. Record IDs stay the same.

HTTP is a trusted-LAN/encrypted-VPN pilot. The app permits HTTP only for private LAN/NetBird addresses and local names. ATS exceptions are scoped to those address ranges; arbitrary public HTTP origins and invalid HTTPS certificates are rejected. The app does not establish or verify the NetBird tunnel. Use trusted HTTPS for production.

If Local Network permission was declined, enable it in iOS Settings for Thrift for Good. If Safari works but the app does not, check that permission before changing database settings.

## Test on a physical device

Use fictional test records:

1. Turn Wi-Fi off and connect NetBird over mobile data.
2. Receive a donation on the iPhone. Refresh the PC and confirm it appears.
3. Print its bag QR label using the iOS print dialog.
4. Record bags only after arrival. Scan the bag from **Being sorted** in the Sorting Room; there is no send/receive step.
5. Sort a clothing item. Take three photos; each accepted shot saves against the selected bag.
6. Save the item and check its photos and donor/bag links on the PC.
7. Print and scan the individual item's label.
8. Record a test sale and check AED amounts and processing history on both devices.
9. Cancel camera/scanner actions and decline camera permission once; confirm the form remains usable with an explanation.
10. Test iPad portrait/landscape and print presentation. Reopen the app and check the saved connection.

Server sessions expire, so staff may need to sign in again. Unsaved form drafts do not survive iOS terminating the app. Already-uploaded photos remain attached to the original bag until the item is saved.

The iOS app loads the same PC-hosted workspace as the browser and Android. Reopen the workspace after updating the server to access **Edit item**, **Edit bag**, donor/customer/cause/sale corrections, marketing consent and **People → Impact dashboard**. These shared changes do not require a new signed iOS build. All resale types require three photos before saving, sale, online marking or Shopify draft export; photos are optional for all other routes, up to three. Remove a thumbnail in **Edit item** to capture a replacement. Corrections preserve the original record ID, QR and workflow status. Marketing consent is optional and separate from supplying contact details; anonymous donations cannot opt in.

## GitHub build checks without your own Mac

The workflow .github/workflows/ios.yml uses a GitHub-hosted macOS runner:

1. Push the iOS source and workflow to the repository.
2. Open **Actions -> iOS build and tests**.
3. Open the run triggered by the push. When offered, **Run workflow** can run it manually on a branch containing the workflow.
4. It validates the project, runs connection tests, builds/tests on iPhone and iPad simulators, and verifies an unsigned device archive.
5. Download **ThriftForGood-iOS-builds** for the compiled simulator ZIP and unsigned device archive. They are published before screen tests. **ThriftForGood-iOS-build-results** additionally contains the logs, screenshots and test results after checks finish.

These artifacts are **not signed device installers**. Simulator builds run only in a compatible Mac simulator. An unsigned device archive verifies compilation and does not replace signing.

GitHub Actions availability/billing depend on the repository/account plan. This workflow has no Apple credentials and never uploads to TestFlight or the App Store.

## TestFlight distribution

After an Apple Developer team is available:

1. Register the bundle identifier with the organisation's team.
2. Create an App Store Connect app record with the same identifier.
3. In Xcode, select the team and **Any iOS Device**, then **Product -> Archive**.
4. In Organizer, validate, choose **Distribute App**, and upload to App Store Connect.
5. Complete privacy/export-compliance declarations for the actual deployment. The required-reason manifest documents local preference storage; it does not replace App Store privacy answers or a donor-data policy.
6. Under TestFlight, add the processed build to a group and invite staff. They install Apple's TestFlight app and accept the invitation.
7. External beta review may need a reachable demonstration backend and review credentials. A private NetBird-only PC is not automatically accessible to Apple reviewers. Plan a separate fictional-data demo rather than exposing the operational donor database.
8. Replace beta builds before expiry. Choose an appropriate supported method for ongoing deployment.

Without a Mac, a macOS build service can sign/upload after the organisation supplies its Apple signing setup. That is not configured by the unsigned verification workflow. Do not send private keys or passwords in chat.

## Developer checks

On a Mac:

    swift test --package-path ios
    xcodebuild -list -project ios/ThriftForGood.xcodeproj
    xcodebuild build -project ios/ThriftForGood.xcodeproj -scheme ThriftForGood -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO

Shared interface checks, from frontend/:

    npm test
    npm run build

After shared frontend changes, rebuild the PC image with docker compose up -d --build app. Native iOS changes require a new signed app build.

Opening the committed Xcode project requires no third-party generator. If source membership changes, install the xcodeproj Ruby gem (version 1.28.1) and run ruby scripts/generate_ios_project.rb. Windows developers can use ios/project-tools.Dockerfile to run that generator. It does not manage signing.

References: [Apple distribution](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases), [free Personal Team testing](https://developer.apple.com/help/account/basics/about-your-developer-account), [preparing distribution](https://developer.apple.com/documentation/xcode/preparing-your-app-for-distribution), [TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/), [registered devices](https://developer.apple.com/help/account/devices/devices-overview/), [membership fee waiver](https://developer.apple.com/support/membership-fee-waiver/), [local-network ATS exceptions](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking).

**People → Export People to Excel** downloads the workbook through the existing iOS share sheet. Save it to Files or open it in Excel. Workbook edits do not update PC records.
