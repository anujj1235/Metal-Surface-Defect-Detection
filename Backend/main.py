# ============================================================
# INDUSTRIAL METAL SURFACE DEFECT DETECTION
# FastAPI Backend
# ============================================================

import base64
import io
import traceback
from pathlib import Path
from datetime import datetime

import numpy as np

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder

from PIL import Image

from . import model_service
from .model_service import predict_image

from . import gradcam

from .database import (
    init_database,
    save_inspection,
    get_all_inspections,
    get_single_inspection,
)

from .pdf_report import generate_pdf_report


# ============================================================
# BASE DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
MODEL_DIR = BASE_DIR / "model"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Industrial Metal Surface Defect Detection",
    description=(
        "Deep Learning based Industrial Metal Surface "
        "Defect Detection using ResNet50 and Grad-CAM."
    ),
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads"
)

app.mount(
    "/reports",
    StaticFiles(directory=str(REPORT_DIR)),
    name="reports"
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

try:
    init_database()

except Exception as error:

    print(
        "Database initialization warning:",
        repr(error)
    )


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png"
}

MAX_FILE_SIZE = 10 * 1024 * 1024


# ============================================================
# JSON / NUMPY SAFE CONVERSION
# ============================================================

def make_json_safe(value):
    """
    Recursively convert NumPy / TensorFlow / PIL-related
    values into standard Python values that FastAPI can
    serialize as JSON.

    Handles:
        numpy.ndarray
        numpy.generic
        numpy.float32
        numpy.float64
        numpy.int32
        numpy.int64
        tuples
        lists
        dictionaries
    """

    # --------------------------------------------------------
    # NumPy array
    # --------------------------------------------------------

    if isinstance(value, np.ndarray):

        return make_json_safe(
            value.tolist()
        )

    # --------------------------------------------------------
    # NumPy scalar
    # --------------------------------------------------------

    if isinstance(value, np.generic):

        return value.item()

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(value, dict):

        return {
            str(key): make_json_safe(val)
            for key, val in value.items()
        }

    # --------------------------------------------------------
    # List / tuple / set
    # --------------------------------------------------------

    if isinstance(
        value,
        (list, tuple, set)
    ):

        return [
            make_json_safe(item)
            for item in value
        ]

    # --------------------------------------------------------
    # Standard values
    # --------------------------------------------------------

    return value


# ============================================================
# MODEL
# ============================================================

def get_loaded_model():
    """
    Load and return the trained model.
    """

    return model_service.load_model()


# ============================================================
# INSPECTION ID
# ============================================================

def make_inspection_id():
    """
    Generate a unique inspection ID.
    """

    return (
        "INS_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )
    )


# ============================================================
# BASE64 IMAGE
# ============================================================

def image_to_base64(
    image_path: Path
):
    """
    Convert image file into a base64 data URL.
    """

    if image_path is None:

        return None

    if not image_path.exists():

        return None

    try:

        with open(
            image_path,
            "rb"
        ) as file:

            encoded = base64.b64encode(
                file.read()
            ).decode("utf-8")

        suffix = image_path.suffix.lower()

        if suffix == ".png":

            mime = "image/png"

        else:

            mime = "image/jpeg"

        return (
            f"data:{mime};base64,{encoded}"
        )

    except Exception as error:

        print(
            "Base64 conversion warning:",
            repr(error)
        )

        return None


# ============================================================
# SAFE RESULT
# ============================================================

def safe_result(
    value,
    default=None
):
    """
    Safely return a value.
    """

    if value is None:

        return default

    return value


# ============================================================
# SEVERITY
# ============================================================

def calculate_severity(
    coverage_percent
):
    """
    Determine defect severity from localized area.

    < 5%      -> Minor
    5-15%     -> Moderate
    >= 15%    -> High
    """

    try:

        coverage = float(
            coverage_percent
        )

    except (
        TypeError,
        ValueError
    ):

        coverage = 0.0

    if coverage < 5.0:

        return "Minor"

    if coverage < 15.0:

        return "Moderate"

    return "High"


