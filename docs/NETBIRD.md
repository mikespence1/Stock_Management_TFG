# NetBird: connect the shop PC and Android devices from other locations

This guide uses **NetBird Cloud for network management**, while your application, PostgreSQL database, photos and item history remain on your Windows PC. You do not need to host NetBird's management server yourself.

Connection: **Android app -> NetBird encrypted private connection -> PC application on TCP 8000 -> PostgreSQL on the PC**.

This is a private-VPN **pilot** using HTTP inside NetBird's encrypted connection. NetBird must remain connected on both devices. The Android app does not establish or verify the VPN itself. Use trusted HTTPS and individual staff accounts for production. The current application uses a shared demo account; remote access does not add separate staff accounts, automatic backups or offline operation.

## 1. Check the application on the PC

Keep the PC powered, connected to the internet and awake. Start Docker Desktop. In PowerShell:

```powershell
Set-Location 'C:\Users\nofel\Downloads\AI Projects\Stock_Management_TFG'
docker compose up -d
docker compose ps
```

Open `http://localhost:8000/api/health` on the PC. Expected:

```json
{"status":"ok","database":"postgresql"}
```

Confirm `http://localhost:8000` opens the staff workspace. Keep the existing `.env`; do not overwrite it from `.env.example` or change database credentials for this setup.

## 2. Create your NetBird network

