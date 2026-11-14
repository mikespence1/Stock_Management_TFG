# Thrift for Good branding

The application uses the official wordmark and site icon from [thriftforgood.org](https://www.thriftforgood.org/), checked on 14 November 2026. The downloaded files are bundled locally, so branding remains available without internet access on the phone.

## Source assets

- Wordmark: `https://static.wixstatic.com/media/a02fd7_6fd82c68485a4df2b26c887be12828cd~mv2.png` (website filename: `TfG_SecondaryLogo_TurquoiseText_ClearBackground.png`). The bundled version uses Wix's CDN crop around the visible lettering; the artwork is unchanged.
- Website icon: `https://static.wixstatic.com/media/5b6e3f_b77fbda7e27d41569aa8f004130c86b4~mv2.jpg`.
- Web copies: `frontend/public/brand/`; native Android copies: `android/app/src/main/res/drawable/tfg_logo.png` and `tfg_icon.jpg`.

## Palette

| Use | Colour | Evidence |
| --- | --- | --- |
| Logo turquoise | `#14999C` | Dominant opaque pixel colour in the official wordmark |
| Primary orange | `#F1562A` | Website colour 18 / primary colour 41 |
| Dark orange | `#A1391C` | Website colour 19 |
| Orange secondary | `#F89825` | Website colour 23 |
| Supporting blue | `#7EB7E4` | Website colour 27 |
| White | `#FFFFFF` | Website header and surfaces |
| Main text | `#323232` | Website custom component text |

Dark turquoise `#0C7376` and pale turquoise `#E9F7F7` support readable controls and backgrounds. Orange buttons use dark text for contrast. `frontend/src/brand.css` defines the shared web theme. Android's native header and connection screen use the same palette; the embedded workspace loads the same React theme from the PC.

User-facing names, headers, loading screens, launcher icon, QR labels, installer page and Android print titles use Thrift for Good. Internal package ID, session cookies, bridge names, database identifiers and saved server preferences retain their existing identifiers so the branding update preserves access and data.

The branded Android package kept its signing certificate and increased its version code to 2. The subsequent NetBird pilot update uses version code 3 with the same signing certificate, allowing an in-place update.
