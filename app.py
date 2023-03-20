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
import os
import cv2
import math
import nums_from_string as nfs
import mediapipe as mp
from func import cut_img, find_coor, calculate_distance_for_scale
from PIL import Image
#from gevent import pywsgi

# 創建Flask物件app并初始化
app = Flask(__name__)
pjdir = os.path.abspath(os.path.dirname(__file__))  # 取得目前文件資料夾路徑
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # 設定可上傳圖片字尾
# 結合目前的檔案路徑和static及uploads路徑
UPLOAD_FOLDER = os.path.join(pjdir,  'static', 'uploads')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(pjdir, 'database.sqlite')  # 設置sqlite檔案路徑
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = 'secretkey'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

color_green = (0, 255, 0)
color_red = (0, 0, 255)
color_blue = (255, 0, 0)

mpHands = mp.solutions.hands
hands = mpHands.Hands(min_detection_confidence=0.5,
                      min_tracking_confidence=0.5, max_num_hands=1)

global frame, camera, camera_mode, capture, det
camera_mode = False
frame = None
capture = 0
det = 0

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return UserReister.query.get(int(user_id))


class UserReister(db.Model, UserMixin):  # 記錄使用者資料的資料表
    __tablename__ = 'UserRgeisters'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    user_point = db.Column(db.String(100), nullable=False)
    proportion = db.Column(db.Float(), nullable=True)

    def __init__(self, username, password, user_point, proportion):
        self.username = username
        self.password = password
        self.user_point = user_point
        self.proportion = proportion


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


def allowed_file(filename):  # 檢查上傳圖片是否在可上傳圖片允許列表
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 通過python裝飾器的方法定義路由地址
@app.route("/")
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        password = hashed_password
        user_point = "NONE"
        user_data = UserReister.query.filter_by(username=username).first()
        if user_data:
            flash('此名稱已有使用者註冊，請輸入新的名稱')
            return redirect(url_for('register'))
        else:
            new_user = UserReister(username, password, user_point)
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
                # flash("成功登入!!")
                # return 'Success Thank You'
                return redirect(url_for('select_func'))
            else:
                flash("使用者名稱或密碼錯誤")
                return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    # Logs a user out. (You do not need to pass the actual user.)
    # This will also clean up the remember me cookie if it exists.
    logout_user()
    return redirect(url_for('login'))


@app.route('/select_func', methods=['POST', 'GET'])
@login_required
def select_func():
    user = load_user(current_user.id)
    return render_template('select_func.html', welcome_text="歡迎 " + user.username + " !!")
#######################################################################################


def frames(user):
    global camera_mode, capture, det
    camera_mode = True
    coor = []
    radius = []
    if (det):
        points = user.user_point
        number_list = nfs.get_nums(points)
        for i in range(0, len(number_list), 3):
            coor.append([number_list[i], number_list[i + 1]])
            radius.append(number_list[i + 2])
        #print("det in")
    if camera_mode == True:
        camera = cv2.VideoCapture(1)
        while True:
            success, frame = camera.read()
            #frame = cv2.flip(frame, 1)
            if success:
                if (capture):
                    capture = 0
                    '''
                    if not os.path.exists(app.config['UPLOAD_FOLDER']):  # 如果資料夾不存在，就建立資料夾
                        os.makedirs(app.config['UPLOAD_FOLDER'])
                    filename = user.username + '.jpg'
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    #filee = request.files['img'].read()
                    #npimg = np.frombuffer(frame, np.uint8)
                    #img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
                    coor, radius = find_coor(frame, file_path)
                    points = ""
                    for i in range(0, len(coor)):
                        points = str(coor[i][0]) + "," + str(coor[i]
                                                 [1]) + "," + str(radius[i]) + "|"
                    user.user_point = points
                    db.session.commit()
                    '''
                    filename = user.username + '.jpg'
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    cv2.imwrite(file_path, frame)
                    camera.release()
                if (det):
                    #print("det in2")
                    H = frame.shape[0]
                    W = frame.shape[1]

                    x0, y0 = 0.0, 0.0
                    x9, y9 = 0.0, 0.0
                    cam_distance = 0.0
                    distance = user.propotion
                    scale = 0.0

                    wrist_x = 0  # 腕關節
                    wrist_y = 0
                    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    result = hands.process(img_gray)  # 偵測手

                    if result.multi_hand_landmarks:
                        for handLms in result.multi_hand_landmarks:
                            for i, lm in enumerate(handLms.landmark):
                                xPos = round(lm.x * W)
                                yPos = round(lm.y * H)
                                if i == 0:  # wrist point
                                    wrist_x, wrist_y = xPos, yPos
                                    x0, y0 = lm.x, lm.y
                                elif i == 9:
                                    x9, y9 = lm.x, lm.y
                                if(x0 != 0 and y0 != 0 and x9 != 0 and y9 != 0):
                                    cam_distance = math.sqrt((x0 - x9) ** 2 + (y0 - y9) ** 2)
                                    scale = distance / cam_distance
                        wrist_y = wrist_y + 15
                        for i in range(0, len(coor)):
                            #print("dis:", coor[i])
                            #print("radius:", radius[i])
                            frame = cv2.circle(
                                frame, (wrist_x - coor[i][0], wrist_y + coor[i][1]), radius[i] * scale, color_red, 1)
                            frame = cv2.circle(
                                frame, (wrist_x - coor[i][0], wrist_y + coor[i][1]), 2 * scale, color_blue, 1)
                try:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                except Exception as e:
                    pass
            else:
                pass


