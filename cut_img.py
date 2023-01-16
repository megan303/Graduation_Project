import numpy as np
import os, cv2, pathlib
import math
import mediapipe as mp

#img = cv2.imread('static\\uploads\\capture0.jpg')
def cut_img(img):
    mpHands = mp.solutions.hands
    hands = mpHands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5, max_num_hands = 1)
    result = hands.process(img)
    if result.multi_hand_landmarks:
        h = img.shape[0]
        w = img.shape[1]
        thumb_x = 0
        thumb_y = 0
        mid_x = 0
        mid_y = 0
        pinky_x = 0
        pinky_y = 0
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
        start_x = pinky_x - c
        end_x = thumb_x + c
        start_y = mid_y - c
        end_y = mid_y + 400
        dis = [start_y, end_y, start_x, end_x]
        new_img = img[start_y : end_y, start_x : end_x]
        cv2.imshow("new", new_img)
        #print("Work!")
        return new_img

cv2.waitKey(0)
cv2.destroyAllWindows()