import os
import json
import random
import shutil
from pathlib import Path

import numpy as np
import tensorflow as tf

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input

from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)

import matplotlib.pyplot as plt


# ============================================================
# 1. CONFIGURATION
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_DIR = BASE_DIR / "Industrial_Metal_Surface_Dataset"
MODEL_DIR = BASE_DIR / "model"
OUTPUT_DIR = BASE_DIR / "training" / "outputs"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "metal_defect_resnet50.keras"
CLASS_NAMES_PATH = MODEL_DIR / "class_names.txt"

IMAGE_SIZE = (224, 224)

BATCH_SIZE = 16

# Initial frozen training
INITIAL_EPOCHS = 15

# Fine-tuning
FINE_TUNE_EPOCHS = 35

VALIDATION_SPLIT = 0.15
TEST_SPLIT = 0.15

INITIAL_LEARNING_RATE = 1e-3
FINE_TUNE_LEARNING_RATE = 1e-5

AUTOTUNE = tf.data.AUTOTUNE


# ============================================================
# 2. CHECK DATASET
# ============================================================

print("\n" + "=" * 70)
print("INDUSTRIAL METAL SURFACE DEFECT DETECTION")
print("RESNET50 TRANSFER LEARNING TRAINING")
print("=" * 70)

print(f"\nBase directory   : {BASE_DIR}")
print(f"Dataset directory: {DATASET_DIR}")
print(f"Model directory : {MODEL_DIR}")
print(f"Output directory: {OUTPUT_DIR}")


if not DATASET_DIR.exists():
    raise FileNotFoundError(
        f"\nDataset not found:\n{DATASET_DIR}\n\n"
        "Make sure the folder is named exactly:\n"
        "Industrial_Metal_Surface_Dataset"
    )


# ============================================================
# 3. DISCOVER CLASSES
# ============================================================

class_directories = []

for metal_dir in sorted(DATASET_DIR.iterdir()):
    if not metal_dir.is_dir():
        continue

    for status_dir in sorted(metal_dir.iterdir()):
        if not status_dir.is_dir():
            continue

        image_files = []

        for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
            image_files.extend(status_dir.glob(ext))

        if image_files:
            class_name = f"{metal_dir.name.lower()}_{status_dir.name.lower()}"

            class_directories.append(
                {
                    "class_name": class_name,
                    "path": status_dir,
                    "count": len(image_files)
                }
            )


if not class_directories:
    raise RuntimeError("No image classes were found in the dataset.")


# Sort for deterministic class order
class_directories = sorted(
    class_directories,
    key=lambda x: x["class_name"]
)

class_names = [
    item["class_name"]
    for item in class_directories
]

print("\nDetected classes:")
print("-" * 70)

total_images = 0

for item in class_directories:
    print(
        f"{item['class_name']:25s} "
        f"{item['count']:5d} images"
    )

    total_images += item["count"]

print("-" * 70)
print(f"{'TOTAL':25s} {total_images:5d}")


# ============================================================
# 4. SAVE EXACT CLASS ORDER
# ============================================================

with open(CLASS_NAMES_PATH, "w", encoding="utf-8") as f:
    for class_name in class_names:
        f.write(class_name + "\n")

print(f"\nClass order saved to:")
print(CLASS_NAMES_PATH)

print("\nIMPORTANT CLASS ORDER:")
for index, class_name in enumerate(class_names):
    print(f"{index}: {class_name}")


# ============================================================
# 5. DATASET LIMITATION WARNING
# ============================================================

print("\n" + "=" * 70)
print("DATASET CHECK")
print("=" * 70)

for item in class_directories:

    if item["count"] < 10:
        print(
            f"WARNING: {item['class_name']} contains only "
            f"{item['count']} images."
        )

print(
    "\nThe current dataset contains no Good Steel or Good Iron "
    "images. The training script will NOT fabricate them."
)


# ============================================================
# 6. COLLECT ALL IMAGE PATHS
# ============================================================

image_paths = []
labels = []

class_to_index = {
    class_name: index
    for index, class_name in enumerate(class_names)
}


