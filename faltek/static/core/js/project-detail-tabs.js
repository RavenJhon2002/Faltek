document.addEventListener("DOMContentLoaded", function () {
    const shouldOpenReports = document.body && document.body.dataset.openReports === "1";
    const shouldOpenEquipment = document.body && document.body.dataset.openEquipment === "1";
    const openEquipmentView = (document.body && document.body.dataset.openEquipmentView) || "settings";
    const homeTab = document.getElementById("homeTab");
    const manpowerTab = document.getElementById("manpowerTab");
    const reportsTab = document.getElementById("reportsTab");
    const equipmentTab = document.getElementById("equipmentTab");
    const openManpowerBtn = document.getElementById("openManpowerBtn");
    const homeView = document.getElementById("homeView");
    const progressOverview = document.getElementById("progress-overview");
    const ganttSection = document.getElementById("ganttSection");
    const reportIssuesSection = document.getElementById("reportIssuesSection");
    const manpowerModal = document.getElementById("manpowerModal");
    const equipmentModal = document.getElementById("equipmentModal");
    const modalSettingsBtn = document.getElementById("modalSettingsBtn");
    const modalReportsBtn = document.getElementById("modalReportsBtn");
    const modalSettingsView = document.getElementById("modalSettingsView");
    const modalReportsView = document.getElementById("modalReportsView");
    const equipmentSettingsBtn = document.getElementById("equipmentSettingsBtn");
    const equipmentReportsBtn = document.getElementById("equipmentReportsBtn");
    const equipmentSettingsView = document.getElementById("equipmentSettingsView");
    const equipmentReportsView = document.getElementById("equipmentReportsView");
    const closeModalButtons = Array.from(document.querySelectorAll("[data-close-modal]"));
    const closeEquipmentModalButtons = Array.from(document.querySelectorAll("[data-close-equipment-modal]"));

    if (!homeTab || !manpowerTab || !homeView) {
        return;
    }

    function activateMain(view) {
        const showHome = view === "home";
        const showReports = view === "reports";

        homeView.classList.toggle("is-hidden", !showHome);
        if (progressOverview) {
            progressOverview.classList.toggle("is-hidden", !showHome);
        }
        if (ganttSection) {
            ganttSection.classList.toggle("is-hidden", !showHome);
        }
        if (reportIssuesSection) {
            reportIssuesSection.classList.toggle("is-hidden", !showReports);
        }

        homeTab.classList.toggle("is-active", showHome);
        if (reportsTab) {
            reportsTab.classList.toggle("is-active", showReports);
        }
        if (equipmentTab) {
            equipmentTab.classList.remove("is-active");
        }
    }

    function activateModal(view) {
        if (!modalSettingsBtn || !modalReportsBtn || !modalSettingsView || !modalReportsView) {
            return;
        }

        const showSettings = view === "settings";
        modalSettingsView.classList.toggle("is-hidden", !showSettings);
        modalReportsView.classList.toggle("is-hidden", showSettings);
        modalSettingsBtn.classList.toggle("is-active", showSettings);
        modalReportsBtn.classList.toggle("is-active", !showSettings);
    }

    function openManpowerModal(view) {
        if (!manpowerModal) {
            return;
        }
        manpowerModal.classList.remove("is-hidden");
        manpowerModal.setAttribute("aria-hidden", "false");
        closeEquipmentModal();
        activateModal(view || "settings");
    }

    function closeManpowerModal() {
        if (!manpowerModal) {
            return;
        }
        manpowerModal.classList.add("is-hidden");
        manpowerModal.setAttribute("aria-hidden", "true");
    }

    function activateEquipmentModal(view) {
        if (!equipmentSettingsBtn || !equipmentReportsBtn || !equipmentSettingsView || !equipmentReportsView) {
            return;
        }

        const showSettings = view === "settings";
        equipmentSettingsView.classList.toggle("is-hidden", !showSettings);
        equipmentReportsView.classList.toggle("is-hidden", showSettings);
        equipmentSettingsBtn.classList.toggle("is-active", showSettings);
        equipmentReportsBtn.classList.toggle("is-active", !showSettings);
    }

    function openEquipmentModal(view) {
        if (!equipmentModal) {
            return;
        }
        equipmentModal.classList.remove("is-hidden");
        equipmentModal.setAttribute("aria-hidden", "false");
        closeManpowerModal();
        activateMain("home");
        if (equipmentTab) {
            equipmentTab.classList.add("is-active");
        }
        activateEquipmentModal(view || "settings");
    }

    function closeEquipmentModal() {
        if (!equipmentModal) {
            return;
        }
        equipmentModal.classList.add("is-hidden");
        equipmentModal.setAttribute("aria-hidden", "true");
        if (equipmentTab) {
            equipmentTab.classList.remove("is-active");
        }
    }

    homeTab.addEventListener("click", function (event) {
        event.preventDefault();
        closeManpowerModal();
        closeEquipmentModal();
        activateMain("home");
    });

    manpowerTab.addEventListener("click", function (event) {
        event.preventDefault();
        activateMain("home");
        openManpowerModal("settings");
    });

    if (reportsTab) {
        reportsTab.addEventListener("click", function (event) {
            event.preventDefault();
            closeEquipmentModal();
            closeManpowerModal();
            activateMain("reports");
        });
    }

    if (equipmentTab) {
        equipmentTab.addEventListener("click", function (event) {
            event.preventDefault();
            openEquipmentModal("settings");
        });
    }

    if (openManpowerBtn) {
        openManpowerBtn.addEventListener("click", function () {
            activateMain("home");
            openManpowerModal("settings");
        });
    }

    if (modalSettingsBtn) {
        modalSettingsBtn.addEventListener("click", function () {
            activateModal("settings");
        });
    }

    if (modalReportsBtn) {
        modalReportsBtn.addEventListener("click", function () {
            activateModal("reports");
        });
    }

    if (equipmentSettingsBtn) {
        equipmentSettingsBtn.addEventListener("click", function () {
            activateEquipmentModal("settings");
        });
    }

    if (equipmentReportsBtn) {
        equipmentReportsBtn.addEventListener("click", function () {
            activateEquipmentModal("reports");
        });
    }

    closeModalButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            closeManpowerModal();
            closeEquipmentModal();
            activateMain("home");
        });
    });

    closeEquipmentModalButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            closeEquipmentModal();
            activateMain("home");
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeManpowerModal();
            closeEquipmentModal();
            activateMain("home");
        }
    });

    activateMain("home");

    if (shouldOpenReports) {
        activateMain("reports");
    }

    if (shouldOpenEquipment) {
        openEquipmentModal(openEquipmentView);
    }
});
