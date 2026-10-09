# ============================================================
# Metal Vision AI - PDF Inspection Report
# ============================================================

from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as ReportLabImage,
    HRFlowable
)


# ============================================================
# HELPERS
# ============================================================

def _safe_text(value, default="Not available"):
    """Return escaped text safe to place inside a ReportLab Paragraph."""
    if value is None or str(value).strip() == "":
        value = default
    return escape(str(value))


def _format_percent(value):
    """Format a percentage while preserving unavailable values as unknown."""
    if value is None or value == "":
        return "Unable to estimate"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unable to estimate"

    if number < 0:
        return "Unable to estimate"

    return f"{number:.2f}%"


def _fit_image(path, max_width, max_height):
    """Create a ReportLab image fitted inside a box without stretching."""
    reader = ImageReader(str(path))
    image_width, image_height = reader.getSize()

    if not image_width or not image_height:
        return None

    scale = min(
        max_width / float(image_width),
        max_height / float(image_height)
    )

    return ReportLabImage(
        str(path),
        width=image_width * scale,
        height=image_height * scale
    )


def _image_cell(path, caption, styles, max_width=76 * mm, max_height=62 * mm):
    """Build an image and caption, or a helpful placeholder if unavailable."""
    if path and Path(path).is_file():
        try:
            image = _fit_image(path, max_width, max_height)
            if image is not None:
                image.hAlign = "CENTER"
                return [
                    Paragraph(f"<b>{_safe_text(caption)}</b>", styles["ImageCaption"]),
                    Spacer(1, 4),
                    image
                ]
        except Exception:
            pass

    return [
        Paragraph(f"<b>{_safe_text(caption)}</b>", styles["ImageCaption"]),
        Spacer(1, 8),
        Paragraph("Image unavailable", styles["NormalReport"])
    ]


# ============================================================
# PDF REPORT GENERATOR
# ============================================================

