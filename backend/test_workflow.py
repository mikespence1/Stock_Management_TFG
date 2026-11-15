"""Integration tests use isolated SQLite memory or a disposable PostgreSQL schema."""
import io
import os
import uuid
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import app as module

@pytest.fixture
def client(monkeypatch):
    url = os.getenv('TEST_DATABASE_URL')
    schema = 'test_' + uuid.uuid4().hex
    if url:
        root_engine = create_engine(url)
        with root_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA {schema}'))
        engine = root_engine.execution_options(schema_translate_map={None: schema})
    else:
        root_engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        engine = root_engine
    monkeypatch.setattr(module, 'engine', engine)
    monkeypatch.setattr(module, 'SessionLocal', sessionmaker(engine, expire_on_commit=False))
    module.login_attempts.clear()
    monkeypatch.setenv('STAFF_EMAIL', 'staff@givingflow.local')
    monkeypatch.setenv('STAFF_PASSWORD', 'GivingFlow123!')
    with TestClient(module.app) as c:
        assert c.post('/api/login', json={'email':'staff@givingflow.local','password':'GivingFlow123!'}).status_code == 200
        yield c
    if url:
        with root_engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
    root_engine.dispose()

def bootstrap(client):
    return client.get('/api/bootstrap').json()

def new_bag(client, anonymous=True):
    r = client.post('/api/donations', json={'anonymous':anonymous, 'donor': None if anonymous else {'name':'Test Person','email':'person@example.com','contact_preference':'email'}})
    assert r.status_code == 201, r.text
    return r.json()

def bag_action(client, bag, action):
    r = client.post(f'/api/donations/{bag["id"]}/action', json={'action':action,'version':bag['version']})
    assert r.status_code == 200, r.text
    return r.json()

def sorting_bag(client):
    return new_bag(client)

def upload_photos(client, bag, count=1):
    photos=[]
    for i in range(count):
        stream=io.BytesIO()
        Image.new('RGB',(20,20),['red','green','blue'][i % 3]).save(stream,'JPEG')
        result=client.post('/api/uploads',data={'donation_id':bag['id']},files={'file':('test.jpg',stream.getvalue(),'image/jpeg')})
        assert result.status_code==201,result.text
        photos.append(result.json()['filename'])
    return photos

def create_item(client, bag, category='Donate', **extra):
    if 'photos' not in extra:
        extra['photos']=upload_photos(client,bag,3) if category=='Re-sale' else []
    body = {'donation_id':bag['id'], 'category':category, 'item_type':'clothing', 'destination':'Community centre', 'disposal_method':'Textile recycling', **extra}
    return client.post('/api/items', json=body)

def item_action(client, item, action):
    r = client.post(f'/api/items/{item["id"]}/action', json={'action':action, 'version':item['version']})
    assert r.status_code == 200, r.text
    return r.json()

def test_seed_counts_and_auth(client):
    data = bootstrap(client)
    assert len(data['items']) == 60
    assert len(data['donors']) == 10
    assert len(data['customers']) == 6
    for category in ['Donate', 'Mend', 'Clean', 'Dispose']:
        assert sum(i['category']==category for i in data['items']) == 10
    assert sum(i['item_type']=='book' and i['category']=='Re-sale' for i in data['items']) == 10
    assert sum(i['item_type']=='clothing' and i['category']=='Re-sale' for i in data['items']) == 10
    client.post('/api/logout')
    assert client.get('/api/bootstrap').status_code == 401
    assert client.get('/api/photos/demo-clothing-0-0.svg').status_code == 401
    assert client.post('/api/customers',json={'name':'Blocked'}).status_code == 401

