import numpy as np
import os
import cv2
import pathlib
import math
import mediapipe as mp
from PIL import Image

color_green = (0, 255, 0)
color_red = (0, 0, 255)
color_blue = (255, 0, 0)
low_bound = 30
upper_bound = 200

#img = cv2.imread('static\\uploads\\capture0.jpg')
pjdir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(pjdir,  'static', 'uploads')


def cut_img(img):
    print("img type: ", type(img))
    mpHands = mp.solutions.hands
    hands = mpHands.Hands(min_detection_confidence=0.5,
                          min_tracking_confidence=0.5, max_num_hands=1)
    #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(img)
    print("in")
    if result.multi_hand_landmarks:
        h = img.shape[0]
        w = img.shape[1]
        thumb_x = 0
        thumb_y = 0
        mid_x = 0
        mid_y = 0
        pinky_x = 0
        pinky_y = 0
        print("in1")
        for handLms in result.multi_hand_landmarks:
            for i, lm in enumerate(handLms.landmark):
                xPos = round(lm.x * w)
                yPos = round(lm.y * h)
                if i == 4:  # thumb
                    thumb_x = xPos
                    thumb_y = yPos
                if i == 12:  # middle finger
                    mid_x = xPos
                    mid_y = yPos
                if i == 20:  # pinky
                    pinky_x = xPos
                    pinky_y = yPos
        c = 13
        start_y = mid_y - c
        end_y = mid_y + 400
        print("in2")
        if result.multi_handedness[0].classification[0].label == "Left":  # right hand
            start_x = pinky_x - c
            end_x = thumb_x + c
            new_img = img[start_y:end_y, start_x:end_x]
        else:  # left hand
            start_x = thumb_x - c
            end_x = pinky_x + c
            new_img = img[start_y:end_y, start_x:end_x]
        print("Work!")
        print("new_img_type: ", type(new_img))
        return new_img


def find_coor(img, file_path):
    #cv2.imshow("img2", img)
    print("ori_img_type: ", type(img))
    img = cut_img(img)
    cv2.imwrite("new_img1.jpg", img)
    print("cut_img_type: ", type(img))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #cv2.imshow("img2", gray)
    canny_img = cv2.Canny(gray, low_bound, upper_bound)
    circles = cv2.HoughCircles(canny_img, cv2.HOUGH_GRADIENT, 1,
                               20, param1=120, param2=30, minRadius=5, maxRadius=50)

    mpHands = mp.solutions.hands
    hands = mpHands.Hands(min_detection_confidence=0.5,
                          min_tracking_confidence=0.5, max_num_hands=1)
    result = hands.process(img)  # 偵測手

    coor = []
    radius = []
    #print("radius:", radius, "coor:", coor)
    if result.multi_hand_landmarks:
        print("in")
        H = img.shape[0]
        W = img.shape[1]
        wrist_x = 0  # 腕關節
        wrist_y = 0
        for handLms in result.multi_hand_landmarks:
            for i, lm in enumerate(handLms.landmark):
                xPos = round(lm.x * W)
                yPos = round(lm.y * H)
                if i == 0:
                    wrist_x = xPos
                    wrist_y = yPos
        wrist_y = wrist_y + 15
        for circle in circles[0]:
            # 座標行列
            x = int(circle[0])
            y = int(circle[1])
            r = int(circle[2])  # 半徑
            rel_x = abs(x - wrist_x)
            rel_y = abs(y - wrist_y)
            img = cv2.circle(img, (x, y), r, color_red, 1)
            img = cv2.circle(img, (x, y), 2, color_blue, 1)
            coor.append([rel_x, rel_y])
            radius.append(r)
            print("radius:", radius, "coor:", coor)
        cv2.imwrite(file_path, img)
        return (coor, radius)


cv2.waitKey(0)
cv2.destroyAllWindows()
