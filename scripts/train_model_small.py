# train_model_small.py

import os
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
import matplotlib.pyplot as plt

# -----------------------
# 1. Configuration
# -----------------------
TRAIN_DIR = 'fyp dataset/train'
TEST_DIR = 'fyp dataset/test'
IMG_SIZE = (48, 48)
BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 0.0001

print("\n" + "="*60)
print("EMOTION DETECTION MODEL - TRAINING")
print("="*60 + "\n")

# -----------------------
# 2. Data Preparation with Augmentation
# -----------------------
print("Setting up data generators...")

# Training data with augmentation
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True,
    zoom_range=0.1,
    fill_mode='nearest'
)

# Test data without augmentation
test_datagen = ImageDataGenerator(rescale=1./255)

# Load training data
train_generator = train_datagen.flow_from_directory(
    TRAIN_DIR,
    target_size=IMG_SIZE,
    color_mode='grayscale',
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=True
)

# Load test data
test_generator = test_datagen.flow_from_directory(
    TEST_DIR,
    target_size=IMG_SIZE,
    color_mode='grayscale',
    batch_size=BATCH_SIZE,
    class_mode='categorical',
    shuffle=False
)

# Get class names
class_names = list(train_generator.class_indices.keys())
num_classes = len(class_names)

print(f"\nClasses found: {class_names}")
print(f"Number of classes: {num_classes}")
print(f"Training samples: {train_generator.samples}")
print(f"Test samples: {test_generator.samples}")

# -----------------------
# 3. Build CNN Model
# -----------------------
print("\nBuilding model...")

model = Sequential([
    # Block 1
    Conv2D(32, (3, 3), activation='relu', input_shape=(48, 48, 1), padding='same'),
    BatchNormalization(),
    Conv2D(32, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    
    # Block 2
    Conv2D(64, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    Conv2D(64, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    
    # Block 3
    Conv2D(128, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    
    # Fully connected
    Flatten(),
    Dense(256, activation='relu'),
    BatchNormalization(),
    Dropout(0.5),
    Dense(num_classes, activation='softmax')
])

model.compile(
    optimizer=Adam(learning_rate=LEARNING_RATE),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# -----------------------
# 4. Callbacks
# -----------------------
callbacks = [
    EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    ),
    ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-7,
        verbose=1
    ),
    ModelCheckpoint(
        'emotion_recognition_model_auto.h5',
        monitor='val_accuracy',
        save_best_only=True,
        verbose=1
    )
]

# -----------------------
# 5. Train Model
# -----------------------
print("\n" + "="*60)
print("STARTING TRAINING")
print("="*60 + "\n")

history = model.fit(
    train_generator,
    validation_data=test_generator,
    epochs=EPOCHS,
    callbacks=callbacks,
    verbose=1
)

# -----------------------
# 6. Save Final Model
# -----------------------
model.save('emotion_model_final.h5')
print("\n✓ Model saved as 'emotion_model_final.h5'")

# -----------------------
# 7. Evaluate
# -----------------------
print("\n" + "="*60)
print("FINAL EVALUATION")
print("="*60)

test_loss, test_acc = model.evaluate(test_generator, verbose=0)
print(f"\nTest accuracy: {test_acc*100:.2f}%")
print(f"Test loss: {test_loss:.4f}")

# -----------------------
# 8. Plot Training History
# -----------------------
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Val Accuracy')
plt.title('Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig('training_history.png')
print("\n✓ Training history saved as 'training_history.png'")

# Save class names for later use
import json
with open('class_names.json', 'w') as f:
    json.dump(class_names, f)
print("✓ Class names saved as 'class_names.json'")

print("\n" + "="*60)
print("TRAINING COMPLETE!")
print("="*60 + "\n")