def test_anonymity_and_contact_validation(client):
    before = len(bootstrap(client)['donors'])
    bag = client.post('/api/donations',json={'anonymous':True,'donor':{'name':'Must not be saved','email':'private@example.com'}}).json()
    assert bag['donor_id'] is None and bag['anonymous']
    assert len(bootstrap(client)['donors']) == before
    assert client.post('/api/donations',json={'donor':{'name':'Test','contact_preference':'email'}}).status_code == 422
    assert client.post('/api/donations',json={'donor':{'name':'Test','contact_preference':'phone'}}).status_code == 422
    new_bag(client, False)
    assert len(bootstrap(client)['donors']) == before+1

def test_bag_lifecycle_and_qr(client):
    bag = new_bag(client)
    assert bag['status']=='sorting'
    assert client.post(f'/api/donations/{bag["id"]}/action',json={'action':'dispatch','version':bag['version']}).status_code==409
    assert client.post(f'/api/donations/{bag["id"]}/action',json={'action':'finish','version':bag['version']}).status_code == 422
    r = create_item(client, bag)
    assert r.status_code == 201
    item = r.json()
    labels = client.get('/api/labels',params={'ids':bag['id']+','+item['id']})
    assert labels.status_code == 200
    assert labels.text.count('<svg') == 2
    assert 'private@example.com' not in labels.text
    assert client.get('/api/resolve',params={'code':f'https://shop.test/track/{item["id"]}'}).json()['id'] == item['id']
    assert client.get('/api/resolve',params={'code':bag['reference']}).json()['id'] == bag['id']
    bag = next(b for b in bootstrap(client)['donations'] if b['id']==bag['id'])
    assert bag_action(client,bag,'finish')['status'] == 'processed'

def test_clothing_validation_and_photo_upload(client):
    bag = sorting_bag(client)
    cause = bootstrap(client)['causes'][0]['id']
    values = dict(title='Cotton shirt',brand='Demo',condition='good',location='A-01',cause_id=cause,materials=[{'name':'Cotton','percent':100}])
    assert create_item(client,bag,'Re-sale',photos=[],**values).status_code == 422
    photos=[]
    for color in ['red','green','blue']:
        stream=io.BytesIO()
        Image.new('RGB',(20,20),color).save(stream,'JPEG')
        r=client.post('/api/uploads',data={'donation_id':bag['id']},files={'file':('test.jpg',stream.getvalue(),'image/jpeg')})
        assert r.status_code == 201
        photos.append(r.json()['filename'])
    values['photos']=photos
    values['materials']=[{'name':'Cotton','percent':55},{'name':'Nylon','percent':35}]
    assert create_item(client,bag,'Re-sale',**values).status_code == 422
    values['materials'][1]['percent']=45
    r=create_item(client,bag,'Re-sale',**values)
    assert r.status_code==201,r.text
    assert client.post('/api/uploads',data={'donation_id':bag['id']},files={'file':('bad.svg',b'<svg/>','image/svg+xml')}).status_code == 422
    for filename in photos:
        assert client.get('/api/photos/'+filename).headers['content-type']=='image/jpeg'
        with module.SessionLocal() as db:
            stored=db.get(module.ItemPhoto,filename)
            assert stored.item_id==r.json()['id'] and stored.donation_id==bag['id']
            assert stored.content.startswith(b'\xff\xd8')
        assert not (module.UPLOADS/filename).exists()

@pytest.mark.parametrize('item_type',['jewellery','ornament'])
def test_broader_resale_types(client,item_type):
    bag=sorting_bag(client)
    cause=bootstrap(client)['causes'][0]['id']
    response=create_item(client,bag,'Re-sale',item_type=item_type,title='Test '+item_type,condition='good',location='Shelf 2',cause_id=cause)
    assert response.status_code==201,response.text
    assert response.json()['item_type']==item_type

@pytest.mark.parametrize('item_type',['toy','shoes','hat','homeware','bag','other'])
def test_restricted_types_cannot_be_resold_but_can_follow_other_routes(client,item_type):
    bag=sorting_bag(client)
    cause=bootstrap(client)['causes'][0]['id']
    response=create_item(client,bag,'Re-sale',item_type=item_type,title='Test item',condition='good',location='Shelf 2',cause_id=cause)
    assert response.status_code==422
    for category in ['Donate','Mend','Clean','Dispose']:
        assert create_item(client,bag,category,item_type=item_type).status_code==201

