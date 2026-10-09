const chatbotButton = document.getElementById("chatbotButton");
const chatbotWindow = document.getElementById("chatbotWindow");
const closeChatbot = document.getElementById("closeChatbot");

const chatbotInput = document.getElementById("chatbotInput");
const sendChatbot = document.getElementById("sendChatbot");

const chatbotMessages = document.querySelector(".chatbot-messages");


chatbotButton.addEventListener("click", () => {

    chatbotWindow.style.display = "flex";

});


closeChatbot.addEventListener("click", () => {

    chatbotWindow.style.display = "none";

});


function addMessage(message, type) {

    const div = document.createElement("div");

    div.classList.add(
        type === "user"
            ? "user-message"
            : "bot-message"
    );

    div.textContent = message;

    chatbotMessages.appendChild(div);

    chatbotMessages.scrollTop =
        chatbotMessages.scrollHeight;
}


function getBotResponse(message) {

    const text = message.toLowerCase();

    if (text.includes("resnet")) {

        return "ResNet50 is the deep learning architecture used by our system to classify metal surface defects.";

    }

    if (text.includes("grad-cam")) {

        return "Grad-CAM highlights image regions that contribute strongly to the model's predicted defect class.";

    }

    if (text.includes("defect")) {

        return "The system classifies metal surface images into 10 defect categories including Punching Hole, Welding Line, Crescent Gap, Water Spot, Oil Spot, Silk Spot, Inclusion, Rolled Pit, Crease and Waist Folding.";

    }

    if (text.includes("model")) {

        return "Our inspection system uses a ResNet50 transfer-learning model trained for industrial metal surface defect classification.";

    }

    return "I can help you understand metal defects, ResNet50, Grad-CAM, image inspection and the Metal Vision AI system.";

}


function sendMessage() {

    const message = chatbotInput.value.trim();

    if (!message) {
        return;
    }

    addMessage(message, "user");

    chatbotInput.value = "";

    setTimeout(() => {

        const response = getBotResponse(message);

        addMessage(response, "bot");

    }, 500);

}


sendChatbot.addEventListener("click", sendMessage);


chatbotInput.addEventListener("keypress", (event) => {

    if (event.key === "Enter") {

        sendMessage();

    }

});