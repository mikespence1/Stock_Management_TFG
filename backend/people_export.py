"""Build an editable People snapshot, with no formulas from user-provided text."""
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO

import xlsxwriter


def contactable(donor):
    channel = donor.get('contact_preference')
    return bool(donor.get('marketing_consent') and channel in ('email', 'phone') and (donor.get(channel) or '').strip())


def people_workbook(donors, customers, donations, items, causes, sales, exported_at):
    output = BytesIO()
    book = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False, 'strings_to_urls': False})
    book.set_properties({'title': 'Thrift for Good — People', 'author': 'Thrift for Good', 'comments': 'Offline snapshot. Changes in Excel are not imported into the application.'})
    header = book.add_format({'bold': True, 'bg_color': '#214D4E', 'font_color': 'white', 'text_wrap': True, 'valign': 'top'})
    title = book.add_format({'bold': True, 'font_size': 18, 'font_color': '#214D4E'})
    note = book.add_format({'text_wrap': True, 'valign': 'top', 'font_color': '#586C68'})
    integer = book.add_format({'num_format': '#,##0'})
    money = book.add_format({'num_format': '"AED "#,##0.00'})
    date = book.add_format({'num_format': 'yyyy-mm-dd hh:mm'})

    def sheet(name, columns, rows):
        ws = book.add_worksheet(name)
        ws.hide_gridlines(2)
        ws.freeze_panes(1, 0)
        ws.set_row(0, 44)
        for col, (label, width, fmt) in enumerate(columns):
            ws.set_column(col, col, width, fmt)
            ws.write_string(0, col, label, header)
        for row_num, row in enumerate(rows, 1):
            for col, value in enumerate(row):
                if isinstance(value, datetime):
                    # Export times are explicitly UTC and stay sortable Excel dates.
                    value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
                    ws.write_datetime(row_num, col, value.replace(tzinfo=None), date)
                elif isinstance(value, str):
                    ws.write_string(row_num, col, value)
                elif value is not None:
                    ws.write(row_num, col, value)
        if rows:
            ws.add_table(0, 0, len(rows), len(columns)-1, {'columns': [{'header': c[0], 'header_format': header} for c in columns], 'style': 'Table Style Medium 2'})
        else:
            ws.autofilter(0, 0, 0, len(columns)-1)
        return ws

    donor_bags = Counter(b['donor_id'] for b in donations if b.get('donor_id') and not b.get('anonymous'))
    bag_donor = {b['id']: b.get('donor_id') if not b.get('anonymous') else None for b in donations}
    donor_items = Counter(bag_donor.get(i['donation_id']) for i in items)
    bag_items = Counter(i['donation_id'] for i in items)
    customer_purchases = Counter(s.get('customer_id') for s in sales)
    customer_spend = Counter()
    for sale in sales:
        if sale['currency'] == 'AED':
            customer_spend[sale.get('customer_id')] += sale['amount_minor']
    cause_names = {c['id']: c['name'] for c in causes}
    anonymous = [b for b in donations if b.get('anonymous') or not b.get('donor_id')]
    allowed_ids = {d['id'] for d in donors if contactable(d)}
    opted_in_bags = sum(not b.get('anonymous') and b.get('donor_id') in allowed_ids for b in donations)

    overview = book.add_worksheet('Overview')
    overview.hide_gridlines(2)
    overview.set_column('A:A', 52)
    overview.set_column('B:B', 28)
    overview.merge_range('A1:B1', 'Thrift for Good — People', title)
    overview.write('A3', 'Exported at (UTC)')
    overview.write_datetime('B3', exported_at.astimezone(timezone.utc).replace(tzinfo=None), date)
    overview.merge_range('A5:B6', 'Editable offline snapshot of all People records, regardless of page filters. Excel edits do not update the app; importing changes is not supported. IDs and versions identify the original records.', note)
    overview.merge_range('A8:B9', 'Marketing requires explicit consent and a matching chosen contact method. Anonymous bags do not identify unique people. Donation and item totals include all statuses. Counts are a snapshot at export time.', note)
    metrics = [('Known donors', len(donors)), ('Customers', len(customers)), ('Donations (bags)', len(donations)), ('Items donated', len(items)), ('Donors with consent and contact details', len(allowed_ids)), ('Donations with current marketing permission', opted_in_bags), ('Known-donor donations without permission', len(donations)-len(anonymous)-opted_in_bags), ('Anonymous donations — do not contact', len(anonymous))]
    for index, (label, value) in enumerate(metrics, 11):
        overview.write_string(index, 0, label)
        overview.write_number(index, 1, value, integer)
    overview.write('A22', 'Nationality (known donors)', header)
    overview.write('B22', 'Donors', header)
    nationalities = Counter((d.get('nationality') or '').strip() or 'Not provided' for d in donors)
    for index, (label, value) in enumerate(sorted(nationalities.items(), key=lambda x: (-x[1], x[0])), 22):
        overview.write_string(index, 0, label)
        overview.write_number(index, 1, value, integer)

    sheet('Donors', [('Donor ID', 38, None), ('Version', 10, integer), ('Name', 26, None), ('Email', 32, None), ('Phone', 22, None), ('Nationality', 20, None), ('Contact preference', 20, None), ('Marketing consent', 20, None), ('May contact for marketing', 26, None), ('Consent updated (UTC)', 24, date), ('Favoured causes', 46, None), ('Cause IDs', 42, None), ('Donations (bags)', 20, integer), ('Items donated', 18, integer)], [
        [d['id'], d['version'], d['name'], d.get('email', ''), d.get('phone', ''), d.get('nationality', ''), d.get('contact_preference', 'none'), bool(d.get('marketing_consent')), contactable(d), d.get('consent_updated_at'), '; '.join(cause_names.get(c, c) for c in d.get('cause_ids', [])), '; '.join(d.get('cause_ids', [])), donor_bags[d['id']], donor_items[d['id']]]
        for d in sorted(donors, key=lambda d: (d['name'].casefold(), d['id']))])
    sheet('Customers', [('Customer ID', 38, None), ('Version', 10, integer), ('Name', 26, None), ('Email', 32, None), ('Phone', 22, None), ('Items purchased', 20, integer), ('Total recorded sales (AED)', 28, money)], [
        [c['id'], c['version'], c['name'], c.get('email', ''), c.get('phone', ''), customer_purchases[c['id']], customer_spend[c['id']]/100]
        for c in sorted(customers, key=lambda c: (c['name'].casefold(), c['id']))])
    sheet('Anonymous donations', [('Donation ID', 38, None), ('Bag reference', 24, None), ('Received (UTC)', 24, date), ('Status', 18, None), ('Location', 28, None), ('Items donated', 20, integer), ('Marketing permission', 26, None)], [
        [b['id'], b['reference'], b['created_at'], b['status'], b['location'], bag_items[b['id']], 'Do not contact']
        for b in sorted(anonymous, key=lambda b: (b['created_at'], b['id']))])
    book.close()
    return output.getvalue()