def test_old_prohibited_resale_stock_is_rerouted_without_losing_bag_identity(client):
    bag=sorting_bag(client)
    with module.SessionLocal() as db:
        item=module.Item(donation_id=bag['id'],category='Re-sale',item_type='toy',title='Legacy toy',status='available',listed_online=True,details={})
        db.add(item);db.commit();key=item.id;reference=item.reference
        module.enforce_resale_policy(db);db.commit()
    item=next(i for i in bootstrap(client)['items'] if i['id']==key)
    assert item['status']=='awaiting_sort' and not item['listed_online']
    assert item['reference']==reference and item['donation_id']==bag['id']
    response=client.put(f'/api/items/{key}/classify',params={'version':item['version']},json={'donation_id':bag['id'],'category':'Donate','item_type':'toy','destination':'Community centre','photos':upload_photos(client,bag)})
    assert response.status_code==200,response.text
    assert response.json()['id']==key

def test_camera_photos_stay_with_original_donor_and_bag(client, monkeypatch):
    bag=new_bag(client,False)
    assert bag['status']=='sorting'
    stream=io.BytesIO()
    Image.new('RGB',(20,20),'green').save(stream,'JPEG')
    captured=client.post('/api/uploads',data={'donation_id':bag['id']},files={'file':('capture.jpg',stream.getvalue(),'image/jpeg')})
    assert captured.status_code==201,captured.text
    photo=captured.json()
    assert photo['donor_id']==bag['donor_id']
    other_bag=sorting_bag(client)
    assert create_item(client,other_bag,photos=[photo['filename']]).status_code==422
    item=create_item(client,bag,photos=[photo['filename']]).json()
    assert item['donation_id']==bag['id']
    assert create_item(client,bag,photos=[photo['filename']]).status_code==422
    with module.SessionLocal() as db:
        stored=db.get(module.ItemPhoto,photo['filename'])
        assert stored.item_id==item['id']
        assert db.get(module.Donation,stored.donation_id).donor_id==bag['donor_id']
    assert client.get('/api/resolve',params={'code':bag['reference']}).json()=={'kind':'donation','id':bag['id']}
    encoded=[]
    original_qr=module.qr_svg
    def capture_qr(url):
        encoded.append(url)
        return original_qr(url)
    monkeypatch.setattr(module,'qr_svg',capture_qr)
    label=client.get('/api/labels',params={'ids':bag['id']})
    assert label.status_code==200 and bag['reference'] in label.text
    assert encoded[0].endswith('/track/'+bag['id'])

@pytest.mark.parametrize('category',['Mend','Clean'])
def test_service_return_preserves_item_identity(client,category):
    bag = sorting_bag(client)
    item = create_item(client,bag,category).json()
    original_id, original_ref = item['id'],item['reference']
    item = item_action(client,item,'send')
    assert item['status'] == 'in_service'
    item = item_action(client,item,'return')
    assert item['status'] == 'awaiting_sort'
    r = client.put(f'/api/items/{item["id"]}/classify',params={'version':item['version']},json={'donation_id':bag['id'],'category':'Donate','item_type':'clothing','destination':'Safe Haven','photos':item['details']['photos']})
    assert r.status_code == 200,r.text
    assert r.json()['id'] == original_id and r.json()['reference'] == original_ref
    item = item_action(client,r.json(),'donate')
    assert item['status'] == 'donated'
    assert len([e for e in bootstrap(client)['events'] if e['entity_id']==original_id])==5

