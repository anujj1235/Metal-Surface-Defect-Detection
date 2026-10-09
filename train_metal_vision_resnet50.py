import os
import zipfile
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input

# ============================================================
# CONFIGURATION
# ============================================================

ZIP_PATH = Path("Industrial_Metal_Surface_Defect_Project_Dataset_REDUCED.zip")
WORK_DIR = Path("metal_vision_training_data")
EXTRACT_DIR = WORK_DIR / "extracted"

MODEL_DIR = Path("model")
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "resnet50_metal_vision_9class.keras"
CLASS_NAMES_PATH = MODEL_DIR / "class_names.txt"
HISTORY_PATH = MODEL_DIR / "training_history.csv"
TEST_RESULTS_PATH = MODEL_DIR / "test_results.txt"

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
SEED = 42

# Phase 1: frozen backbone
FROZEN_EPOCHS = 12

# Phase 2: fine tuning
FINETUNE_EPOCHS = 15
UNFREEZE_LAST_LAYERS = 30

# ============================================================
# REPRODUCIBILITY
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

# ============================================================
# EXTRACT DATASET
# ============================================================

if not ZIP_PATH.exists():
    raise FileNotFoundError(
        f"Dataset ZIP not found: {ZIP_PATH.resolve()}\n"
        "Place the reduced ZIP in the same folder as this script."
    )

if EXTRACT_DIR.exists():
    print("Using existing extracted dataset.")
else:
    print("Extracting dataset...")
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(EXTRACT_DIR)

# ZIP contains one top-level folder.
top_dirs = [p for p in EXTRACT_DIR.iterdir() if p.is_dir()]
if not top_dirs:
    raise RuntimeError("Could not find the extracted dataset folder.")

DATASET_ROOT = top_dirs[0]
RAW_ROOT = DATASET_ROOT / "01_RAW_REAL_DATASETS"

if not RAW_ROOT.exists():
    raise RuntimeError(f"Raw dataset folder not found: {RAW_ROOT}")

# ============================================================
# DISCOVER ACTUAL RAW IMAGES
# ============================================================

class_dirs = {
    "steel_crazing": RAW_ROOT / "NEU_DET" / "NEU-DET" / "train" / "images" / "crazing",
    "steel_inclusion": RAW_ROOT / "NEU_DET" / "NEU-DET" / "train" / "images" / "inclusion",
    "steel_patches": RAW_ROOT / "NEU_DET" / "NEU-DET" / "train" / "images" / "patches",
    "steel_pitted_surface": RAW_ROOT / "NEU_DET" / "NEU-DET" / "train" / "images" / "pitted_surface",
    "steel_rolled_in_scale": RAW_ROOT / "NEU_DET" / "NEU-DET" / "train" / "images" / "rolled-in_scale",
    "steel_scratches": RAW_ROOT / "NEU_DET" / "NEU-DET" / "train" / "images" / "scratches",
    "316L_OT_Good": RAW_ROOT / "DD1_LPBF_316L" / "Croped Defects" / "OT" / "Good",
    "316L_OT_Defects": RAW_ROOT / "DD1_LPBF_316L" / "Croped Defects" / "OT" / "Defects",
    "316L_PB_Defects": RAW_ROOT / "DD1_LPBF_316L" / "Croped Defects" / "PB" / "Defects",
}

# Add NEU validation images, assigning their labels from the filename.
# NEU validation filenames use the same defect-name convention in this reduced copy.
VAL_ROOT = RAW_ROOT / "NEU_DET" / "NEU-DET" / "validation" / "images"
neu_names = {
    "crazing": "steel_crazing",
    "inclusion": "steel_inclusion",
    "patches": "steel_patches",
    "pitted_surface": "steel_pitted_surface",
    "rolled-in_scale": "steel_rolled_in_scale",
    "scratches": "steel_scratches",
}

records = []

for label, folder in class_dirs.items():
    if not folder.exists():
        raise RuntimeError(f"Required class folder missing: {folder}")
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            records.append({"path": str(p), "label": label})

# Validation images are distributed in a single folder in the reduced ZIP.
# Assign labels by matching the filename against known NEU class tokens.
if VAL_ROOT.exists():
    for p in sorted(VAL_ROOT.iterdir()):
        if not (p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}):
            continue

        stem = p.stem.lower()
        matched = None
        for token, label in neu_names.items():
            if token.replace("-", "_") in stem or token in stem:
                matched = label
                break

        if matched is not None:
            records.append({"path": str(p), "label": matched})
        else:
            print(f"WARNING: Could not infer NEU validation label: {p.name}")

df = pd.DataFrame(records)

if df.empty:
    raise RuntimeError("No training images were found.")

CLASS_NAMES = sorted(df["label"].unique())

print("\nActual classes found:")
print(df["label"].value_counts().sort_index())
print(f"\nTotal usable unique raw images: {len(df)}")
print(f"Classes: {len(CLASS_NAMES)}")

# Save class names for model_service.py.
CLASS_NAMES_PATH.write_text("\n".join(CLASS_NAMES), encoding="utf-8")

# ============================================================
# TRAIN / VALIDATION / TEST SPLIT
# ============================================================

# 70% train, 15% validation, 15% test.
train_df, temp_df = train_test_split(
    df,
    test_size=0.30,
    stratify=df["label"],
    random_state=SEED
)

