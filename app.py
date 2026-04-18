from flask import Flask, render_template, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, login_required, LoginManager, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, IntegerField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange
from flask_bcrypt import Bcrypt
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'keykey'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================= MODELS =================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(35), nullable=False)
    last_name = db.Column(db.String(35), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(35), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(100))
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    descripition = db.Column(db.String(250))


# ================= FORMS =================
class RegisterForm(FlaskForm):
    first_name = StringField(validators=[InputRequired(), Length(min=3, max=25)])
    last_name = StringField(validators=[InputRequired(), Length(min=3, max=25)])
    age = IntegerField(validators=[InputRequired(), NumberRange(min=1, max=120)])
    username = StringField(validators=[InputRequired(), Length(min=3, max=25)])
    email = EmailField(validators=[InputRequired(), Length(min=5, max=50)])
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)])
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError("Username already exists")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=3, max=25)])
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)])
    submit = SubmitField("Login")


# ================= ROUTES =================

@app.route("/")
def home():
    products = Product.query.all()
    return render_template('dash.html', products=products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dash'))
        else:
            return render_template('login.html', form=form, error='Invalid credentials')

    return render_template('login.html', form=form)


@app.route('/dash')
@login_required
def dash():
    products = Product.query.all()
    return render_template('dash.html', products=products)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            age=form.age.data,
            username=form.username.data,
            email=form.email.data,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('dash'))

    return render_template('register.html', form=form)


# ================= PRODUCT =================
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get(product_id)
    return render_template('product.html', product=product)


# ================= ADMIN =================
class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.username == "admin"

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))


admin = Admin(app)
admin.add_view(AdminModelView(Product, db.session))
admin.add_view(AdminModelView(User, db.session))


# ================= CART =================
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    session['cart'] = cart
    return redirect(url_for('dash'))


@app.route('/cart')
@login_required
def cart():
    cart = session.get('cart', {})
    products = []
    total = 0

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))

        if product:
            subtotal = product.price * quantity
            total += subtotal

            products.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })

    return render_template('cart.html', products=products, total=total)


@app.route('/update_cart/<int:product_id>/<action>')
@login_required
def update_cart(product_id, action):
    cart = session.get('cart', {})
    pid = str(product_id)

    if pid not in cart:
        cart[pid] = 0

    if action == "increase":
        cart[pid] += 1

    elif action == "decrease":
        cart[pid] -= 1
        if cart[pid] <= 0:
            del cart[pid]

    session['cart'] = cart
    session.modified = True

    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})

    if str(product_id) in cart:
        cart.pop(str(product_id))

    session['cart'] = cart
    return redirect(url_for('cart'))


# ================= FIXED CHECKOUT FLOW =================

@app.route('/checkout')
@login_required
def checkout():
    return redirect(url_for('cart'))


@app.route('/confirm_order', methods=['POST'])
@login_required
def confirm_order():

    name = request.form.get('name')
    phone = request.form.get('phone')
    address = request.form.get('address')
    city = request.form.get('city')

    print("🚚 NEW ORDER")
    print(name, phone, address, city)

    session.pop('cart', None)

    return render_template('cart.html')


@app.route('/success')
def success():
    return "<h2>🎉 Order Confirmed! We will contact you 📞</h2>"


# ================= RUN =================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
