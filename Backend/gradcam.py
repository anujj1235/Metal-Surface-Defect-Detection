# Backend/gradcam.py
"""Grad-CAM helpers for Metal Vision AI.

Only call localization for a defective classifier prediction. For a good
prediction, pass predicted_status="GOOD" so no heatmap or boxes are generated.
Grad-CAM is an approximate visual explanation, not ground-truth segmentation.
"""

import base64
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image
from tensorflow.keras.applications.resnet50 import preprocess_input


IMG_SIZE = (224, 224)
MIN_CONTOUR_AREA = 40
MAX_BOXES = 5
MIN_HEATMAP_THRESHOLD = 0.25
MAX_HEATMAP_THRESHOLD = 0.70
HEATMAP_PERCENTILE = 75
MORPH_KERNEL_SIZE = 3
OVERLAY_ALPHA = 0.42


def _prepare_image(image):
    """Return original RGB pixels and a ResNet50-preprocessed tensor."""
    if isinstance(image, (str, Path)):
        with Image.open(image) as loaded:
        # Convert while the file is open.
            pil_image = loaded.convert("RGB")
    elif isinstance(image, Image.Image):
        pil_image = image.convert("RGB")
    else:
        arr = np.asarray(image)
        if arr.ndim != 3 or arr.shape[-1] != 3:
            raise ValueError("Expected an RGB image with shape (height, width, 3).")
        if arr.dtype != np.uint8:
            arr = np.nan_to_num(arr, nan=0.0, posinf=255.0, neginf=0.0)
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        pil_image = Image.fromarray(arr).convert("RGB")

    original = np.asarray(pil_image).copy()
    if original.size == 0:
        raise ValueError("The supplied image is empty.")
    resized = pil_image.resize(IMG_SIZE, Image.Resampling.LANCZOS)
    arr = np.asarray(resized, dtype=np.float32)
    arr = preprocess_input(arr)
    return original, tf.convert_to_tensor(np.expand_dims(arr, 0), dtype=tf.float32)


def _get_model_parts(model):
    """Retrieve expected layers from the saved classifier."""
    required = (
        "resnet50", "global_average_pooling", "batch_normalization",
        "dense_features", "predictions"
    )
    parts = {}
    for name in required:
        try:
            parts[name] = model.get_layer(name)
        except Exception as exc:
            raise ValueError(
                f"Required model layer '{name}' was not found. "
                f"Check the loaded model. Details: {exc}"
            ) from exc
    for name in ("data_augmentation", "dropout_1", "dropout_2"):
        try:
            parts[name] = model.get_layer(name)
        except Exception:
            parts[name] = None
    return {
        "augmentation": parts["data_augmentation"],
        "backbone": parts["resnet50"],
        "global_pool": parts["global_average_pooling"],
        "batch_norm": parts["batch_normalization"],
        "dropout_1": parts["dropout_1"],
        "dense_features": parts["dense_features"],
        "dropout_2": parts["dropout_2"],
        "predictions": parts["predictions"],
    }


def _find_last_conv_layer(model):
    """Find the final convolution layer in the nested ResNet50."""
    backbone = _get_model_parts(model)["backbone"]
    for name in ("conv5_block3_out", "conv5_block3_3_conv"):
        try:
            layer = backbone.get_layer(name)
            print(f"[Grad-CAM] Using convolution layer: {layer.name}")
            return layer
        except Exception:
            pass
    for layer in reversed(backbone.layers):
        if isinstance(layer, tf.keras.layers.Conv2D):
            print(f"[Grad-CAM] Using final Conv2D: {layer.name}")
            return layer
    raise ValueError("Could not find a convolutional layer in ResNet50.")


def find_last_conv_layer(model):
    """Public compatibility function used by the FastAPI startup check."""
    return _find_last_conv_layer(model)


def _get_prediction_index(model, input_tensor):
    """Return the predicted class index from the complete saved model."""
    predictions = model(tf.convert_to_tensor(input_tensor, dtype=tf.float32),
                        training=False)
    if len(predictions.shape) != 2:
        raise ValueError("Expected model predictions with shape (batch, classes).")
    return int(tf.argmax(predictions[0], axis=-1).numpy())


