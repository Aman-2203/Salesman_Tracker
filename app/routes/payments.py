from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Payment, Customer, User
from app import db
from app.timezone_utils import today_ist
from datetime import datetime, date

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/')
@login_required
def list_payments():
    q = request.args.get('q', '').strip()
    date_filter = request.args.get('date', '').strip()
    rep_filter = request.args.get('rep_id', type=int)

    query = Payment.query
    if current_user.role != 'admin':
        query = query.filter(Payment.rep_id == current_user.id)
    elif rep_filter:
        query = query.filter(Payment.rep_id == rep_filter)

    if date_filter:
        try:
            if '/' in date_filter:
                parts = date_filter.split('/')
                parsed_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
            else:
                parsed_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Payment.collection_date == parsed_date)
        except Exception:
            pass

    if q:
        search_pattern = f'%{q}%'
        query = query.join(Customer).filter(
            db.or_(
                Payment.cheque_number.ilike(search_pattern),
                Customer.name.ilike(search_pattern),
                Payment.bank_name.ilike(search_pattern),
                Payment.notes.ilike(search_pattern)
            )
        )

    payments = query.order_by(Payment.collection_date.desc(), Payment.id.desc()).limit(200).all()
    total = sum(p.cheque_amount for p in payments)
    reps = User.query.filter_by(role='rep', is_active=True).order_by(User.name).all() if current_user.role == 'admin' else []

    return render_template(
        'payments/list.html',
        payments=payments,
        total=total,
        reps=reps,
        selected_q=q,
        selected_date=date_filter,
        selected_rep=rep_filter
    )


@payments_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_payment():
    if current_user.role == 'rep':
        flash('Payment collections can only be recorded during a customer visit.', 'info')
        return redirect(url_for('visits.record_visit'))

    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        if not customer_id:
            flash('Please select a customer.', 'danger')
            return redirect(url_for('payments.new_payment'))

        amounts = request.form.getlist('cheque_amount[]')
        cheque_numbers = request.form.getlist('cheque_number[]')
        cheque_dates = request.form.getlist('cheque_date[]')
        bank_names = request.form.getlist('bank_name[]')

        # Fallback for single scalar submission
        if not amounts and request.form.get('cheque_amount'):
            amounts = [request.form.get('cheque_amount')]
            cheque_numbers = [request.form.get('cheque_number', '')]
            cheque_dates = [request.form.get('cheque_date', '')]
            bank_names = [request.form.get('bank_name', '')]

        notes = request.form.get('notes', '').strip()
        now = today_ist()

        collected_count = 0
        total_collected = 0.0

        for i in range(len(amounts)):
            amt_str = amounts[i].strip() if i < len(amounts) else ''
            if not amt_str:
                continue
            try:
                amt = float(amt_str)
            except (ValueError, TypeError):
                continue
            if amt <= 0:
                continue

            chq_num = cheque_numbers[i].strip() if i < len(cheque_numbers) and cheque_numbers[i] else f'COL-{now.strftime("%Y%m%d")}-{i+1}'
            bank = bank_names[i].strip() if i < len(bank_names) and bank_names[i] else ''

            c_date = now
            if i < len(cheque_dates) and cheque_dates[i]:
                try:
                    raw_date = cheque_dates[i].strip()
                    if '/' in raw_date:
                        parts = raw_date.split('/')
                        c_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                    else:
                        c_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                except Exception:
                    c_date = now

            payment = Payment(
                rep_id=current_user.id,
                customer_id=customer_id,
                collection_date=now,
                cheque_number=chq_num,
                cheque_amount=amt,
                cheque_date=c_date,
                bank_name=bank,
                notes=notes
            )
            db.session.add(payment)
            collected_count += 1
            total_collected += amt

        if collected_count == 0:
            flash('Please enter at least one valid cheque with an amount greater than zero.', 'danger')
        else:
            db.session.commit()
            cheque_word = 'Cheque' if collected_count == 1 else 'Cheques'
            flash(f'{collected_count} {cheque_word} recorded (Total ₹{total_collected:,.2f})!', 'success')
            return redirect(url_for('payments.list_payments'))

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    return render_template('payments/new_payment.html', customers=customers)
