import os
import re
from pathlib import Path

import numpy as np
from PIL import Image

import tensorflow as tf

from tensorflow.keras.models import load_model

from tensorflow.keras.applications.resnet50 import (
    preprocess_input
)


# ============================================================
# BASE DIRECTORIES
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent.parent

MODEL_DIR = (
    BASE_DIR / "model"
)

MODEL_PATH = (
    MODEL_DIR /
    "metal_defect_resnet50.keras"
)

CLASS_NAMES_PATH = (
    MODEL_DIR /
    "class_names.txt"
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

IMG_SIZE = (
    224,
    224
)

MODEL_ARCHITECTURE = (
    "ResNet50"
)


# ============================================================
# LAZY LOADING
# ============================================================
#
# The model is loaded only when prediction is required.
#
# This prevents unnecessary model loading during simple
# imports and makes FastAPI startup more reliable.
# ============================================================

_model = None

_class_names = None


# ============================================================
# METAL NAME NORMALIZATION
# ============================================================

METAL_NAMES = {
    "steel": "Steel",
    "aluminium": "Aluminium",
    "aluminum": "Aluminium",
    "copper": "Copper",
    "iron": "Iron"
}


# ============================================================
# VERIFIED DEFECT TYPES
# ============================================================
#
# The current dataset does NOT have these labels.
#
# These names are included only so that the service can
# support a future verified defect-specific dataset.
# ============================================================

KNOWN_DEFECT_TYPES = {
    "rust": "Rust",
    "corrosion": "Corrosion",
    "scratch": "Scratch",
    "crack": "Crack",
    "dent": "Dent",
    "pitting": "Pitting",
    "pit": "Pitting",
    "inclusion": "Inclusion",
    "patch": "Surface Patch",
    "surface_defect": "Surface Defect",
    "defect": "Surface Defect",
    "defective": "Surface Defect"
}


# ============================================================
# LOAD CLASS NAMES
# ============================================================

def load_class_names():
    """
    Load class names from:

        model/class_names.txt

    Expected examples:

        steel_defective
        aluminium_defective
        aluminium_good
        copper_defective
        copper_good
        iron_defective

    Returns:
        list[str]
    """

    global _class_names

    if _class_names is not None:
        return _class_names

    if not CLASS_NAMES_PATH.exists():

        raise FileNotFoundError(
            "class_names.txt was not found at:\n"
            f"{CLASS_NAMES_PATH}\n\n"
            "Please make sure the trained model and "
            "class_names.txt are inside the model folder."
        )

    with open(
        CLASS_NAMES_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        class_names = [
            line.strip()
            for line in file.readlines()
            if line.strip()
        ]

    if not class_names:

        raise ValueError(
            "class_names.txt is empty."
        )

    _class_names = class_names

    print(
        "Loaded class names:",
        _class_names
    )

    return _class_names


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():
    """
    Load the trained Keras model.

    The model is loaded only once.
    """

    global _model

    if _model is not None:
        return _model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Trained model was not found at:\n"
            f"{MODEL_PATH}\n\n"
            "Train the model first and place the resulting "
            "metal_defect_resnet50.keras file inside the "
            "model folder."
        )

    print("Loading Metal Vision AI model...")
    print(f"Model path: {MODEL_PATH}")

    # IMPORTANT:
    # Use TensorFlow's loader explicitly to avoid calling
    # this function recursively.
    _model = tf.keras.models.load_model(
        str(MODEL_PATH),
        compile=False
    )

    print("Metal Vision AI model loaded successfully.")

    return _model


# ============================================================
# CLASS NAME CLEANING
# ============================================================

def clean_class_name(
    class_name
):
    """
    Normalize a class name.

    Examples:

        steel_defective
        Steel Defective
        steel-defective

    become a consistent representation.
    """

    if class_name is None:
        return ""

    class_name = str(
        class_name
    ).strip().lower()

    class_name = class_name.replace(
        "-",
        "_"
    )

    class_name = class_name.replace(
        " ",
        "_"
    )

    class_name = re.sub(
        r"_+",
        "_",
        class_name
    )

    return class_name


# ============================================================
# PARSE METAL TYPE
# ============================================================

def parse_metal_type(
    class_name
):
    """
    Extract metal type from a model class name.
    """

    normalized = clean_class_name(
        class_name
    )

    # Check longer names first
    # so aluminium is handled correctly.
    for key in (
        "aluminium",
        "aluminum",
        "steel",
        "copper",
        "iron"
    ):

        if key in normalized:

            return METAL_NAMES[
                key
            ]

    return "Unknown"


# ============================================================
# PARSE STATUS
# ============================================================

def parse_status(
    class_name
):
    """
    Extract GOOD / DEFECTIVE status from a class name.
    """

    normalized = clean_class_name(
        class_name
    )

    # --------------------------------------------------------
    # Good
    # --------------------------------------------------------

    good_patterns = [
        "good",
        "normal",
        "non_defective",
        "nondefective",
        "no_defect",
        "nodefect",
        "healthy"
    ]

    for pattern in good_patterns:

        if pattern in normalized:

            return "GOOD"

    # --------------------------------------------------------
    # Defective
    # --------------------------------------------------------

    defective_patterns = [
        "defective",
        "defect",
        "defected",
        "faulty",
        "damaged"
    ]

    for pattern in defective_patterns:

        if pattern in normalized:

            return "DEFECTIVE"

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return "UNKNOWN"


# ============================================================
# PARSE DEFECT TYPE
# ============================================================

def parse_defect_type(
    class_name,
    status
):
    """
    Determine the defect type.

    IMPORTANT:
    We only return a specific defect type if the class name
    explicitly contains a verified defect label.

    Otherwise:

        GOOD      -> No Defect
        DEFECTIVE -> Surface Defect
    """

    if status == "GOOD":

        return "No Defect"

    normalized = clean_class_name(
        class_name
    )

    # --------------------------------------------------------
    # Look for explicitly named defect
    # --------------------------------------------------------

    for key, display_name in (
        KNOWN_DEFECT_TYPES.items()
    ):

        if key in normalized:

            return display_name

    # --------------------------------------------------------
    # Current dataset
    # --------------------------------------------------------

    return "Surface Defect"


# ============================================================
# PREPROCESS IMAGE
# ============================================================

def preprocess_image(
    image
):
    """
    Convert a PIL image into the input format expected
    by ResNet50.

    Returns:
        numpy array of shape:

            (1, 224, 224, 3)
    """

    if not isinstance(
        image,
        Image.Image
    ):

        image = Image.fromarray(
            np.asarray(image)
        )

    image = image.convert(
        "RGB"
    )

    image = image.resize(
        IMG_SIZE,
        Image.Resampling.LANCZOS
    )

    image_array = np.asarray(
        image,
        dtype=np.float32
    )

    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    image_array = preprocess_input(
        image_array
    )

    return image_array


# ============================================================
# CONFIDENCE CALCULATION
# ============================================================

def calculate_confidence(
    probabilities,
    predicted_index,
    status
):
    """
    Calculate displayed confidence.

    Good predictions:
        always displayed as 100%

    Defective predictions:
        use the model's predicted probability.
    """

    status = str(
        status
    ).upper()

    # --------------------------------------------------------
    # User requirement:
    # Good = 100%
    # --------------------------------------------------------

    if status == "GOOD":

        return 100.0

    # --------------------------------------------------------
    # Defective
    # --------------------------------------------------------

    try:

        confidence = float(
            probabilities[
                predicted_index
            ]
        )

    except (
        IndexError,
        TypeError,
        ValueError
    ):

        confidence = 0.0

    # Model probabilities are normally 0-1.
    if 0 <= confidence <= 1:

        confidence *= 100

    return max(
        0.0,
        min(
            100.0,
            confidence
        )
    )


# ============================================================
# SAFE PROBABILITY CONVERSION
# ============================================================

def convert_probabilities(
    probabilities,
    class_names
):
    """
    Convert model output probabilities into a JSON-safe
    dictionary.

    Example:

        {
            "steel_defective": 91.42,
            "aluminium_good": 2.31,
            ...
        }
    """

    result = {}

    for index, probability in enumerate(
        probabilities
    ):

        if index < len(
            class_names
        ):

            class_name = class_names[
                index
            ]

        else:

            class_name = (
                f"class_{index}"
            )

        try:

            value = float(
                probability
            )

        except (
            TypeError,
            ValueError
        ):

            value = 0.0

        # Return probabilities as percentages.
        if 0 <= value <= 1:

            value *= 100

        result[
            class_name
        ] = round(
            value,
            4
        )

    return result


# ============================================================
# PREDICT IMAGE
# ============================================================

def predict_image(
    image
):
    """
    Predict the metal and defect status of an image.

    Returns:

        {
            "metal_type": ...,
            "defect_type": ...,
            "status": ...,
            "confidence_score": ...,
            "predicted_class": ...,
            "predicted_index": ...,
            "probabilities": ...,
            "defected_area": ...
        }

    Defect localization is handled separately by Grad-CAM.
    """

    # ========================================================
    # VALIDATE IMAGE
    # ========================================================

    if image is None:

        raise ValueError(
            "No image was provided."
        )

    # ========================================================
    # LOAD MODEL
    # ========================================================

    model = load_model()

    # ========================================================
    # LOAD CLASS NAMES
    # ========================================================

    class_names = load_class_names()

    # ========================================================
    # PREPROCESS
    # ========================================================

    input_tensor = preprocess_image(
        image
    )

    # ========================================================
    # PREDICTION
    # ========================================================

    prediction = model.predict(
        input_tensor,
        verbose=0
    )

    prediction = np.asarray(
        prediction
    )

    # ========================================================
    # HANDLE MODEL OUTPUT SHAPE
    # ========================================================

    if prediction.ndim == 2:

        probabilities = prediction[
            0
        ]

    elif prediction.ndim == 1:

        probabilities = prediction

    else:

        probabilities = prediction.reshape(
            -1
        )

    # ========================================================
    # HANDLE SINGLE-OUTPUT BINARY MODEL
    # ========================================================
    #
    # If the trained model has only one sigmoid output,
    # convert it into two probabilities.
    #
    # IMPORTANT:
    # For this project, a multiclass model with class_names
    # is preferred. This is only a compatibility fallback.
    # ========================================================

    if len(
        class_names
    ) == 2 and len(
        probabilities
    ) == 1:

        defective_probability = float(
            probabilities[0]
        )

        defective_probability = max(
            0.0,
            min(
                1.0,
                defective_probability
            )
        )

        probabilities = np.array(
            [
                1.0 - defective_probability,
                defective_probability
            ],
            dtype=np.float32
        )

    # ========================================================
    # CHECK CLASS/OUTPUT MATCH
    # ========================================================

    if len(
        probabilities
    ) != len(
        class_names
    ):

        raise ValueError(
            "The number of model outputs does not match "
            "the number of class names.\n\n"
            f"Model outputs: {len(probabilities)}\n"
            f"Class names: {len(class_names)}\n\n"
            "Please check model/class_names.txt and make "
            "sure they belong to the same trained model."
        )

    # ========================================================
    # PREDICTED INDEX
    # ========================================================

    predicted_index = int(
        np.argmax(
            probabilities
        )
    )

    # ========================================================
    # PREDICTED CLASS
    # ========================================================

    predicted_class = str(
        class_names[
            predicted_index
        ]
    )

    # ========================================================
    # METAL
    # ========================================================

    metal_type = parse_metal_type(
        predicted_class
    )

    # ========================================================
    # STATUS
    # ========================================================

    status = parse_status(
        predicted_class
    )

    # ========================================================
    # FALLBACK STATUS
    # ========================================================
    #
    # If the class name is unusual but contains "good"
    # or "defective" we already handled it.
    #
    # If completely unknown, do NOT invent a status.
    # ========================================================

    if status == "UNKNOWN":

        normalized_class = clean_class_name(
            predicted_class
        )

        if (
            "good" in normalized_class
            or
            "normal" in normalized_class
        ):

            status = "GOOD"

        else:

            status = "DEFECTIVE"

    # ========================================================
    # DEFECT TYPE
    # ========================================================

    defect_type = parse_defect_type(
        predicted_class,
        status
    )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    confidence_score = calculate_confidence(
        probabilities=probabilities,
        predicted_index=predicted_index,
        status=status
    )

    # ========================================================
    # PROBABILITY DICTIONARY
    # ========================================================

    probability_dict = (
        convert_probabilities(
            probabilities,
            class_names
        )
    )

    # ========================================================
    # EMPTY DEFECT AREA
    # ========================================================
    #
    # Grad-CAM will fill this later in main.py.
    # ========================================================

    defected_area = {

        "detected": False,

        "coverage_percent": 0.0,

        "boxes": []
    }

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "metal_type":
            metal_type,

        "defect_type":
            defect_type,

        "status":
            status,

        "confidence_score":
            round(
                confidence_score,
                2
            ),

        "predicted_class":
            predicted_class,

        "predicted_index":
            predicted_index,

        "class_name":
            predicted_class,

        "confidence":
            round(
                confidence_score,
                2
            ),

        "probabilities": [float(x) for x in probabilities],

        "defected_area":
            defected_area
    }