def test_book_sale_customer_and_duplicate_prevention(client):
    bag=sorting_bag(client)
    cause=bootstrap(client)['causes'][0]['id']
    values=dict(item_type='book',title='Test book',author='Test author',condition='good',location='Book shelf',cause_id=cause)
    item=create_item(client,bag,'Re-sale',**values).json()
    customer=client.post('/api/customers',json={'name':'Test customer','email':'customer@example.com'}).json()
    export=client.get(f'/api/items/{item["id"]}/shopify-export').json()
    assert export['mode']=='draft_only' and 'donor' not in export
    assert export['currency']=='AED'
    payload={'version':item['version'],'amount_minor':1250,'currency':'AED','customer_id':customer['id']}
    for currency in ['GBP','USD','EUR']:
        assert client.post(f'/api/items/{item["id"]}/sale',json={**payload,'currency':currency}).status_code==422
    sale=client.post(f'/api/items/{item["id"]}/sale',json=payload)
    assert sale.status_code==201,sale.text
    assert sale.json()['cause_id']==cause
    assert sale.json()['currency']=='AED'
    assert client.post(f'/api/items/{item["id"]}/sale',json=payload).status_code==409
    current=next(x for x in bootstrap(client)['items'] if x['id']==item['id'])
    assert current['status']=='sold' and not current['listed_online']

def test_aed_is_default_and_old_fictional_sales_are_updated_without_changing_amount(client):
    assert module.SaleInput(version=1,amount_minor=1250).currency=='AED'
    with module.SessionLocal() as db:
        sale=db.scalar(select(module.Sale))
        original=sale.amount_minor
        sale.currency='GBP'
        db.commit()
        module.normalize_demo_sale_currency(db)
        db.commit()
        assert sale.currency=='AED' and sale.amount_minor==original
    assert all(s['currency']=='AED' for s in bootstrap(client)['sales'])

def test_disposal_and_stale_updates(client):
    bag=sorting_bag(client)
    item=create_item(client,bag,'Dispose').json()
    moved=client.post(f'/api/items/{item["id"]}/action',json={'action':'move','version':item['version'],'location':'Disposal zone'}).json()
    assert moved['location']=='Disposal zone'
    assert client.post(f'/api/items/{item["id"]}/action',json={'action':'dispose','version':item['version']}).status_code==409
    assert item_action(client,moved,'dispose')['status']=='disposed'

def test_cause_fk_and_origin_protection(client):
    assert client.post('/api/donations',json={'donor':{'name':'Test','cause_ids':['not-a-cause']}}).status_code==404
    assert client.post('/api/customers',json={'name':'Blocked'},headers={'origin':'https://evil.test'}).status_code==403
    assert client.post('/api/causes',json={'name':'Local learning fund','description':'Books for children'}).status_code==201

@pytest.mark.parametrize('item_type', ['clothing','book','jewellery','ornament'])
def test_every_resale_type_requires_three_photos_before_any_item_is_saved(client,item_type):
    bag=sorting_bag(client)
    photos=upload_photos(client,bag,3)
    values=dict(item_type=item_type,title='Resale item',brand='Maker',author='Writer',condition='good',location='Shelf',cause_id=bootstrap(client)['causes'][0]['id'],materials=[{'name':'Cotton','percent':100}])
    before=len(bootstrap(client)['items'])
    for invalid in [[],photos[:1],photos[:2],photos+[photos[0]],[photos[0]]*3]:
        assert create_item(client,bag,'Re-sale',photos=invalid,**values).status_code==422
        assert len(bootstrap(client)['items'])==before
    assert create_item(client,bag,'Re-sale',photos=photos,**values).status_code==201

