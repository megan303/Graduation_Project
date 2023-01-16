def frames():
    while True:
        success, frame = camera.read()
        if success:
            try:
                
                ret, buffer = cv2.imencode('.jpg', cv2.flip(frame, 1))
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                pass
        else:
            pass
###############################################################################################################################
def init_predict():
    global camera_mode, mode, frame, show_pic, select
    camera_mode = False
    mode = 1
    frame = None
    show_pic = None
    select = 1
    release_camera()
def release_camera():
    try:
        camera.release()
        cv2.destroyAllWindows()
    except:
        pass
@app.route('/predict_home')
@login_required
def predict_home():
    init_predict()
    return render_template('page.html')

@app.route('/video_feed')
@login_required
def video_feed():
    global camera_mode
    if camera_mode == True:
        return Response(frames(), mimetype = 'multipart/x-mixed-replace; boundary=frame')
    else:
        try: 
            tmp = show_pic
            if tmp.shape[0] != 500: #reshape by rate
                tmp = cv2.resize(tmp, None, fx = 500 /tmp.shape[0],fy= 500 /tmp.shape[0],interpolation=cv2.INTER_LINEAR)
            ret, buffer = cv2.imencode('.jpg', cv2.flip(tmp, 1))
            show = buffer.tobytes()
            
        except:
            tmp = cv2.imread('static/preshow.png')
            ret, buffer = cv2.imencode('.jpg', tmp)
            show = buffer.tobytes()
            
        return Response(show, mimetype = 'multipart/x-mixed-replace;')

@app.route("/setCamera", methods=["POST"])
@login_required
def setCamera():
    global camera, camera_mode, mode
    if request.method == 'POST':
        mode = 0
        try:
            camera.release()
            cv2.destroyAllWindows()
        except:
            pass
        camera_mode = True
        camera = cv2.VideoCapture(0)
    if select == 1:
        return render_template('page.html')
    if select == 2: 
        user = load_user(current_user.id)
        return render_template('record_home.html', show_display_area = '您目前的儲存的位置為: ' + user.user_point)
    if select == 3:
        user = load_user(current_user.id)
        return render_template('predictByrecord_home.html', show_display_area = '您目前的儲存的位置為: ' + user.user_point)