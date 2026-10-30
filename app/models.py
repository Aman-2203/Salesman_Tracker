from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='rep')  # 'admin' or 'rep'
    is_active = db.Column(db.Boolean, default=True)
    avatar_url = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    visits = db.relationship('Visit', backref='rep', lazy=True, foreign_keys='Visit.rep_id')
    orders = db.relationship('Order', backref='rep', lazy=True, foreign_keys='Order.rep_id')
    attendances = db.relationship('Attendance', backref='rep', lazy=True)
    payments = db.relationship('Payment', backref='rep', lazy=True, foreign_keys='Payment.rep_id')
    locations = db.relationship('RepLocation', backref='rep', lazy=True)
    customers = db.relationship('Customer', backref='assigned_rep', lazy=True, foreign_keys='Customer.assigned_rep_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name} ({self.role})>'


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    area = db.Column(db.String(100))
    city = db.Column(db.String(100))
    lat = db.Column(db.Float, default=0.0)
    lng = db.Column(db.Float, default=0.0)
    assigned_rep_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    visits = db.relationship('Visit', backref='customer', lazy=True)
    orders = db.relationship('Order', backref='customer', lazy=True)
    payments = db.relationship('Payment', backref='customer', lazy=True)

    def __repr__(self):
        return f'<Customer {self.name}>'


class Visit(db.Model):
    __tablename__ = 'visits'
    id = db.Column(db.Integer, primary_key=True)
    rep_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    visit_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    check_in_time = db.Column(db.DateTime)
    check_out_time = db.Column(db.DateTime)
    check_in_lat = db.Column(db.Float)
    check_in_lng = db.Column(db.Float)
    check_out_lat = db.Column(db.Float)
    check_out_lng = db.Column(db.Float)
    status = db.Column(db.String(30), default='planned')  # planned, checked_in, completed, missed, skipped
    outcome = db.Column(db.String(30))  # met, not_met, follow_up
    has_order = db.Column(db.Boolean, default=False)
    has_payment = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    photo_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_dual_hit(self):
        """Visit where both an order and a payment were secured."""
        return bool(self.has_order and self.has_payment)

    @property
    def is_cash_rescue(self):
        """Debt recovery visit: payment collected but no new order placed."""
        return bool(self.has_payment and not self.has_order)

    @property
    def is_order_only(self):
        """Order secured without payment collection."""
        return bool(self.has_order and not self.has_payment)

    def duration_minutes(self):
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self):
        return f'<Visit {self.id} rep={self.rep_id} customer={self.customer_id}>'


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    rep_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    order_number = db.Column(db.String(50), unique=True)
    items_json = db.Column(db.Text, default='[]')  # JSON list of {name, qty, price}
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default='pending')  # pending, confirmed, delivered, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def items(self):
        return json.loads(self.items_json or '[]')

    @items.setter
    def items(self, value):
        self.items_json = json.dumps(value)

    def __repr__(self):
        return f'<Order {self.order_number}>'


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    rep_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    day_start = db.Column(db.DateTime)
    day_end = db.Column(db.DateTime)
    start_lat = db.Column(db.Float)
    start_lng = db.Column(db.Float)
    end_lat = db.Column(db.Float)
    end_lng = db.Column(db.Float)
    status = db.Column(db.String(20), default='absent')  # present, absent, half_day
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def hours_worked(self):
        if self.day_start and self.day_end:
            delta = self.day_end - self.day_start
            return round(delta.total_seconds() / 3600, 2)
        return 0.0

    def __repr__(self):
        return f'<Attendance rep={self.rep_id} date={self.attendance_date}>'


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    rep_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    collection_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    cheque_number = db.Column(db.String(50), nullable=False)
    cheque_amount = db.Column(db.Float, nullable=False)
    cheque_date = db.Column(db.Date, nullable=False)
    bank_name = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment cheque={self.cheque_number} amt={self.cheque_amount}>'


class RepLocation(db.Model):
    __tablename__ = 'rep_locations'
    id = db.Column(db.Integer, primary_key=True)
    rep_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_fake_gps = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<RepLocation rep={self.rep_id} lat={self.lat} lng={self.lng}>'