# ============================================================
# MODEL INFORMATION
# ============================================================

def get_model_info():
    """
    Return information about the trained model.

    Test accuracy is deliberately NOT returned.
    """

    class_names = load_class_names()

    model = None

    try:

        model = load_model()

    except Exception as error:

        print(
            "Model info warning:",
            error
        )

    # --------------------------------------------------------
    # Determine input size
    # --------------------------------------------------------

    input_size = [
        IMG_SIZE[0],
        IMG_SIZE[1]
    ]

    if model is not None:

        try:

            shape = model.input_shape

            if (
                isinstance(shape, tuple)
                and
                len(shape) == 4
                and
                shape[1] is not None
                and
                shape[2] is not None
            ):

                input_size = [
                    int(shape[1]),
                    int(shape[2])
                ]

        except Exception:
            pass

    # --------------------------------------------------------
    # Metal types
    # --------------------------------------------------------

    metal_types = []

    for class_name in class_names:

        metal = parse_metal_type(
            class_name
        )

        if (
            metal != "Unknown"
            and
            metal not in metal_types
        ):

            metal_types.append(
                metal
            )

    # Ensure current project metals are represented.
    for metal in (
        "Steel",
        "Aluminium",
        "Copper",
        "Iron"
    ):

        if metal not in metal_types:

            metal_types.append(
                metal
            )

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {

        "model":
            MODEL_PATH.name,

        "architecture":
            MODEL_ARCHITECTURE,

        "input_size":
            input_size,

        "number_of_classes":
            len(class_names),

        "classes":
            class_names,

        "metal_types":
            metal_types,

        "localization":
            "Grad-CAM",

        "normal_class_available":
            any(
                parse_status(
                    name
                ) == "GOOD"
                for name in class_names
            ),

        "normal_classes":
            [
                name
                for name in class_names
                if parse_status(
                    name
                ) == "GOOD"
            ]
    }


# ============================================================
# RESET MODEL
# ============================================================

def reset_model():
    """
    Clear the cached model and class names.

    Useful after replacing the trained model.
    """

    global _model
    global _class_names

    _model = None
    _class_names = None

    print(
        "Model service cache cleared."
    )


# ============================================================
# MODULE INFORMATION
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "Metal Vision AI - Model Service"
    )

    print(
        "=========================================="
    )

    print(
        f"Base directory : {BASE_DIR}"
    )

    print(
        f"Model path     : {MODEL_PATH}"
    )

    print(
        f"Classes path   : {CLASS_NAMES_PATH}"
    )

    print(
        f"Input size     : {IMG_SIZE}"
    )

    print(
        "=========================================="
    )

    try:

        print(
            "\nClass names:"
        )

        for index, name in enumerate(
            load_class_names()
        ):

            print(
                f"  {index}: {name}"
            )

        print(
            "\nModel information:"
        )

        print(
            get_model_info()
        )

    except Exception as error:

        print(
            "\nModel service error:"
        )

        print(
            error
        )