# Thrift for Good

A compact, touch-friendly donation and stock prototype built with **React + TypeScript**, **Python + FastAPI**, and **PostgreSQL**. Staff receive bags, print unique QR labels, sort individually labelled items, and record sales, donations, service returns and disposal.

The web workspace and Android app use the official Thrift for Good logo and website palette. See [branding sources and colours](docs/BRANDING.md). Install the updated Android APK from the phone installation page to replace the native header and launcher branding; the package ID, signing certificate and saved connection remain compatible with the original test app.

**Android test app:** open **http://192.168.70.5:8000/android** on your phone while connected to the same Wi-Fi network as this PC. See [Android installation and end-to-end testing](docs/ANDROID.md). The APK includes native camera capture, QR scanning and label printing, and uses this PC's existing database.

**iPhone and iPad:** the native iOS project is under `ios/`, with camera capture, QR scanning, label printing and NetBird support. See [iOS installation and distribution](docs/IOS.md). Installation requires an Apple-signed build; an Android APK cannot be used on iOS.

**Other locations:** use [the NetBird PC and Android setup guide](docs/NETBIRD.md) for a private VPN pilot that keeps the application, PostgreSQL, photos and item history on this PC.

## User guides

- Setup, configuration, mobile installation and database backups: [Word guide](artifacts/user-guides/Thrift_for_Good_Setup_and_Access_Guide.docx) ? [PowerPoint guide](artifacts/user-guides/Thrift_for_Good_Setup_and_Access_Guide.pptx).
- Everyday staff tasks with screenshots: [Word guide](artifacts/user-guides/Thrift_for_Good_Staff_User_Guide.docx) ? [PowerPoint guide](artifacts/user-guides/Thrift_for_Good_Staff_User_Guide.pptx).

The guides contain clickable reference links. In Word, hold Ctrl and click. In PowerPoint, click in Slide Show mode or right-click and choose Open Hyperlink while editing. Links labelled ?server PC? use localhost and require the application to be running on that PC. Other devices must use the server address supplied by the manager.

## Start the application

Docker Desktop must be running. From this project folder in PowerShell:

```powershell
Copy-Item .env.example .env
Set-Location frontend
npm.cmd ci
npm.cmd run build
Set-Location ..
docker compose up -d --build
```

If `.env` already exists, keep it instead of overwriting your settings.

- App: **http://localhost:8000**
- API documentation: **http://localhost:8000/docs**
- Health / database connection: **http://localhost:8000/api/health**
- Demo email: **staff@givingflow.local**
- Demo password: **GivingFlow123!**

The first startup creates tables and fictional sample records. Repeated startup preserves existing records. PostgreSQL stores records and photos in its named Docker volume; a separate uploads volume retains legacy files during migration. `docker compose stop` stops the app without removing them. Do not use `docker compose down -v` unless you intend to erase the data.

The app includes **60 items**: 10 resale clothing items, 10 resale books, and 10 each for Donate, Mend, Clean and Dispose. It also includes 15 bags, 10 donors, 6 customers, 5 causes and 2 example sales. Clothing sample images are explicitly labelled illustrations, not real item photographs.

## Try the full workflow

1. Once a bag arrives, in **Donations**, choose **Receive donation**. Enter donor details, select an existing donor, or choose **Anonymous donation**. Marketing consent is optional and unchecked for new donors; choosing email or phone requires the matching contact detail. Contact details alone do not grant consent.
2. Save the bag. In its details, choose **Print QR label**. Print it or save the browser print output as PDF. Attach the label to the bag. It is ready for sorting immediately; there is no dispatch or in-transit step.
3. In Warehouse, scan the bag or enter its reference, then choose **Sort an item**.
4. In the Sorting Room, tap a top card to choose a bag, then **Scan this bag**. The selected bag stays visible while you sort; a mismatched bag scan is rejected. **Open manually** is available when a label cannot be scanned.
5. Choose **Sort next item** for every physical item. Clothes are selected by default. **Re-sale permits only clothes, books, ornaments and jewellery.** Shoes, hats, toys, homeware, bags and Other remain available for Donate, Mend, Clean and Dispose. Select the category and complete its form. Use **Take photos** to capture up to three views; each shot saves automatically to PostgreSQL. The Android app opens the native camera directly; the web version uses live preview or its Device camera fallback. Print and attach the item's own QR label. All items and photos retain a link to their original donation and donor.
6. Finish the bag after all its physical contents have been recorded. A completed bag does not close its items; they continue independently.
7. Scan an item later to move it, sell it, confirm donation, send/receive repairs or cleaning, re-sort it, or confirm disposal. Every successful processing step records the staff member and timestamp. In **People → Donors**, tap a donor to see all their bags, items and photos.

See [the staff process](docs/WORKFLOW.md) for the route map and QR rules. The same process guide is built into the app.

All resale items require exactly **three different photos** before an item record can be saved, marked online, sold or exported as a Shopify draft. Photos are optional for all other routes, with a maximum of three. Existing records with fewer photos are retained; use **Edit item** to supply the missing photos.

Use **Edit item** / **Edit bag** in record details, **Edit donor** / **Edit customer** in People, **Edit cause** in Causes, and **Edit sale** in a sold item's details. Corrections retain IDs, QR labels and workflow status, record the staff member and changes, and reject stale versions. Correcting a sold item's cause also updates its recorded sale allocation.

**People → Impact dashboard** shows donations and items by donor, donor nationalities, opted-in donors with contact details, and anonymous donations. Select a nationality or rank by donations/items, then open a donor to inspect their records. Anonymous bags are counted separately because their donors cannot be identified. Consent can be granted or withdrawn at intake or through Edit donor. No marketing messages are sent by this prototype.

