from flask import Flask ,render_template,redirect,url_for,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, login_required, LoginManager,logout_user,current_user
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,EmailField,IntegerField
from wtforms.validators import InputRequired,Length,ValidationError ,NumberRange
from flask_bcrypt import Bcrypt
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
app =Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY']='keykey'
db=SQLAlchemy(app)
bcrypt=Bcrypt(app)
#تذكر المستخدم بlogin manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
class User(db.Model,UserMixin):
    id=db.Column(db.Integer,primary_key=True)
    first_name=db.Column(db.String(35),nullable=False)
    last_name=db.Column(db.String(35),nullable=False)
    age =db.Column(db.Integer, nullable=False)
    username=db.Column(db.String(35),nullable=False,unique=True) #يمنع استخدم نفس الاسم او ايميل
    email=db.Column(db.String(50),nullable=False,unique=True)
    password=db.Column(db.String(128),nullable=False)
class Product(db.Model):
    id=db.Column(db.Integer,primary_key=True) # خاص به يمنع تكرر idكل منتج عنده 
    image =db.Column(db.String(100))
    name=db.Column(db.String(100),nullable=False)#يمنع ان يكون فارغ
    price=db.Column(db.Float,nullable=False)
    descripition=db.Column(db.String(250))
class RegisterForm(FlaskForm):
    first_name = StringField(validators=[InputRequired(),Length(min=3,max=25)],render_kw={"placeholder":"first_name"})
    last_name = StringField(validators=[InputRequired(),Length(min=3,max=25)],render_kw={"placeholder":"last_name"})
    age = IntegerField(validators=[InputRequired(), NumberRange(min=1, max=120)], render_kw={"placeholder": "age"})
    username= StringField(validators=[InputRequired(),Length(min=3,max=25)],render_kw={"placeholder":"username"})
    email=EmailField(validators=[InputRequired(),Length(min=5,max=50)],render_kw={"placeholder":"email"})
    password=PasswordField(validators=[InputRequired(),Length(min=6,max=20)], render_kw={"placeholder": "password"})
    submit=SubmitField("Register")   
    def validate_username(self,username):  #اذ كان يوجد اسم مكرر فلا يقبل ذالك
        existing_user=User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError("change username in other name")
class LoginForm(FlaskForm): 
    username=StringField(validators=[InputRequired(),Length(min=3,max=25)],render_kw={"placeholder":"username"})
    password=PasswordField(validators=[InputRequired(),Length(min=6,max=20)], render_kw={"placeholder": "password"})
    submit=SubmitField("login")
@app.route("/") 
def home():
    products = Product.query.all()
    return render_template('home.html', products=products)
@app.route('/login',methods=['GET','POST'])
def login(): 
     form=LoginForm()
     if form.validate_on_submit():
        user= User.query.filter_by(username=form.username.data).first() #تحقق اذا كان يوجد الاسم في التخزين
        if user and bcrypt.check_password_hash(user.password, form.password.data):#اذ كان كلمة سر صحيحة يسجل
            login_user(user)
            return redirect(url_for('dash'))
        else:
           return render_template('login.html',form=form , error='Invalid username or password')   
     return render_template('login.html',form=form)
@app.route('/dash',methods=['GET','POST'])
@login_required  
def dash():
    products = Product.query.all()
    return render_template('dash.html', products=products) #دخول الى الصفحة
@app.route('/logout',methods=['GETt','POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))
@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
     hashed_password= bcrypt.generate_password_hash(form.password.data).decode('utf-8')   #تشفير 
     new_user=User(first_name=form.first_name.data, last_name=form.last_name.data, age=form.age.data,username=form.username.data, email=form.email.data ,password=hashed_password)
     db.session.add(new_user)
     db.session.commit()
     login_user(new_user)
     return redirect(url_for('dash'))
    return render_template('register.html',form=form)
@app.route('/product/<int:product_id>')     
def product_detail(product_id):
    product=Product.query.get(product_id) 
    return render_template('product.html',product=product)
class AdminModelView(ModelView):
    def is_accessible(self): 
        return current_user.is_authenticated and current_user.username == "admin" 
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))
admin=Admin(app)
admin.add_view(AdminModelView(Product,db.session))  
admin.add_view(AdminModelView(User,db.session))  
@app.route("/about")
def about():
    return render_template("about.html")

#السلة
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:#sesion its  cookies or هو ذاكرة مخزنة لكل شخص
        session['cart'] = {}
    cart = session['cart']
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1
    session['cart'] = cart
    return redirect(url_for('dash'))
@app.route('/cart')#صناعة السلة
def cart():
    cart = session.get('cart', {})
    products = []
    total = 0

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))
        if product:
            subtotal = product.price * quantity
            total += subtotal
            products.append({'product': product,'quantity': quantity,'subtotal': subtotal})
    return render_template('cart.html', products=products, total=total)
@app.route('/remove_from_cart/<int:product_id>') #حذف داخل السلة
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart:
        cart.pop(str(product_id))
    session['cart'] = cart
    return redirect(url_for('cart'))
@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))
@app.route('/checkout')
#تاكيد الطلب
@login_required
def checkout():
    cart = session.get('cart', {})
    total = 0
    items = []
    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))
        if product:
            subtotal = product.price * quantity
            total += subtotal
        items.append({'product': product,'quantity': quantity,'subtotal': subtotal })
    return render_template('checkout.html', items=items, total=total)
@app.route('/confirm_order', methods=['POST'])
 # اتمام الطلب وتفريغ السلة
@login_required
def confirm_order():
    session.pop('cart', None) 
    return render_template('success.html')
if __name__=="__main__":
 with app.app_context():
    db.create_all()
 app.run(debug=True)