for item in class_directories:

    class_name = item["class_name"]
    class_index = class_to_index[class_name]

    files = []

    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        files.extend(item["path"].glob(ext))

    for image_path in files:

        image_paths.append(str(image_path))
        labels.append(class_index)


image_paths = np.array(image_paths)
labels = np.array(labels)


# ============================================================
# 7. SHUFFLE DATA
# ============================================================

indices = np.arange(len(image_paths))

rng = np.random.default_rng(SEED)
rng.shuffle(indices)

image_paths = image_paths[indices]
labels = labels[indices]


# ============================================================
# 8. STRATIFIED SPLIT
# ============================================================

print("\nCreating train / validation / test split...")


def stratified_split(paths, labels, validation_fraction, seed):

    rng = np.random.default_rng(seed)

    train_indices = []
    validation_indices = []

    unique_classes = np.unique(labels)

    for class_index in unique_classes:

        class_indices = np.where(labels == class_index)[0]

        rng.shuffle(class_indices)

        count = len(class_indices)

        if count == 1:
            n_validation = 0

        elif count == 2:
            # Keep at least one image for training.
            n_validation = 1

        else:
            n_validation = max(
                1,
                int(round(count * validation_fraction))
            )

            # Never take the entire class into validation.
            n_validation = min(
                n_validation,
                count - 1
            )

        validation_indices.extend(
            class_indices[:n_validation]
        )

        train_indices.extend(
            class_indices[n_validation:]
        )

    rng.shuffle(train_indices)
    rng.shuffle(validation_indices)

    return (
        paths[train_indices],
        labels[train_indices],
        paths[validation_indices],
        labels[validation_indices]
    )


(
    train_paths,
    train_labels,
    temp_paths,
    temp_labels
) = stratified_split(
    image_paths,
    labels,
    VALIDATION_SPLIT,
    SEED
)


# Split remaining data into validation and test
(
    val_paths,
    val_labels,
    test_paths,
    test_labels
) = stratified_split(
    temp_paths,
    temp_labels,
    0.50,
    SEED + 1
)


print("\nDataset split:")
print(f"Training   : {len(train_paths)}")
print(f"Validation : {len(val_paths)}")
print(f"Testing    : {len(test_paths)}")
print(f"Total      : {len(train_paths) + len(val_paths) + len(test_paths)}")


# ============================================================
# 9. SHOW SPLIT DISTRIBUTION
# ============================================================

def print_distribution(name, labels_array):

    print(f"\n{name} distribution:")

    for index, class_name in enumerate(class_names):

        count = int(
            np.sum(labels_array == index)
        )

        print(
            f"  {class_name:25s}: {count}"
        )


print_distribution("TRAIN", train_labels)
print_distribution("VALIDATION", val_labels)
print_distribution("TEST", test_labels)


# ============================================================
# 10. IMAGE LOADING
# ============================================================

def load_image(path, label):

    image = tf.io.read_file(path)

    image = tf.image.decode_image(
        image,
        channels=3,
        expand_animations=False
    )

    image = tf.image.resize(
        image,
        IMAGE_SIZE
    )

    image = tf.cast(
        image,
        tf.float32
    )

    image = preprocess_input(image)

    label = tf.cast(
        label,
        tf.int32
    )

    return image, label


def create_dataset(paths, labels, shuffle=False):

    dataset = tf.data.Dataset.from_tensor_slices(
        (paths, labels)
    )

    if shuffle:
        dataset = dataset.shuffle(
            buffer_size=len(paths),
            seed=SEED,
            reshuffle_each_iteration=True
        )

    dataset = dataset.map(
        load_image,
        num_parallel_calls=AUTOTUNE
    )

    dataset = dataset.batch(
        BATCH_SIZE
    )

    dataset = dataset.prefetch(
        AUTOTUNE
    )

    return dataset


train_dataset = create_dataset(
    train_paths,
    train_labels,
    shuffle=True
)

val_dataset = create_dataset(
    val_paths,
    val_labels,
    shuffle=False
)

test_dataset = create_dataset(
    test_paths,
    test_labels,
    shuffle=False
)


# ============================================================
# 11. DATA AUGMENTATION
# ============================================================