def test_other_routes_allow_no_photos_and_legacy_resale_exports_are_blocked(client):
    bag=sorting_bag(client)
    for category in ['Donate','Mend','Clean','Dispose']:
        assert create_item(client,bag,category,photos=[]).status_code==201
        assert create_item(client,bag,category).status_code==201
        assert create_item(client,bag,category,photos=upload_photos(client,bag,3)).status_code==201
        assert create_item(client,bag,category,photos=upload_photos(client,bag,3)+['extra.jpg']).status_code==422
        photographed=create_item(client,bag,category,photos=upload_photos(client,bag)).json()
        corrected=client.put(f'/api/items/{photographed["id"]}',params={'version':photographed['version']},json={**item_body(photographed),'photos':[]})
        assert corrected.status_code==200,corrected.text
        assert corrected.json()['details']['photos']==[]
    with module.SessionLocal() as db:
        item=module.Item(donation_id=bag['id'],category='Re-sale',item_type='book',title='Legacy book',status='available',details={})
        db.add(item);db.commit();key=item.id;version=item.version
    assert client.get(f'/api/items/{key}/shopify-export').status_code==422
    assert client.post(f'/api/items/{key}/action',json={'action':'toggle_online','version':version}).status_code==422
    assert client.post(f'/api/items/{key}/sale',json={'version':version,'amount_minor':100}).status_code==422

def item_body(item):
    return {**item['details'],**{key:item[key] for key in ['donation_id','category','item_type','title','location','cause_id','listed_online']}}

def test_item_correction_replaces_photos_and_cause_without_reopening_sold_stock(client):
    bag=sorting_bag(client)
    causes=bootstrap(client)['causes']
    item=create_item(client,bag,'Re-sale',item_type='book',title='Typo',author='Writer',condition='good',location='Books',cause_id=causes[0]['id']).json()
    sale=client.post(f'/api/items/{item["id"]}/sale',json={'version':item['version'],'amount_minor':1800}).json()
    item=next(i for i in bootstrap(client)['items'] if i['id']==item['id'])
    photos=upload_photos(client,bag,3)
    body={**item_body(item),'title':'Corrected title','cause_id':causes[1]['id'],'photos':photos}
    response=client.put(f'/api/items/{item["id"]}',params={'version':item['version']},json=body)
    assert response.status_code==200,response.text
    updated=response.json()
    assert updated['status']=='sold' and not updated['listed_online']
    assert updated['reference']==item['reference'] and updated['donation_id']==bag['id']
    assert updated['details']['photos']==photos and updated['title']=='Corrected title'
    assert next(s for s in bootstrap(client)['sales'] if s['id']==sale['id'])['cause_id']==causes[1]['id']
    assert client.put(f'/api/items/{item["id"]}',params={'version':item['version']},json=body).status_code==409
    other=sorting_bag(client)
    assert client.put(f'/api/items/{item["id"]}',params={'version':updated['version']},json={**body,'donation_id':other['id']}).status_code==409
    assert client.put(f'/api/items/{item["id"]}',params={'version':updated['version']},json={**body,'photos':photos[:2]}).status_code==422
    with module.SessionLocal() as db:
        assert all(db.get(module.ItemPhoto,name).item_id==item['id'] for name in photos)
        assert db.get(module.ItemPhoto,item['details']['photos'][0]).item_id==item['id']
        history=list(db.scalars(select(module.Event).where(module.Event.entity_id==item['id'])))
        assert any(e.snapshot.get('title')=='Typo' for e in history)
        assert any(e.snapshot.get('title')=='Corrected title' for e in history)

