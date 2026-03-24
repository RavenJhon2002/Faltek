document.addEventListener("DOMContentLoaded", function () {
    const reportDateFilter = document.getElementById("equipmentReportDateFilter");
    const reportTable = document.getElementById("equipmentReportTable");
    const reportEmpty = document.getElementById("equipmentReportEmpty");
    const entryDateInput = document.getElementById("equipmentEntryDate");
    const equipmentList = document.getElementById("equipmentList");
    const equipmentEmpty = document.getElementById("equipmentFilterEmpty");

    function applyEntryDateFilter() {
        if (!entryDateInput || !equipmentList) {
            return;
        }

        const selectedDate = entryDateInput.value;
        const cards = Array.from(equipmentList.querySelectorAll(".equipment-day-card"));
        let visibleCards = 0;

        cards.forEach(function (card) {
            const cardStartDate = card.getAttribute("data-start-date") || "";
            const cardEndDate = card.getAttribute("data-end-date") || "";
            const show = !selectedDate || (
                cardStartDate &&
                cardStartDate <= selectedDate &&
                (!cardEndDate || selectedDate <= cardEndDate)
            );
            card.style.display = show ? "" : "none";
            if (show) {
                visibleCards += 1;
            }
        });

        if (equipmentEmpty) {
            equipmentEmpty.classList.toggle("is-hidden", visibleCards > 0);
        }
    }

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

    if (entryDateInput && equipmentList) {
        entryDateInput.addEventListener("change", applyEntryDateFilter);
        applyEntryDateFilter();
    }
});
