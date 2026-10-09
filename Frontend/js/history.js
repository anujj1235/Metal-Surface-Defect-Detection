/* =========================================================
   METAL VISION AI
   PROFESSIONAL INSPECTION HISTORY
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    const API_URL = "http://127.0.0.1:8000";


    /* =====================================================
       USER INFORMATION
    ===================================================== */

    const storedUser =
        localStorage.getItem("metalVisionCurrentUser");

    let userName = "User";

    if (storedUser) {

        try {

            const user =
                JSON.parse(storedUser);

            if (user && user.name) {
                userName = user.name;
            }

        } catch (error) {

            console.warn(
                "Unable to read user information."
            );

        }

    }


    const userNameElement =
        document.getElementById("historyUserName");

    const userAvatar =
        document.getElementById("userAvatar");


    if (userNameElement) {
        userNameElement.textContent = userName;
    }


    if (userAvatar) {

        userAvatar.textContent =
            userName.charAt(0).toUpperCase();

    }



    /* =====================================================
       LOGOUT
    ===================================================== */

    const logoutBtn =
        document.getElementById("logoutBtn");


    if (logoutBtn) {

        logoutBtn.addEventListener(
            "click",
            () => {

                localStorage.removeItem(
                    "metalVisionLoggedIn"
                );

                localStorage.removeItem(
                    "metalVisionCurrentUser"
                );

                window.location.href =
                    "login.html";

            }
        );

    }



    /* =====================================================
       MOBILE SIDEBAR
    ===================================================== */

    const mobileMenuBtn =
        document.getElementById("mobileMenuBtn");

    const sidebar =
        document.getElementById("sidebar");


    if (mobileMenuBtn && sidebar) {

        mobileMenuBtn.addEventListener(
            "click",
            () => {

                sidebar.classList.toggle(
                    "open"
                );

            }
        );

    }



    /* =====================================================
       ELEMENTS
    ===================================================== */

    const searchInput =
        document.getElementById(
            "historySearch"
        );

    const conditionFilter =
        document.getElementById(
            "conditionFilter"
        );

    const metalFilter =
        document.getElementById(
            "metalFilter"
        );

    const fromDate =
        document.getElementById(
            "fromDate"
        );

    const toDate =
        document.getElementById(
            "toDate"
        );

    const clearFiltersBtn =
        document.getElementById(
            "clearFiltersBtn"
        );

    const emptyClearBtn =
        document.getElementById(
            "emptyClearBtn"
        );

    const tableBody =
        document.getElementById(
            "historyTableBody"
        );

    const historyEmpty =
        document.getElementById(
            "historyEmpty"
        );

    const visibleRecords =
        document.getElementById(
            "visibleRecords"
        );

    const recordsCount =
        document.getElementById(
            "recordsCount"
        );

    const historyTotal =
        document.getElementById(
            "historyTotal"
        );

    const historyGood =
        document.getElementById(
            "historyGood"
        );

    const historyDefective =
        document.getElementById(
            "historyDefective"
        );



    /* =====================================================
       DATA
    ===================================================== */

    let inspectionRecords = [];



    /* =====================================================
       NORMALIZE RECORD
    ===================================================== */

    function normalizeRecord(record) {

        const rawStatus =
            String(
                record.status ||
                record.condition ||
                "DEFECTIVE"
            ).toUpperCase();


        const status =
            rawStatus === "GOOD"
                ? "GOOD"
                : "DEFECTIVE";


        let metalType =
            record.metal_type ||
            record.metalType ||
            "Unknown";


        metalType =
            normalizeMetalName(
                metalType
            );


        let dateTime = null;


        if (record.created_at) {

            const parsed =
                new Date(
                    record.created_at
                );

            if (
                !Number.isNaN(
                    parsed.getTime()
                )
            ) {

                dateTime = parsed;

            }

        }


        let date = "N/A";
        let time = "N/A";


        if (dateTime) {

            date =
                dateTime.toLocaleDateString(
                    "en-IN",
                    {
                        day: "2-digit",
                        month: "short",
                        year: "numeric"
                    }
                );


            time =
                dateTime.toLocaleTimeString(
                    "en-IN",
                    {
                        hour: "2-digit",
                        minute: "2-digit",
                        hour12: true
                    }
                );

        }


        return {

            id:
                String(
                    record.inspection_id ||
                    record.id ||
                    "N/A"
                ),

            metalType:

                metalType,

            status:

                status,

            date:

                date,

            time:

                time,

            dateObject:

                dateTime,

            fileName:

                record.file_name ||
                record.filename ||
                "Uploaded image"

        };

    }



    /* =====================================================
       METAL NAME
    ===================================================== */

    function normalizeMetalName(
        metal
    ) {

        const value =
            String(
                metal || ""
            ).toLowerCase();


        if (
            value.includes(
                "aluminium"
            ) ||
            value.includes(
                "aluminum"
            )
        ) {

            return "Aluminium";

        }


        if (
            value.includes(
                "steel"
            )
        ) {

            return "Steel";

        }


        if (
            value.includes(
                "iron"
            )
        ) {

            return "Iron";

        }


        return "Unknown";

    }



    /* =====================================================
       LOAD HISTORY
    ===================================================== */

    async function loadHistory() {

        try {

            console.log(
                "Loading inspection history..."
            );


            const response =
                await fetch(
                    `${API_URL}/api/history`,
                    {
                        method: "GET",
                        headers: {
                            "Accept":
                                "application/json"
                        }
                    }
                );


            if (!response.ok) {

                throw new Error(
                    `History API returned ${response.status}`
                );

            }


            const data =
                await response.json();


            // The FastAPI route may return a raw list, or a wrapped
            // object depending on the backend version.
            const records = Array.isArray(data)
                ? data
                : (data && Array.isArray(data.records)
                    ? data.records
                    : []);

            if (!Array.isArray(data) && data && data.success === false) {
                throw new Error(data.message || "Unable to load inspection history.");
            }

            inspectionRecords = records.map(normalizeRecord);


            /*
             * Newest inspection first.
             */

            inspectionRecords.sort(
                (
                    a,
                    b
                ) => {

                    if (
                        a.dateObject &&
                        b.dateObject
                    ) {

                        return (
                            b.dateObject -
                            a.dateObject
                        );

                    }

                    return 0;

                }
            );


            updateSummary(
                inspectionRecords
            );


            renderRecords(
                inspectionRecords
            );


        } catch (error) {

            console.error(
                "Unable to load inspection history:",
                error
            );


            inspectionRecords = [];


            if (tableBody) {
                tableBody.innerHTML = "";
            }


            if (historyEmpty) {

                historyEmpty.style.display =
                    "block";

            }


            if (visibleRecords) {

                visibleRecords.textContent =
                    "0";

            }


            if (recordsCount) {

                recordsCount.textContent =
                    "0";

            }


            updateSummary([]);


            const emptyMessage =
                historyEmpty
                    ? historyEmpty.querySelector("p")
                    : null;


            if (emptyMessage) {

                emptyMessage.textContent =
                    "Unable to load inspection history. Please make sure the AI server is running.";

            }

        }

    }



    /* =====================================================
       SUMMARY
    ===================================================== */

    function updateSummary(
        records
    ) {

        const total =
            records.length;


        const good =
            records.filter(
                record =>
                    record.status === "GOOD"
            ).length;


        const defective =
            records.filter(
                record =>
                    record.status ===
                    "DEFECTIVE"
            ).length;


        if (historyTotal) {

            historyTotal.textContent =
                total;

        }


        if (historyGood) {

            historyGood.textContent =
                good;

        }


        if (historyDefective) {

            historyDefective.textContent =
                defective;

        }

    }



    /* =====================================================
       RENDER RECORDS
    ===================================================== */

    function renderRecords(
        records
    ) {

        if (!tableBody) {
            return;
        }


        tableBody.innerHTML = "";


        if (
            !records ||
            records.length === 0
        ) {

            if (historyEmpty) {

                historyEmpty.style.display =
                    "block";

            }


            updateVisibleCount(0);

            return;

        }


        if (historyEmpty) {

            historyEmpty.style.display =
                "none";

        }


        records.forEach(
            record => {

                const row =
                    document.createElement(
                        "tr"
                    );


                const conditionClass =
                    record.status === "GOOD"
                        ? "condition-good"
                        : "condition-defective";


                const conditionIcon =
                    record.status === "GOOD"
                        ? "✓"
                        : "!";


                row.innerHTML = `

                    <td>

                        <div class="inspection-id-cell">

                            <span class="id-icon">
                                #
                            </span>

                            <div>

                                <strong>
                                    ${escapeHTML(
                                        record.id
                                    )}
                                </strong>

                                <small>
                                    Inspection
                                </small>

                            </div>

                        </div>

                    </td>


                    <td>

                        <div class="metal-cell">

                            <span class="metal-icon">
                                ◈
                            </span>

                            <span>
                                ${escapeHTML(
                                    record.metalType
                                )}
                            </span>

                        </div>

                    </td>


                    <td>

                        <span
                            class="history-condition ${conditionClass}"
                        >

                            <span class="condition-icon">
                                ${conditionIcon}
                            </span>

                            ${escapeHTML(
                                record.status
                            )}

                        </span>

                    </td>


                    <td>

                        <span class="history-date">
                            ${escapeHTML(
                                record.date
                            )}
                        </span>

                    </td>


                    <td>

                        <span class="history-time">
                            ${escapeHTML(
                                record.time
                            )}
                        </span>

                    </td>


                    <td class="action-column">

                        <button
                            class="view-result-btn"
                            type="button"
                            data-id="${escapeHTML(
                                record.id
                            )}"
                        >

                            <span>
                                View Results
                            </span>

                            <span class="view-arrow">
                                →
                            </span>

                        </button>

                    </td>

                `;


                tableBody.appendChild(
                    row
                );

            }
        );


        updateVisibleCount(
            records.length
        );


        attachResultButtons();

    }



    /* =====================================================
       VISIBLE COUNT
    ===================================================== */

    function updateVisibleCount(
        count
    ) {

        if (visibleRecords) {

            visibleRecords.textContent =
                count;

        }


        if (recordsCount) {

            recordsCount.textContent =
                count;

        }

    }



    /* =====================================================
       ESCAPE HTML
    ===================================================== */

    function escapeHTML(
        value
    ) {

        return String(
            value ?? ""
        )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

    }



    /* =====================================================
       FILTER RECORDS
    ===================================================== */

    function filterRecords() {

        const searchTerm =
            searchInput
                ? searchInput.value
                    .trim()
                    .toLowerCase()
                : "";


        const selectedCondition =
            conditionFilter
                ? conditionFilter.value
                : "all";


        const selectedMetal =
            metalFilter
                ? metalFilter.value
                : "all";


        const fromValue =
            fromDate
                ? fromDate.value
                : "";


        const toValue =
            toDate
                ? toDate.value
                : "";


        let filtered =
            inspectionRecords.filter(
                record => {

                    /* ---------------------------------
                       INSPECTION ID SEARCH
                    --------------------------------- */

                    const matchesSearch =

                        record.id
                            .toLowerCase()
                            .includes(
                                searchTerm
                            );


                    /* ---------------------------------
                       CONDITION
                    --------------------------------- */

                    const matchesCondition =

                        selectedCondition ===
                        "all"

                        ||

                        record.status ===
                        selectedCondition;


                    /* ---------------------------------
                       METAL
                    --------------------------------- */

                    const matchesMetal =

                        selectedMetal ===
                        "all"

                        ||

                        record.metalType ===
                        selectedMetal;


                    /* ---------------------------------
                       FROM DATE
                    --------------------------------- */

                    let matchesFromDate =
                        true;


                    if (
                        fromValue &&
                        record.dateObject
                    ) {

                        const start =
                            new Date(
                                fromValue +
                                "T00:00:00"
                            );


                        matchesFromDate =
                            record.dateObject >=
                            start;

                    }


                    /* ---------------------------------
                       TO DATE
                    --------------------------------- */

                    let matchesToDate =
                        true;


                    if (
                        toValue &&
                        record.dateObject
                    ) {

                        const end =
                            new Date(
                                toValue +
                                "T23:59:59"
                            );


                        matchesToDate =
                            record.dateObject <=
                            end;

                    }


                    return (

                        matchesSearch &&

                        matchesCondition &&

                        matchesMetal &&

                        matchesFromDate &&

                        matchesToDate

                    );

                }
            );


        renderRecords(
            filtered
        );

    }



    /* =====================================================
       CLEAR FILTERS
    ===================================================== */

    function clearFilters() {

        if (searchInput) {
            searchInput.value = "";
        }


        if (conditionFilter) {
            conditionFilter.value = "all";
        }


        if (metalFilter) {
            metalFilter.value = "all";
        }


        if (fromDate) {
            fromDate.value = "";
        }


        if (toDate) {
            toDate.value = "";
        }


        renderRecords(
            inspectionRecords
        );

    }



    if (clearFiltersBtn) {

        clearFiltersBtn.addEventListener(
            "click",
            clearFilters
        );

    }


    if (emptyClearBtn) {

        emptyClearBtn.addEventListener(
            "click",
            clearFilters
        );

    }



    /* =====================================================
       FILTER EVENTS
    ===================================================== */

    if (searchInput) {

        searchInput.addEventListener(
            "input",
            filterRecords
        );

    }


    if (conditionFilter) {

        conditionFilter.addEventListener(
            "change",
            filterRecords
        );

    }


    if (metalFilter) {

        metalFilter.addEventListener(
            "change",
            filterRecords
        );

    }


    if (fromDate) {

        fromDate.addEventListener(
            "change",
            filterRecords
        );

    }


    if (toDate) {

        toDate.addEventListener(
            "change",
            filterRecords
        );

    }



    /* =====================================================
       VIEW RESULTS
    ===================================================== */

    function attachResultButtons() {

        const buttons =
            document.querySelectorAll(
                ".view-result-btn"
            );


        buttons.forEach(
            button => {

                button.addEventListener(
                    "click",
                    async () => {

                        const inspectionId =
                            button.dataset.id;


                        if (!inspectionId) {
                            return;
                        }


                        /*
                         * Save inspection ID.
                         */

                        sessionStorage.setItem(
                            "selectedInspectionId",
                            inspectionId
                        );


                        /*
                         * Fetch complete historical record.
                         */

                        try {

                            const response =
                                await fetch(
                                    `${API_URL}/api/history/${encodeURIComponent(
                                        inspectionId
                                    )}`
                                );


                            if (response.ok) {

                                const data =
                                    await response.json();


                                if (
                                    data &&
                                    data.success &&
                                    data.record
                                ) {

                                    sessionStorage.setItem(
                                        "selectedInspectionResult",
                                        JSON.stringify(
                                            data.record
                                        )
                                    );

                                }

                            }

                        } catch (error) {

                            console.warn(
                                "Unable to load selected inspection.",
                                error
                            );

                        }


                        /*
                         * Open existing result page.
                         */

                        window.location.href =
                            "result.html";

                    }
                );

            }
        );

    }



    /* =====================================================
       INITIAL LOAD
    ===================================================== */

    loadHistory();

});