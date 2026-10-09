/* =========================================================
   METAL VISION AI - FAQ JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       USER INFORMATION
       ===================================================== */

    const userNameElement = document.getElementById("faqUserName");
    const userAvatarElement = document.getElementById("userAvatar");

    const storedUser = localStorage.getItem("metalVisionCurrentUser");
    const registeredUser = localStorage.getItem("metalVisionUser");

    let currentUser = null;

    try {
        if (storedUser) {
            currentUser = JSON.parse(storedUser);
        } else if (registeredUser) {
            currentUser = JSON.parse(registeredUser);
        }
    } catch (error) {
        console.warn("Unable to read stored user information.");
    }

    if (currentUser) {

        const name =
            currentUser.name ||
            currentUser.fullName ||
            "User";

        if (userNameElement) {
            userNameElement.textContent = name;
        }

        if (userAvatarElement) {
            const initials = name
                .split(" ")
                .filter(Boolean)
                .slice(0, 2)
                .map(word => word.charAt(0).toUpperCase())
                .join("");

            userAvatarElement.textContent = initials || "U";
        }
    }


    /* =====================================================
       FAQ ACCORDION
       ===================================================== */

    const faqQuestions =
        document.querySelectorAll(".faq-question");

    faqQuestions.forEach(question => {

        question.addEventListener("click", () => {

            const faqItem =
                question.closest(".faq-item");

            const answer =
                faqItem.querySelector(".faq-answer");

            const isActive =
                faqItem.classList.contains("active");


            /* Close other FAQ items */

            document
                .querySelectorAll(".faq-item.active")
                .forEach(item => {

                    if (item !== faqItem) {

                        item.classList.remove("active");

                        const otherAnswer =
                            item.querySelector(".faq-answer");

                        if (otherAnswer) {
                            otherAnswer.style.maxHeight = null;
                        }
                    }
                });


            /* Toggle selected item */

            if (isActive) {

                faqItem.classList.remove("active");

                answer.style.maxHeight = null;

            } else {

                faqItem.classList.add("active");

                answer.style.maxHeight =
                    answer.scrollHeight + "px";
            }

        });

    });


    /* =====================================================
       FAQ SEARCH
       ===================================================== */

    const searchInput =
        document.getElementById("faqSearch");

    const faqItems =
        document.querySelectorAll(".faq-item");

    const noResults =
        document.getElementById("faqNoResults");


    if (searchInput) {

        searchInput.addEventListener("input", () => {

            const searchText =
                searchInput.value
                    .trim()
                    .toLowerCase();

            let visibleCount = 0;


            faqItems.forEach(item => {

                const question =
                    item
                        .querySelector(".faq-question")
                        ?.textContent
                        .toLowerCase() || "";

                const answer =
                    item
                        .querySelector(".faq-answer")
                        ?.textContent
                        .toLowerCase() || "";


                const matches =
                    question.includes(searchText) ||
                    answer.includes(searchText);


                if (matches) {

                    item.style.display = "";

                    visibleCount++;

                } else {

                    item.style.display = "none";

                    item.classList.remove("active");

                    const answerElement =
                        item.querySelector(".faq-answer");

                    if (answerElement) {
                        answerElement.style.maxHeight = null;
                    }
                }

            });


            if (noResults) {

                if (visibleCount === 0 && searchText !== "") {
                    noResults.classList.add("show");
                } else {
                    noResults.classList.remove("show");
                }

            }

        });

    }


    /* =====================================================
       PDF BUTTON
       ===================================================== */

    const pdfButton =
        document.querySelector(".faq-pdf-btn");

    if (pdfButton) {

        pdfButton.addEventListener("click", () => {

            /*
             The PDF is stored in:
             frontend/assets/Metal_Vision_AI_FAQ.pdf
            */

            console.log(
                "Opening Metal Vision AI FAQ PDF..."
            );

        });

    }


    /* =====================================================
       MOBILE SIDEBAR
       ===================================================== */

    const menuButton =
        document.getElementById("faqMenuBtn");

    const sidebar =
        document.querySelector(".dashboard-sidebar");

    const overlay =
        document.querySelector(".faq-sidebar-overlay");


    if (menuButton && sidebar) {

        menuButton.addEventListener("click", () => {

            sidebar.classList.toggle("open");

            if (overlay) {
                overlay.classList.toggle("show");
            }

        });

    }


    if (overlay && sidebar) {

        overlay.addEventListener("click", () => {

            sidebar.classList.remove("open");
            overlay.classList.remove("show");

        });

    }


    /* =====================================================
       LOGOUT
       ===================================================== */

    const logoutButton =
        document.getElementById("logoutBtn");

    if (logoutButton) {

        logoutButton.addEventListener("click", () => {

            const confirmLogout =
                confirm(
                    "Are you sure you want to logout?"
                );

            if (!confirmLogout) {
                return;
            }

            localStorage.removeItem(
                "metalVisionLoggedIn"
            );

            localStorage.removeItem(
                "metalVisionCurrentUser"
            );

            window.location.href = "login.html";

        });

    }


    /* =====================================================
       FAQ PAGE LOAD ANIMATION
       ===================================================== */

    faqItems.forEach((item, index) => {

        item.style.opacity = "0";
        item.style.transform = "translateY(8px)";

        setTimeout(() => {

            item.style.transition =
                "opacity 0.35s ease, transform 0.35s ease";

            item.style.opacity = "1";
            item.style.transform = "translateY(0)";

        }, index * 45);

    });

});