data_augmentation = keras.Sequential(
    [
        layers.RandomFlip(
            "horizontal"
        ),

        layers.RandomRotation(
            0.08
        ),

        layers.RandomZoom(
            height_factor=(-0.10, 0.10),
            width_factor=(-0.10, 0.10)
        ),

        layers.RandomTranslation(
            height_factor=0.05,
            width_factor=0.05
        ),

        layers.RandomContrast(
            0.15
        ),
    ],
    name="data_augmentation"
)


# ============================================================
# 12. CLASS WEIGHTS
# ============================================================

print("\nCalculating class weights...")

unique_train_classes = np.unique(train_labels)

weights = compute_class_weight(
    class_weight="balanced",
    classes=unique_train_classes,
    y=train_labels
)

class_weights = {
    int(class_index): float(weight)
    for class_index, weight
    in zip(unique_train_classes, weights)
}

print("\nClass weights:")

for index, weight in class_weights.items():

    print(
        f"{class_names[index]:25s}: {weight:.4f}"
    )


# ============================================================
# 13. BUILD RESNET50 MODEL
# ============================================================

print("\n" + "=" * 70)
print("BUILDING RESNET50")
print("=" * 70)


base_model = ResNet50(
    weights="imagenet",
    include_top=False,
    input_shape=(
        IMAGE_SIZE[0],
        IMAGE_SIZE[1],
        3
    )
)


# Initially freeze ResNet
base_model.trainable = False


inputs = keras.Input(
    shape=(
        IMAGE_SIZE[0],
        IMAGE_SIZE[1],
        3
    ),
    name="input_image"
)


x = data_augmentation(inputs)

x = base_model(
    x,
    training=False
)

x = layers.GlobalAveragePooling2D(
    name="global_average_pooling"
)(x)

x = layers.BatchNormalization(
    name="batch_normalization"
)(x)

x = layers.Dropout(
    0.45,
    name="dropout_1"
)(x)

x = layers.Dense(
    256,
    activation="relu",
    kernel_regularizer=keras.regularizers.l2(1e-4),
    name="dense_features"
)(x)

x = layers.Dropout(
    0.30,
    name="dropout_2"
)(x)

outputs = layers.Dense(
    len(class_names),
    activation="softmax",
    name="predictions"
)(x)


model = keras.Model(
    inputs=inputs,
    outputs=outputs,
    name="Metal_Defect_ResNet50"
)


# ============================================================
# 14. COMPILE STAGE 1
# ============================================================

model.compile(
    optimizer=keras.optimizers.Adam(
        learning_rate=INITIAL_LEARNING_RATE
    ),

    loss=keras.losses.SparseCategoricalCrossentropy(),

    metrics=[
        keras.metrics.SparseCategoricalAccuracy(
            name="accuracy"
        )
    ]
)


model.summary()


# ============================================================
# 15. CALLBACKS STAGE 1
# ============================================================

stage1_best_path = (
    OUTPUT_DIR /
    "stage1_best.weights.h5"
)


callbacks_stage1 = [

    keras.callbacks.ModelCheckpoint(
        filepath=str(stage1_best_path),
        monitor="val_accuracy",
        mode="max",
        save_best_only=True,
        save_weights_only=True,
        verbose=1
    ),

    keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=6,
        restore_best_weights=True,
        verbose=1
    ),

    keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.3,
        patience=2,
        min_lr=1e-7,
        verbose=1
    )
]


# ============================================================
# 16. STAGE 1 TRAINING
# ============================================================

print("\n" + "=" * 70)
print("STAGE 1: TRAINING CLASSIFICATION HEAD")
print("=" * 70)

history_stage1 = model.fit(
    train_dataset,
    validation_data=val_dataset,
    epochs=INITIAL_EPOCHS,
    class_weight=class_weights,
    callbacks=callbacks_stage1,
    verbose=1
)


# Restore best Stage 1 weights
if stage1_best_path.exists():

    model.load_weights(
        stage1_best_path
    )


# ============================================================
# 17. FINE-TUNING
# ============================================================

print("\n" + "=" * 70)
print("STAGE 2: FINE-TUNING RESNET50")
print("=" * 70)


base_model.trainable = True


# Freeze early ResNet layers.
# Fine-tune only upper layers.
fine_tune_from = 100


