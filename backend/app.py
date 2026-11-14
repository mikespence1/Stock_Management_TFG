"""GivingFlow prototype. PostgreSQL in Compose; explicit SQLite mode for local QA."""
import hashlib
import hmac
import io
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import qrcode
import qrcode.image.svg
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, create_engine, event, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

ROOT = Path(__file__).resolve().parent
UPLOADS = ROOT / 'uploads'
UPLOADS.mkdir(exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "prototype.db"}')
engine = create_engine(DATABASE_URL, **({'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite') else {'pool_pre_ping': True}))
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def now():
    return datetime.now(timezone.utc)

def uid():
    return str(uuid.uuid4())

def ref(prefix):
    return f'{prefix}-{uuid.uuid4().hex[:10].upper()}'

class Base(DeclarativeBase):
    pass

class Cause(Base):
    __tablename__ = 'causes'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default='')

class Donor(Base):
    __tablename__ = 'donors'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, default='')
    phone: Mapped[str] = mapped_column(String, default='')
    nationality: Mapped[str] = mapped_column(String, default='')
    contact_preference: Mapped[str] = mapped_column(String, default='none')
    cause_ids: Mapped[list] = mapped_column(JSON, default=list)

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, default='')
    phone: Mapped[str] = mapped_column(String, default='')

