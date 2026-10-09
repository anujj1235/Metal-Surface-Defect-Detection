/* =========================================================
   METAL VISION AI - DASHBOARD JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    console.log("Metal Vision AI Dashboard loaded successfully.");


    /* =====================================================
       USER INFORMATION
       ===================================================== */

    const storedUser =
        localStorage.getItem("metalVisionCurrentUser");

    let userName = "Inspector";

    if (storedUser) {

        try {

            const user =
                JSON.parse(storedUser);

            if (user.name) {
                userName = user.name;
            }

        } catch (error) {

            console.log(
                "Unable to read stored user information."
            );

        }

    }


    const welcomeUserName =
        document.getElementById("welcomeUserName");

    const dashboardUserName =
        document.getElementById("dashboardUserName");

    const userAvatar =
        document.getElementById("userAvatar");


    if (welcomeUserName) {
        welcomeUserName.textContent = userName;
    }


    if (dashboardUserName) {
        dashboardUserName.textContent = userName;
    }


    if (userAvatar) {

        userAvatar.textContent =
            userName
                .charAt(0)
                .toUpperCase();

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
            function () {

                sidebar.classList.toggle(
                    "mobile-open"
                );

            }
        );

    }


    /* =====================================================
       CLOSE MOBILE SIDEBAR WHEN NAV ITEM CLICKED
       ===================================================== */

    const navItems =
        document.querySelectorAll(
            ".sidebar .nav-item"
        );


    navItems.forEach(function (item) {

        item.addEventListener(
            "click",
            function () {

                if (
                    window.innerWidth <= 800 &&
                    sidebar
                ) {

                    sidebar.classList.remove(
                        "mobile-open"
                    );

                }

            }
        );

    });


    /* =====================================================
       LOGOUT
       ===================================================== */

    const logoutBtn =
        document.getElementById("logoutBtn");


    if (logoutBtn) {

        logoutBtn.addEventListener(
            "click",
            function () {

                const confirmLogout =
                    confirm(
                        "Are you sure you want to logout?"
                    );


                if (confirmLogout) {

                    localStorage.removeItem(
                        "metalVisionLoggedIn"
                    );

                    localStorage.removeItem(
                        "metalVisionCurrentUser"
                    );

                    window.location.href =
                        "login.html";

                }

            }
        );

    }


    /* =====================================================
       AI ASSISTANT
       ===================================================== */

    const aiButton =
        document.getElementById("dashboardAiBtn");

    const chatbot =
        document.getElementById("dashboardChatbot");

    const closeChatbot =
        document.getElementById(
            "closeDashboardChatbot"
        );


    if (aiButton && chatbot) {

        aiButton.addEventListener(
            "click",
            function () {

                chatbot.classList.toggle(
                    "open"
                );

            }
        );

    }


    if (closeChatbot && chatbot) {

        closeChatbot.addEventListener(
            "click",
            function () {

                chatbot.classList.remove(
                    "open"
                );

            }
        );

    }


    /* =====================================================
       CHATBOT
       ===================================================== */

    const chatInput =
        document.getElementById(
            "dashboardChatInput"
        );

    const chatSend =
        document.getElementById(
            "dashboardChatSend"
        );

    const chatBody =
        document.getElementById(
            "dashboardChatBody"
        );


    function sendDashboardMessage() {

        if (!chatInput || !chatBody) {
            return;
        }


        const message =
            chatInput.value.trim();


        if (!message) {
            return;
        }


        /* USER MESSAGE */

        const userMessage =
            document.createElement("div");

        userMessage.className =
            "chat-message user";

        userMessage.textContent =
            message;


        chatBody.appendChild(
            userMessage
        );


        chatInput.value = "";


        /* BOT RESPONSE */

        setTimeout(
            function () {

                const botMessage =
                    document.createElement("div");

                botMessage.className =
                    "chat-message bot";


                const lowerMessage =
                    message.toLowerCase();


                if (
                    lowerMessage.includes("resnet")
                ) {

                    botMessage.textContent =
                        "ResNet50 is the deep learning model used in this project to classify metal surface defects into 10 defect categories.";

                }

                else if (
                    lowerMessage.includes("grad")
                ) {

                    botMessage.textContent =
                        "Grad-CAM generates a heatmap showing the important image regions that influenced the model's defect prediction.";

                }

                else if (
                    lowerMessage.includes("defect")
                ) {

                    botMessage.textContent =
                        "The system supports 10 defect classes including Punching Hole, Welding Line, Crescent Gap, Water Spot, Oil Spot, Silk Spot, Inclusion, Rolled Pit, Crease and Waist Folding.";

                }

                else if (
                    lowerMessage.includes("inspection")
                ) {

                    botMessage.textContent =
                        "You can start a new inspection by clicking the 'New Inspection' button. Upload a metal surface image and the AI model will analyze it.";

                }

                else {

                    botMessage.textContent =
                        "I can help you understand ResNet50, Grad-CAM, defect classification, inspection results and the Metal Vision AI system.";

                }


                chatBody.appendChild(
                    botMessage
                );


                chatBody.scrollTop =
                    chatBody.scrollHeight;

            },
            500
        );

    }


    if (chatSend) {

        chatSend.addEventListener(
            "click",
            sendDashboardMessage
        );

    }


    if (chatInput) {

        chatInput.addEventListener(
            "keydown",
            function (event) {

                if (event.key === "Enter") {

                    sendDashboardMessage();

                }

            }
        );

    }


    /* =====================================================
       SIMPLE DASHBOARD ANIMATION
       ===================================================== */

    const cards =
        document.querySelectorAll(
            ".stat-card, .dashboard-card, .quick-action-card"
        );


    cards.forEach(function (card, index) {

        card.style.opacity = "0";

        card.style.transform =
            "translateY(12px)";


        setTimeout(
            function () {

                card.style.transition =
                    "all 0.45s ease";

                card.style.opacity =
                    "1";

                card.style.transform =
                    "translateY(0)";

            },
            80 + index * 50
        );

    });

});