## Tablets, mobiles and iPads

The browser is the complete staff interface. The server runs on one local machine; tablets need no Python or Node installation. Connect devices to the same trusted network and open `http://YOUR-SERVER-IP:8000` for an initial trial. Keep PostgreSQL bound to the server's loopback interface; tablets access the app, not PostgreSQL directly.

Set `PUBLIC_BASE_URL` in `.env` to the actual address your devices can reach **before printing labels**, then recreate the app with `docker compose up -d`. `localhost` in a printed label points to the scanning device itself, so it is only suitable for single-computer testing. Keep the chosen server address stable once labels are in use.

**Live camera capture and in-browser QR scanning on phones/tablets require HTTPS and camera permission.** Put the app behind a trusted HTTPS reverse proxy for the pilot and set `PUBLIC_BASE_URL=https://your-internal-hostname` and `COOKIE_SECURE=true`. Do not enable secure cookies while still accessing via HTTP. A normal phone camera can also open a QR link. Typed label references and hardware scanners that act as keyboards work without the embedded camera. **Device camera** requests native rear-camera capture on supported mobile browsers, including as a fallback when live preview is unavailable; **Library** is a separate optional path. Camera shots save immediately against the chosen bag, and become linked to the item when it is saved. Accepted images are JPEG, PNG and WebP, up to 8 MB and 25 megapixels each. Images are resized and metadata is removed. Camera streams stop when closed, when the form closes, or after the third photo.

The app needs a connection to the local server. It does not queue changes offline. Use the browser print/share facility or a network/AirPrint-compatible printer to print from tablets.

## Native development

Python 3.13+ and Node 22+ are recommended. Create a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Run only PostgreSQL in Docker, then start FastAPI:

```powershell
docker compose up -d db
$env:DATABASE_URL = 'postgresql+psycopg://givingflow:local-prototype-only@localhost:55432/givingflow'
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to FastAPI; both production and development use same-origin session cookies. Native development does not automatically load `.env`: export environment variables in the shell or pass `--env-file .env` to Uvicorn. Without `DATABASE_URL`, the backend explicitly uses `backend/prototype.db` (SQLite). The interface labels that mode clearly; Docker Compose uses PostgreSQL.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest backend/test_workflow.py -q -p no:cacheprovider
Set-Location frontend
npm.cmd test
npm.cmd run build
```

To run the same integration tests against PostgreSQL, set `TEST_DATABASE_URL` to your local PostgreSQL URL. Tests create and remove their own uniquely named schema, leaving application tables intact. Tests exercise authentication, anonymous intake, contact constraints, category counts, QR label generation/lookup, bag transitions, three-photo validation, material totals, service return/reclassification with unchanged QR identity, customer-linked sales, duplicate sale prevention, stale edits and disposal.

## Internet and Shopify

The locally hosted backend can make outbound HTTPS requests without moving PostgreSQL to the internet. Resale item details include an online listing marker and a **Shopify draft** JSON download. The export includes product details and the item's reference as SKU, and deliberately excludes donor and customer details.

The marker is manual and the JSON export is a preparation tool. **Live Shopify publishing, media upload, pricing, inventory sync and order webhooks are not enabled in this prototype.** See [integration notes](docs/INTEGRATIONS.md) for the handoff contract and the required safeguards against selling the same physical item twice. No Shopify credentials are requested or stored by this version.

## Prototype boundaries

- Uses a single seeded staff account, hashed passwords and expiring HttpOnly sessions. All staff can access donor/customer records; production needs individual accounts, roles and account administration. Default credentials are for the fictional demo only.
- Anonymous means **no donor identity is stored for that donation**. Choosing no contact stores identity but no contact permission. No email, SMS or marketing is sent. The contact preference is not inferred from merely supplying an address.
- Sale recording is bookkeeping, not payment processing or accounting. **AED is the only supported currency**; amounts are stored as integer fils. Entry, sale details and totals all use AED. The two original fictional sample sales are updated to AED without changing their numeric amounts; no exchange-rate conversion is applied.
- Table creation is automatic for this first prototype. Use schema migrations, managed backups, staff access controls and a retention policy before real operational use. Changing `STAFF_PASSWORD` after initialization does not change an existing staff password.
- New photos are stored as private binary image records **inside PostgreSQL**, with foreign keys to the donation bag and item. The donor is inherited through the original bag. Existing file-based photos are imported automatically without changing bag or item QR codes; keep the uploads volume until you have verified and backed up the migration. Back up PostgreSQL, which now contains the photos too. An item is one physical unit; there is no quantity batching. Discarded form drafts can leave bag-linked photos without an item; orphan-photo retention is a future housekeeping task.
- QR codes identify records and require staff sign-in; they are not authorization tokens. Reprints always identify the same record. Human-readable references are also unique in the database.
- No live Shopify synchronization, payment capture, tax/Gift Aid processing, or offline mode is claimed.

## Project layout

```text
backend/app.py            Models, validation, API, session auth, photos and QR labels
backend/seed.py           Fictional, idempotent demo data
backend/test_workflow.py  End-to-end API/database integration tests
frontend/src/main.tsx     React staff workspace and forms
frontend/src/styles.css  Responsive compact tablet/mobile design
compose.yaml             PostgreSQL and application services
docs/                    Staff workflow and integration design
```

In **People**, choose **Export People to Excel** to download an editable `.xlsx` snapshot of all People records, regardless of filters. The workbook contains an overview, donors (contact details, nationality, consent, preferred causes, donation/item counts, IDs and versions), customers (purchase counts and AED totals) and anonymous donations. It includes sorting/filtering and preserves phone numbers as text. Excel edits stay offline; there is no import back into the database.
