from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_bcrypt import Bcrypt
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
    LoginManager
)
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from models import db, User, Item, Category, ClaimedItem
from datetime import datetime
import os
import random


# =========================================================
# APP CONFIGURATION
# =========================================================

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static")
)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "d6b5f6a4d1c1e3c9b7d9d2f1e8b9c0a4e5d6f7a8b9c0d1e2f3a4b5c6d7e8f9g0h"
)

app.config["SECURITY_PASSWORD_SALT"] = os.environ.get(
    "SECURITY_PASSWORD_SALT",
    "my_precious_salt"
)


# =========================================================
# DATABASE
# =========================================================

db_url = os.environ.get("DATABASE_URL", "sqlite:///lostfound.db")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280
}

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path,
    "static",
    "images"
)


# =========================================================
# MAIL
# =========================================================

app.config["MAIL_SERVER"] = os.environ.get(
    "MAIL_SERVER",
    "smtp.gmail.com"
)

app.config["MAIL_PORT"] = int(
    os.environ.get("MAIL_PORT", 587)
)

app.config["MAIL_USERNAME"] = os.environ.get(
    "MAIL_USERNAME",
    "lostandfoundportal59@gmail.com"
)

app.config["MAIL_PASSWORD"] = os.environ.get(
    "MAIL_PASSWORD",
    "udoz bgsp qvqa ptgg"
)

app.config["MAIL_USE_TLS"] = (
    os.environ.get("MAIL_USE_TLS", "True").lower() == "true"
)
# =========================================================
# INITIALIZE EXTENSIONS
# =========================================================

db.init_app(app)

mail = Mail(app)

bcrypt = Bcrypt(app)

login_manager = LoginManager(app)

login_manager.login_view = "login"


# =========================================================
# LOGIN MANAGER
# =========================================================

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        print("User loading error:", e)
        return None


# =========================================================
# EMAIL FUNCTION
# =========================================================

def send_user_details_email(
    receiver_email,
    sender_user,
    item,
    action
):
    """
    Sends an email to the owner when somebody
    responds to their lost/found item.

    Email errors are caught so they don't crash
    the application.
    """

    if not app.config["MAIL_USERNAME"]:
        print("Mail not configured. Skipping email.")
        return

    try:
        msg = Message(
            subject="Lost & Found Match Found!",
            sender=app.config["MAIL_USERNAME"],
            recipients=[receiver_email]
        )

        msg.body = f"""
Hello,

Someone responded to your post.

Action: {action}
Item: {item.name}

User Details:

Name: {sender_user.first_name or ''} {sender_user.last_name or ''}
Email: {sender_user.email}
Roll Number: {sender_user.roll_number or 'Not provided'}
Branch: {sender_user.branch or 'Not provided'}
Mobile Number: {sender_user.mobile_number or 'Not provided'}

Please contact them.

- Lost & Found Portal
"""

        mail.send(msg)

    except Exception as e:
        print("Mail Error:", e)


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        roll_number = request.form.get("roll_number", "").strip()
        batch = request.form.get("batch", "").strip()
        course = request.form.get("course", "").strip()
        branch = request.form.get("branch", "").strip()
        mobile_number = request.form.get("mobile_number", "").strip()
        password = request.form.get("password", "")

        print("=" * 60)
        print("REGISTRATION FORM DATA")
        print("First Name  :", first_name)
        print("Last Name   :", last_name)
        print("Email       :", email)
        print("Roll Number :", roll_number)
        print("Batch       :", batch)
        print("Course      :", course)
        print("Branch      :", branch)
        print("Mobile      :", mobile_number)
        print("Form Keys   :", list(request.form.keys()))
        print("=" * 60)

        if not first_name or not last_name:
            flash("Please enter your first and last name.", "danger")
            return render_template("register.html")
        if not email:
            flash("Please enter your email address.", "danger")
            return render_template("register.html")
        if not roll_number:
            flash("Please enter your roll number.", "danger")
            return render_template("register.html")
        if not batch:
            flash("Please enter your batch.", "danger")
            return render_template("register.html")
        if not course:
            flash("Please select your course.", "danger")
            return render_template("register.html")
        if not branch:
            flash("Please select your branch.", "danger")
            return render_template("register.html")
        if not mobile_number:
            flash("Please enter your mobile number.", "danger")
            return render_template("register.html")
        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            flash("Password must be at least 8 characters and contain both letters and numbers.", "danger")
            return render_template("register.html")

        try:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("This email is already registered. Please login.", "warning")
                return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            print("EMAIL CHECK ERROR:", repr(e))
            flash("Database error while checking your email.", "danger")
            return render_template("register.html")

        try:
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        except Exception as e:
            print("PASSWORD HASH ERROR:", repr(e))
            flash("Unable to create your password.", "danger")
            return render_template("register.html")

        otp = str(random.randint(100000, 999999))
        session["registration_otp"] = otp
        session["registration_data"] = {
            "email": email,
            "password": hashed_password,
            "first_name": first_name,
            "last_name": last_name,
            "roll_number": roll_number,
            "batch": batch,
            "course": course,
            "branch": branch,
            "mobile_number": mobile_number
        }

        if not app.config["MAIL_USERNAME"] or not app.config["MAIL_PASSWORD"]:
            session.pop("registration_otp", None)
            session.pop("registration_data", None)
            flash("Email service is not configured. Set MAIL_USERNAME and MAIL_PASSWORD.", "danger")
            return render_template("register.html")

        try:
            msg = Message(
                subject="Lost & Found - Email Verification OTP",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )
            msg.body = f"""Hello {first_name},

Your Lost & Found Portal verification OTP is:

{otp}

This OTP is required to complete your registration.
Please do not share it with anyone.

- Lost & Found Portal
"""
            mail.send(msg)
            print("OTP EMAIL SENT:", email)
            flash("OTP has been sent to your email address.", "success")
            return redirect(url_for("verify_registration"))
        except Exception as e:
            print("OTP EMAIL ERROR:", repr(e))
            session.pop("registration_otp", None)
            session.pop("registration_data", None)
            flash("Unable to send OTP email. Please check your email settings.", "danger")
            return render_template("register.html")

    return render_template("register.html")