for layer in base_model.layers[:fine_tune_from]:

    layer.trainable = False


for layer in base_model.layers[fine_tune_from:]:

    layer.trainable = True


# Keep BatchNorm frozen.
for layer in base_model.layers:

    if isinstance(
        layer,
        layers.BatchNormalization
    ):
        layer.trainable = False


trainable_count = sum(
    1
    for layer in model.layers
    if layer.trainable
)

print(
    f"Trainable layers: {trainable_count}"
)


model.compile(
    optimizer=keras.optimizers.Adam(
        learning_rate=FINE_TUNE_LEARNING_RATE
    ),

    loss=keras.losses.SparseCategoricalCrossentropy(),

    metrics=[
        keras.metrics.SparseCategoricalAccuracy(
            name="accuracy"
        )
    ]
)


# ============================================================
# 18. FINE-TUNE CALLBACKS
# ============================================================

fine_tune_best_path = (
    OUTPUT_DIR /
    "fine_tuned_best.weights.h5"
)


callbacks_stage2 = [

    keras.callbacks.ModelCheckpoint(
        filepath=str(fine_tune_best_path),
        monitor="val_accuracy",
        mode="max",
        save_best_only=True,
        save_weights_only=True,
        verbose=1
    ),

    keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=8,
        restore_best_weights=True,
        verbose=1
    ),

    keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.3,
        patience=3,
        min_lr=1e-8,
        verbose=1
    )
]


# ============================================================
# 19. STAGE 2 TRAINING
# ============================================================

history_stage2 = model.fit(
    train_dataset,
    validation_data=val_dataset,
    epochs=FINE_TUNE_EPOCHS,
    class_weight=class_weights,
    callbacks=callbacks_stage2,
    verbose=1
)


# Restore best fine-tuned weights
if fine_tune_best_path.exists():

    model.load_weights(
        fine_tune_best_path
    )


# ============================================================
# 20. SAVE FINAL MODEL
# ============================================================

print("\n" + "=" * 70)
print("SAVING FINAL MODEL")
print("=" * 70)

model.save(
    MODEL_PATH
)

print(
    f"\nModel saved to:\n{MODEL_PATH}"
)


# ============================================================
# 21. TEST EVALUATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST EVALUATION")
print("=" * 70)


test_loss, test_accuracy = model.evaluate(
    test_dataset,
    verbose=1
)


print(
    f"\nTest Accuracy: {test_accuracy * 100:.2f}%"
)


# ============================================================
# 22. PREDICT TEST DATA
# ============================================================

y_true = []
y_pred = []


for images, labels_batch in test_dataset:

    predictions = model.predict(
        images,
        verbose=0
    )

    predicted_classes = np.argmax(
        predictions,
        axis=1
    )

    y_true.extend(
        labels_batch.numpy()
    )

    y_pred.extend(
        predicted_classes
    )


y_true = np.array(y_true)
y_pred = np.array(y_pred)


# ============================================================
# 23. CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    y_true,
    y_pred,
    labels=np.arange(len(class_names)),
    target_names=class_names,
    zero_division=0
)

print("\nClassification Report:")
print(report)


report_path = (
    OUTPUT_DIR /
    "classification_report.txt"
)

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "Industrial Metal Surface Defect Detection\n"
    )

    f.write(
        "Classification Report\n\n"
    )

    f.write(report)


# ============================================================
# 24. CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=np.arange(len(class_names))
)


plt.figure(
    figsize=(11, 9)
)

plt.imshow(
    cm,
    interpolation="nearest"
)

plt.title(
    "Confusion Matrix"
)

plt.colorbar()

tick_marks = np.arange(
    len(class_names)
)

plt.xticks(
    tick_marks,
    class_names,
    rotation=45,
    ha="right"
)

plt.yticks(
    tick_marks,
    class_names
)

threshold = cm.max() / 2.0


for i in range(cm.shape[0]):

    for j in range(cm.shape[1]):

        plt.text(
            j,
            i,
            str(cm[i, j]),
            horizontalalignment="center",
            verticalalignment="center",
            color="white"
            if cm[i, j] > threshold
            else "black"
        )


plt.ylabel(
    "True Label"
)

