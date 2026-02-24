document.addEventListener("DOMContentLoaded", function () {
    const reportDateFilter = document.getElementById("equipmentReportDateFilter");
    const reportTable = document.getElementById("equipmentReportTable");
    const reportEmpty = document.getElementById("equipmentReportEmpty");

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