# =========================================================
# VERIFY REGISTRATION OTP
# =========================================================

# =========================================================
# VERIFY REGISTRATION OTP
# =========================================================

@app.route("/verify_registration", methods=["GET", "POST"])
def verify_registration():

    # ---------------------------------------------------------
    # CHECK REGISTRATION SESSION
    # ---------------------------------------------------------

    if "registration_otp" not in session or "registration_data" not in session:

        flash(
            "Registration session expired. Please register again.",
            "danger"
        )

        return redirect(url_for("register"))


    # ---------------------------------------------------------
    # GET REQUEST
    # ---------------------------------------------------------

    if request.method == "GET":

        return render_template(
            "verify_registration.html"
        )


    # ---------------------------------------------------------
    # POST REQUEST
    # ---------------------------------------------------------

    entered_otp = request.form.get(
        "otp",
        ""
    ).strip()

    stored_otp = str(
        session.get("registration_otp")
    )

    registration_data = session.get(
        "registration_data"
    )


    # ---------------------------------------------------------
    # CHECK OTP
    # ---------------------------------------------------------

    if not entered_otp:

        flash(
            "Please enter the 6-digit OTP.",
            "danger"
        )

        return render_template(
            "verify_registration.html"
        )


    if not entered_otp.isdigit() or len(entered_otp) != 6:

        flash(
            "Please enter a valid 6-digit OTP.",
            "danger"
        )

        return render_template(
            "verify_registration.html"
        )


    if entered_otp != stored_otp:

        flash(
            "Invalid OTP. Please enter the correct OTP.",
            "danger"
        )

        return render_template(
            "verify_registration.html"
        )


    # ---------------------------------------------------------
    # OTP IS CORRECT
    # ---------------------------------------------------------

    try:

        # Check email again before creating account

        existing_user = User.query.filter_by(
            email=registration_data["email"]
        ).first()


        if existing_user:

            session.pop(
                "registration_otp",
                None
            )

            session.pop(
                "registration_data",
                None
            )

            flash(
                "This email is already registered. Please login.",
                "warning"
            )

            return redirect(
                url_for("login")
            )


        # -----------------------------------------------------
        # CREATE USER
        # -----------------------------------------------------

        user = User(

            email=registration_data["email"],

            password=registration_data["password"],

            first_name=registration_data["first_name"],

            last_name=registration_data["last_name"],

            roll_number=registration_data["roll_number"],

            batch=registration_data["batch"],

            course=registration_data["course"],

            branch=registration_data["branch"],

            mobile_number=registration_data["mobile_number"],

            is_verified=True
        )


        db.session.add(user)

        db.session.commit()


        # -----------------------------------------------------
        # CLEAR TEMPORARY REGISTRATION DATA
        # -----------------------------------------------------

        session.pop(
            "registration_otp",
            None
        )

        session.pop(
            "registration_data",
            None
        )


        print(
            "REGISTRATION VERIFIED SUCCESS:",
            user.email
        )


        flash(
            "Email verified successfully! "
            "Your account has been created. Please login.",
            "success"
        )


        return redirect(
            url_for("login")
        )


    except Exception as e:

        db.session.rollback()


        print("=" * 60)
        print("OTP VERIFICATION DATABASE ERROR")
        print(repr(e))
        print("=" * 60)


        flash(
            "Unable to create your account. Please try again.",
            "danger"
        )


        return render_template(
            "verify_registration.html"
        )

    # =====================================================
    # GET REQUEST
    # =====================================================

    return render_template(
        "verify_registration.html"
    )
# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        try:

            user = User.query.filter_by(
                email=email
            ).first()

            if user and bcrypt.check_password_hash(
                user.password,
                password
            ):

                login_user(user)

                return redirect(
                    url_for("home_page")
                )

            flash(
                "Invalid email or password.",
                "danger"
            )

        except Exception as e:

            print("Login error:", e)

            db.session.rollback()

            flash(
                "Unable to login right now. Please try again.",
                "danger"
            )

    return render_template("login.html")


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        try:

            user = User.query.filter_by(
                email=email
            ).first()

            if user:

                token = user.get_reset_token()

                reset_link = url_for(
                    "reset_password",
                    token=token,
                    _external=True
                )

                if app.config["MAIL_USERNAME"]:

                    msg = Message(
                        "Password Reset Request",
                        sender=app.config["MAIL_USERNAME"],
                        recipients=[email]
                    )

                    msg.body = (
                        f"Hello {user.first_name},\n\n"
                        f"To reset your password, visit:\n\n"
                        f"{reset_link}\n\n"
                        "If you did not make this request, "
                        "you can ignore this email."
                    )

                    try:

                        mail.send(msg)

                        flash(
                            "Password reset email sent!",
                            "success"
                        )

                    except Exception as e:

                        print(
                            "Password reset mail error:",
                            e
                        )

                        flash(
                            "Unable to send reset email.",
                            "danger"
                        )

                else:

                    flash(
                        "Mail service is not configured.",
                        "warning"
                    )

            else:

                # Do not reveal whether an account exists.
                flash(
                    "If that email exists, a reset link "
                    "has been sent.",
                    "info"
                )

        except Exception as e:

            print("Forgot password error:", e)

            db.session.rollback()

            flash(
                "Something went wrong. Please try again.",
                "danger"
            )

        return redirect(
            url_for("login")
        )

    return render_template("forgot_password.html")


# =========================================================
# RESET PASSWORD
# =========================================================

