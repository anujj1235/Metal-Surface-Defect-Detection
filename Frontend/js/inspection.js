
/* =========================================================
   METAL VISION AI
   INSPECTION PAGE JAVASCRIPT
========================================================= */

console.log("INSPECTION.JS IS RUNNING");

document.addEventListener("DOMContentLoaded", function () {
    console.log("Inspection JavaScript loaded successfully.");

    /* ELEMENTS */
    const imageInput = document.getElementById("imageInput");
    const uploadArea = document.getElementById("uploadArea");
    const uploadPlaceholder = document.getElementById("uploadPlaceholder");

    const previewContainer = document.getElementById("previewContainer");
    const previewImage = document.getElementById("previewImage");
    const removeImageBtn = document.getElementById("removeImageBtn");

    const imageInformation = document.getElementById("imageInformation");
    const fileName = document.getElementById("fileName");
    const fileSize = document.getElementById("fileSize");
    const fileType = document.getElementById("fileType");

    const analyzeBtn = document.getElementById("analyzeBtn");
    const processingBox = document.getElementById("processingBox");

    const errorBox = document.getElementById("errorBox");
    const errorMessage = document.getElementById("errorMessage");

    const userAvatar = document.getElementById("userAvatar");
    const inspectionUserName = document.getElementById("inspectionUserName");

    /* BACKEND URL */
    const API_URL = "http://127.0.0.1:8000";

    let selectedFile = null;
    let isAnalyzing = false;
    let previewURL = null;
    let pipelineTimer = null;

    /* USER INFORMATION */
    function loadUser() {
        try {
            const userData = JSON.parse(
                localStorage.getItem("metalVisionCurrentUser")
            );

            if (!userData) return;

            const name = userData.name || userData.fullName || "User";

            if (inspectionUserName) {
                inspectionUserName.textContent = name;
            }

            if (userAvatar) {
                userAvatar.textContent =
                    name.trim().charAt(0).toUpperCase() || "U";
            }
        } catch (error) {
            console.warn("Unable to load user information.", error);
        }
    }

    loadUser();

    /* ERROR HELPERS */
    function hideError() {
        if (errorBox) errorBox.style.display = "none";
    }

    function showError(message) {
        if (errorBox && errorMessage) {
            errorMessage.textContent = message;
            errorBox.style.display = "flex";
            errorBox.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });
        } else {
            alert(message);
        }
    }

    /* FILE SIZE */
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + " KB";
        }
        return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    }

    /* RESET PREVIEW */
    function resetPreview() {
        selectedFile = null;

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
            previewURL = null;
        }

        if (imageInput) imageInput.value = "";

        if (uploadPlaceholder) {
            uploadPlaceholder.style.display = "flex";
        }

        if (uploadArea) {
            uploadArea.classList.remove("has-image", "dragging");
            uploadArea.style.display = "flex";
        }

        if (previewContainer) {
            previewContainer.classList.remove("show");
            previewContainer.style.display = "none";
        }

        if (previewImage) {
            previewImage.removeAttribute("src");
            previewImage.classList.remove("loaded");
        }

        if (imageInformation) {
            imageInformation.style.display = "none";
        }

        if (analyzeBtn) {
            analyzeBtn.disabled = true;
            analyzeBtn.classList.remove("ready", "analyzing");
        }

        hideError();
    }

    /* DISPLAY SELECTED IMAGE */
    function displaySelectedImage(file) {
        if (!file || isAnalyzing) return;

        hideError();

        const allowedTypes = ["image/jpeg", "image/png"];

        if (!allowedTypes.includes(file.type)) {
            showError("Please select a JPG, JPEG, or PNG image.");
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            showError("Image size must be less than 10 MB.");
            return;
        }

        if (previewURL) {
            URL.revokeObjectURL(previewURL);
        }

        selectedFile = file;
        previewURL = URL.createObjectURL(file);

        if (previewImage) {
            previewImage.onload = function () {
                previewImage.classList.add("loaded");
            };

            previewImage.onerror = function () {
                showError("Unable to display the selected image.");
            };

            previewImage.src = previewURL;
        }

        if (uploadPlaceholder) {
            uploadPlaceholder.style.display = "none";
        }

        if (uploadArea) {
            uploadArea.classList.add("has-image");
        }

        if (previewContainer) {
            previewContainer.style.display = "block";
            previewContainer.classList.add("show");
        }

        if (fileName) fileName.textContent = file.name;
        if (fileSize) fileSize.textContent = formatFileSize(file.size);

        if (fileType) {
            fileType.textContent =
                file.type === "image/png" ? "PNG" : "JPEG";
        }

        if (imageInformation) {
            imageInformation.style.display = "block";
        }

        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.classList.add("ready");
        }
    }

    /* FILE INPUT */
    if (imageInput) {
        imageInput.addEventListener("change", function (event) {
            const file = event.target.files && event.target.files[0];

            if (file) displaySelectedImage(file);
        });
    } else {
        console.error("Element #imageInput was not found.");
    }

    /* UPLOAD AREA CLICK AND DRAG/DROP */
    if (uploadArea) {
        uploadArea.addEventListener("click", function (event) {
            if (
                removeImageBtn &&
                (event.target === removeImageBtn ||
                    removeImageBtn.contains(event.target))
            ) {
                return;
            }

            if (
                !selectedFile &&
                imageInput &&
                event.target !== imageInput
            ) {
                imageInput.click();
            }
        });

        uploadArea.addEventListener("dragover", function (event) {
            event.preventDefault();
            uploadArea.classList.add("dragging");
        });

        uploadArea.addEventListener("dragleave", function () {
            uploadArea.classList.remove("dragging");
        });

        uploadArea.addEventListener("drop", function (event) {
            event.preventDefault();
            uploadArea.classList.remove("dragging");

            const file =
                event.dataTransfer.files && event.dataTransfer.files[0];

            if (file) displaySelectedImage(file);
        });
    }

    /* REMOVE IMAGE */
    if (removeImageBtn) {
        removeImageBtn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (isAnalyzing) return;

            resetPreview();
        });
    }

    /* ANALYZE IMAGE */
    async function analyzeImage(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        console.log("ANALYZE BUTTON CLICKED");
        console.log("ANALYZE BUTTON CLICKED");
        alert("Analyze button handler is running");
console.log("Selected file:", selectedFile);

        if (isAnalyzing) return;

        if (!selectedFile) {
            showError("Please select an image first.");
            return;
        }

        isAnalyzing = true;
        hideError();

        if (analyzeBtn) {
            analyzeBtn.disabled = true;
            analyzeBtn.classList.add("analyzing");
        }

        if (processingBox) {
            processingBox.style.display = "flex";
        }

        const pipelineSteps =
            document.querySelectorAll(".pipeline-step");

        pipelineSteps.forEach(function (step) {
            step.classList.remove("active", "completed");
        });

        let stepIndex = 0;

        pipelineTimer = setInterval(function () {
            if (stepIndex >= pipelineSteps.length) {
                clearInterval(pipelineTimer);
                pipelineTimer = null;
                return;
            }

            if (stepIndex > 0) {
                pipelineSteps[stepIndex - 1].classList.remove("active");
                pipelineSteps[stepIndex - 1].classList.add("completed");
            }

            pipelineSteps[stepIndex].classList.add("active");
            stepIndex++;
        }, 900);

        try {
            alert("Reached API request section");
            console.log("Sending request to:", API_URL + "/api/analyze");

            const formData = new FormData();
            formData.append("file", selectedFile);

            console.log("SENDING REQUEST NOW");
const response = await fetch(API_URL + "/api/analyze", {
    method: "POST",
    body: formData
});

            const responseText = await response.text();
            let data;

            try {
                data = JSON.parse(responseText);
            } catch {
                throw new Error(
                    "The backend returned an invalid response. HTTP " +
                    response.status
                );
            }

            if (!response.ok) {
                throw new Error(
                    typeof data.detail === "string"
                        ? data.detail
                        : "Analysis failed. HTTP " + response.status
                );
            }

            if (data.success === false) {
                throw new Error(
                    data.message || "Unable to analyze the image."
                );
            }

            clearInterval(pipelineTimer);
            pipelineTimer = null;

            pipelineSteps.forEach(function (step) {
                step.classList.remove("active");
                step.classList.add("completed");
            });

            sessionStorage.setItem(
                "selectedInspectionResult",
                JSON.stringify(data)
            );

            const reader = new FileReader();

            reader.onload = function () {
                try {
                    sessionStorage.setItem(
                        "selectedInspectionImage",
                        reader.result
                    );

                    sessionStorage.setItem(
                        "selectedInspectionFileName",
                        selectedFile.name
                    );

                    window.location.href = "result.html";
                } catch (storageError) {
                    console.error("Storage error:", storageError);
                    showError(
                        "Unable to save the result in browser storage."
                    );
                    finishAnalysis();
                }
            };

            reader.onerror = function () {
                showError("Unable to read the selected image.");
                finishAnalysis();
            };

            reader.readAsDataURL(selectedFile);

        } catch (error) {
            console.error("Inspection error:", error);

            if (error instanceof TypeError) {
                showError(
                    "Cannot connect to the backend. Make sure " +
                    "http://127.0.0.1:8000 is running and CORS allows " +
                    "requests from port 5500."
                );
            } else {
                showError(
                    error.message || "Unable to analyze the image."
                );
            }

            finishAnalysis();
        }
    }

    /* RESTORE UI AFTER ANALYSIS FAILURE */
    function finishAnalysis() {
        if (pipelineTimer) {
            clearInterval(pipelineTimer);
            pipelineTimer = null;
        }

        if (processingBox) {
            processingBox.style.display = "none";
        }

        if (analyzeBtn) {
            analyzeBtn.disabled = !selectedFile;
            analyzeBtn.classList.remove("analyzing");
        }

        isAnalyzing = false;
    }

    /* ANALYZE BUTTON */
    if (analyzeBtn) {
        analyzeBtn.addEventListener("click", analyzeImage);
    } else {
        console.error("Element #analyzeBtn was not found.");
    }

    /* INITIAL STATE */
    resetPreview();
});

