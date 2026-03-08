document.addEventListener("DOMContentLoaded", function () {
    const shouldOpenReports = document.body && document.body.dataset.openReports === "1";
    const shouldOpenEquipment = document.body && document.body.dataset.openEquipment === "1";
    const isViewerMode = document.body && document.body.dataset.viewerMode === "1";
    const homeTab = document.getElementById("homeTab");
    const manpowerTab = document.getElementById("manpowerTab");
    const reportsTab = document.getElementById("reportsTab");
    const equipmentTab = document.getElementById("equipmentTab");
    const openManpowerBtn = document.getElementById("openManpowerBtn");
    const homeView = document.getElementById("homeView");
    const progressOverview = document.getElementById("progress-overview");
    const ganttSection = document.getElementById("ganttSection");
    const reportIssuesSection = document.getElementById("reportIssuesSection");
    const reportsIssuesTab = document.getElementById("reportsIssuesTab");
    const reportsProgressTab = document.getElementById("reportsProgressTab");
    const reportsManpowerTab = document.getElementById("reportsManpowerTab");
    const reportsEquipmentTab = document.getElementById("reportsEquipmentTab");
    const reportsIssuesView = document.getElementById("reportsIssuesView");
    const reportsProgressView = document.getElementById("reportsProgressView");
    const reportsManpowerView = document.getElementById("reportsManpowerView");
    const reportsEquipmentView = document.getElementById("reportsEquipmentView");
    const manpowerModal = document.getElementById("manpowerModal");
    const equipmentModal = document.getElementById("equipmentModal");
    const modalSettingsBtn = document.getElementById("modalSettingsBtn");
    const modalSettingsView = document.getElementById("modalSettingsView");
    const equipmentSettingsBtn = document.getElementById("equipmentSettingsBtn");
    const equipmentSettingsView = document.getElementById("equipmentSettingsView");
    const closeModalButtons = Array.from(document.querySelectorAll("[data-close-modal]"));
    const closeEquipmentModalButtons = Array.from(document.querySelectorAll("[data-close-equipment-modal]"));
    const copyViewerLinkBtn = document.getElementById("copyViewerLinkBtn");
    const viewerLinkInput = document.getElementById("viewerLinkInput");
    let currentReportsView = "issues";

    if (!homeTab || !homeView) {
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
            if (showReports) {
                activateReportsSubview(currentReportsView);
            }
        }

        homeTab.classList.toggle("is-active", showHome);
        if (reportsTab) {
            reportsTab.classList.toggle("is-active", showReports);
        }
        if (equipmentTab) {
            equipmentTab.classList.remove("is-active");
        }
    }

    function activateReportsSubview(view) {
        const validView = view === "progress" || view === "manpower" || view === "equipment" ? view : "issues";
        currentReportsView = validView;

        if (reportsIssuesView) {
            reportsIssuesView.classList.toggle("is-hidden", validView !== "issues");
        }
        if (reportsProgressView) {
            reportsProgressView.classList.toggle("is-hidden", validView !== "progress");
        }
        if (reportsManpowerView) {
            reportsManpowerView.classList.toggle("is-hidden", validView !== "manpower");
        }
        if (reportsEquipmentView) {
            reportsEquipmentView.classList.toggle("is-hidden", validView !== "equipment");
        }

        if (reportsIssuesTab) {
            reportsIssuesTab.classList.toggle("is-active", validView === "issues");
        }
        if (reportsProgressTab) {
            reportsProgressTab.classList.toggle("is-active", validView === "progress");
        }
        if (reportsManpowerTab) {
            reportsManpowerTab.classList.toggle("is-active", validView === "manpower");
        }
        if (reportsEquipmentTab) {
            reportsEquipmentTab.classList.toggle("is-active", validView === "equipment");
        }
    }

    function activateModal() {
        if (!modalSettingsView) {
            return;
        }
        modalSettingsView.classList.remove("is-hidden");
        if (modalSettingsBtn) {
            modalSettingsBtn.classList.add("is-active");
        }
    }

    function openManpowerModal() {
        if (!manpowerModal) {
            return;
        }
        manpowerModal.classList.remove("is-hidden");
        manpowerModal.setAttribute("aria-hidden", "false");
        closeEquipmentModal();
        activateModal();
    }

    function closeManpowerModal() {
        if (!manpowerModal) {
            return;
        }
        manpowerModal.classList.add("is-hidden");
        manpowerModal.setAttribute("aria-hidden", "true");
    }

    function activateEquipmentModal() {
        if (!equipmentSettingsView) {
            return;
        }
        equipmentSettingsView.classList.remove("is-hidden");
        if (equipmentSettingsBtn) {
            equipmentSettingsBtn.classList.add("is-active");
        }
    }

    function openEquipmentModal() {
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
        activateEquipmentModal();
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

    if (manpowerTab) {
        manpowerTab.addEventListener("click", function (event) {
            event.preventDefault();
            activateMain("home");
            openManpowerModal();
        });
    }

    if (reportsTab) {
        reportsTab.addEventListener("click", function (event) {
            event.preventDefault();
            closeEquipmentModal();
            closeManpowerModal();
            activateMain("reports");
        });
    }

    if (reportsIssuesTab) {
        reportsIssuesTab.addEventListener("click", function () {
            activateReportsSubview("issues");
        });
    }

    if (reportsProgressTab) {
        reportsProgressTab.addEventListener("click", function () {
            activateReportsSubview("progress");
        });
    }

    if (reportsManpowerTab) {
        reportsManpowerTab.addEventListener("click", function () {
            activateReportsSubview("manpower");
        });
    }

    if (reportsEquipmentTab) {
        reportsEquipmentTab.addEventListener("click", function () {
            activateReportsSubview("equipment");
        });
    }

    if (equipmentTab) {
        equipmentTab.addEventListener("click", function (event) {
            event.preventDefault();
            openEquipmentModal();
        });
    }

    if (openManpowerBtn) {
        openManpowerBtn.addEventListener("click", function () {
            activateMain("home");
            openManpowerModal();
        });
    }

    if (modalSettingsBtn) {
        modalSettingsBtn.addEventListener("click", function () {
            activateModal();
        });
    }

    if (equipmentSettingsBtn) {
        equipmentSettingsBtn.addEventListener("click", function () {
            activateEquipmentModal();
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
    activateReportsSubview("issues");

    if (shouldOpenReports) {
        activateMain("reports");
    }

    if (shouldOpenEquipment) {
        openEquipmentModal();
    }

    if (copyViewerLinkBtn && viewerLinkInput) {
        copyViewerLinkBtn.addEventListener("click", function () {
            const value = viewerLinkInput.value || "";
            if (!value) {
                return;
            }

            navigator.clipboard.writeText(value).then(function () {
                copyViewerLinkBtn.textContent = "Copied";
                window.setTimeout(function () {
                    copyViewerLinkBtn.textContent = "Copy Link";
                }, 1200);
            });
        });
    }

    if (isViewerMode) {
        closeManpowerModal();
        closeEquipmentModal();
    }
});