val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    stratify=temp_df["label"],
    random_state=SEED
)

print("\nSplit sizes:")
print("Train:", len(train_df))
print("Validation:", len(val_df))
print("Test:", len(test_df))

# ============================================================
# TF.DATA PIPELINE
# ============================================================

label_to_index = {name: i for i, name in enumerate(CLASS_NAMES)}

def load_image(path, label):
    image = tf.io.read_file(path)
    image = tf.image.decode_image(
        image,
        channels=3,
        expand_animations=False
    )
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, IMG_SIZE)
    image = tf.cast(image, tf.float32)
    image = preprocess_input(image)
    return image, label

def make_dataset(frame, shuffle=False):
    paths = frame["path"].values
    labels = frame["label"].map(label_to_index).values.astype(np.int32)

    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    ds = ds.map(load_image, num_parallel_calls=tf.data.AUTOTUNE)

    if shuffle:
        ds = ds.shuffle(
            buffer_size=len(frame),
            seed=SEED,
            reshuffle_each_iteration=True
        )

    return ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

train_ds = make_dataset(train_df, shuffle=True)
val_ds = make_dataset(val_df)
test_ds = make_dataset(test_df)

# ============================================================
# CLASS WEIGHTS
# ============================================================

weights = compute_class_weight(
    class_weight="balanced",
    classes=np.arange(len(CLASS_NAMES)),
    y=train_df["label"].map(label_to_index).values
)

class_weights = {
    i: float(w)
    for i, w in enumerate(weights)
}

print("\nClass weights:")
for i, name in enumerate(CLASS_NAMES):
    print(f"{name}: {class_weights[i]:.4f}")

# ============================================================
# DATA AUGMENTATION
# ============================================================

augmentation = tf.keras.Sequential(
    [
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.05),
        layers.RandomZoom(0.10),
        layers.RandomContrast(0.10),
    ],
    name="data_augmentation"
)

# ============================================================
# BUILD RESNET50 MODEL
# ============================================================

base_model = ResNet50(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3)
)

base_model.trainable = False

inputs = layers.Input(shape=(224, 224, 3), name="image")
x = augmentation(inputs)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.35)(x)
outputs = layers.Dense(
    len(CLASS_NAMES),
    activation="softmax",
    name="classification"
)(x)

model = models.Model(inputs, outputs, name="MetalVisionResNet50")

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# ============================================================
# CALLBACKS
# ============================================================

checkpoint = callbacks.ModelCheckpoint(
    MODEL_PATH,
    monitor="val_accuracy",
    save_best_only=True,
    verbose=1
)

early_stop = callbacks.EarlyStopping(
    monitor="val_accuracy",
    patience=5,
    restore_best_weights=True,
    verbose=1
)

reduce_lr = callbacks.ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.3,
    patience=2,
    min_lr=1e-7,
    verbose=1
)

# ============================================================
# PHASE 1 - TRAIN CLASSIFIER
# ============================================================

print("\n========== PHASE 1: FROZEN RESNET50 ==========")

history1 = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=FROZEN_EPOCHS,
    class_weight=class_weights,
    callbacks=[checkpoint, early_stop, reduce_lr]
)

# ============================================================
# PHASE 2 - FINE TUNING
# ============================================================

print("\n========== PHASE 2: FINE TUNING ==========")

base_model.trainable = True

# Freeze earlier layers, fine-tune the last N layers.
for layer in base_model.layers[:-UNFREEZE_LAST_LAYERS]:
    layer.trainable = False

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

history2 = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=FINETUNE_EPOCHS,
    class_weight=class_weights,
    callbacks=[checkpoint, early_stop, reduce_lr]
)

# ============================================================
# LOAD BEST MODEL
# ============================================================

model = tf.keras.models.load_model(MODEL_PATH)

# ============================================================
# TEST SET EVALUATION
# ============================================================

print("\n========== FINAL TEST EVALUATION ==========")

test_loss, test_accuracy = model.evaluate(
    test_ds,
    verbose=1
)

print(f"\nTest Accuracy: {test_accuracy * 100:.2f}%")
print(f"Test Loss: {test_loss:.4f}")

# ============================================================
# SAVE TRAINING HISTORY
# ============================================================

history = {}

for k, values in history1.history.items():
    history.setdefault(k, [])
    history[k].extend(values)

for k, values in history2.history.items():
    history.setdefault(k, [])
    history[k].extend(values)

pd.DataFrame(history).to_csv(
    HISTORY_PATH,
    index=False
)

TEST_RESULTS_PATH.write_text(
    f"Model: ResNet50\n"
    f"Classes: {len(CLASS_NAMES)}\n"
    f"Test images: {len(test_df)}\n"
    f"Test accuracy: {test_accuracy * 100:.2f}%\n"
    f"Test loss: {test_loss:.6f}\n",
    encoding="utf-8"
)

print("\n========== TRAINING COMPLETE ==========")
print(f"Model saved to: {MODEL_PATH.resolve()}")
print(f"Class names saved to: {CLASS_NAMES_PATH.resolve()}")
print(f"History saved to: {HISTORY_PATH.resolve()}")
print(f"Test results saved to: {TEST_RESULTS_PATH.resolve()}")