def generate_pdf_report(
    output_path: str,
    original_image_path: str,
    annotated_image_path: str,
    result: dict
):
    """
    Generate a complete Metal Surface Inspection PDF.

    Includes the original and annotated images, prediction details,
    defect coverage and severity where available, recommendations,
    reuse guidance, and a Grad-CAM localization disclaimer.

    Test accuracy is intentionally not included.
    """

    result = result if isinstance(result, dict) else {}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # DOCUMENT AND STYLES
    # ========================================================

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=24,
        spaceAfter=10
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        "NormalReport",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        wordWrap="CJK"
    )

    caption_style = ParagraphStyle(
        "ImageCaption",
        parent=normal_style,
        alignment=TA_CENTER,
        fontSize=9,
        leading=12
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=normal_style,
        fontSize=8,
        leading=11
    )

    # Make helper styles available to the image helper.
    styles.add(caption_style)

    story = []

    # ========================================================
    # TITLE
    # ========================================================

    story.append(Paragraph("METAL SURFACE INSPECTION REPORT", title_style))
    story.append(
        Paragraph(
            datetime.now().strftime("Inspection Date: %d-%m-%Y %H:%M:%S"),
            normal_style
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Spacer(1, 4))

    # ========================================================
    # ORIGINAL AND ANNOTATED IMAGES
    # ========================================================

    story.append(Paragraph("Inspection Images", heading_style))

    original_cell = _image_cell(
        original_image_path,
        "Original Uploaded Image",
        styles
    )

    # If the annotated image path is missing, the report should still show
    # the original image and explicitly indicate that annotation is unavailable.
    annotated_cell = _image_cell(
        annotated_image_path,
        "Annotated Image / Grad-CAM Localization",
        styles
    )

    image_table = Table(
        [[original_cell, annotated_cell]],
        colWidths=[82.5 * mm, 82.5 * mm],
        hAlign="CENTER"
    )

    image_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(image_table)
    story.append(Spacer(1, 8))

    # ========================================================
    # RESULT DATA
    # ========================================================

    story.append(Paragraph("Inspection Result", heading_style))

    metal_type = result.get("metal_type", "Unknown")
    defect_type = result.get("defect_type", "Surface Defect")
    status = str(result.get("status", "UNKNOWN")).strip().upper()

    confidence = result.get(
        "confidence_score",
        result.get("confidence", 0)
    )

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    # Support either a 0-1 probability or a 0-100 percentage.
    if 0 <= confidence <= 1:
        confidence *= 100

    # Project presentation rule: Good predictions are displayed as 100%.
    if status == "GOOD":
        confidence = 100.0

    defect_info = result.get("defected_area", {})
    if not isinstance(defect_info, dict):
        defect_info = {}

    raw_coverage = defect_info.get(
        "coverage_percent",
        result.get("coverage_percent", result.get("defect_coverage"))
    )

    if status == "GOOD":
        coverage = 0.0
        detected = False
        area_text = "None — no defect predicted"
    else:
        try:
            coverage = (
                None if raw_coverage is None or raw_coverage == ""
                else float(raw_coverage)
            )
            if coverage is not None and coverage < 0:
                coverage = None
        except (TypeError, ValueError):
            coverage = None

        detected = bool(defect_info.get("detected", False))

        if detected and coverage is not None:
            area_text = (
                "Approximate highlighted region "
                f"({coverage:.2f}% of visible image area)"
            )
        else:
            area_text = "Not reliably localized"

    data = [
        ["Metal Type", _safe_text(metal_type)],
        ["Defect Type", _safe_text(defect_type)],
        ["Status", _safe_text(status)],
        ["Confidence Score", f"{confidence:.2f}%"],
        ["Defected Area", _safe_text(area_text)],
    ]

    result_table = Table(data, colWidths=[55 * mm, 110 * mm])
    result_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )
    story.append(result_table)

    # ========================================================
    # DEFECT ASSESSMENT
    # ========================================================

    story.append(Paragraph("Defect Assessment", heading_style))

    recommendation = result.get("recommendation", {})
    if not isinstance(recommendation, dict):
        recommendation = {}

    if status == "GOOD":
        severity = "Not Applicable"
    else:
        severity = recommendation.get(
            "severity",
            result.get("severity", "Unable to estimate")
        )
        if not detected or coverage is None:
            severity = "Unable to estimate"

    assessment_data = [
        ["Severity", _safe_text(severity)],
        ["Visible Defect Coverage", _safe_text(_format_percent(coverage))],
    ]

    assessment_table = Table(
        assessment_data,
        colWidths=[55 * mm, 110 * mm]
    )
    assessment_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )
    story.append(assessment_table)

    # ========================================================
    # RECOMMENDED SOLUTION
    # ========================================================

    story.append(Paragraph("Recommended Solution", heading_style))

    solution = recommendation.get(
        "solution",
        result.get("recommendation", "No recommendation available.")
    )

    if isinstance(solution, dict):
        solution = solution.get("solution", "No recommendation available.")

    story.append(Paragraph(_safe_text(solution), normal_style))

    # ========================================================
    # REUSE GUIDANCE
    # ========================================================

    story.append(Paragraph("Reuse Guidance", heading_style))

    reuse_guidance = recommendation.get(
        "reuse_guidance",
        result.get("reuse_guidance", "Further inspection may be required.")
    )

    story.append(Paragraph(_safe_text(reuse_guidance), normal_style))

    # ========================================================
    # LOCALIZATION NOTE
    # ========================================================

    story.append(Paragraph("Localization Note", heading_style))

    if status == "GOOD":
        localization_note = (
            "The model predicted no surface defect for this image. "
            "No defect region is reported."
        )
    elif detected and coverage is not None:
        localization_note = (
            "The highlighted region is generated using Grad-CAM based on "
            "the model's visual attention. It is an approximate region, not "
            "an exact ground-truth physical boundary or a pixel-level "
            "measurement."
        )
    else:
        localization_note = (
            "The model predicted a surface defect, but a reliable region "
            "could not be localized. Defect coverage and severity are "
            "therefore reported as unable to estimate."
        )

    story.append(Paragraph(_safe_text(localization_note), normal_style))

    # ========================================================
    # DISCLAIMER
    # ========================================================

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5))
    story.append(Spacer(1, 5))

    disclaimer = (
        "<b>Important:</b> This report provides an image-based surface "
        "assessment. Grad-CAM localization, when shown, is approximate. "
        "Final reuse, structural integrity, and safety decisions must be "
        "confirmed through appropriate physical or engineering inspection."
    )
    story.append(Paragraph(disclaimer, disclaimer_style))

    # ========================================================
    # BUILD PDF
    # ========================================================

    document.build(story)
    return str(output_path)
