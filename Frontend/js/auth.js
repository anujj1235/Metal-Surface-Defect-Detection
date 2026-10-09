/* =========================================================
   METAL VISION AI - AUTHENTICATION
========================================================= */


/* =========================================================
   REGISTER
========================================================= */

const registerForm =
    document.getElementById("registerForm");


if (registerForm) {

    registerForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();


            const name =
                document.getElementById("fullName").value.trim();

            const email =
                document.getElementById("email").value.trim();

            const password =
                document.getElementById("password").value;

            const confirmPassword =
                document.getElementById("confirmPassword").value;

            const message =
                document.getElementById("registerMessage");


            if (password !== confirmPassword) {

                message.textContent =
                    "Passwords do not match.";

                message.style.color =
                    "#d64545";

                return;
            }


            if (password.length < 6) {

                message.textContent =
                    "Password must contain at least 6 characters.";

                message.style.color =
                    "#d64545";

                return;
            }


            const user = {

                name: name,

                email: email,

                password: password

            };


            localStorage.setItem(
                "metalVisionUser",
                JSON.stringify(user)
            );


            message.textContent =
                "Account created successfully! Redirecting...";

            message.style.color =
                "#2e9b62";


            setTimeout(() => {

                window.location.href =
                    "login.html";

            }, 1200);

        }
    );

}


/* =========================================================
   LOGIN
========================================================= */

const loginForm =
    document.getElementById("loginForm");


if (loginForm) {

    loginForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();


            const email =
                document.getElementById("loginEmail")
                .value
                .trim();

            const password =
                document.getElementById("loginPassword")
                .value;


            const message =
                document.getElementById("loginMessage");


            const storedUser =
                localStorage.getItem(
                    "metalVisionUser"
                );


            if (!storedUser) {

                message.textContent =
                    "No account found. Please register first.";

                message.style.color =
                    "#d64545";

                return;
            }


            const user =
                JSON.parse(storedUser);


            if (
                email === user.email &&
                password === user.password
            ) {

                localStorage.setItem(
                    "metalVisionLoggedIn",
                    "true"
                );


                localStorage.setItem(
                    "metalVisionCurrentUser",
                    JSON.stringify({
                        name: user.name,
                        email: user.email
                    })
                );


                message.textContent =
                    "Login successful! Opening dashboard...";

                message.style.color =
                    "#2e9b62";


                setTimeout(() => {

                    window.location.href =
                        "dashboard.html";

                }, 1000);


            } else {

                message.textContent =
                    "Invalid email or password.";

                message.style.color =
                    "#d64545";

            }

        }
    );

}