/* =========================================================
   METAL VISION AI
   RESULT PAGE JAVASCRIPT
   FINAL VERSION
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    // FastAPI backend origin. Change this only if the backend host/port changes.
    const API_URL = "http://127.0.0.1:8000";

    /* =====================================================
       SESSION DATA
    ====================================================== */

    const resultDataRaw =
        sessionStorage.getItem(
            "selectedInspectionResult"
        );

    const originalImageData =
        sessionStorage.getItem(
            "selectedInspectionImage"
        );

    const storedFileName =
        sessionStorage.getItem(
            "selectedInspectionFileName"
        );


    /* =====================================================
       CHECK RESULT
    ====================================================== */

    if (!resultDataRaw) {

        console.warn(
            "No inspection result found."
        );

        window.location.href =
            "inspection.html";

        return;
    }


    let resultData;

    try {

        resultData =
            JSON.parse(resultDataRaw);

    } catch (error) {

        console.error(
            "Unable to parse inspection result:",
            error
        );

        alert(
            "Inspection result could not be loaded."
        );

        window.location.href =
            "inspection.html";

        return;
    }


    console.log(
        "Metal Vision AI Result:",
        resultData
    );


    /* =====================================================
       HELPERS
    ===================================================== */

    function getValue(...keys) {

        for (const key of keys) {

            const value =
                resultData[key];

            if (
                value !== undefined &&
                value !== null &&
                value !== ""
            ) {

                return value;
            }
        }

        return null;
    }


    function setText(id, value) {

        const element =
            document.getElementById(id);

        if (!element) {
            return;
        }

        if (
            value === undefined ||
            value === null ||
            value === ""
        ) {

            element.textContent = "—";

        } else {

            element.textContent =
                String(value);
        }
    }


    function formatConfidence(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return "—";
        }


        let number =
            Number(value);


        if (Number.isNaN(number)) {

            return String(value);
        }


        /*
         * Backend may return 0-1.
         */

        if (number <= 1) {

            number *= 100;
        }


        return number.toFixed(2) + "%";
    }


    function formatCoverage(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return "0%";
        }


        let number =
            Number(value);


        if (Number.isNaN(number)) {

            return String(value);
        }


        return number.toFixed(2) + "%";
    }


    function normalizeStatus(value) {

        if (!value) {

            return "DEFECTIVE";
        }


        const status =
            String(value)
                .trim()
                .toUpperCase();


        if (
            status === "GOOD" ||
            status === "NORMAL" ||
            status === "NO DEFECT" ||
            status === "NO_DEFECT"
        ) {

            return "GOOD";
        }


        return "DEFECTIVE";
    }


    function normalizeMetal(value) {

        if (!value) {
            return "—";
        }


        const metal =
            String(value)
                .trim()
                .toLowerCase();


        if (
            metal === "aluminum" ||
            metal === "aluminium"
        ) {

            return "Aluminium";
        }


        if (metal === "steel") {
            return "Steel";
        }


        if (metal === "copper") {
            return "Copper";
        }


        if (metal === "iron") {
            return "Iron";
        }


        return String(value);
    }


    function normalizeDefectType(
        value,
        status
    ) {

        if (status === "GOOD") {

            return "No Defect";
        }


        /*
         * Current project dataset has no verified
         * named defect categories such as rust,
         * scratch, crack, etc.
         */

        if (
            !value ||
            String(value).trim() === ""
        ) {

            return "Surface Defect";
        }


        const text =
            String(value)
                .trim()
                .toLowerCase();


        if (
            text.includes("defective") ||
            text === "defect"
        ) {

            return "Surface Defect";
        }


        if (
            text === "surface defect"
        ) {

            return "Surface Defect";
        }


        if (
            text === "good" ||
            text === "no defect"
        ) {

            return "No Defect";
        }


        return String(value);
    }


    function normalizeSeverity(
        value,
        status
    ) {

        if (status === "GOOD") {

            return "Not Applicable";
        }


        if (!value) {

            return "Not Available";
        }


        return String(value);
    }


    function normalizeLocation(value) {

        if (!value) {
            return null;
        }


        if (typeof value === "string") {

            return value;
        }


        if (
            typeof value === "object"
        ) {

            if (
                value.description
            ) {

                return value.description;
            }


            if (
                value.message
            ) {

                return value.message;
            }


            if (
                value.detected === false
            ) {

                return "No defect region detected.";
            }


            if (
                value.coverage_percent !==
                undefined
            ) {

                return (
                    "Approximate defect region identified " +
                    "using Grad-CAM."
                );
            }
        }


        return null;
    }


    function normalizeImageValue(value) {

        if (!value) {
            return null;
        }


        if (
            typeof value !== "string"
        ) {

            return null;
        }


        /*
         * Base64 image.
         */

        if (
            value.startsWith(
                "data:image"
            )
        ) {

            return value;
        }


        /*
         * Backend static URL.
         */

        if (
            value.startsWith(
                "http://"
            ) ||
            value.startsWith(
                "https://"
            )
        ) {

            return value;
        }


        if (
            value.startsWith("/")
        ) {

            // Backend static files such as /uploads/... live on FastAPI,
            // not on the frontend development server.
            return value.startsWith("/uploads/") || value.startsWith("/reports/")
                ? API_URL + value
                : value;
        }


        /*
         * Raw base64.
         */

        if (
            value.length > 100 &&
            !value.includes("\\")
        ) {

            return (
                "data:image/jpeg;base64," +
                value
            );
        }


        return value;
    }


    function getImageFromResult(
        ...keys
    ) {

        for (const key of keys) {

            const value =
                resultData[key];

            const image =
                normalizeImageValue(
                    value
                );

            if (image) {

                return image;
            }
        }


        return null;
    }


    function getCoverage() {

        const direct =
            getValue(
                "defect_coverage",
                "coverage_percent",
                "defectCoverage"
            );


        if (
            direct !== null &&
            direct !== undefined
        ) {

            return Number(direct);
        }


        const location =
            getValue(
                "defect_location",
                "defectLocation"
            );


        if (
            location &&
            typeof location === "object"
        ) {

            const nested =
                location.coverage_percent ??
                location.coveragePercent ??
                location.coverage;


            if (
                nested !== undefined &&
                nested !== null
            ) {

                return Number(nested);
            }
        }


        return 0;
    }


    /* =====================================================
       RESULT VALUES
    ===================================================== */

    const inspectionId =
        getValue(
            "inspection_id",
            "inspectionId",
            "id"
        );


    const status =
        normalizeStatus(
            getValue(
                "status",
                "analysis_status",
                "result_status"
            )
        );


    const metalType =
        normalizeMetal(
            getValue(
                "metal_type",
                "metalType"
            )
        );


    const defectType =
        normalizeDefectType(
            getValue(
                "defect_type",
                "defectType",
                "prediction",
                "class_name"
            ),
            status
        );


    const confidence =
        status === "GOOD"
            ? 100
            : getValue(
                "confidence",
                "confidence_score",
                "prediction_confidence"
            );


    const coverage =
        getCoverage();


    const severity =
        normalizeSeverity(
            getValue(
                "severity",
                "estimated_severity"
            ),
            status
        );


    const rawLocation =
        getValue(
            "defect_location",
            "defectLocation",
            "location",
            "defected_area",
            "defectedArea"
        );


    const locationText =
        normalizeLocation(
            rawLocation
        );


    const defectedArea =
        status === "GOOD"
            ? "No defect detected"
            : (
                locationText ||
                "Approximate defect region identified by Grad-CAM"
            );


    const modelName =
        getValue(
            "model",
            "model_name",
            "modelName"
        ) || "ResNet50";


    const actualFileName =
        getValue(
            "file_name",
            "fileName"
        ) ||
        storedFileName ||
        "Inspection image";


    const recommendation =
        getValue(
            "recommendation",
            "solution",
            "recommended_action"
        );


    const reuseGuidance =
        getValue(
            "reuse_guidance",
            "reuseGuidance",
            "inspection_guidance"
        );


    /* =====================================================
       IMAGE DATA
    ===================================================== */

    const originalResultImage =
        getImageFromResult(
            "image_path",
            "image_url",
            "original_image",
            "originalImage",
            "original_image_path"
        );


    const annotatedResultImage =
        getImageFromResult(
            "annotated_image_path",
            "annotated_image",
            "annotatedImage",
            "gradcam_path",
            "gradcam_image",
            "gradcamImage",
            "gradcam"
        );


    const originalImage =
        originalImageData ||
        originalResultImage;


    const annotatedImage =
        annotatedResultImage;


    /* =====================================================
       MAIN RESULT
    ===================================================== */

    setText(
        "inspectionId",
        inspectionId
    );


    setText(
        "resultStatus",
        status
    );


    setText(
        "summaryMetalType",
        metalType
    );


    setText(
        "defectType",
        defectType
    );


    setText(
        "confidence",
        formatConfidence(confidence)
    );


    setText(
        "modelName",
        modelName
    );


    setText(
        "resultFileName",
        actualFileName
    );


    /* =====================================================
       ANALYSIS DETAILS
    ===================================================== */

    setText(
        "detailMetalType",
        metalType
    );


    setText(
        "detailDefectType",
        defectType
    );


    setText(
        "detailDefectedArea",
        defectedArea
    );


    setText(
        "detailCoverage",
        formatCoverage(coverage)
    );


    setText(
        "detailConfidence",
        formatConfidence(confidence)
    );


    setText(
        "detailSeverity",
        severity
    );


    /* =====================================================
       ORIGINAL IMAGE
    ===================================================== */

    const originalElement =
        document.getElementById(
            "originalImage"
        );


    const originalPlaceholder =
        document.getElementById(
            "originalPlaceholder"
        );


    if (
        originalElement &&
        originalImage
    ) {

        originalElement.src =
            originalImage;

        originalElement.style.display =
            "block";


        if (originalPlaceholder) {

            originalPlaceholder.style.display =
                "none";
        }

    } else {

        if (originalElement) {

            originalElement.style.display =
                "none";
        }


        if (originalPlaceholder) {

            originalPlaceholder.style.display =
                "flex";
        }
    }


    /* =====================================================
       ANNOTATED IMAGE
    ===================================================== */

    const annotatedElement =
        document.getElementById(
            "annotatedImage"
        );


    const annotatedPlaceholder =
        document.getElementById(
            "annotatedPlaceholder"
        );


    if (
        annotatedElement &&
        annotatedImage &&
        status !== "GOOD"
    ) {

        annotatedElement.src =
            annotatedImage;

        annotatedElement.style.display =
            "block";


        if (annotatedPlaceholder) {

            annotatedPlaceholder.style.display =
                "none";
        }

    } else {

        if (annotatedElement) {

            annotatedElement.style.display =
                "none";
        }


        if (annotatedPlaceholder) {

            annotatedPlaceholder.style.display =
                "flex";
        }
    }


    /* =====================================================
       ANNOTATION CAPTION
    ===================================================== */

    setText(
        "annotationCaption",
        status === "GOOD"
            ? "No defect region detected"
            : `Approximate defect region — ${formatCoverage(coverage)} of image`
    );


    /* =====================================================
       STATUS CARD
    ===================================================== */

    const statusCard =
        document.querySelector(
            ".result-status-card"
        );


    const statusIcon =
        document.getElementById(
            "resultStatusIcon"
        );


    const statusDescription =
        document.getElementById(
            "resultStatusDescription"
        );


    if (status === "GOOD") {

        if (statusCard) {

            statusCard.classList.add(
                "status-good"
            );
        }


        if (statusIcon) {

            statusIcon.textContent =
                "✓";
        }


        if (statusDescription) {

            statusDescription.textContent =
                "No surface defect detected by the trained AI model.";
        }

    } else {

        if (statusCard) {

            statusCard.classList.remove(
                "status-good"
            );
        }


        if (statusIcon) {

            statusIcon.textContent =
                "!";
        }


        if (statusDescription) {

            statusDescription.textContent =
                "Surface defect identified by the trained AI model.";
        }
    }


    /* =====================================================
       AI INTERPRETATION
    ===================================================== */

    let interpretationText;


    if (status === "GOOD") {

        interpretationText =
            `The AI model analyzed the uploaded ${metalType.toLowerCase()} surface image and classified it as No Defect with a confidence score of ${formatConfidence(confidence)}. No defect localization was required.`;

    } else {

        interpretationText =
            `The AI model analyzed the uploaded ${metalType.toLowerCase()} surface image and classified it as Surface Defect with a confidence score of ${formatConfidence(confidence)}. The estimated affected area is ${formatCoverage(coverage)}, with an estimated severity of ${severity}.`;
    }


    setText(
        "aiInterpretation",
        interpretationText
    );


    /* =====================================================
       RECOMMENDATION
    ===================================================== */

    let recommendationText;


    if (status === "GOOD") {

        recommendationText =
            recommendation ||
            "No corrective action is indicated from this image-based inspection. Continue routine inspection and maintenance procedures.";

    } else if (
        recommendation
    ) {

        recommendationText =
            recommendation;

    } else if (
        String(severity)
            .toLowerCase()
            .includes("minor")
    ) {

        recommendationText =
            "For a minor surface indication, cleaning or suitable surface treatment/polishing may be considered, followed by reinspection. This image-based result should not be treated as a guarantee of structural safety.";

    } else if (
        String(severity)
            .toLowerCase()
            .includes("moderate")
    ) {

        recommendationText =
            "Inspect the affected region more closely and consider appropriate surface treatment or maintenance according to the applicable industrial procedure. Reinspect after corrective action.";

    } else {

        recommendationText =
            "The detected surface indication should be reviewed by an appropriate inspection or maintenance professional before further use. Additional inspection may be required to determine the actual condition of the material.";
    }


    setText(
        "recommendationText",
        recommendationText
    );


    /* =====================================================
       REUSE GUIDANCE
    ===================================================== */

    const finalReuseGuidance =
        reuseGuidance ||
        (
            status === "GOOD"
                ? "The image shows no detected surface defect. Continue normal inspection procedures."
                : "AI image classification is an assistive inspection result. Final reuse or service decisions should follow the applicable engineering and safety inspection procedure."
        );


    setText(
        "reuseGuidanceText",
        finalReuseGuidance
    );


    /* =====================================================
       LOCALIZATION NOTE
    ===================================================== */

    const localizationNote =
        document.getElementById(
            "localizationNote"
        );


    if (localizationNote) {

        if (status === "GOOD") {

            localizationNote.innerHTML =
                `<strong>Note:</strong> No defect region was identified because the image was classified as No Defect.`;

        } else {

            localizationNote.innerHTML =
                `<strong>Note:</strong> Grad-CAM provides an approximate visualization of important regions and does not represent an exact defect boundary.`;
        }
    }


    /* =====================================================
       RESULT PREVIEW DATA
    ===================================================== */

    setText(
        "previewInspectionId",
        inspectionId
    );


    setText(
        "previewFileName",
        actualFileName
    );


    setText(
        "previewModelName",
        modelName
    );


    setText(
        "previewStatus",
        status
    );


    setText(
        "previewMetalType",
        metalType
    );


    setText(
        "previewDefectType",
        defectType
    );


    setText(
        "previewConfidence",
        formatConfidence(confidence)
    );


    setText(
        "previewDefectedArea",
        defectedArea
    );


    setText(
        "previewCoverage",
        formatCoverage(coverage)
    );


    setText(
        "previewSeverity",
        severity
    );


    setText(
        "previewLocalization",
        defectedArea
    );


    setText(
        "previewInterpretation",
        interpretationText
    );


    setText(
        "previewRecommendation",
        recommendationText
    );


    /* =====================================================
       PREVIEW ORIGINAL IMAGE
    ===================================================== */

    const previewOriginalImage =
        document.getElementById(
            "previewOriginalImage"
        );


    if (
        previewOriginalImage &&
        originalImage
    ) {

        previewOriginalImage.src =
            originalImage;

        previewOriginalImage.style.display =
            "block";
    }


    /* =====================================================
       PREVIEW ANNOTATED IMAGE
    ===================================================== */

    const previewAnnotatedImage =
        document.getElementById(
            "previewAnnotatedImage"
        );


    if (
        previewAnnotatedImage &&
        annotatedImage &&
        status !== "GOOD"
    ) {

        previewAnnotatedImage.src =
            annotatedImage;

        previewAnnotatedImage.style.display =
            "block";

    } else if (previewAnnotatedImage) {

        previewAnnotatedImage.style.display =
            "none";
    }


    /* =====================================================
       RESULT PREVIEW MODAL
    ===================================================== */

    const previewButton =
        document.getElementById(
            "resultPreviewBtn"
        );


    const previewModal =
        document.getElementById(
            "resultPreviewModal"
        );


    const closePreview =
        document.getElementById(
            "closeResultPreview"
        );


    const closePreviewBottom =
        document.getElementById(
            "closeResultPreviewBottom"
        );


    function openPreview() {

        if (!previewModal) {
            return;
        }


        previewModal.classList.add(
            "active"
        );


        previewModal.style.display =
            "flex";

        previewModal.style.visibility =
            "visible";

        previewModal.style.opacity =
            "1";

        previewModal.style.pointerEvents =
            "auto";


        document.body.classList.add(
            "preview-open"
        );


        document.body.style.overflow =
            "hidden";
    }


    function closePreviewModal() {

        if (!previewModal) {
            return;
        }


        previewModal.classList.remove(
            "active"
        );


        previewModal.style.display =
            "none";

        previewModal.style.visibility =
            "hidden";

        previewModal.style.opacity =
            "0";

        previewModal.style.pointerEvents =
            "none";


        document.body.classList.remove(
            "preview-open"
        );


        document.body.style.overflow =
            "";
    }


    if (previewButton) {

        previewButton.addEventListener(
            "click",
            openPreview
        );
    }


    if (closePreview) {

        closePreview.addEventListener(
            "click",
            closePreviewModal
        );
    }


    if (closePreviewBottom) {

        closePreviewBottom.addEventListener(
            "click",
            closePreviewModal
        );
    }


    if (previewModal) {

        const overlay =
            previewModal.querySelector(
                ".result-preview-overlay"
            );


        if (overlay) {

            overlay.addEventListener(
                "click",
                closePreviewModal
            );
        }
    }


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape" &&
                previewModal &&
                previewModal.classList.contains(
                    "active"
                )
            ) {

                closePreviewModal();
            }
        }
    );


    if (previewModal) {

        previewModal.style.display =
            "none";

        previewModal.style.visibility =
            "hidden";

        previewModal.style.opacity =
            "0";

        previewModal.style.pointerEvents =
            "none";
    }


    /* =====================================================
       PDF GENERATION
    ===================================================== */

    async function generatePDF() {

        if (!inspectionId) {

            alert(
                "Inspection ID is not available."
            );

            return;
        }


        const pdfButtons = [
            document.getElementById(
                "generatePdfBtn"
            ),
            document.getElementById(
                "previewGeneratePdfBtn"
            )
        ].filter(Boolean);


        const originalTexts =
            pdfButtons.map(
                button =>
                    button.innerHTML
            );


        try {

            pdfButtons.forEach(
                button => {

                    button.disabled =
                        true;

                    button.innerHTML =
                        "Generating...";
                }
            );


            const response =
                await fetch(
                    API_URL + "/api/generate-report/" +
                    encodeURIComponent(
                        inspectionId
                    ),
                    {
                        method: "GET"
                    }
                );


            if (!response.ok) {

                let message =
                    `PDF generation failed: ${response.status}`;

                try {

                    const errorData =
                        await response.json();

                    if (errorData.detail) {

                        message =
                            errorData.detail;
                    }

                } catch {
                    /* Ignore non-JSON errors */
                }


                throw new Error(
                    message
                );
            }


            const blob =
                await response.blob();


            const downloadUrl =
                window.URL.createObjectURL(
                    blob
                );


            const link =
                document.createElement(
                    "a"
                );


            link.href =
                downloadUrl;


            link.download =
                `Metal_Vision_Report_${inspectionId}.pdf`;


            document.body.appendChild(
                link
            );


            link.click();


            link.remove();


            window.URL.revokeObjectURL(
                downloadUrl
            );


        } catch (error) {

            console.error(
                "PDF generation error:",
                error
            );


            alert(
                error.message ||
                "Unable to generate the PDF report."
            );

        } finally {

            pdfButtons.forEach(
                (button, index) => {

                    button.disabled =
                        false;

                    button.innerHTML =
                        originalTexts[index];
                }
            );
        }
    }


    const generatePdfButton =
        document.getElementById(
            "generatePdfBtn"
        );


    const previewGeneratePdfButton =
        document.getElementById(
            "previewGeneratePdfBtn"
        );


    if (generatePdfButton) {

        generatePdfButton.addEventListener(
            "click",
            generatePDF
        );
    }


    if (previewGeneratePdfButton) {

        previewGeneratePdfButton.addEventListener(
            "click",
            generatePDF
        );
    }


    /* =====================================================
       NEW INSPECTION
    ===================================================== */

    const backInspectionButton =
        document.getElementById(
            "backInspectionBtn"
        );


    const newInspectionButton =
        document.getElementById(
            "newInspectionBtn"
        );


    function goToNewInspection() {

        sessionStorage.removeItem(
            "selectedInspectionResult"
        );

        sessionStorage.removeItem(
            "selectedInspectionImage"
        );

        sessionStorage.removeItem(
            "selectedInspectionFileName"
        );

        sessionStorage.removeItem(
            "selectedGradcamImage"
        );


        window.location.href =
            "inspection.html";
    }


    if (backInspectionButton) {

        backInspectionButton.addEventListener(
            "click",
            goToNewInspection
        );
    }


    if (newInspectionButton) {

        newInspectionButton.addEventListener(
            "click",
            goToNewInspection
        );
    }


    /* =====================================================
       USER INFORMATION
    ===================================================== */

    let userName =
        "User";


    /*
     * Support the same storage key used
     * by the inspection page first.
     */

    const currentUser =
        localStorage.getItem(
            "metalVisionCurrentUser"
        );


    const legacyUser =
        localStorage.getItem(
            "loggedInUser"
        );


    const storedUser =
        currentUser ||
        legacyUser;


    if (storedUser) {

        try {

            const userData =
                JSON.parse(
                    storedUser
                );


            userName =
                userData.name ||
                userData.fullName ||
                userData.username ||
                userData.email ||
                "User";

        } catch {

            userName =
                storedUser;
        }
    }


    setText(
        "resultUserName",
        userName
    );


    const userAvatar =
        document.getElementById(
            "userAvatar"
        );


    if (userAvatar) {

        userAvatar.textContent =
            userName
                .trim()
                .charAt(0)
                .toUpperCase() ||
            "U";
    }


    /* =====================================================
       FINAL DEBUG
    ===================================================== */

    console.log(
        "--------------------------------------"
    );

    console.log(
        "METAL VISION AI RESULT"
    );

    console.log(
        "Inspection ID:",
        inspectionId
    );

    console.log(
        "Metal Type:",
        metalType
    );

    console.log(
        "Status:",
        status
    );

    console.log(
        "Defect Type:",
        defectType
    );

    console.log(
        "Confidence:",
        formatConfidence(confidence)
    );

    console.log(
        "Defected Area:",
        defectedArea
    );

    console.log(
        "Coverage:",
        formatCoverage(coverage)
    );

    console.log(
        "Severity:",
        severity
    );

    console.log(
        "Recommendation:",
        recommendationText
    );

    console.log(
        "Model:",
        modelName
    );

    console.log(
        "Original Image:",
        Boolean(originalImage)
    );

    console.log(
        "Annotated Image:",
        Boolean(annotatedImage)
    );

    console.log(
        "--------------------------------------"
    );

});