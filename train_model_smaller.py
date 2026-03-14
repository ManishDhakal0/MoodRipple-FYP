# train_model_auto.py
import os
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam

# -----------------------
# 1. Paths
# -----------------------
train_dir = 'fyp dataset/train'  # change if needed
test_dir = 'fyp dataset/test'

# -----------------------
# 2. Data Preparation
# -----------------------
train_datagen = ImageDataGenerator(rescale=1./255)
test_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    train_dir,
    target_size=(48,48),
    color_mode='grayscale',
    batch_size=32,
    class_mode='categorical',
    shuffle=True
)

test_generator = test_datagen.flow_from_directory(
    test_dir,
    target_size=(48,48),
    color_mode='grayscale',
    batch_size=32,
    class_mode='categorical',
    shuffle=False
)

# -----------------------
# 3. CNN Model (simplified for weak laptop)
# -----------------------
model = Sequential([
    Conv2D(16, (3,3), activation='relu', input_shape=(48,48,1)),
    MaxPooling2D(2,2),
    Conv2D(32, (3,3), activation='relu'),
    MaxPooling2D(2,2),
    Flatten(),
    Dense(64, activation='relu'),
    Dropout(0.5)
])

# -----------------------
# 4. Automatically set output layer based on dataset
# -----------------------
num_classes = len(train_generator.class_indices)
model.add(Dense(num_classes, activation='softmax'))

model.compile(optimizer=Adam(0.001), loss='categorical_crossentropy', metrics=['accuracy'])
model.summary()

# -----------------------
# 5. Train Model on small subset
# -----------------------
steps_per_epoch = 200      # reduce for weak laptop
validation_steps = 50
epochs = 16               # fewer epochs for quick testing

history = model.fit(
    train_generator,
    steps_per_epoch=steps_per_epoch,
    validation_data=test_generator,
    validation_steps=validation_steps,
    epochs=epochs
)

# -----------------------
# 6. Save Model
# -----------------------
model.save('emotion_recognition_model_auto.h5')
print("Model saved as 'emotion_recognition_model_auto.h5'")
