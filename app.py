from flask import Flask ,render_template,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, login_required, LoginManager,logout_user
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,EmailField
from wtforms.validators import InputRequired,Length,ValidationError
from flask_bcrypt import Bcrypt
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
    age=db.Column(db.String(3),nullable=False)
    username=db.Column(db.String(35),nullable=False,unique=True) #يمنع استخدم نفس الاسم او ايميل
    email=db.Column(db.String(35),nullable=False)
    password=db.Column(db.String(128),nullable=False)
class RegisterForm(FlaskForm):
    first_name = StringField(validators=[InputRequired(),Length(min=3,max=25)],render_kw={"placeholder":"first_name"})
    last_name = StringField(validators=[InputRequired(),Length(min=3,max=25)],render_kw={"placeholder":"last_name"})
    age = StringField(validators=[InputRequired(),Length(min=1,max=3)],render_kw={"placeholder":"age"})
    username= StringField(validators=[InputRequired(),Length(min=6,max=25)],render_kw={"placeholder":"username"})
    email=EmailField(validators=[InputRequired(),Length(min=5,max=25)],render_kw={"placeholder":"email"})
    password=PasswordField(validators=[InputRequired(),Length(min=6,max=20)], render_kw={"placeholder": "password"})
    submit=SubmitField("Register")   
    def validate_username(self,username):  #اذ كان يوجد اسم مكرر فلا يقبل ذالك
        existing_user=User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError("change username in other name")
class LoginForm(FlaskForm): 
    username=StringField(validators=[InputRequired(),Length(min=6,max=25)],render_kw={"placeholder":"username"})
    password=PasswordField(validators=[InputRequired(),Length(min=6,max=20)], render_kw={"placeholder": "password"})
    submit=SubmitField("login")
@app.route("/") 
def home():
    return render_template('home.html')
@app.route('/login',methods=['GET','POST'])
def login(): 
     form=LoginForm()
     if form.validate_on_submit():
        user= User.query.filter_by(username=form.username.data).first() #تحقق اذا كان يوجد الاسم في التخزين
        if user: 
         if bcrypt.check_password_hash(user.password, form.password.data):#اذ كان كلمة سر صحيحة يسجل
            login_user(user)
            return redirect(url_for('dash'))
        else:
           return render_template('login.html',form=form , error='user or password is wrong')   
     return render_template('login.html',form=form)
@app.route('/dash',methods=['GET','POST'])
@login_required  
def dash():
    return render_template('dash.html') #دخول الى الصفحة
@app.route('/logout',methods=['get','post'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
     hashed_password= bcrypt.generate_password_hash(form.password.data).decode('utf-8')   #تشفير 
     new_user=User(first_name=form.first_name.data, last_name=form.last_name.data, age=form.age.data,username=form.username.data, email=form.email.data ,password=hashed_password)
     db.session.add(new_user)
     db.session.commit()
     return redirect(url_for('login'))
    return render_template('register.html',form=form)
@app.route("/about")
def about():
    return render_template("about.html")
if __name__=="__main__":
    app.run(debug=True)