def release_camera():
    try:
        camera.release()
        cv2.destroyAllWindows()
    except:
        pass
########################################################################################


@app.route('/select_file', methods=['POST', 'GET'])
@login_required
def select_file():
    if request.method == "POST":
        error = None
        file = request.files['img']
        if file.filename == '':
            flash('請選擇檔案上傳')
            return render_template('select_file.html')
        if not (file and allowed_file(file.filename)):
            flash('請檢查上傳的圖片類型')
            return render_template('select_file.html')
        if not os.path.exists(app.config['UPLOAD_FOLDER']):  # 如果資料夾不存在，就建立資料夾
            os.makedirs(app.config['UPLOAD_FOLDER'])
        else:
            return render_template('uploadfail.html')
        user = load_user(current_user.id)
        filename = secure_filename(file.filename)
        filename = user.username + '.jpg'
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        filee = request.files['img'].read()
        npimg = np.frombuffer(filee, np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        coor, radius = find_coor(img, file_path)
        points = ""
        for i in range(0, len(coor)):
            points = points + str(coor[i][0]) + "," + str(coor[i]
                                                          [1]) + "," + str(radius[i]) + "|"
        print("points:", points)
        distance = calculate_distance_for_scale(filename)
        user.user_point = points
        user.propotion = distance
        db.session.commit()
        return redirect(url_for('show_result'))
    return render_template('select_file.html')


@app.route('/show_result', methods=['GET'])
@login_required
def show_result():
    global camera, camera_mode
    camera_mode = False
    user = load_user(current_user.id)
    path = "/static/uploads/" + user.username + ".jpg"
    return render_template("show_result.html", user_image=path)


@app.route('/video_feed')
@login_required
def video_feed():
    user = load_user(current_user.id)
    global camera_mode
    camera_mode = True
    return Response(frames(user), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/take_photo', methods=['POST', 'GET'])
@login_required
def take_photo():
    global camera_mode, camera
    camera_mode = True
    if request.method == 'POST':
        if request.form.get('click') == 'Capture':
            global capture
            capture = 1
            return redirect(url_for('show_result'))
    return render_template('take_photo.html')


@app.route('/detect', methods=['POST', 'GET'])
@login_required
def detect():
    if request.method == 'POST':
        user = load_user(current_user.id)
        global camera_mode, camera
        camera_mode = True
        if request.form.get('det') == 'Detect':
            global det
            det = not det
    return render_template('detect.html')


if __name__ == '__main__':
    app.run(host="localhost", port=3000)
    app.debug = True
    #server = pywsgi.WSGIServer(("localhost", 3000), app)
    # server.serve_forever()