class Donation(Base):
    __tablename__ = 'donations'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    reference: Mapped[str] = mapped_column(String, unique=True, default=lambda: ref('BAG'))
    donor_id: Mapped[str | None] = mapped_column(ForeignKey('donors.id'), nullable=True)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default='received')
    location: Mapped[str] = mapped_column(String, default='Shop reception')
    notes: Mapped[str] = mapped_column(String, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {'version_id_col': version}

class Item(Base):
    __tablename__ = 'items'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    reference: Mapped[str] = mapped_column(String, unique=True, default=lambda: ref('ITM'))
    donation_id: Mapped[str] = mapped_column(ForeignKey('donations.id'), index=True)
    category: Mapped[str] = mapped_column(String)
    item_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    location: Mapped[str] = mapped_column(String, default='')
    cause_id: Mapped[str | None] = mapped_column(ForeignKey('causes.id'), nullable=True)
    listed_online: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {'version_id_col': version}

class Sale(Base):
    __tablename__ = 'sales'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    item_id: Mapped[str] = mapped_column(ForeignKey('items.id'), unique=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey('customers.id'), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String, default='AED')
    cause_id: Mapped[str | None] = mapped_column(ForeignKey('causes.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ItemPhoto(Base):
    __tablename__ = 'item_photos'
    filename: Mapped[str] = mapped_column(String, primary_key=True)
    donation_id: Mapped[str] = mapped_column(ForeignKey('donations.id'), index=True)
    item_id: Mapped[str | None] = mapped_column(ForeignKey('items.id'), nullable=True, index=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    media_type: Mapped[str] = mapped_column(String, default='image/jpeg')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    message: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Staff(Base):
    __tablename__ = 'staff'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)

class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey('staff.id'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000).hex()
    return f'{salt}${digest}'

def record(db, entity_id, message, actor):
    item = db.get(Item, entity_id)
    snapshot = {'category': item.category, 'status': item.status, 'location': item.location, 'details': item.details} if item else {}
    db.add(Event(entity_id=entity_id, message=message, actor=actor, snapshot=snapshot))

def get_db():
    with SessionLocal() as db:
        yield db

def staff_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get('givingflow_session', '')
    session = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < now():
        raise HTTPException(401, 'Please sign in to continue.')
    return db.get(Staff, session.staff_id)

class DonorInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str = Field(default='', max_length=40)
    nationality: str = Field(default='', max_length=100)
    contact_preference: Literal['none', 'email', 'phone'] = 'none'
    cause_ids: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def contact_details(self):
        if not self.name.strip():
            raise ValueError('Enter the donor name.')
        if self.contact_preference == 'email' and not self.email:
            raise ValueError('Email contact requires an email address.')
        if self.contact_preference == 'phone' and not self.phone.strip():
            raise ValueError('Phone contact requires a phone number.')
        return self

class DonationInput(BaseModel):
    anonymous: bool = False
    donor: DonorInput | None = None
    location: str = Field(default='Shop reception', min_length=1, max_length=120)
    notes: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def identity(self):
        if not self.anonymous and not self.donor:
            raise ValueError('Enter donor details or select anonymous.')
        if self.anonymous:
            self.donor = None
        return self

class Material(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    percent: float = Field(gt=0, le=100)

class ItemInput(BaseModel):
    donation_id: str
    category: Literal['Re-sale', 'Donate', 'Mend', 'Clean', 'Dispose']
    item_type: Literal['clothing', 'book', 'shoes', 'hat', 'jewellery', 'ornament', 'homeware', 'toy', 'bag', 'other'] = 'clothing'
    title: str = Field(default='', max_length=200)
    location: str = Field(default='', max_length=120)
    cause_id: str | None = None
    listed_online: bool = False
    condition: Literal['excellent', 'very good', 'good', 'fair'] | None = None
    brand: str = Field(default='', max_length=120)
    author: str = Field(default='', max_length=160)
    photos: list[str] = Field(default_factory=list, max_length=3)
    materials: list[Material] = Field(default_factory=list, max_length=20)
    destination: str = Field(default='', max_length=160)
    disposal_method: str = Field(default='', max_length=160)
    notes: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def category_fields(self):
        if not self.item_type.strip():
            raise ValueError('Choose an item type.')
        if self.category == 'Re-sale':
            if self.item_type not in ['clothing', 'book', 'ornament', 'jewellery']:
                raise ValueError('Only clothes, books, ornaments and jewellery can be sorted for resale.')
            if not self.condition or not self.location.strip() or not self.cause_id:
                raise ValueError('Resale requires condition, storage location and a cause.')
            if not self.title.strip():
                raise ValueError('Enter the item or book title.')
            if self.item_type == 'clothing':
                if not self.brand.strip() or len(self.photos) != 3 or len(set(self.photos)) != 3:
                    raise ValueError('Clothing requires a brand and three different photos.')
                if not self.materials or abs(sum(m.percent for m in self.materials) - 100) > .01:
                    raise ValueError('Material percentages must total 100%.')
            elif self.item_type == 'book' and not self.author.strip():
                raise ValueError('Books require an author.')
        elif self.category in ['Donate', 'Mend', 'Clean'] and not self.destination.strip():
            raise ValueError('Enter the recipient or service destination.')
        elif self.category == 'Dispose' and not self.disposal_method.strip():
            raise ValueError('Record how the item will be discarded.')
        if self.category != 'Re-sale':
            self.listed_online = False
        return self

class ActionInput(BaseModel):
    action: str
    version: int
    location: str = Field(default='', max_length=160)
    notes: str = Field(default='', max_length=1000)

class SaleInput(BaseModel):
    version: int
    amount_minor: int = Field(gt=0, le=100000000)
    currency: Literal['AED'] = 'AED'
    customer_id: str | None = None

class CustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str = Field(default='', max_length=40)

class CauseInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=500)

def obj(row):
    values = {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name != 'password'}
    return {key: value.replace(tzinfo=timezone.utc) if isinstance(value, datetime) and value.tzinfo is None else value for key, value in values.items()}

def require(db, model, key):
    row = db.get(model, key)
    if not row:
        raise HTTPException(404, 'Record not found.')
    return row

def commit(db):
    try:
        db.commit()
    except StaleDataError:
        db.rollback()
        raise HTTPException(409, 'Another staff member updated this record. Refresh and try again.')

def check_version(row, version):
    if row.version != version:
        raise HTTPException(409, 'This record has changed. Refresh before continuing.')

def apply_item(db, item, data):
    if data.cause_id:
        require(db, Cause, data.cause_id)
    for photo in data.photos:
        saved = db.get(ItemPhoto, photo)
        if not saved or saved.donation_id != data.donation_id:
            raise HTTPException(422, 'Each photo must belong to this donation bag.')
        if saved.item_id and saved.item_id != item.id:
            raise HTTPException(422, 'This photo already belongs to another item.')
    item.category, item.item_type = data.category, data.item_type
    item.title = data.title.strip() or data.item_type.capitalize()
    item.location = data.location.strip() or data.destination.strip() or 'Warehouse'
    item.cause_id, item.listed_online = data.cause_id, data.listed_online
    item.status = {'Re-sale': 'available', 'Donate': 'awaiting_donation', 'Mend': 'awaiting_service', 'Clean': 'awaiting_service', 'Dispose': 'awaiting_disposal'}[data.category]
    item.details = data.model_dump(exclude={'donation_id', 'category', 'item_type', 'title', 'location', 'cause_id', 'listed_online'})

def bind_photos(db, item):
    for filename in item.details.get('photos', []):
        photo = db.get(ItemPhoto, filename)
        photo.item_id = item.id

def enforce_resale_policy(db):
    for item in db.scalars(select(Item).where(Item.category == 'Re-sale', Item.status == 'available')).all():
        if item.item_type not in ['clothing', 'book', 'ornament', 'jewellery']:
            item.status, item.listed_online = 'awaiting_sort', False
            record(db, item.id, 'Resale policy updated · Choose Donate, Mend, Clean or Dispose for this item type', 'System')

def normalize_demo_sale_currency(db):
    # Correct fictional sample data only; never perform an implicit FX conversion.
    demo_ids = select(Event.entity_id).where(Event.message == 'Sold · Demo transaction')
    for sale in db.scalars(select(Sale).where(Sale.currency != 'AED', Sale.item_id.in_(demo_ids))).all():
        sale.currency = 'AED'
        record(db, sale.item_id, 'Fictional demo price updated to AED; numeric amount unchanged', 'System')

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    # Additive migration for early prototype installs; no existing data is removed.
    schema = engine.get_execution_options().get('schema_translate_map', {}).get(None)
    if 'snapshot' not in {column['name'] for column in inspect(engine).get_columns('events', schema=schema)}:
        with engine.begin() as connection:
            table = f'{engine.dialect.identifier_preparer.quote(schema)}.events' if schema else 'events'
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN snapshot JSON NOT NULL DEFAULT '{{}}'"))
    from .seed import seed
    with SessionLocal() as db:
        seed(db)
        enforce_resale_policy(db)
        normalize_demo_sale_currency(db)
        # Import existing file-based photos once, preserving all existing item URLs.
        for item in db.scalars(select(Item)).all():
            migrated = []
            for filename in item.details.get('photos', []):
                path = UPLOADS / filename
                saved = db.get(ItemPhoto, filename)
                # Old demo items reused illustration files. Give each its own DB photo.
                if saved and saved.item_id != item.id:
                    filename = f'{item.id}-{filename}'
                    if not db.get(ItemPhoto, filename):
                        db.add(ItemPhoto(filename=filename, donation_id=item.donation_id, item_id=item.id, content=saved.content, media_type=saved.media_type))
                elif not saved and Path(filename).name == filename and path.is_file():
                    media_type = 'image/svg+xml' if path.suffix == '.svg' else 'image/jpeg'
                    db.add(ItemPhoto(filename=filename, donation_id=item.donation_id, item_id=item.id, content=path.read_bytes(), media_type=media_type))
                migrated.append(filename)
            if migrated != item.details.get('photos', []):
                item.details = {**item.details, 'photos': migrated}
        db.commit()
    yield

app = FastAPI(title='Thrift for Good API', version='0.1.0', lifespan=lifespan)

@app.exception_handler(StaleDataError)
async def stale_update(request, exc):
    return JSONResponse(status_code=409, content={'detail': 'Another staff member changed this record. Refresh and try again.'})

@app.middleware('http')
async def origin_check(request, call_next):
    origin = request.headers.get('origin')
    if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and origin:
        if urlparse(origin).netloc != request.headers.get('host'):
            return Response('Origin is not allowed.', status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response

class LoginInput(BaseModel):
    email: str
    password: str

login_attempts = {}

@app.post('/api/login')
def login(data: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    key = request.client.host if request.client else 'local'
    attempts = [t for t in login_attempts.get(key, []) if t > now() - timedelta(minutes=10)]
    if len(attempts) >= 20:
        raise HTTPException(429, 'Too many attempts. Try again in ten minutes.')
    staff = db.scalar(select(Staff).where(Staff.email == data.email.strip().lower()))
    if not staff or not hmac.compare_digest(staff.password, password_hash(data.password, staff.password.split('$')[0])):
        login_attempts[key] = attempts + [now()]
        raise HTTPException(401, 'Email or password is incorrect.')
    login_attempts.pop(key, None)
    token = secrets.token_urlsafe(48)
    db.add(LoginSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), staff_id=staff.id, expires_at=now() + timedelta(hours=12)))
    db.commit()
    response.set_cookie('givingflow_session', token, httponly=True, secure=os.getenv('COOKIE_SECURE') == 'true', samesite='strict', max_age=43200)
    return {'name': staff.name, 'email': staff.email}

@app.post('/api/logout')
def logout(request: Request, response: Response, staff=Depends(staff_user), db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(request.cookies.get('givingflow_session', '').encode()).hexdigest()
    session = db.get(LoginSession, token_hash)
    if session:
        db.delete(session)
        db.commit()
    response.delete_cookie('givingflow_session')
    return {'ok': True, 'signed_out': True}

@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {'status': 'ok', 'database': engine.dialect.name}

@app.get('/api/bootstrap')
def bootstrap(staff=Depends(staff_user), db: Session = Depends(get_db)):
    result = {key: [obj(r) for r in db.scalars(select(model)).all()] for key, model in [('donors', Donor), ('customers', Customer), ('donations', Donation), ('items', Item), ('causes', Cause), ('sales', Sale), ('events', Event)]}
    result['staff'] = {'name': staff.name, 'email': staff.email}
    result['database'] = engine.dialect.name
    result['public_base_url'] = os.getenv('PUBLIC_BASE_URL', 'http://localhost:8000')
    return result

@app.post('/api/donations', status_code=201)
def create_donation(data: DonationInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    donor = None
    if data.donor and not data.anonymous:
        for cause_id in data.donor.cause_ids:
            require(db, Cause, cause_id)
        donor = Donor(**data.donor.model_dump())
        donor.email = str(data.donor.email or '')
        db.add(donor)
        db.flush()
    donation = Donation(donor_id=donor.id if donor else None, anonymous=data.anonymous, location=data.location, notes=data.notes)
    db.add(donation)
    db.flush()
    record(db, donation.id, f'Donation received at {donation.location}', staff.name)
    db.commit()
    return obj(donation)

@app.post('/api/donations/{key}/action')
def donation_action(key: str, data: ActionInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    donation = require(db, Donation, key)
    check_version(donation, data.version)
    transitions = {('received', 'dispatch'): 'in_transit', ('in_transit', 'receive'): 'sorting', ('sorting', 'finish'): 'processed'}
    target = transitions.get((donation.status, data.action))
    if not target:
        raise HTTPException(409, 'This action is not available at the current stage.')
    if target == 'processed' and not db.scalar(select(Item).where(Item.donation_id == key)):
        raise HTTPException(422, 'Add at least one item before finishing the bag.')
    donation.status = target
    donation.location = data.location.strip() or ('Warehouse' if target in ['sorting', 'processed'] else 'To warehouse')
    record(db, key, f'{target.replace("_", " ").capitalize()} · {donation.location}' + (f' · {data.notes}' if data.notes else ''), staff.name)
    commit(db)
    return obj(donation)

@app.post('/api/items', status_code=201)
def create_item(data: ItemInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    donation = require(db, Donation, data.donation_id)
    if donation.status != 'sorting':
        raise HTTPException(409, 'Receive this bag at the warehouse before sorting items.')
    item = Item(id=uid(), donation_id=donation.id)
    apply_item(db, item, data)
    # Updating the bag version prevents simultaneous finish/add operations losing items.
    donation.version += 1
    db.add(item)
    db.flush()
    bind_photos(db, item)
    record(db, item.id, f'Sorted into {item.category} · {item.location}', staff.name)
    commit(db)
    return obj(item)

@app.put('/api/items/{key}/classify')
def classify(key: str, data: ItemInput, version: int, staff=Depends(staff_user), db: Session = Depends(get_db)):
    item = require(db, Item, key)
    check_version(item, version)
    if item.status != 'awaiting_sort' or item.donation_id != data.donation_id:
        raise HTTPException(409, 'Only returned service items can be reclassified.')
    old = item.category
    apply_item(db, item, data)
    bind_photos(db, item)
    record(db, key, f'Reclassified from {old} to {item.category} · {item.location}', staff.name)
    commit(db)
    return obj(item)

@app.post('/api/items/{key}/action')
def item_action(key: str, data: ActionInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    item = require(db, Item, key)
    check_version(item, data.version)
    if data.action == 'move' and item.status not in ['sold', 'donated', 'disposed']:
        if not data.location.strip():
            raise HTTPException(422, 'Enter the new storage location.')
        message = f'Moved to {data.location.strip()}'
        item.location = data.location.strip()
    elif data.action == 'toggle_online' and item.status == 'available':
        if item.item_type not in ['clothing', 'book', 'ornament', 'jewellery']:
            raise HTTPException(422, 'This item type is not permitted for resale.')
        item.listed_online = not item.listed_online
        message = 'Marked as listed online' if item.listed_online else 'Marked as not listed online'
    else:
        target = {('awaiting_service', 'send'): 'in_service', ('in_service', 'return'): 'awaiting_sort', ('awaiting_donation', 'donate'): 'donated', ('awaiting_disposal', 'dispose'): 'disposed'}.get((item.status, data.action))
        if not target:
            raise HTTPException(409, 'This action is not available at the current stage.')
        item.status = target
        if target in ['in_service', 'donated']:
            item.location = item.details.get('destination', '')
        elif target == 'disposed':
            item.location = item.details.get('disposal_method', '')
        else:
            item.location = data.location.strip() or 'Warehouse returns'
        message = f'{target.replace("_", " ").capitalize()} · {item.location}'
    record(db, key, message + (f' · {data.notes}' if data.notes else ''), staff.name)
    commit(db)
    return obj(item)

@app.post('/api/items/{key}/sale', status_code=201)
def sell(key: str, data: SaleInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    item = require(db, Item, key)
    check_version(item, data.version)
    if item.category != 'Re-sale' or item.status != 'available':
        raise HTTPException(409, 'Only available resale items can be sold.')
    if item.item_type not in ['clothing', 'book', 'ornament', 'jewellery']:
        raise HTTPException(422, 'This item type is not permitted for resale. Re-sort it first.')
    if data.customer_id:
        require(db, Customer, data.customer_id)
    sale = Sale(item_id=key, customer_id=data.customer_id, amount_minor=data.amount_minor, currency=data.currency, cause_id=item.cause_id)
    db.add(sale)
    item.status, item.listed_online = 'sold', False
    record(db, key, f'Sold for {data.currency} {data.amount_minor / 100:.2f}', staff.name)
    commit(db)
    return obj(sale)

@app.post('/api/customers', status_code=201)
def customer(data: CustomerInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    row = Customer(name=data.name.strip(), email=str(data.email or ''), phone=data.phone)
    if not row.name:
        raise HTTPException(422, 'Enter the customer name.')
    db.add(row)
    db.commit()
    return obj(row)

@app.post('/api/causes', status_code=201)
def cause(data: CauseInput, staff=Depends(staff_user), db: Session = Depends(get_db)):
    if not data.name.strip():
        raise HTTPException(422, 'Enter the cause name.')
    row = Cause(name=data.name.strip(), description=data.description)
    db.add(row)
    db.commit()
    return obj(row)

@app.post('/api/uploads', status_code=201)
async def upload(file: UploadFile, donation_id: str = Form(...), staff=Depends(staff_user), db: Session = Depends(get_db)):
    donation = require(db, Donation, donation_id)
    if donation.status not in ['sorting', 'processed']:
        raise HTTPException(409, 'Receive this bag at the warehouse before taking item photos.')
    raw = await file.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, 'Each photo must be under 8 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ['JPEG', 'PNG', 'WEBP'] or image.width * image.height > 25000000:
                raise ValueError()
            from PIL import ImageOps
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1600, 1600))
            name = f'{uuid.uuid4().hex}.jpg'
            output = io.BytesIO()
            image.save(output, 'JPEG', quality=85)
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'Choose a JPEG, PNG or WebP photo, at most 25 megapixels.')
    db.add(ItemPhoto(filename=name, donation_id=donation.id, content=output.getvalue()))
    db.commit()
    return {'filename': name, 'donation_id': donation.id, 'donor_id': donation.donor_id}

@app.get('/api/photos/{name}')
def photo(name: str, staff=Depends(staff_user), db: Session = Depends(get_db)):
    saved = db.get(ItemPhoto, name)
    if saved:
        return Response(content=saved.content, media_type=saved.media_type)
    if Path(name).name != name or name.startswith('.') or not (UPLOADS / name).is_file():
        raise HTTPException(404, 'Photo not found.')
    return FileResponse(UPLOADS / name)

@app.get('/api/resolve')
def resolve(code: str, staff=Depends(staff_user), db: Session = Depends(get_db)):
    code = code.strip().rstrip('/').split('/')[-1].split('?')[0]
    for model, kind in [(Donation, 'donation'), (Item, 'item')]:
        row = db.scalar(select(model).where((model.id == code) | (model.reference == code.upper())))
        if row:
            return {'kind': kind, 'id': row.id}
    raise HTTPException(404, 'No matching bag or item. Check the reference and try again.')

def qr_svg(url):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).to_string().decode()

@app.get('/api/labels', response_class=HTMLResponse)
def labels(ids: str, request: Request, staff=Depends(staff_user), db: Session = Depends(get_db)):
    keys = ids.split(',')
    if len(keys) > 100:
        raise HTTPException(422, 'Print up to 100 labels at once.')
    base = os.getenv('PUBLIC_BASE_URL', str(request.base_url).rstrip('/'))
    cards = []
    for key in keys:
        row = db.get(Donation, key) or db.get(Item, key)
        if not row:
            raise HTTPException(404, 'Label record not found.')
        url = f'{base}/track/{row.id}'
        title = 'Donation bag' if isinstance(row, Donation) else row.title
        cards.append(f'<article>{qr_svg(url)}<div><img class="print-brand" src="/brand/thrift-for-good-logo.png" alt="THRIFT FOR GOOD"/><p>{escape(title)}</p><strong>{escape(row.reference)}</strong><p>Scan to track · Staff sign-in required</p></div></article>')
    return '<!doctype html><html><head><meta name="viewport" content="width=device-width"><title>Thrift for Good labels</title><style>body{font:13px system-ui;margin:12mm}main{display:flex;flex-wrap:wrap;gap:5mm}article{width:85mm;min-height:40mm;border:1px dashed #aaa;display:flex;align-items:center;break-inside:avoid;padding:3mm;box-sizing:border-box}img.print-brand{width:40mm;max-width:100%;height:auto;margin-bottom:2mm}svg{width:36mm;height:36mm;flex-shrink:0}p{font-size:11px;margin:4px 0}strong{font-size:11px}button{padding:12px;margin:0 0 20px;cursor:pointer}@page{size:A4;margin:10mm}@media print{button{display:none}body{margin:0}}</style></head><body><button onclick="window.print()">Print labels / Save PDF</button><main>' + ''.join(cards) + '</main></body></html>'

@app.get('/api/items/{key}/shopify-export')
def shopify_export(key: str, staff=Depends(staff_user), db: Session = Depends(get_db)):
    item = require(db, Item, key)
    if item.category != 'Re-sale' or item.status != 'available':
        raise HTTPException(409, 'Only available resale items can be exported.')
    if item.item_type not in ['clothing', 'book', 'ornament', 'jewellery']:
        raise HTTPException(422, 'This item type is not permitted for resale.')
    # An offline draft, deliberately excluding donor/customer information.
    return {'mode': 'draft_only', 'currency': 'AED', 'sku': item.reference, 'title': item.title, 'vendor': item.details.get('brand', ''), 'product_type': item.item_type, 'condition': item.details.get('condition'), 'materials': item.details.get('materials', []), 'cause': require(db, Cause, item.cause_id).name if item.cause_id else None, 'quantity': 1, 'photo_files': item.details.get('photos', []), 'note': 'Map this draft to Shopify GraphQL; configure credentials, price, media upload and order webhooks before live sync.'}

@app.get('/android/download')
def download_android():
    apk = ROOT.parent / 'artifacts' / 'GivingFlow-debug.apk'
    if not apk.is_file():
        raise HTTPException(404, 'Android APK not built yet. See docs/ANDROID.md.')
    return FileResponse(apk, media_type='application/vnd.android.package-archive', filename='ThriftForGood-test.apk')

@app.get('/android', response_class=HTMLResponse)
def android_setup(request: Request):
    base = os.getenv('PUBLIC_BASE_URL', str(request.base_url).rstrip('/'))
    download = base + '/android/download'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Thrift for Good Android test</title><style>body{font:16px system-ui;background:#fafafa;color:#323232;margin:0;padding:24px}main{max-width:560px;margin:20px auto;background:white;border:1px solid #e4e4e4;border-radius:12px;padding:26px}h1{font-size:27px}p,li{line-height:1.7}code{background:#e9f7f7;padding:5px;overflow-wrap:anywhere}a{display:block;background:#f1562a;color:#171717;padding:15px;border-radius:7px;text-decoration:none;text-align:center}svg{width:180px;height:180px;display:block;margin:10px auto}small{color:#626262}</style></head><body><main><img src="/brand/thrift-for-good-logo.png" alt="THRIFT FOR GOOD" style="display:block;width:100%;max-width:300px;height:auto;margin:10px 0 25px"/><h1>Thrift for Good for Android</h1><p>Install the test app on your Android 8 or newer phone or tablet. Connect the phone to the same Wi-Fi network as your PC.</p><a href="/android/download">Download Android test APK</a>' + qr_svg(download) + '<p>Scan this QR on your phone to download the installer.</p><ol><li>Download and open the APK. If Android asks, allow your browser to install this test app. Keep Play Protect enabled.</li><li>Open <b>THRIFT FOR GOOD</b>.</li><li>Use server address <code>' + escape(base) + '</code> and tap <b>Test connection &amp; open workspace</b>.</li><li>Sign in with the same staff account as on your PC.</li><li>Receive a donation, print its bag label, dispatch and scan it at the warehouse, then sort and photograph its items.</li></ol><p>Native camera capture, QR scanning and Android printing work over this local HTTP connection. Records and photos are stored in PostgreSQL on your PC.</p><small>Debug-signed prototype for a trusted local network. Keep the PC awake and Docker running. It needs a connection to the PC and does not store an offline copy of the database.</small></main></body></html>'

DIST = ROOT.parent / 'frontend' / 'dist'
if DIST.is_dir():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
    if (DIST / 'brand').is_dir():
        app.mount('/brand', StaticFiles(directory=DIST / 'brand'), name='brand')

@app.get('/{path:path}')
def spa(path: str):
    if path.startswith('api/'):
        raise HTTPException(404, 'API endpoint not found.')
    if DIST.is_dir():
        return FileResponse(DIST / 'index.html')
    return HTMLResponse('<h1>Thrift for Good API is running</h1><p>Start the React frontend on port 5173, or build frontend/dist.</p>')