plt.xlabel(
    "Predicted Label"
)

plt.tight_layout()


confusion_path = (
    OUTPUT_DIR /
    "confusion_matrix.png"
)

plt.savefig(
    confusion_path,
    dpi=200,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 25. TRAINING HISTORY
# ============================================================

def combine_history(h1, h2):

    history = {}

    keys = set(
        h1.history.keys()
    ).union(
        h2.history.keys()
    )

    for key in keys:

        history[key] = (
            h1.history.get(key, [])
            +
            h2.history.get(key, [])
        )

    return history


history = combine_history(
    history_stage1,
    history_stage2
)


# ============================================================
# 26. ACCURACY GRAPH
# ============================================================

plt.figure(
    figsize=(10, 6)
)

if "accuracy" in history:

    plt.plot(
        history["accuracy"],
        label="Training Accuracy"
    )

if "val_accuracy" in history:

    plt.plot(
        history["val_accuracy"],
        label="Validation Accuracy"
    )


plt.title(
    "Training and Validation Accuracy"
)

plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Accuracy"
)

plt.legend()

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()


accuracy_graph = (
    OUTPUT_DIR /
    "accuracy_curve.png"
)

plt.savefig(
    accuracy_graph,
    dpi=200,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 27. LOSS GRAPH
# ============================================================

plt.figure(
    figsize=(10, 6)
)

if "loss" in history:

    plt.plot(
        history["loss"],
        label="Training Loss"
    )

if "val_loss" in history:

    plt.plot(
        history["val_loss"],
        label="Validation Loss"
    )


plt.title(
    "Training and Validation Loss"
)

plt.xlabel(
    "Epoch"
)

plt.ylabel(
    "Loss"
)

plt.legend()

plt.grid(
    True,
    alpha=0.3
)

plt.tight_layout()


loss_graph = (
    OUTPUT_DIR /
    "loss_curve.png"
)

plt.savefig(
    loss_graph,
    dpi=200,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 28. SAVE TRAINING INFORMATION
# ============================================================

training_info = {

    "dataset": str(DATASET_DIR),

    "total_images": int(total_images),

    "train_images": int(len(train_paths)),

    "validation_images": int(len(val_paths)),

    "test_images": int(len(test_paths)),

    "image_size": list(IMAGE_SIZE),

    "batch_size": BATCH_SIZE,

    "initial_epochs": INITIAL_EPOCHS,

    "fine_tune_epochs": FINE_TUNE_EPOCHS,

    "classes": class_names,

    "class_counts": {
        item["class_name"]: item["count"]
        for item in class_directories
    },

    "class_weights": {
        class_names[index]: weight
        for index, weight
        in class_weights.items()
    },

    "test_accuracy": float(test_accuracy),

    "test_accuracy_percent": float(
        test_accuracy * 100
    ),

    "model": "ResNet50",

    "pretrained": "ImageNet",

    "augmentation": True,

    "class_weighting": True,

    "two_stage_training": True,

    "fine_tuning": True,

    "note": (
        "Test accuracy is saved for training analysis only. "
        "It is intentionally not exposed by the application API "
        "or inspection PDF."
    )
}


training_info_path = (
    OUTPUT_DIR /
    "training_info.json"
)


with open(
    training_info_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        training_info,
        f,
        indent=4
    )


# ============================================================
# 29. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TRAINING COMPLETED")
print("=" * 70)

print(
    f"\nFinal Test Accuracy: "
    f"{test_accuracy * 100:.2f}%"
)

print("\nGenerated files:")

print(
    f"  Model              : {MODEL_PATH}"
)

print(
    f"  Class names        : {CLASS_NAMES_PATH}"
)

print(
    f"  Classification     : {report_path}"
)

print(
    f"  Confusion matrix   : {confusion_path}"
)

print(
    f"  Accuracy curve     : {accuracy_graph}"
)

print(
    f"  Loss curve         : {loss_graph}"
)

print(
    f"  Training info      : {training_info_path}"
)

print("\nIMPORTANT:")
print(
    "The accuracy above is for model-development/evaluation only."
)

print(
    "It will NOT be displayed in the application result or PDF."
)

print("\nModel is ready for backend integration.")