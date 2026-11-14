"""Integration tests use isolated SQLite memory or a disposable PostgreSQL schema."""
import io
import os
import uuid

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
    bag = new_bag(client)
    return bag_action(client, bag_action(client, bag, 'dispatch'), 'receive')

def create_item(client, bag, category='Donate', **extra):
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
    assert create_item(client, bag).status_code == 409
    bag = bag_action(client, bag, 'dispatch')
    bag = bag_action(client, bag, 'receive')
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
    assert create_item(client,bag,'Re-sale',**values).status_code == 422
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
    response=client.put(f'/api/items/{key}/classify',params={'version':item['version']},json={'donation_id':bag['id'],'category':'Donate','item_type':'toy','destination':'Community centre'})
    assert response.status_code==200,response.text
    assert response.json()['id']==key

def test_camera_photos_stay_with_original_donor_and_bag(client, monkeypatch):
    bag=new_bag(client,False)
    bag=bag_action(client,bag_action(client,bag,'dispatch'),'receive')
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
    r = client.put(f'/api/items/{item["id"]}/classify',params={'version':item['version']},json={'donation_id':bag['id'],'category':'Donate','item_type':'clothing','destination':'Safe Haven'})
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