@app.route(
    "/reset_password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    if current_user.is_authenticated:

        return redirect(
            url_for("home_page")
        )

    try:

        user = User.verify_reset_token(token)

    except Exception as e:

        print("Reset token error:", e)

        user = None

    if user is None:

        flash(
            "That is an invalid or expired token.",
            "warning"
        )

        return redirect(
            url_for("forgot_password")
        )


    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "danger"
            )

            return render_template(
                "reset_password.html",
                token=token
            )

        try:

            hashed_password = (
                bcrypt
                .generate_password_hash(password)
                .decode("utf-8")
            )

            user.password = hashed_password

            db.session.commit()

            flash(
                "Your password has been updated! "
                "You can now login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as e:

            db.session.rollback()

            print("Password reset error:", e)

            flash(
                "Unable to reset password.",
                "danger"
            )

    return render_template(
        "reset_password.html",
        token=token
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
@login_required
def view_profile():

    return render_template(
        "profile.html"
    )


# =========================================================
# UPDATE PROFILE
# =========================================================

@app.route(
    "/update_profile",
    methods=["GET", "POST"]
)
@login_required
def update_profile():

    if request.method == "POST":

        current_user.first_name = request.form.get(
            "first_name"
        )

        current_user.last_name = request.form.get(
            "last_name"
        )

        current_user.roll_number = request.form.get(
            "roll_number"
        )

        current_user.batch = request.form.get(
            "batch"
        )

        current_user.course = request.form.get(
            "course"
        )

        current_user.branch = request.form.get(
            "branch"
        )

        current_user.mobile_number = request.form.get(
            "mobile_number"
        )


        # -------------------------------------------------
        # Profile picture
        # -------------------------------------------------

        file = request.files.get(
            "profile_pic"
        )

        if file and file.filename:

            filename = secure_filename(
                file.filename
            )

            os.makedirs(
                app.config["UPLOAD_FOLDER"],
                exist_ok=True
            )

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            current_user.profile_pic = filename


        # -------------------------------------------------
        # Student ID card
        # -------------------------------------------------

        id_card = request.files.get(
            "student_id_card"
        )

        if id_card and id_card.filename:

            filename = secure_filename(
                id_card.filename
            )

            os.makedirs(
                app.config["UPLOAD_FOLDER"],
                exist_ok=True
            )

            id_card.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            current_user.student_id_card = filename


        try:

            db.session.commit()

            flash(
                "Profile updated!",
                "success"
            )

            return redirect(
                url_for("view_profile")
            )

        except Exception as e:

            db.session.rollback()

            print("Profile update error:", e)

            flash(
                "Unable to update profile.",
                "danger"
            )


    return render_template(
        "update_profile.html",
        user=current_user
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("login")
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home_page():

    search = request.args.get(
        "search"
    )

    category_id = request.args.get(
        "category"
    )

    query = Item.query

    if search:

        query = query.filter(
            Item.name.contains(search)
            |
            Item.description.contains(search)
        )

    if category_id:

        query = query.filter_by(
            category_id=category_id
        )

    try:

        items = query.all()

        categories = Category.query.all()

    except Exception as e:

        print("Home database error:", e)

        items = []

        categories = []


    return render_template(
        "home.html",
        items=items,
        categories=categories
    )


# =========================================================
# ADD ITEM
# =========================================================

@app.route(
    "/add_item",
    methods=["GET", "POST"]
)
@login_required
def add_item():

    categories = Category.query.all()

    if request.method == "POST":

        file = request.files.get(
            "image"
        )

        filename = "default.jpg"

        if file and file.filename:

            filename = secure_filename(
                file.filename
            )

            os.makedirs(
                app.config["UPLOAD_FOLDER"],
                exist_ok=True
            )

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )


        date_value = request.form.get(
            "date"
        )

        if date_value:

            try:

                date_value = datetime.strptime(
                    date_value,
                    "%Y-%m-%d"
                )

            except ValueError:

                flash(
                    "Invalid date.",
                    "danger"
                )

                return render_template(
                    "add_item.html",
                    categories=categories
                )

        else:

            date_value = None


        try:

            item = Item(
                name=request.form.get("name"),
                description=request.form.get(
                    "description"
                ),
                category_id=request.form.get(
                    "category"
                ),
                status=request.form.get(
                    "status"
                ),
                date=date_value,
                location=request.form.get(
                    "location"
                ),
                image_file=filename,
                user_id=current_user.id,
                claimed=0
            )

            db.session.add(item)

            db.session.commit()

            flash(
                "Item added!",
                "success"
            )

            return redirect(
                url_for("home_page")
            )

        except Exception as e:

            db.session.rollback()

            print("Add item error:", e)

            flash(
                "Unable to add item.",
                "danger"
            )


    return render_template(
        "add_item.html",
        categories=categories
    )


# =========================================================
# ITEM DETAIL
# =========================================================

@app.route(
    "/item/<int:item_id>"
)
def item_detail(item_id):

    item = Item.query.get_or_404(
        item_id
    )

    return render_template(
        "item_detail.html",
        item=item
    )


# =========================================================
# EDIT ITEM
# =========================================================

@app.route(
    "/edit_item/<int:item_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_item(item_id):

    item = Item.query.get_or_404(
        item_id
    )


    # Only owner can edit

    if item.user_id != current_user.id:

        flash(
            "Not allowed.",
            "danger"
        )

        return redirect(
            url_for("home_page")
        )


    if request.method == "POST":

        item.name = request.form.get(
            "name"
        )

        item.description = request.form.get(
            "description"
        )

        item.category_id = request.form.get(
            "category"
        )

        item.status = request.form.get(
            "status"
        )

        item.location = request.form.get(
            "location"
        )


        date_value = request.form.get(
            "date"
        )

        if date_value:

            try:

                item.date = datetime.strptime(
                    date_value,
                    "%Y-%m-%d"
                )

            except ValueError:

                flash(
                    "Invalid date.",
                    "danger"
                )

                return render_template(
                    "edit_item.html",
                    item=item,
                    categories=Category.query.all()
                )

        else:

            item.date = None


        try:

            db.session.commit()

            flash(
                "Item updated!",
                "success"
            )

            return redirect(
                url_for(
                    "item_detail",
                    item_id=item.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "Edit item error:",
                e
            )

            flash(
                "Unable to update item.",
                "danger"
            )


    categories = Category.query.all()

    return render_template(
        "edit_item.html",
        item=item,
        categories=categories
    )


# =========================================================
# DELETE ITEM
# =========================================================

@app.route(
    "/delete_item/<int:item_id>",
    methods=["POST"]
)
@login_required
def delete_item(item_id):

    item = Item.query.get_or_404(
        item_id
    )


    if item.user_id != current_user.id:

        flash(
            "Not allowed.",
            "danger"
        )

        return redirect(
            url_for("home_page")
        )


    try:

        db.session.delete(item)

        db.session.commit()

        flash(
            "Item deleted.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print(
            "Delete item error:",
            e
        )

        flash(
            "Unable to delete item.",
            "danger"
        )


    return redirect(
        url_for("home_page")
    )


# =========================================================
# MARK FOUND
# =========================================================

@app.route(
    "/mark_found/<int:item_id>",
    methods=["POST"]
)
@login_required
def mark_found(item_id):

    item = Item.query.get_or_404(
        item_id
    )


    if item.claimed:

        flash(
            "Already resolved!",
            "warning"
        )

        return redirect(
            url_for(
                "item_detail",
                item_id=item.id
            )
        )


    owner = User.query.get(
        item.user_id
    )


    if owner:

        send_user_details_email(
            owner.email,
            current_user,
            item,
            "FOUND YOUR ITEM"
        )


    try:

        item.claimed = 1

        claimed_item = ClaimedItem(
            item_id=item.id,
            claimer_id=current_user.id
        )

        db.session.add(
            claimed_item
        )

        db.session.commit()

        flash(
            "Owner notified!",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print(
            "Mark found error:",
            e
        )

        flash(
            "Unable to mark item as found.",
            "danger"
        )


    return redirect(
        url_for(
            "item_detail",
            item_id=item.id
        )
    )


# =========================================================
# MARK LOST / CLAIM
# =========================================================

@app.route(
    "/mark_lost/<int:item_id>",
    methods=["POST"]
)
@login_required
def mark_lost(item_id):

    item = Item.query.get_or_404(
        item_id
    )


    if item.claimed:

        flash(
            "Already resolved!",
            "warning"
        )

        return redirect(
            url_for(
                "item_detail",
                item_id=item.id
            )
        )


    owner = User.query.get(
        item.user_id
    )


    if owner:

        send_user_details_email(
            owner.email,
            current_user,
            item,
            "CLAIMED YOUR ITEM"
        )


    try:

        item.claimed = 1

        claimed_item = ClaimedItem(
            item_id=item.id,
            claimer_id=current_user.id
        )

        db.session.add(
            claimed_item
        )

        db.session.commit()

        flash(
            "Owner notified!",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print(
            "Mark lost error:",
            e
        )

        flash(
            "Unable to claim item.",
            "danger"
        )


    return redirect(
        url_for(
            "item_detail",
            item_id=item.id
        )
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():

    try:

        db.create_all()

        # Seed categories if database is empty

        if not Category.query.first():

            categories = [
                "Electronics",
                "Documents",
                "Books",
                "Clothing",
                "Keys",
                "Wallets",
                "Other"
            ]

            for cat_name in categories:

                db.session.add(
                    Category(
                        name=cat_name
                    )
                )

            db.session.commit()

    except Exception as e:

        print(
            "Database initialization error:",
            e
        )

        db.session.rollback()


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )