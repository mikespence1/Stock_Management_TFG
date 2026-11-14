"""Idempotent fictional demonstration records; never contacts external services."""
import os
from datetime import timedelta
from sqlalchemy import select

def seed(db):
    from .app import Cause, Customer, Donation, Donor, Event, Item, Sale, Staff, UPLOADS, now, password_hash
    if not db.scalar(select(Staff)):
        db.add(Staff(email=os.getenv('STAFF_EMAIL', 'staff@givingflow.local').lower(), name='Alex Morgan', password=password_hash(os.getenv('STAFF_PASSWORD', 'GivingFlow123!'))))
        db.commit()
    if db.scalar(select(Donation)):
        return
    causes = [Cause(name=n, description=d) for n, d in [('Community Food Fund', 'Meals and essentials for local families'), ('Bright Futures', 'School supplies and youth opportunities'), ('Safe Haven', 'Practical help for people without a home'), ('Care Together', 'Support for older people'), ('Green Tomorrow', 'Repair, reuse and environmental projects')]]
    db.add_all(causes)
    db.flush()
    names = ['Amira Hassan', 'James Wilson', 'Priya Shah', 'Omar Khalid', 'Sophie Martin', 'Daniel Okafor', 'Leila Ahmed', 'Maya Chen', 'Noah Taylor', 'Fatima Ali']
    donors = [Donor(name=name, email=f'donor{i+1}@example.com', phone=f'+44 7700 900{i:03}', nationality=['British', 'Emirati', 'Indian', 'Canadian', 'French'][i % 5], contact_preference=['none', 'email', 'phone'][i % 3], cause_ids=[causes[i % 5].id]) for i, name in enumerate(names)]
    customers = [Customer(name=name, email=f'customer{i+1}@example.com', phone=f'+44 7700 901{i:03}') for i, name in enumerate(['Emma Parker', 'Yusuf Malik', 'Chloe Evans', 'Arjun Patel', 'Grace Kim', 'Adam Green'])]
    db.add_all(donors + customers)
    db.flush()
    bags = []
    for i in range(15):
        status = 'received' if i < 3 else 'in_transit' if i < 5 else 'sorting' if i < 8 else 'processed'
        bag = Donation(donor_id=None if i in [2, 9] else donors[i % 10].id, anonymous=i in [2, 9], status=status, location='Shop reception' if i < 3 else 'Warehouse A', created_at=now() - timedelta(days=15-i), notes='Fictional demo donation')
        db.add(bag)
        db.flush()
        bags.append(bag)
        db.add(Event(entity_id=bag.id, message='Donation received · Demo record', actor='Alex Morgan', created_at=bag.created_at))
        if status != 'received':
            db.add(Event(entity_id=bag.id, message='Dispatched to warehouse', actor='Alex Morgan', created_at=bag.created_at + timedelta(hours=1)))
        if status in ['sorting', 'processed']:
            db.add(Event(entity_id=bag.id, message='Received at warehouse · Sorting started', actor='Sam Rivera', created_at=bag.created_at + timedelta(hours=3)))
    colors = ['#7b8e73', '#ab765e', '#607d8b', '#bcad8d', '#706b8d']
    for n, color in enumerate(colors):
        for view in range(3):
            name = f'demo-clothing-{n}-{view}.svg'
            # Local, clearly identified illustration placeholders, not real item photographs.
            artwork = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500"><rect width="500" height="500" fill="#f0eee8"/><path d="M170 100L100 150L130 230L170 210L170 400L330 400L330 210L370 230L400 150L330 100L290 120Q250 160 210 120Z" fill="{color}"/><path d="M210 120Q250 190 290 120" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="5"/><text x="250" y="465" font-family="sans-serif" text-anchor="middle" font-size="16" fill="#5f665e">DEMO ILLUSTRATION · VIEW {view+1}</text></svg>'
            (UPLOADS / name).write_text(artwork, encoding='utf-8')
    clothing = ['Linen blend shirt', 'Everyday cotton tee', 'Classic knit jumper', 'Lightweight jacket', 'Relaxed summer dress', 'Denim overshirt', 'Soft wool cardigan', 'Tailored trousers', 'Striped polo shirt', 'Cotton weekend top']
    books = [('The Secret Garden', 'Frances Hodgson Burnett'), ('Pride and Prejudice', 'Jane Austen'), ('A Room of One’s Own', 'Virginia Woolf'), ('The Wind in the Willows', 'Kenneth Grahame'), ('Little Women', 'Louisa May Alcott'), ('The Railway Children', 'E. Nesbit'), ('Treasure Island', 'Robert Louis Stevenson'), ('Emma', 'Jane Austen'), ('Jane Eyre', 'Charlotte Brontë'), ('The Jungle Book', 'Rudyard Kipling')]
    for group, category in enumerate(['Re-sale', 'Re-sale', 'Donate', 'Mend', 'Clean', 'Dispose']):
        for i in range(10):
            item_type = 'clothing' if group == 0 else 'book' if group == 1 else ['clothing', 'homeware', 'shoes', 'toy', 'bag'][i % 5]
            title = clothing[i] if group == 0 else books[i][0] if group == 1 else f'{["Winter coat", "Ceramic bowl", "Walking shoes", "Wooden toy", "Canvas bag"][i % 5]}'
            status = {'Re-sale': 'available', 'Donate': 'awaiting_donation', 'Mend': 'awaiting_service', 'Clean': 'awaiting_service', 'Dispose': 'awaiting_disposal'}[category]
            if category in ['Mend', 'Clean'] and i < 3:
                status = 'in_service'
            if category in ['Mend', 'Clean'] and i == 3:
                status = 'awaiting_sort'
            if category == 'Donate' and i < 2:
                status = 'donated'
            if category == 'Dispose' and i < 2:
                status = 'disposed'
            details = {'condition': ['excellent', 'very good', 'good', 'fair'][i % 4], 'notes': 'Fictional demo item'}
            if group == 0:
                details.update(brand=['M&S', 'Uniqlo', 'Next', 'Zara', 'COS'][i % 5], photos=[f'demo-clothing-{i%5}-{v}.svg' for v in range(3)], materials=[{'name': 'Cotton', 'percent': 55}, {'name': 'Nylon', 'percent': 45}])
            if group == 1:
                details['author'] = books[i][1]
            if category in ['Donate', 'Mend', 'Clean']:
                details['destination'] = {'Donate': 'Safe Haven Community Centre', 'Mend': 'Stitch & Care workshop', 'Clean': 'Fresh Start laundry'}[category]
            if category == 'Dispose':
                details['disposal_method'] = 'Textile recycling' if i % 2 == 0 else 'Approved waste collection'
            item = Item(donation_id=bags[5 + i % 10].id, category=category, item_type=item_type, title=title, status=status, location=f'A-{group+1:02d} / Shelf {i+1:02d}', cause_id=causes[i % 5].id if category == 'Re-sale' else None, listed_online=category == 'Re-sale' and i % 3 == 0, details=details, created_at=now() - timedelta(days=10-i))
            db.add(item)
            db.flush()
            db.add(Event(entity_id=item.id, message=f'Sorted into {category} · {item.location}', actor='Sam Rivera', created_at=item.created_at))
            if group < 2 and i == 9:
                item.status, item.listed_online = 'sold', False
                db.add(Sale(item_id=item.id, customer_id=customers[group].id, amount_minor=1800 if group == 0 else 450, currency='AED', cause_id=item.cause_id))
                db.add(Event(entity_id=item.id, message='Sold · Demo transaction', actor='Alex Morgan'))
            elif status != {'Re-sale': 'available', 'Donate': 'awaiting_donation', 'Mend': 'awaiting_service', 'Clean': 'awaiting_service', 'Dispose': 'awaiting_disposal'}[category]:
                db.add(Event(entity_id=item.id, message=f'Status updated · {status.replace("_", " ")}', actor='Sam Rivera'))
    db.commit()