# ============================================================
# RECOMMENDATION
# ============================================================

def get_recommendation(
    status,
    severity,
    defect_type
):
    """
    Generate practical inspection recommendation.
    """

    status = str(
        status or ""
    ).upper()

    severity = str(
        severity or ""
    ).strip()

    defect_type = str(
        defect_type or ""
    ).strip()

    if status == "GOOD":

        return (
            "No visible surface defect was classified. "
            "The inspected surface may proceed to the "
            "next inspection or production stage according "
            "to the organization's normal quality-control "
            "procedure."
        )

    if severity == "Unable to estimate":

        return (
            "The classifier predicted a surface defect, but the "
            "affected region could not be localized reliably. "
            "Have the surface reviewed by quality-control staff. "
            "Do not infer defect size or structural safety from "
            "this automated result alone."
        )

    if severity == "Minor":

        return (
            "Minor surface defect detected. Consider "
            "cleaning, polishing, or an appropriate "
            "surface treatment based on the material and "
            "defect type, followed by reinspection. "
            "If the defect appears to affect structural "
            "integrity, perform a qualified engineering "
            "inspection before reuse."
        )

    if severity == "Moderate":

        return (
            "Moderate surface defect detected. The affected "
            "area should be inspected and evaluated by the "
            "quality-control team. Consider appropriate "
            "repair or surface treatment followed by "
            "reinspection before reuse."
        )

    return (
        "Significant surface defect detected. Hold the "
        "component for detailed inspection and appropriate "
        "repair or replacement assessment. Do not assume "
        "structural safety from this automated inspection "
        "alone."
    )


# ============================================================
# REUSE GUIDANCE
# ============================================================

def get_reuse_guidance(
    status,
    severity
):
    """
    Generate reuse guidance.
    """

    status = str(
        status or ""
    ).upper()

    severity = str(
        severity or ""
    ).strip()

    if status == "GOOD":

        return (
            "No surface defect was detected by the "
            "classification model. Follow the organization's "
            "normal quality-control and acceptance procedure."
        )

    if severity == "Unable to estimate":

        return (
            "Do not release the component based only on this result. "
            "Arrange a visual or qualified quality inspection because "
            "the predicted defect region could not be localized reliably."
        )

    if severity == "Minor":

        return (
            "Reuse may be considered only after appropriate "
            "surface treatment and reinspection according "
            "to the applicable quality-control procedure."
        )

    if severity == "Moderate":

        return (
            "Do not automatically release for reuse. "
            "Perform quality inspection and any required "
            "repair before acceptance."
        )

    return (
        "Do not automatically release for reuse. "
        "Perform detailed engineering/quality inspection "
        "and determine whether repair or replacement is "
        "required."
    )


# ============================================================
# NORMALIZE DEFECT AREA
# ============================================================

def normalize_defect_area(raw_area):
    """Normalize Grad-CAM output without treating missing localization as 0%."""
    if isinstance(raw_area, np.ndarray):
        raw_area = raw_area.tolist()

    if not isinstance(raw_area, dict):
        return {
            "detected": False,
            "coverage_percent": None,
            "boxes": []
        }

    boxes = raw_area.get("boxes") or []
    if isinstance(boxes, np.ndarray):
        boxes = boxes.tolist()
    if not isinstance(boxes, (list, tuple)):
        boxes = []

    normalized_boxes = []
    for box in boxes:
        try:
            if isinstance(box, dict):
                normalized_boxes.append({
                    "x": int(float(box.get("x", 0))),
                    "y": int(float(box.get("y", 0))),
                    "width": int(float(box.get("width", box.get("w", 0)))),
                    "height": int(float(box.get("height", box.get("h", 0))))
                })
            elif isinstance(box, (list, tuple)) and len(box) >= 4:
                normalized_boxes.append({
                    "x": int(float(box[0])),
                    "y": int(float(box[1])),
                    "width": int(float(box[2])),
                    "height": int(float(box[3]))
                })
        except (TypeError, ValueError, OverflowError):
            continue

    detected = bool(raw_area.get("detected", False) or normalized_boxes)
    raw_coverage = raw_area.get("coverage_percent")
    coverage = None
    if detected and raw_coverage is not None:
        try:
            coverage = round(max(0.0, min(100.0, float(raw_coverage))), 2)
        except (TypeError, ValueError, OverflowError):
            coverage = None

    # A non-detected region must not carry a fabricated 0% estimate.
    if not detected:
        coverage = None

    return {
        "detected": detected,
        "coverage_percent": coverage,
        "boxes": normalized_boxes
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    model_loaded = False
    model_error = None

    try:

        get_loaded_model()

        model_loaded = True

    except Exception as error:

        model_error = str(error)

    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "service": (
            "Industrial Metal Surface "
            "Defect Detection"
        ),
        "model_error": model_error
    }


