document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("manpowerSearch");
    const roleSelect = document.getElementById("manpowerRoleFilter");
    const list = document.getElementById("manpowerList");
    const empty = document.getElementById("manpowerFilterEmpty");
    const entryDateInput = document.getElementById("manpowerEntryDate");
    const reportDateFilter = document.getElementById("manpowerReportDateFilter");
    const reportTable = document.getElementById("manpowerReportTable");
    const reportEmpty = document.getElementById("manpowerReportEmpty");

    if (!searchInput || !roleSelect || !list) {
        return;
    }

    const cards = Array.from(list.querySelectorAll(".manpower-card"));

    function applyFilter() {
        const searchValue = searchInput.value.trim().toLowerCase();
        const roleValue = roleSelect.value;
        const selectedDate = entryDateInput ? entryDateInput.value : "";
        let visibleCards = 0;

        cards.forEach(function (card) {
            const title = card.querySelector("h3");
            const titleText = (title ? title.textContent : "").toLowerCase();
            const cardStartDate = card.getAttribute("data-start-date") || "";
            const cardEndDate = card.getAttribute("data-end-date") || "";
            const rows = Array.from(card.querySelectorAll("tbody tr"));

            let visibleRows = 0;

            rows.forEach(function (row) {
                const roleCell = row.querySelector("td");
                const roleText = roleCell ? roleCell.textContent.trim().toUpperCase() : "";
                const roleMatches = roleValue === "ALL" || roleText === roleValue;

                row.style.display = roleMatches ? "" : "none";
                if (roleMatches) {
                    visibleRows += 1;
                }
            });

            const titleMatches = !searchValue || titleText.includes(searchValue);
            const dateMatches = !selectedDate || (
                cardStartDate &&
                cardStartDate <= selectedDate &&
                (!cardEndDate || selectedDate <= cardEndDate)
            );
            const showCard = titleMatches && dateMatches && visibleRows > 0;

            card.style.display = showCard ? "" : "none";
            if (showCard) {
                visibleCards += 1;
            }
        });

        if (empty) {
            empty.classList.toggle("is-hidden", visibleCards > 0);
        }
    }

    searchInput.addEventListener("input", applyFilter);
    roleSelect.addEventListener("change", applyFilter);
    if (entryDateInput) {
        entryDateInput.addEventListener("change", applyFilter);
    }
    applyFilter();

    function applyReportDateFilter() {
        if (!reportDateFilter || !reportTable) {
            return;
        }

        const selectedDate = reportDateFilter.value;
        const rows = Array.from(reportTable.querySelectorAll("tbody tr"));
        let visibleRows = 0;

        rows.forEach(function (row) {
            const rowDate = row.getAttribute("data-report-date") || "";
            const show = !selectedDate || rowDate === selectedDate;
            row.style.display = show ? "" : "none";
            if (show) {
                visibleRows += 1;
            }
        });

        if (reportEmpty) {
            reportEmpty.classList.toggle("is-hidden", visibleRows > 0);
        }
    }

    if (reportDateFilter && reportTable) {
        reportDateFilter.addEventListener("change", applyReportDateFilter);
        applyReportDateFilter();
    }
});