def make_gradcam_heatmap(model, input_tensor, pred_index=None):
    """Generate Grad-CAM using the selected class logit when possible."""
    input_tensor = tf.convert_to_tensor(input_tensor, dtype=tf.float32)
    p = _get_model_parts(model)

    backbone = p["backbone"]
    last_conv = _find_last_conv_layer(model)

    feature_model = tf.keras.Model(
        inputs=backbone.input,
        outputs=[last_conv.output, backbone.output],
        name="gradcam_backbone_features"
    )

    with tf.GradientTape() as tape:
        x = input_tensor

        if p["augmentation"] is not None:
            x = p["augmentation"](x, training=False)

        conv, backbone_output = feature_model(x, training=False)

        x = p["global_pool"](backbone_output)
        x = p["batch_norm"](x, training=False)

        if p["dropout_1"] is not None:
            x = p["dropout_1"](x, training=False)

        x = p["dense_features"](x)

        if p["dropout_2"] is not None:
            x = p["dropout_2"](x, training=False)

        prediction_layer = p["predictions"]

        # Select the predicted class using the complete model.
        if pred_index is None:
            full_predictions = model(input_tensor, training=False)
            pred_index = int(
                tf.argmax(full_predictions[0], axis=-1).numpy()
            )

        pred_index = int(pred_index)

        # Prefer the final Dense layer's pre-softmax score.
        # This avoids using a potentially saturated softmax probability.
        try:
            kernel = prediction_layer.kernel
            logits = tf.linalg.matmul(x, kernel)

            if prediction_layer.use_bias:
                logits = tf.nn.bias_add(logits, prediction_layer.bias)

            target_score = logits[:, pred_index]

        except (AttributeError, TypeError, ValueError):
            # Compatibility fallback for a non-standard output layer.
            scores = prediction_layer(x)
            target_score = scores[:, pred_index]

    gradients = tape.gradient(target_score, conv)

    if gradients is None:
        raise ValueError(
            "Grad-CAM gradients are unavailable. The selected class "
            "score is not connected to the chosen convolution layer."
        )

    conv = conv[0]
    gradients = gradients[0]

    weights = tf.reduce_mean(gradients, axis=(0, 1))
    heatmap = tf.reduce_sum(conv * weights, axis=-1)
    heatmap = tf.maximum(heatmap, 0.0)

    maximum = tf.reduce_max(heatmap)
    heatmap = tf.where(
        maximum > 1e-8,
        heatmap / tf.maximum(maximum, 1e-8),
        tf.zeros_like(heatmap)
    )

    result = heatmap.numpy().astype(np.float32)

    print(
        "[Grad-CAM] Heatmap diagnostics:",
        f"shape={result.shape},",
        f"min={float(np.min(result)):.8f},",
        f"max={float(np.max(result)):.8f},",
        f"nonzero_pixels={int(np.count_nonzero(result))}"
    )

    return result


def resize_heatmap(heatmap, width, height):
    """Resize a heatmap to the original image dimensions."""
    heatmap = np.asarray(heatmap, dtype=np.float32).squeeze()
    if heatmap.ndim != 2:
        raise ValueError("Expected a two-dimensional Grad-CAM heatmap.")
    resized = cv2.resize(
        heatmap, (int(width), int(height)), interpolation=cv2.INTER_CUBIC
    )
    return np.clip(resized, 0.0, 1.0)


def detect_defect_regions(heatmap, original_width, original_height):
    """Extract candidate regions; failed localization has None coverage."""
    width, height = int(original_width), int(original_height)
    if width <= 0 or height <= 0:
        raise ValueError("Original image dimensions must be positive.")
    resized = resize_heatmap(heatmap, width, height)
    empty = np.zeros((height, width), dtype=np.uint8)
    positive = resized[resized > 1e-8]
    if positive.size == 0 or float(np.max(positive)) <= 1e-8:
        return {"detected": False, "coverage_percent": None,
                "boxes": [], "mask": empty}

    adaptive = float(np.percentile(positive, HEATMAP_PERCENTILE))
    threshold = max(MIN_HEATMAP_THRESHOLD,
                    min(MAX_HEATMAP_THRESHOLD, adaptive))
    binary = (resized >= threshold).astype(np.uint8) * 255
    kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), dtype=np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < MIN_CONTOUR_AREA:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        region = resized[y:y + h, x:x + w]
        candidates.append({
            "x": int(x), "y": int(y), "width": int(w), "height": int(h),
            "area": area, "score": round(float(np.max(region)), 4)
        })
    candidates.sort(key=lambda item: item["area"], reverse=True)
    boxes = candidates[:MAX_BOXES]
    mask = np.zeros_like(binary)
    for box in boxes:
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        mask[y:y + h, x:x + w] = binary[y:y + h, x:x + w]

    detected = bool(boxes)
    coverage = None
    if detected:
        coverage = round(
            min(float(np.count_nonzero(mask)) / (width * height) * 100.0, 100.0),
            2
        )
    return {"detected": detected, "coverage_percent": coverage,
            "boxes": boxes, "mask": mask}


def _is_good_status(predicted_status):
    """Recognize the API's usual GOOD label and class-name variants."""
    status = str(predicted_status or "").strip().upper()
    return status == "GOOD" or status.endswith("_GOOD")


def localize_defect(image, model, predicted_status="DEFECTIVE", pred_index=None):
    """
    Localize only a defective prediction.

    Pass predicted_status='GOOD' for a good prediction. That returns no
    heatmap or boxes. The default remains DEFECTIVE for compatibility with
    existing calls made only from a defective-result branch.
    """
    original, tensor = _prepare_image(image)
    height, width = original.shape[:2]
    if _is_good_status(predicted_status):
        return {
            "detected": False, "coverage_percent": 0.0, "boxes": [],
            "mask": np.zeros((height, width), dtype=np.uint8),
            "heatmap": None, "skipped": True
        }

    if pred_index is None:
        pred_index = _get_prediction_index(model, tensor)
    print(f"[Grad-CAM] Target class index: {pred_index}")
    heatmap = make_gradcam_heatmap(model, tensor, pred_index)
    result = detect_defect_regions(heatmap, width, height)
    result["heatmap"] = heatmap
    result["skipped"] = False
    if result["detected"]:
        print(f"[Grad-CAM] Regions: {len(result['boxes'])}; "
              f"approximate coverage: {result['coverage_percent']}%")
    else:
        print("[Grad-CAM] No reliable box found; heatmap remains available "
              "for visualization, but coverage is unavailable.")
    return result


def draw_defect_boxes(image, boxes, color=(255, 0, 0), thickness=5):
    """Draw red boxes; empty boxes return an unchanged image."""
    if isinstance(image, (str, Path)):
        with Image.open(image) as loaded:
            arr = np.asarray(loaded.convert("RGB")).copy()
    elif isinstance(image, Image.Image):
        arr = np.asarray(image.convert("RGB")).copy()
    else:
        arr = np.asarray(image).copy()
        if arr.dtype != np.uint8:
            arr = np.clip(np.nan_to_num(
                arr, nan=0.0, posinf=255.0, neginf=0.0
            ), 0, 255).astype(np.uint8)
    if arr.ndim != 3 or arr.shape[-1] != 3:
        raise ValueError("Expected an RGB image to annotate.")
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    h, w = arr.shape[:2]
    for box in boxes or []:
        x, y = max(0, int(box["x"])), max(0, int(box["y"]))
        x2 = min(w - 1, x + max(0, int(box["width"])))
        y2 = min(h - 1, y + max(0, int(box["height"])))
        if x < w and y < h and x2 > x and y2 > y:
            cv2.rectangle(bgr, (x, y), (x2, y2), (0, 0, 255),
                          max(1, int(thickness)))
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def save_annotated_image(image, boxes, output_path):
    """Save an image with boxes; empty boxes preserve the original."""
    annotated = draw_defect_boxes(image, boxes)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    annotated.save(output_path, format="JPEG", quality=95)
    return str(output_path)


def save_heatmap(image, model, output_path, heatmap=None,
                 predicted_status="DEFECTIVE", alpha=OVERLAY_ALPHA):
    """
    Save a heatmap overlay for defective predictions only.

    A defective prediction gets a heatmap overlay even if contour detection
    found no box. A GOOD prediction is saved unchanged. Existing 3-argument
    calls remain compatible; callers should pass predicted_status explicitly
    when status is available.
    """
    original, tensor = _prepare_image(image)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if _is_good_status(predicted_status):
        Image.fromarray(original).save(output_path, format="JPEG", quality=95)
        return str(output_path)

    if heatmap is None:
        pred_index = _get_prediction_index(model, tensor)
        heatmap = make_gradcam_heatmap(model, tensor, pred_index)
    heatmap = np.asarray(heatmap, dtype=np.float32).squeeze()
    if heatmap.ndim != 2:
        Image.fromarray(original).save(output_path, format="JPEG", quality=95)
        return str(output_path)
    heatmap = np.nan_to_num(heatmap, nan=0.0, posinf=0.0, neginf=0.0)
    peak = float(np.max(heatmap))
    if peak <= 1e-8:
        Image.fromarray(original).save(output_path, format="JPEG", quality=95)
        return str(output_path)

    resized = resize_heatmap(heatmap, original.shape[1], original.shape[0])
    colored = cv2.applyColorMap(
        np.uint8(np.clip(resized * 255.0, 0, 255)), cv2.COLORMAP_JET
    )
    original_bgr = cv2.cvtColor(original, cv2.COLOR_RGB2BGR)
    overlay = cv2.addWeighted(
        original_bgr, 1.0 - float(alpha), colored, float(alpha), 0
    )
    if not cv2.imwrite(str(output_path), overlay):
        raise OSError(f"Could not save Grad-CAM heatmap to: {output_path}")
    return str(output_path)


def image_to_base64(image_path):
    """Convert an image file to a base64 data URI."""
    image_path = Path(image_path)
    with open(image_path, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")
    suffix = image_path.suffix.lower()
    mime = ("image/png" if suffix == ".png" else
            "image/jpeg" if suffix in (".jpg", ".jpeg") else
            "application/octet-stream")
    return f"data:{mime};base64,{encoded}"