# ============================================================
# MODEL INFORMATION
# ============================================================

@app.get("/api/model-info")
def model_info():

    try:

        result = model_service.get_model_info()

        return make_json_safe(
            result
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# ANALYZE IMAGE
# ============================================================

@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...)
):
    """
    Analyze an uploaded metal surface image.

    Returns:

        metal type
        defect type
        status
        confidence
        defected area
        coverage
        severity
        recommendation
        reuse guidance
        original image
        annotated image
        heatmap
    """

    inspection_id = make_inspection_id()

    original_path = None
    annotated_path = None
    heatmap_path = None

    try:

        # ====================================================
        # VALIDATE FILE
        # ====================================================

        if not file.filename:

            raise HTTPException(
                status_code=400,
                detail="No file was selected."
            )

        original_filename = Path(
            file.filename
        ).name

        extension = Path(
            original_filename
        ).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported image format. "
                    "Please upload JPG, JPEG, or PNG."
                )
            )

        # ====================================================
        # READ FILE
        # ====================================================

        file_bytes = await file.read()

        if not file_bytes:

            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty."
            )

        if len(file_bytes) > MAX_FILE_SIZE:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Image size exceeds the 10 MB limit."
                )
            )

        # ====================================================
        # OPEN IMAGE
        # ====================================================

        try:

            image = Image.open(
                io.BytesIO(file_bytes)
            )

            image.load()

            image = image.convert(
                "RGB"
            )

        except Exception as error:

            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded file is not a valid "
                    f"image: {error}"
                )
            )

        # ====================================================
        # SAVE ORIGINAL
        # ====================================================

        original_path = (
            UPLOAD_DIR
            /
            f"{inspection_id}{extension}"
        )

        image.save(
            original_path
        )

        # ====================================================
        # LOAD MODEL
        # ====================================================

        model = get_loaded_model()

        # ====================================================
        # CLASSIFICATION
        # ====================================================

        prediction = predict_image(
            image
        )

        # Convert all model output to JSON-safe values
        prediction = make_json_safe(
            prediction
        )

        if not isinstance(
            prediction,
            dict
        ):

            raise RuntimeError(
                "Model prediction did not return "
                "a dictionary."
            )

        # ====================================================
        # BASIC PREDICTION VALUES
        # ====================================================

        metal_type = safe_result(
            prediction.get(
                "metal_type"
            ),
            "Unknown"
        )

        defect_type = safe_result(
            prediction.get(
                "defect_type"
            ),
            "Surface Defect"
        )

        status = str(
            safe_result(
                prediction.get(
                    "status"
                ),
                "DEFECTIVE"
            )
        ).upper()

        # ====================================================
        # CONFIDENCE
        # ====================================================

        if status == "GOOD":

            confidence = 100.0

        else:

            try:

                confidence = float(
                    prediction.get(
                        "confidence_score",
                        prediction.get(
                            "confidence",
                            0.0
                        )
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                confidence = 0.0

        confidence = max(
            0.0,
            min(
                100.0,
                confidence
            )
        )

        # ====================================================
        # GOOD RESULT
        # ====================================================

        if status == "GOOD":

            defect_type = "No Defect"

            severity = "None"

            coverage_percent = 0.0

            defect_area = {
                "detected": False,
                "coverage_percent": 0.0,
                "boxes": []
            }

            recommendation = get_recommendation(
                status="GOOD",
                severity="None",
                defect_type=defect_type
            )

            reuse_guidance = get_reuse_guidance(
                status="GOOD",
                severity="None"
            )

            # ----------------------------------------------
            # No defect boundary required.
            # ----------------------------------------------

            annotated_path = (
                UPLOAD_DIR
                /
                f"{inspection_id}_defected.jpg"
            )

            image.save(
                annotated_path,
                quality=95
            )

            heatmap_path = None

            localization_note = (
                "No defect was detected, so no defect "
                "boundary was generated."
            )

        # ====================================================
        # DEFECTIVE RESULT
        # ====================================================

        else:
            if not defect_type:
                defect_type = "Surface Defect"

            # Generate Grad-CAM once. Keep heatmap/mask as arrays
            # internally; never serialize them into the API response.
            gradcam_result = gradcam.localize_defect(
                image=image,
                model=model
            )
            if not isinstance(gradcam_result, dict):
                gradcam_result = {}

            heatmap = gradcam_result.get("heatmap")
            defect_area = normalize_defect_area({
                "detected": gradcam_result.get("detected", False),
                "coverage_percent": gradcam_result.get("coverage_percent"),
                "boxes": gradcam_result.get("boxes", [])
            })

            coverage_percent = defect_area.get("coverage_percent")
            if not defect_area.get("detected") or coverage_percent is None:
                coverage_percent = None
                severity = "Unable to estimate"
                localization_note = (
                    "A surface defect was predicted by the classifier, "
                    "but Grad-CAM could not reliably localize the region. "
                    "Defect coverage and severity are unavailable. "
                    "Grad-CAM is approximate localization, not ground-truth segmentation."
                )
            else:
                coverage_percent = max(0.0, min(100.0, float(coverage_percent)))
                coverage_percent = round(coverage_percent, 2)
                severity = calculate_severity(coverage_percent)
                localization_note = (
                    "Defect location and highlighted-pixel coverage are "
                    "estimated using Grad-CAM. This is approximate visual "
                    "localization, not ground-truth defect segmentation."
                )

            defect_area["coverage_percent"] = coverage_percent

            recommendation = get_recommendation(
                status=status,
                severity=severity,
                defect_type=defect_type
            )
            reuse_guidance = get_reuse_guidance(
                status=status,
                severity=severity
            )

            # The classifier has already predicted DEFECTIVE here.
            # Show the Grad-CAM overlay even when reliable boxes cannot be found.
            annotated_path = UPLOAD_DIR / f"{inspection_id}_defected.jpg"
            heatmap_path = None

            try:
                if heatmap is not None:
                    candidate_heatmap_path = (
                        UPLOAD_DIR / f"{inspection_id}_heatmap.jpg"
                    )
                    gradcam.save_heatmap(
                        image=image,
                        model=model,
                        output_path=str(candidate_heatmap_path),
                        heatmap=heatmap,
                        predicted_status="DEFECTIVE"
                    )

                    if candidate_heatmap_path.exists():
                        heatmap_path = candidate_heatmap_path
                        with Image.open(candidate_heatmap_path) as overlay_file:
                            annotated_image = overlay_file.convert("RGB").copy()

                        # Add red rectangles only when localization found boxes.
                        boxes = defect_area.get("boxes", [])
                        if boxes:
                            annotated_image = gradcam.draw_defect_boxes(
                                image=annotated_image,
                                boxes=boxes
                            )
                        annotated_image.save(
                            annotated_path, format="JPEG", quality=95
                        )
                    else:
                        raise OSError("Grad-CAM overlay was not saved.")
                else:
                    # No heatmap available: preserve the image without
                    # inventing a localized defect region.
                    annotated_image = gradcam.draw_defect_boxes(
                        image=image,
                        boxes=defect_area.get("boxes", [])
                    )
                    annotated_image.save(
                        annotated_path, format="JPEG", quality=95
                    )
            except Exception as annotation_error:
                print("Grad-CAM annotation warning:", repr(annotation_error))
                try:
                    fallback = gradcam.draw_defect_boxes(
                        image=image,
                        boxes=defect_area.get("boxes", [])
                    )
                    fallback.save(annotated_path, format="JPEG", quality=95)
                except Exception as fallback_error:
                    print("Fallback annotation warning:", repr(fallback_error))
                    image.save(annotated_path, format="JPEG", quality=95)

        # ====================================================
        # BASE64 IMAGES
        # ====================================================

        original_base64 = image_to_base64(
            original_path
        )

        annotated_base64 = image_to_base64(
            annotated_path
        )

        heatmap_base64 = None

        if heatmap_path is not None:

            heatmap_base64 = image_to_base64(
                heatmap_path
            )

        # ====================================================
        # IMAGE URLS
        # ====================================================

        original_url = (
            f"/uploads/{original_path.name}"
        )

        annotated_url = (
            f"/uploads/{annotated_path.name}"
        )

        heatmap_url = None

        if heatmap_path is not None:

            heatmap_url = (
                f"/uploads/{heatmap_path.name}"
            )

        # ====================================================
        # DATABASE SAVE
        # ====================================================

        try:

            save_inspection(
                inspection_id=inspection_id,
                file_name=original_filename,
                metal_type=str(
                    metal_type
                ),
                defect_type=str(
                    defect_type
                ),
                confidence=float(
                    confidence
                ),
                status=str(
                    status
                ),
                severity=str(
                    severity
                ),
                defect_location=defect_area,
                image_path=str(
                    original_path
                ),
                gradcam_path=(
                    str(annotated_path)
                    if annotated_path
                    else None
                ),
                defect_coverage=float(
                    coverage_percent if coverage_percent is not None else 0.0
                ),
                recommendation=str(
                    recommendation
                ),
                reuse_guidance=str(
                    reuse_guidance
                )
            )

        except TypeError:

            # ----------------------------------------------
            # Backward compatibility
            # ----------------------------------------------

            save_inspection(
                inspection_id=inspection_id,
                file_name=original_filename,
                metal_type=str(
                    metal_type
                ),
                defect_type=str(
                    defect_type
                ),
                confidence=float(
                    confidence
                ),
                status=str(
                    status
                ),
                severity=str(
                    severity
                ),
                defect_location=defect_area,
                image_path=str(
                    original_path
                ),
                gradcam_path=(
                    str(annotated_path)
                    if annotated_path
                    else None
                )
            )

        # ====================================================
        # RESPONSE
        # ====================================================

        result = {

            "success": True,

            "inspection_id":
                inspection_id,

            "file_name":
                original_filename,

            "metal_type":
                str(
                    metal_type
                ),

            "defect_type":
                str(
                    defect_type
                ),

            "status":
                str(
                    status
                ),

            "confidence":
                round(
                    float(
                        confidence
                    ),
                    2
                ),

            "confidence_score":
                round(
                    float(
                        confidence
                    ),
                    2
                ),

            "defected_area":
                defect_area,

            "coverage_percent": (
                round(float(coverage_percent), 2)
                if coverage_percent is not None
                else None
            ),

            "severity":
                str(
                    severity
                ),

            "recommendation":
                str(
                    recommendation
                ),

            "reuse_guidance":
                str(
                    reuse_guidance
                ),

            "localization_note":
                str(
                    localization_note
                ),

            "predicted_class":
                prediction.get(
                    "predicted_class"
                ),

            "predicted_index":
                prediction.get(
                    "predicted_index"
                ),

            "probabilities":
                prediction.get(
                    "probabilities",
                    {}
                ),

            "original_image_url":
                original_url,

            "original_image":
                original_base64,

            "annotated_image_url":
                annotated_url,

            "annotated_image":
                annotated_base64,

            "heatmap_url":
                heatmap_url,

            "heatmap_image":
                heatmap_base64
        }

        # ====================================================
        # FINAL JSON SAFETY CONVERSION
        # ====================================================

        result = make_json_safe(
            result
        )

        result = jsonable_encoder(
            result
        )

        return result

    # ========================================================
    # HTTP ERROR
    # ========================================================

    except HTTPException:

        raise

    # ========================================================
    # GENERAL ERROR
    # ========================================================

    except Exception as error:

        print(
            "\n=========================================="
        )

        print(
            "ANALYSIS ERROR"
        )

        print(
            "=========================================="
        )

        print(
            repr(error)
        )

        traceback.print_exc()

        print(
            "==========================================\n"
        )

        # ----------------------------------------------------
        # Remove partially generated files
        # ----------------------------------------------------

        for path in (
            original_path,
            annotated_path,
            heatmap_path
        ):

            try:

                if (
                    path is not None
                    and path.exists()
                ):

                    path.unlink()

            except Exception:

                pass

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# INSPECTION HISTORY
# ============================================================

@app.get("/api/history")
def inspection_history():

    try:

        result = get_all_inspections()

        return jsonable_encoder(
            make_json_safe(
                result
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# SINGLE INSPECTION
# ============================================================

@app.get(
    "/api/inspection/{inspection_id}"
)
def inspection_details(
    inspection_id: str
):

    try:

        result = get_single_inspection(
            inspection_id
        )

        if result is None:

            raise HTTPException(
                status_code=404,
                detail="Inspection not found."
            )

        result = make_json_safe(
            result
        )

        return jsonable_encoder(
            result
        )

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# GENERATE PDF REPORT
# ============================================================

@app.get(
    "/api/generate-report/{inspection_id}"
)
def generate_report(
    inspection_id: str
):

    try:

        # ====================================================
        # GET DATABASE RECORD
        # ====================================================

        record = get_single_inspection(
            inspection_id
        )

        if record is None:

            raise HTTPException(
                status_code=404,
                detail="Inspection not found."
            )

        # ====================================================
        # CONVERT RECORD
        # ====================================================

        if hasattr(
            record,
            "keys"
        ):

            result = dict(
                record
            )

        else:

            result = record

        result = make_json_safe(
            result
        )

        # ====================================================
        # IMAGE PATHS
        # ====================================================

        original_path_value = result.get(
            "image_path"
        )

        annotated_path_value = result.get(
            "gradcam_path"
        )

        if original_path_value:

            original_path = Path(
                original_path_value
            )

        else:

            original_path = (
                UPLOAD_DIR
                /
                f"{inspection_id}.jpg"
            )

        if annotated_path_value:

            annotated_path = Path(
                annotated_path_value
            )

        else:

            annotated_path = (
                UPLOAD_DIR
                /
                f"{inspection_id}_defected.jpg"
            )

        # ====================================================
        # FIND ORIGINAL IMAGE
        # ====================================================

        if not original_path.exists():

            candidates = list(
                UPLOAD_DIR.glob(
                    f"{inspection_id}.*"
                )
            )

            candidates = [
                path
                for path in candidates
                if not path.name.endswith(
                    "_defected.jpg"
                )
                and not path.name.endswith(
                    "_heatmap.jpg"
                )
            ]

            if candidates:

                original_path = candidates[0]

        # ====================================================
        # FIND ANNOTATED IMAGE
        # ====================================================

        if not annotated_path.exists():

            fallback_annotated = (
                UPLOAD_DIR
                /
                f"{inspection_id}_defected.jpg"
            )

            if fallback_annotated.exists():

                annotated_path = (
                    fallback_annotated
                )

            else:

                annotated_path = (
                    original_path
                )

        # ====================================================
        # PDF OUTPUT
        # ====================================================

        pdf_path = (
            REPORT_DIR
            /
            f"{inspection_id}_report.pdf"
        )

        # ====================================================
        # NORMALIZE PDF RESULT
        # ====================================================

        pdf_result = {

            "inspection_id":
                inspection_id,

            "file_name":
                result.get(
                    "file_name",
                    ""
                ),

            "metal_type":
                result.get(
                    "metal_type",
                    "Unknown"
                ),

            "defect_type":
                result.get(
                    "defect_type",
                    "Surface Defect"
                ),

            "status":
                result.get(
                    "status",
                    "DEFECTIVE"
                ),

            "confidence":
                result.get(
                    "confidence",
                    100.0
                    if str(
                        result.get(
                            "status",
                            ""
                        )
                    ).upper() == "GOOD"
                    else 0.0
                ),

            "confidence_score":
                result.get(
                    "confidence_score",
                    result.get(
                        "confidence",
                        0.0
                    )
                ),

            "severity":
                result.get(
                    "severity",
                    "None"
                ),

            "defected_area":
                result.get(
                    "defect_location",
                    {
                        "detected": False,
                        "coverage_percent": (
                            result.get(
                                "defect_coverage",
                                0
                            )
                        ),
                        "boxes": []
                    }
                ),

            "coverage_percent": (
                (result.get("defect_location") or {}).get("coverage_percent")
                if isinstance(result.get("defect_location"), dict)
                else result.get("defect_coverage", 0)
            ),

            "recommendation":
                result.get(
                    "recommendation",
                    ""
                ),

            "reuse_guidance":
                result.get(
                    "reuse_guidance",
                    ""
                ),

            "localization_note": (
                "No defect boundary was generated for this Good classification."
                if str(result.get("status", "")).upper() == "GOOD"
                else (
                    "The defect region could not be localized reliably; "
                    "coverage and severity are unavailable."
                    if str(result.get("severity", "")).lower() == "unable to estimate"
                    else "Defect location and highlighted-pixel coverage are estimated using Grad-CAM; this is approximate localization, not ground-truth segmentation."
                )
            )
        }

        # ====================================================
        # GOOD = 100%
        # ====================================================

        if str(
            pdf_result["status"]
        ).upper() == "GOOD":

            pdf_result[
                "confidence"
            ] = 100.0

            pdf_result[
                "confidence_score"
            ] = 100.0

            pdf_result[
                "defect_type"
            ] = "No Defect"
            pdf_result["coverage_percent"] = 0.0
            pdf_result["severity"] = "None"

        # ====================================================
        # JSON SAFE PDF DATA
        # ====================================================

        pdf_result = make_json_safe(
            pdf_result
        )

        # ====================================================
        # GENERATE PDF
        # ====================================================

        generate_pdf_report(
            output_path=str(
                pdf_path
            ),
            original_image_path=str(
                original_path
            ),
            annotated_image_path=str(
                annotated_path
            ),
            result=pdf_result
        )

        # ====================================================
        # VERIFY PDF
        # ====================================================

        if not pdf_path.exists():

            raise RuntimeError(
                "PDF report was not created."
            )

        # ====================================================
        # RETURN PDF
        # ====================================================

        return FileResponse(
            path=str(
                pdf_path
            ),
            media_type="application/pdf",
            filename=(
                f"{inspection_id}_report.pdf"
            )
        )

    except HTTPException:

        raise

    except Exception as error:

        print(
            "\n=========================================="
        )

        print(
            "PDF REPORT ERROR"
        )

        print(
            "=========================================="
        )

        print(
            repr(error)
        )

        traceback.print_exc()

        print(
            "==========================================\n"
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():

    print(
        "\n=========================================="
    )

    print(
        "Industrial Metal Surface "
        "Defect Detection"
    )

    print(
        "=========================================="
    )

    print(
        f"Base directory: {BASE_DIR}"
    )

    print(
        f"Model directory: {MODEL_DIR}"
    )

    try:

        model = get_loaded_model()

        print(
            "Model loaded successfully."
        )

        print(
            f"Model input shape: "
            f"{model.input_shape}"
        )

        try:

            layer = gradcam.find_last_conv_layer(
                model
            )

            print(
                "Grad-CAM layer:",
                layer.name
                if layer is not None
                else "Not found"
            )

        except Exception as gradcam_error:

            print(
                "Grad-CAM layer warning:",
                repr(
                    gradcam_error
                )
            )

    except Exception as error:

        print(
            "Model startup warning:",
            repr(error)
        )

    print(
        "==========================================\n"
    )


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "Backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )