document.addEventListener("DOMContentLoaded", function () {

    console.log("[Module 5] Navigation initialized.");

    const navItems = document.querySelectorAll(".nav-item");

    const mapSection =
        document.getElementById("flood-map-section");

    const warningsSection =
        document.getElementById("warnings-section");

    const forecastSection =
        document.getElementById("forecast-section");

    const settingsSection =
        document.getElementById("settings-section");

    const mainContent =
        document.getElementById("main-content");


    /*
    ========================================================
    NAVIGATION
    ========================================================
    */

    navItems.forEach(function (button) {

        button.addEventListener("click", function () {

            const view = button.dataset.view;

            console.log(
                "[Module 5] Navigation:",
                view
            );


            // Remove active state
            navItems.forEach(function (item) {
                item.classList.remove("active");
            });


            // Activate clicked button
            button.classList.add("active");


            /*
            =================================================
            DASHBOARD
            =================================================
            */

            if (view === "dashboard") {

                scrollToTop();

            }


            /*
            =================================================
            FLOOD MAP
            =================================================
            */

            else if (view === "map") {

                scrollToSection(mapSection);

                // Important for Leaflet
                setTimeout(function () {

                    if (
                        typeof map !== "undefined" &&
                        map
                    ) {

                        map.invalidateSize();

                    }

                }, 300);

            }


            /*
            =================================================
            FLOOD WARNINGS
            =================================================
            */

            else if (view === "warnings") {

                scrollToSection(warningsSection);

            }


            /*
            =================================================
            FORECAST
            =================================================
            */

            else if (view === "forecast") {

                scrollToSection(forecastSection);

            }


            /*
            =================================================
            SETTINGS
            =================================================
            */

            else if (view === "settings") {

                scrollToSection(settingsSection);

            }

        });

    });


    /*
    ========================================================
    SCROLL FUNCTIONS
    ========================================================
    */

    function scrollToSection(section) {

        if (!section) {

            console.warn(
                "[Module 5] Navigation section not found."
            );

            return;

        }

        section.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }


    function scrollToTop() {

        if (mainContent) {

            mainContent.scrollTo({
                top: 0,
                behavior: "smooth"
            });

        } else {

            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });

        }

    }


    /*
    ========================================================
    FORECAST CARDS
    ========================================================
    */

    const forecastCards =
        document.querySelectorAll(".forecast-time");

    const slider =
        document.getElementById("time-slider");

    forecastCards.forEach(function (card, index) {

        card.style.cursor = "pointer";

        card.addEventListener("click", function () {

            console.log(
                "[Module 5] Forecast card selected:",
                index
            );


            // Update active card
            forecastCards.forEach(function (item) {

                item.classList.remove("active");

            });

            card.classList.add("active");


            // Update slider
            if (slider) {

                slider.value = index;

                slider.dispatchEvent(
                    new Event("input")
                );

            }


            // Go to forecast section
            scrollToSection(forecastSection);

        });

    });


    /*
    ========================================================
    SETTINGS STATUS
    ========================================================
    */

    const wsStatus =
        document.getElementById("settings-ws-status");

    if (wsStatus) {

        const normalStatus =
            document.getElementById("ws-status-text");

        if (
            normalStatus &&
            normalStatus.textContent.includes("Connected")
        ) {

            wsStatus.textContent =
                "● Connected";

            wsStatus.classList.add("online");

        } else {

            wsStatus.textContent =
                "● Waiting for connection";

        }

    }

});