def test_consent_is_explicit_repeat_donors_reused_and_withdrawal_is_audited(client):
    assert client.post('/api/donations',json={'donor':{'name':'No channel','marketing_consent':True}}).status_code==422
    bag=new_bag(client,False)
    donor=next(d for d in bootstrap(client)['donors'] if d['id']==bag['donor_id'])
    assert not donor['marketing_consent']
    before=len(bootstrap(client)['donors'])
    details={'name':'Correct Name','email':'person@example.com','contact_preference':'email','marketing_consent':True,'nationality':'Emirati'}
    repeat=client.post('/api/donations',json={'donor_id':donor['id'],'donor_version':donor['version'],'donor':details})
    assert repeat.status_code==201,repeat.text
    assert repeat.json()['donor_id']==donor['id']
    assert len(bootstrap(client)['donors'])==before
    current=next(d for d in bootstrap(client)['donors'] if d['id']==donor['id'])
    assert current['marketing_consent'] and current['consent_updated_at']
    assert client.put(f'/api/donors/{donor["id"]}',params={'version':donor['version']},json=details).status_code==409
    withdrawal=client.put(f'/api/donors/{donor["id"]}',params={'version':current['version']},json={**details,'marketing_consent':False})
    assert withdrawal.status_code==200 and not withdrawal.json()['marketing_consent']
    assert any('withdrawn' in e['message'] for e in bootstrap(client)['events'] if e['entity_id']==donor['id'])
    assert client.post('/api/donations',json={'anonymous':True,'donor':details,'donor_id':donor['id'],'donor_version':current['version']}).json()['donor_id'] is None

def test_bag_customer_cause_and_sale_corrections_preserve_identity_and_check_versions(client):
    bag=sorting_bag(client)
    edited=client.put(f'/api/donations/{bag["id"]}',params={'version':bag['version']},json={'location':'Store','notes':'Corrected note'})
    assert edited.status_code==200 and edited.json()['reference']==bag['reference']
    assert edited.json()['status']=='sorting'
    customer=client.post('/api/customers',json={'name':'Typo'}).json()
    cause=client.post('/api/causes',json={'name':'Typo cause'}).json()
    for path,row,body in [('customers',customer,{'name':'Correct Customer','email':'new@example.com'}),('causes',cause,{'name':'Correct Cause','description':'Updated'})]:
        response=client.put(f'/api/{path}/{row["id"]}',params={'version':row['version']},json=body)
        assert response.status_code==200,response.text
        assert response.json()['id']==row['id']
        assert client.put(f'/api/{path}/{row["id"]}',params={'version':row['version']},json=body).status_code==409
    item=create_item(client,bag,'Re-sale',item_type='book',title='Book',author='Writer',condition='good',location='Shelf',cause_id=cause['id']).json()
    sale=client.post(f'/api/items/{item["id"]}/sale',json={'version':item['version'],'amount_minor':1000}).json()
    other=bootstrap(client)['causes'][0]
    response=client.put(f'/api/sales/{sale["id"]}',params={'version':sale['version']},json={'amount_minor':2200,'customer_id':customer['id'],'cause_id':other['id']})
    assert response.status_code==200,response.text
    assert response.json()['amount_minor']==2200 and response.json()['currency']=='AED'
    item=next(i for i in bootstrap(client)['items'] if i['id']==item['id'])
    assert item['status']=='sold' and item['cause_id']==other['id']

def test_additive_migration_preserves_legacy_records_and_never_infers_consent(client):
    # Exercise the same migration against a pre-consent database structure.
    schema=module.engine.get_execution_options().get('schema_translate_map',{}).get(None)
    table=f'{module.engine.dialect.identifier_preparer.quote(schema)}.donors' if schema else 'donors'
    with module.engine.begin() as connection:
        before=list(connection.execute(text(f'SELECT id, name FROM {table}')))
        connection.execute(text(f'ALTER TABLE {table} DROP COLUMN marketing_consent'))
        connection.execute(text(f'ALTER TABLE {table} DROP COLUMN consent_updated_at'))
        connection.execute(text(f'ALTER TABLE {table} DROP COLUMN version'))
    module.migrate_records()
    module.migrate_records()  # Repeated startup is safe.
    with module.SessionLocal() as db:
        assert [(d.id,d.name) for d in db.scalars(select(module.Donor))]==[tuple(r) for r in before]
        assert all(not d.marketing_consent and d.version==1 for d in db.scalars(select(module.Donor)))

