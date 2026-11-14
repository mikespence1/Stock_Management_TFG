# Thrift for Good for iPhone and iPad

Open ThriftForGood.xcodeproj in Xcode on a Mac. Select the ThriftForGood scheme and your signing team.

The app uses the existing React/FastAPI workspace, plus native photo capture, QR scanning, AirPrint and export sharing. It supports iOS/iPadOS 16 and later. The database and photos remain on the shop PC.

See [installation, NetBird and distribution instructions](../docs/IOS.md). Windows cannot build or sign an iOS device installer. The included GitHub Actions workflow runs the Apple build tools on macOS; its unsigned artifacts are for verification and are not installable device packages.
