from flask import Flask, render_template, request, jsonify, url_for, redirect, flash, Response, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired, EqualTo
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import webbrowser
import numpy as np
import os, cv2
import math
import mediapipe as mp
from cut_img import cut_img
from PIL import Image

#創建Flask物件app并初始化
app = Flask(__name__)
pjdir = os.path.abspath(os.path.dirname(__file__)) # 取得目前文件資料夾路徑
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # 設定可上傳圖片字尾 
# 結合目前的檔案路徑和static及uploads路徑 
UPLOAD_FOLDER = os.path.join(pjdir,  'static', 'uploads')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(pjdir, 'database.sqlite') # 設置sqlite檔案路徑
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = 'secretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return UserReister.query.get(int(user_id))

class UserReister(db.Model, UserMixin): # 記錄使用者資料的資料表
    __tablename__ = 'UserRgeisters'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    user_img_path = db.Column(db.String(100), nullable=False)
    def __init__(self, username, password, user_img_path):
        self.username = username
        self.password = password
        self.user_img_path = user_img_path

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                        InputRequired(), Length(min=3, max=20)], render_kw={"placeholder": "使用者名稱"})

    password = PasswordField(validators=[
                        InputRequired(), 
                        Length(min=6, max=20),
                        EqualTo('pass_confirm', message='PASSWORD NEED MATCH')], 
                        render_kw={"placeholder": "密碼"})
    
    pass_confirm = PasswordField(validators=[
                        InputRequired(), Length(min=6, max=20)], render_kw={"placeholder": "確認密碼"})
    submit = SubmitField('註冊')
    '''
    def validate_username(self, field):
        if UserReister.query.filter_by(username=field.data).first():
            raise ValidationError('此名稱已有使用者註冊，請輸入新的名稱')
    '''

class LoginForm(FlaskForm):
    username = StringField(validators=[
                        InputRequired(), Length(min=3, max=20)], render_kw={"placeholder": "使用者名稱"})
    password = PasswordField(validators=[
                        InputRequired(), Length(min=6, max=20)], render_kw={"placeholder": "密碼"})
    submit = SubmitField('登入')

def allowed_file(filename): # 檢查上傳圖片是否在可上傳圖片允許列表
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
                

#通過python裝飾器的方法定義路由地址
@app.route("/")
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username=form.username.data
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        password=hashed_password
        user_img_path = "NONE"
        user_data = UserReister.query.filter_by(username=username).first()
        if user_data:
            flash('此名稱已有使用者註冊，請輸入新的名稱')
            return redirect(url_for('register'))
        else:
            new_user = UserReister(username, password, user_img_path)
            db.session.add(new_user)
            db.session.commit()
            flash('註冊成功!!')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = UserReister.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                #flash("成功登入!!")
                #return 'Success Thank You'
                return redirect(url_for('select_func'))
            else:
                flash("使用者名稱或密碼錯誤")
                return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route('/logout',methods=['POST','GET'])
@login_required
def logout():
    #Logs a user out. (You do not need to pass the actual user.)
    # This will also clean up the remember me cookie if it exists.
    logout_user()
    return redirect(url_for('login'))

@app.route('/select_func',methods=['POST','GET'])
@login_required
def select_func():
    user = load_user(current_user.id)
    return render_template('select_func.html', welcome_text = "歡迎 " + user.username + "!!")

@app.route('/select_file',methods=['POST','GET'])
@login_required
def select_file():
    if request.method == "POST":
        file = request.files['img']
        if file.filename == '':
            flash('No selected file')
            return render_template('select_file.html')
        if not (file and allowed_file(file.filename)):
            flash('請檢查上傳的圖片類型, 限png, jpg, jpeg')
            return render_template('select_file.html')
        if not os.path.exists(app.config['UPLOAD_FOLDER']): # 如果資料夾不存在，就建立資料夾
            os.makedirs(app.config['UPLOAD_FOLDER'])
        user = load_user(current_user.id)
        filename = secure_filename(file.filename)
        filename = user.username + '.jpg'
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        filee = request.files['img'].read()
        npimg = np.fromstring(filee, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        img = cut_img(img)
        cv2.imwrite(file_path, img)
        user.user_img_path = file_path
        db.session.commit()
        return redirect(url_for('show_result'))
    return render_template('select_file.html')

@app.route('/show_result', methods=['GET'])
@login_required
def show_result():
    user = load_user(current_user.id)
    path = "/static/uploads/" + user.username + ".jpg"
    print("path: ", path)
    return render_template("show_result.html", user_image=path)

@app.route('/take_photo',methods=['POST','GET'])
@login_required
def take_photo():
    return render_template('take_photo.html')

@app.route('/detect')
@login_required
def detect():
    return render_template('detect.html')

if __name__ == '__main__':
    if not os.path.exists('database.sqlite'):
        db.create_all()
    app.run(host="localhost", port=3000, debug=True)