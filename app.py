from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_bcrypt import Bcrypt
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
import random
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from models import db, User, Item, Category
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG =================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'd6b5f6a4d1c1e3c9b7d9d2f1e8b9c0a4e5d6f7a8b9c0d1e2f3a4b5c6d7e8f9g0h')
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get('SECURITY_PASSWORD_SALT', 'my_precious_salt')

# Handle DATABASE_URL from deployment platforms
db_url = os.environ.get('DATABASE_URL', 'sqlite:///lostfound.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')




# ================= MAIL =================
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'aggnourabhilash12@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'ywkdxgqkybchydcr')
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'


# ================= INIT =================
db.init_app(app)
mail = Mail(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================= EMAIL FUNCTION =================
def send_user_details_email(receiver_email, sender_user, item, action):
    msg = Message(
        subject="Lost & Found Match Found!",
        sender=app.config['MAIL_USERNAME'],
        recipients=[receiver_email]
    )

    msg.body = f"""
Hello,

Someone responded to your post.

Action: {action}
Item: {item.name}

User Details:
Name: {sender_user.first_name} {sender_user.last_name}
Email: {sender_user.email}
Roll Number: {sender_user.roll_number}
Branch: {sender_user.branch}

Please contact them.

- Lost & Found Portal
"""

    try:
        mail.send(msg)
    except Exception as e:
        print("Mail Error:", e)


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = str(random.randint(100000, 999999))

        session.update({
            'otp': otp,
            'email': request.form.get('email'),
            'password': bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8'),
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'roll_number': request.form.get('roll_number'),
            'batch': request.form.get('batch'),
            'course': request.form.get('course'),
            'branch': request.form.get('branch')
        })

        msg = Message("OTP Verification", sender=app.config['MAIL_USERNAME'], recipients=[session['email']])
        msg.body = f"Your OTP is {otp}"

        try:
            mail.send(msg)
        except Exception as e:
            print("Mail Error:", e)
            flash("Email failed", "danger")

        return redirect(url_for('verify_registration'))

    return render_template('register.html')


@app.route('/verify_registration', methods=['GET', 'POST'])
def verify_registration():
    if request.method == 'POST':
        if request.form.get('otp') == session.get('otp'):
            user = User(
                email=session['email'],
                password=session['password'],
                first_name=session['first_name'],
                last_name=session['last_name'],
                roll_number=session['roll_number'],
                batch=session['batch'],
                course=session['course'],
                branch=session['branch'],
                is_verified=True
            )
            db.session.add(user)
            db.session.commit()
            session.clear()
            flash("Account created!", "success")
            return redirect(url_for('login'))

    return render_template('verify_registration.html')


# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()

        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('home_page'))

        flash("Invalid login", "danger")

    return render_template('login.html')


# ================= FORGOT PASSWORD =================
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            token = user.get_reset_token()
            msg = Message("Password Reset Request", sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Hello {user.first_name},\n\nTo reset your password, visit the following link: {url_for('reset_password', token=token, _external=True)}\n\nIf you did not make this request then simply ignore this email and no changes will be made."


            try:
                mail.send(msg)
                flash("Email sent!", "success")
            except:
                flash("Mail error!", "danger")

        return redirect(url_for('login'))

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home_page'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html')



# ================= PROFILE =================
@app.route('/profile')
@login_required
def view_profile():
    return render_template('profile.html')


@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.roll_number = request.form.get('roll_number')
        current_user.batch = request.form.get('batch')
        current_user.course = request.form.get('course')
        current_user.branch = request.form.get('branch')

        file = request.files.get('profile_pic')
        if file and file.filename:
            filename = secure_filename(file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename

        db.session.commit()
        flash("Profile updated!", "success")
        return redirect(url_for('view_profile'))

    return render_template('update_profile.html', user=current_user)



# ================= LOGOUT =================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ================= HOME =================
@app.route('/')
def home_page():
    search = request.args.get('search')
    category_id = request.args.get('category')

    query = Item.query

    if search:
        query = query.filter(Item.name.contains(search) | Item.description.contains(search))
    
    if category_id:
        query = query.filter_by(category_id=category_id)

    items = query.all()
    categories = Category.query.all()

    return render_template('home.html', items=items, categories=categories)



# ================= ADD ITEM =================
@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    categories = Category.query.all()

    if request.method == 'POST':
        file = request.files.get('image')
        filename = 'default.jpg'

        if file and file.filename:
            filename = secure_filename(file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


        date_value = request.form.get('date')
        date_value = datetime.strptime(date_value, "%Y-%m-%d") if date_value else None

        item = Item(
            name=request.form.get('name'),
            description=request.form.get('description'),
            category_id=request.form.get('category'),
            status=request.form.get('status'),
            date=date_value,
            location=request.form.get('location'),
            image_file=filename,
            user_id=current_user.id,
            claimed=0
        )

        db.session.add(item)
        db.session.commit()

        flash("Item added!", "success")
        return redirect(url_for('home_page'))

    return render_template('add_item.html', categories=categories)


# ================= ITEM DETAIL =================
@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)

    # Only owner can edit
    if item.user_id != current_user.id:
        flash("Not allowed", "danger")
        return redirect(url_for('home_page'))

    if request.method == 'POST':
        item.name = request.form.get('name')
        item.description = request.form.get('description')
        item.category_id = request.form.get('category')
        item.status = request.form.get('status')
        item.location = request.form.get('location')

        date_value = request.form.get('date')
        item.date = datetime.strptime(date_value, "%Y-%m-%d") if date_value else None

        db.session.commit()
        flash("Item updated!", "success")

        return redirect(url_for('item_detail', item_id=item.id))

    categories = Category.query.all()
    return render_template('edit_item.html', item=item, categories=categories)


# ================= DELETE =================
@app.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        return redirect(url_for('home_page'))

    db.session.delete(item)
    db.session.commit()

    flash("Item deleted", "success")
    return redirect(url_for('home_page'))


# ================= FOUND =================
@app.route('/mark_found/<int:item_id>', methods=['POST'])
@login_required
def mark_found(item_id):
    item = Item.query.get_or_404(item_id)

    if item.claimed:
        flash("Already resolved!", "warning")
        return redirect(url_for('item_detail', item_id=item.id))

    owner = User.query.get(item.user_id)

    send_user_details_email(owner.email, current_user, item, "FOUND YOUR ITEM")

    item.claimed = 1
    db.session.commit()

    flash("Owner notified!", "success")
    return redirect(url_for('item_detail', item_id=item.id))


# ================= CLAIM =================
@app.route('/mark_lost/<int:item_id>', methods=['POST'])
@login_required
def mark_lost(item_id):
    item = Item.query.get_or_404(item_id)

    if item.claimed:
        flash("Already resolved!", "warning")
        return redirect(url_for('item_detail', item_id=item.id))

    owner = User.query.get(item.user_id)

    send_user_details_email(owner.email, current_user, item, "CLAIMED YOUR ITEM")

    item.claimed = 1
    db.session.commit()

    flash("Owner notified!", "success")
    return redirect(url_for('item_detail', item_id=item.id))


# ================= INIT =================
with app.app_context():
    db.create_all()
    # Seed categories if they don't exist
    if not Category.query.first():
        categories = ['Electronics', 'Documents', 'Books', 'Clothing', 'Keys', 'Wallets', 'Other']
        for cat_name in categories:
            db.session.add(Category(name=cat_name))
        db.session.commit()



if __name__ == '__main__':
    app.run(debug=True)