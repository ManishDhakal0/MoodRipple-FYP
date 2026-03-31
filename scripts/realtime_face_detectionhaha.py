# realtime_face_detection_auto.py
import cv2
import numpy as np
from tensorflow.keras.models import load_model

# -----------------------
# 1. Load trained model
# -----------------------
model = load_model('emotion_recognition_model_auto.h5')
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# -----------------------
# 2. Auto-detect emotion labels
# -----------------------
# Update this list according to the folder names in your dataset
emotion_labels = ['angry','disgust','fear','happy','sad','neutral','surprise']

# -----------------------
# 3. Start webcam and detect face + emotion
# -----------------------
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    for (x,y,w,h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        roi_gray = cv2.resize(roi_gray, (48,48))
        roi = roi_gray.reshape(1,48,48,1)/255.0
        
        prediction = model.predict(roi)
        emotion = emotion_labels[np.argmax(prediction)]
        
        cv2.rectangle(frame,(x,y),(x+w,y+h),(255,0,0),2)
        cv2.putText(frame, emotion, (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
    
    cv2.imshow('MoodRipple Face Detection', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