def read_workbook(content):
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(io.BytesIO(content)) as archive:
        assert archive.testzip() is None
        strings=[''.join(node.itertext()) for node in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si',ns)]
        sheets=ET.fromstring(archive.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns)
        result={}
        for index,sheet in enumerate(sheets,1):
            root=ET.fromstring(archive.read(f'xl/worksheets/sheet{index}.xml'))
            assert not root.findall('.//m:f',ns), 'People data must never become spreadsheet formulas.'
            rows=[]
            for row in root.findall('m:sheetData/m:row',ns):
                values=[]
                for cell in row.findall('m:c',ns):
                    value=cell.findtext('m:v',default='',namespaces=ns)
                    kind=cell.get('t')
                    value=strings[int(value)] if kind=='s' else value=='1' if kind=='b' else float(value) if value else None
                    values.append((cell.get('r'),value))
                rows.append(dict(values))
            result[sheet.get('name')]=(root,rows)
        return result

def test_people_excel_export_is_authenticated_editable_and_matches_people_metrics(client):
    bag=client.post('/api/donations',json={'donor':{'name':'=1+1','email':'excel@example.com','phone':'+9710012345','nationality':'Emirati','contact_preference':'email','marketing_consent':True,'cause_ids':[bootstrap(client)['causes'][0]['id']]}}).json()
    donor_id=bag['donor_id']
    repeat=client.post('/api/donations',json={'donor_id':donor_id}).json()
    create_item(client,bag)
    create_item(client,bag,'Dispose')
    create_item(client,repeat,'Clean')
    customer=client.post('/api/customers',json={'name':'Offline customer','phone':'0012345'}).json()
    values=dict(item_type='book',title='Export book',author='Writer',condition='good',location='Shelf',cause_id=bootstrap(client)['causes'][0]['id'])
    item=create_item(client,bag,'Re-sale',**values).json()
    client.post(f'/api/items/{item["id"]}/sale',json={'version':item['version'],'amount_minor':1725,'customer_id':customer['id']})
    before=bootstrap(client)
    response=client.get('/api/people/export.xlsx')
    assert response.status_code==200,response.text
    assert response.headers['content-type']=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment;' in response.headers['content-disposition'] and '.xlsx' in response.headers['content-disposition']
    assert response.headers['cache-control']=='no-store'
    workbook=read_workbook(response.content)
    assert list(workbook)==['Overview','Donors','Customers','Anonymous donations']
    _,rows=workbook['Donors']
    assert len(rows)==len(before['donors'])+1
    exported=next(row for row in rows[1:] if list(row.values())[0]==donor_id)
    values=list(exported.values())
    assert values[2:9]==['=1+1','excel@example.com','+9710012345','Emirati','email',True,True]
    assert isinstance(values[9],float)  # Typed, sortable Excel timestamp.
    assert values[-2:]==[2,4]
    assert list(next(row for row in workbook['Customers'][1][1:] if list(row.values())[0]==customer['id']).values())==[customer['id'],1.0,'Offline customer','','0012345',1.0,17.25]
    overview={list(row.values())[0]:list(row.values())[1] for row in workbook['Overview'][1] if len(row)==2}
    assert overview['Known donors']==len(before['donors'])
    assert overview['Donors with consent and contact details']==1
    assert overview['Donations with current marketing permission']==2
    assert len(workbook['Anonymous donations'][1])-1==sum(b['anonymous'] or not b['donor_id'] for b in before['donations'])
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    assert workbook['Donors'][0].find('m:sheetViews/m:sheetView/m:pane',ns).get('state')=='frozen'
    assert len(bootstrap(client)['donors'])==len(before['donors'])
    client.post('/api/logout')
    assert client.get('/api/people/export.xlsx').status_code==401

def test_empty_people_workbook_has_headers_and_no_errors():
    from backend.people_export import people_workbook
    workbook=read_workbook(people_workbook([],[],[],[],[],[],module.now()))
    assert all(len(workbook[name][1])==1 for name in ['Donors','Customers','Anonymous donations'])
