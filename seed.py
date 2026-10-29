"""
Seed script: Creates default admin, sample reps, and customers.
Run once: python seed.py
"""
from app import create_app, db
from app.models import User, Customer
from datetime import date

app = create_app()

with app.app_context():
    db.create_all()

    # ── Admin ──
    if not User.query.filter_by(email='admin@salesforce.com').first():
        admin = User(name='Admin Manager', email='admin@salesforce.com',
                     phone='+91 98000 00001', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print('[OK] Created admin: admin@salesforce.com / admin123')

    # ── Reps ──
    reps_data = [
        ('Rajesh Kumar', 'rajesh@salesforce.com', '+91 98111 11111'),
        ('Priya Sharma', 'priya@salesforce.com', '+91 98222 22222'),
        ('Amit Singh', 'amit@salesforce.com', '+91 98333 33333'),
    ]

    reps = []
    for name, email, phone in reps_data:
        if not User.query.filter_by(email=email).first():
            rep = User(name=name, email=email, phone=phone, role='rep')
            rep.set_password('rep123')
            db.session.add(rep)
            db.session.flush()
            print(f'[OK] Created rep: {email} / rep123')
            reps.append(rep)
        else:
            reps.append(User.query.filter_by(email=email).first())

    db.session.commit()

    # ── Customers ──
    customers_data = [
        ('Sharma General Store', 'Rohit Sharma', '+91 90001 00001', 'North Zone', 'Mumbai', 19.0760, 72.8777, 0),
        ('Gupta Kirana', 'Suresh Gupta', '+91 90002 00002', 'South Zone', 'Mumbai', 19.0196, 72.8490, 0),
        ('Mehta Supermart', 'Vijay Mehta', '+91 90003 00003', 'East Zone', 'Mumbai', 19.0548, 72.9418, 0),
        ('Patel Wholesale', 'Kiran Patel', '+91 90004 00004', 'West Zone', 'Mumbai', 19.0990, 72.8351, 1),
        ('Singh Provision', 'Harpreet Singh', '+91 90005 00005', 'North Zone', 'Mumbai', 19.1136, 72.8697, 1),
        ('Reddy Mart', 'Venkat Reddy', '+91 90006 00006', 'Central Zone', 'Mumbai', 19.0178, 72.8478, 2),
        ('Khan Stores', 'Iqbal Khan', '+91 90007 00007', 'South Zone', 'Mumbai', 18.9388, 72.8354, 2),
    ]

    for name, contact, phone, area, city, lat, lng, rep_idx in customers_data:
        if not Customer.query.filter_by(name=name).first():
            c = Customer(
                name=name,
                contact_person=contact,
                phone=phone,
                area=area,
                city=city,
                lat=lat,
                lng=lng,
                assigned_rep_id=reps[rep_idx].id if rep_idx < len(reps) else None
            )
            db.session.add(c)
            print(f'[OK] Created customer: {name}')

    db.session.commit()
    print('\nSeed complete! Run: python run.py')
    print('   Admin login: admin@salesforce.com / admin123')
    print('   Rep login:   rajesh@salesforce.com / rep123')