1. Open [app.netbird.io](https://app.netbird.io/) and create an organisation/account for the charity.
2. Use NetBird Cloud, not a self-hosted management server.
3. Use your organisation's identity provider and enable MFA on the account where available.
4. For your first phone, you can use your own account on both PC and phone. Invite other staff into the **same NetBird organisation**, using their own accounts, as you expand. Do not share your administrator password.

NetBird's published cloud Free plan supports **5 users and 100 machines**, checked 14 November 2026. Users and devices are different limits; choose an appropriate plan when you exceed them. See [plans and billing](https://docs.netbird.io/manage/settings/plans-and-billing).

## 3. Install NetBird on the PC

1. Download the official installer from [NetBird's Windows installation page](https://docs.netbird.io/get-started/install/windows).
2. Install it on **Windows itself**, alongside Docker Desktop. Do not install only inside the application container.
3. Open NetBird, select NetBird Cloud and click **Connect**. Sign in to the organisation from step 2.
4. In the dashboard's **Peers** list, find the PC and give it an identifiable name, such as `TFG-Stock-PC`.
5. Copy its **NetBird IPv4 address**. NetBird normally allocates an address in `100.64.0.0/10`.
6. Enable **Connect on Startup** and verify connectivity after a PC restart. Ensure **Block Inbound Connections** is not preventing access on this server; inbound access is restricted by the policy in step 5.

For example, the PC might be `100.110.0.10`. **Every address in this guide is an example; copy the actual address from your dashboard.** The previous `192.168.70.5` address is the shop LAN address, not the NetBird address. `localhost` on the phone means the phone itself.

From a new PowerShell window, `netbird status` shows the PC's connection status. The Windows installer adds NetBird to PATH; an already-open terminal may need reopening.

## 4. Install NetBird on Android

1. Install the official **NetBird** app from Google Play using the link in [NetBird's Android guide](https://docs.netbird.io/get-started/install/android).
2. Keep the default NetBird Cloud management server. Do not enter your PC's address into NetBird's **Management Server** setting.
3. Tap Connect/the NetBird logo, approve Android's VPN connection prompt and sign in to the same organisation as the PC.
4. In the dashboard, confirm that both PC and Android peers are connected.
5. Copy the Android peer's NetBird IP too; you will use it in the Windows firewall rule.

For example, the phone might be `100.110.0.20`. The phone uses **the PC's address** when opening Thrift for Good, not its own address.

If Android stops the connection while idle, allow NetBird to run in the background using your device's battery settings. Android generally allows one active VPN service at a time; check for another VPN if NetBird cannot connect.

## 5. Restrict NetBird access to the application

In the NetBird dashboard's **Access Control / Groups & Policies** area:

1. Create a group named `TFG-Server` and add only the PC.
2. Create a group named `TFG-Devices` and add the authorised phones/tablets.
3. Add an enabled policy with these settings:

| Setting | Value |
| --- | --- |
| Source | `TFG-Devices` |
| Destination | `TFG-Server` |
| Protocol | TCP |
| Destination port | `8000` |
| Direction | Unidirectional: devices initiate connections to server |

4. After saving the replacement policy, disable the broad default **All-to-All** policy. Also check that no other broad policy grants the devices access to unrelated services.

No subnet route, routing peer or exit node is needed: both endpoints have NetBird installed. Do not create access rules for PostgreSQL ports `5432` or `55432`. The app communicates with the database internally.

See [NetBird's groups and access policies](https://docs.netbird.io/manage/access-control/manage-network-access).

## 6. Allow the app through Windows Firewall

The existing same-Wi-Fi firewall rule is not the NetBird rule. On the PC, open **PowerShell as Administrator**, replace both example addresses, and run once for this phone:

```powershell
$pcNetBirdIp = '100.110.0.10'       # Actual PC NetBird IP
$phoneNetBirdIp = '100.110.0.20'    # Actual phone NetBird IP
New-NetFirewallRule -DisplayName 'TFG NetBird app - phone 1' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -LocalAddress $pcNetBirdIp -RemoteAddress $phoneNetBirdIp -Profile Any
```

Repeat with a distinct rule name and the actual IP for each additional approved device. `Profile Any` handles the VPN adapter's Windows network profile; the local and remote address restrictions keep this rule narrow. If Windows has an explicit conflicting block rule, have the PC administrator review it rather than disabling the firewall.

Do not forward application or database ports on the internet router. NetBird handles the private connection. Leave the PostgreSQL binding in `compose.yaml` as `127.0.0.1:55432:5432`.

## 7. Test the connection using mobile data

1. Turn **Wi-Fi off** on the phone and enable mobile data. This confirms you are testing away from the PC's local network.
2. Verify NetBird is connected on the phone and PC.
3. In the phone browser, open the following, substituting the PC's actual NetBird IP:

```text
http://100.110.0.10:8000/api/health
```

Expected: `status: ok` and `database: postgresql`. Then open `http://100.110.0.10:8000` and sign in to the staff workspace.

The browser connection is a useful reachability check. Native Android camera capture and QR scanning use the installed Thrift for Good APK; in-browser live camera functions need trusted HTTPS.

## 8. Set the QR address for all sites

On the PC, edit only these settings in the existing project `.env`, using the actual PC NetBird IP:

```dotenv
PUBLIC_BASE_URL=http://100.110.0.10:8000
COOKIE_SECURE=false
```

Then, from the project folder:

```powershell
docker compose up -d app
```

`COOKIE_SECURE=false` is required for this HTTP-inside-VPN pilot; secure-only cookies do not work over HTTP. With a future trusted HTTPS endpoint, set `COOKIE_SECURE=true` and use that HTTPS address instead.

This changes the address printed in **new** QR labels and the installer page's QR. It does not change existing record IDs or database contents. Reprint existing labels when you need their embedded links to work across sites. The native app can still resolve an old bag/item label by record ID; a normal camera/browser follows its old printed address.

Do not run the original LAN setup script afterwards with its default address, because it would reset `PUBLIC_BASE_URL` to the LAN address.

## 9. Install the updated Thrift for Good APK

Install **version `0.3.1-test` (version code 3)** or later. The original APK rejected HTTP addresses in NetBird's `100.64.0.0/10` range. This pilot build accepts that range, while still rejecting arbitrary public HTTP servers and invalid certificates.

1. With NetBird connected, open `http://YOUR-PC-NETBIRD-IP:8000/android` on the phone and download the APK. You can also download while on shop Wi-Fi at `http://192.168.70.5:8000/android`, or transfer `artifacts/GivingFlow-debug.apk` by USB.
2. Install it as an update over the existing Thrift for Good app. It uses the same package and signing certificate on this PC. Keep Play Protect enabled.
3. Open **THRIFT FOR GOOD** and tap the native **Server** button.
4. Enter `http://YOUR-PC-NETBIRD-IP:8000`, using the actual PC IP and **without** `/api`, `/android` or another path.
5. Tap **Test connection & open workspace**.
6. Sign in using your existing **Thrift for Good staff account**. This is separate from the NetBird sign-in.

If installing a downloaded test APK is blocked by your device's security controls, stop and have your device administrator review it; do not bypass the protection.

## 10. Confirm an end-to-end update

Use a fictional test donation, clearly labelled as a remote connectivity test:

1. Receive a bag from the phone on mobile data.
2. Refresh the PC workspace and confirm the bag appears.
3. Dispatch/receive the bag, sort an item, take its photos and save it.
4. Check the same item, photos, donor/bag links and processing history on the PC.
5. Close/reopen the app and verify the saved PC connection still works.
6. Repeat from another shop's Wi-Fi. Test the actual mobile networks and sites you intend to use; successful setup on one connection does not establish availability on every network.

Keep NetBird, Docker and the PC running while staff use the application. The app has no offline queue. A PC power or internet outage stops remote work; it does not erase saved records.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| PC localhost health fails | Start Docker Desktop, run `docker compose ps`, then `docker compose logs --tail 50 app`. |
| Phone browser health times out | Correct PC NetBird IP, both peers connected, device groups, TCP 8000 policy, Windows firewall address scope, PC awake. |
| `ping` fails but health works | Expected when only TCP 8000 is allowed; ICMP is not part of the policy. Use HTTP health as the test. |
| NetBird reports relayed instead of direct | A relay can still carry the encrypted connection; test application performance. Do not open the database port. |
| Browser health works but native app rejects HTTP | Install version `0.3.1-test` or later and enter the PC's actual NetBird IP with port 8000. |
| Login succeeds but immediately returns to login | For this HTTP pilot check `COOKIE_SECURE=false` and recreate the app container. |
| Health reports SQLite | You reached a separate development server; use the Docker application connected to PostgreSQL. |
| Browser cannot use live camera | Use the installed app's native camera or configure trusted HTTPS for the browser. |
| QR opens old LAN address | Update `PUBLIC_BASE_URL`, recreate the app and reprint the label. |
| Phone worked yesterday but stopped | NetBird disconnected, battery restrictions, expired sign-in, changed peer registration/address, another active VPN, or PC/Docker stopped. |

Before routine use with real donor information, replace the shared demo access with individual staff accounts, set a retention policy, and arrange scheduled encrypted off-PC PostgreSQL backups with a tested restore. The database backup includes the photos and item processing events. NetBird's own connection/audit log retention is separate from your application's item history.

References: [Windows installation](https://docs.netbird.io/get-started/install/windows), [Android installation](https://docs.netbird.io/get-started/install/android), [access policies](https://docs.netbird.io/manage/access-control/manage-network-access), [connect on startup](https://docs.netbird.io/client/connect-on-startup), [relayed connections](https://docs.netbird.io/help/troubleshooting-relayed-connections).
