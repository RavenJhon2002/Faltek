document.addEventListener("DOMContentLoaded", function () {
    const dataElement = document.getElementById("gantt-data");
    const container = document.getElementById("ganttTimeline");
    const infoPanel = document.getElementById("ganttInfo");

    if (!dataElement || !container) {
        return;
    }

    let tasks = [];
    try {
        tasks = JSON.parse(dataElement.textContent);
    } catch (error) {
        container.innerHTML = "<p>Invalid Gantt data</p>";
        return;
    }

    if (!tasks.length) {
        container.innerHTML = "<p>No tasks to display</p>";
        return;
    }

    const headersWithTimeline = [];
    const headersSet = new Set();
    let scanHeader = null;

    tasks.forEach(function (task) {
        if (task.is_group) {
            scanHeader = task.name || null;
            return;
        }
        if (!scanHeader || !task.start || !task.end) {
            return;
        }
        if (!headersSet.has(scanHeader)) {
            headersSet.add(scanHeader);
            headersWithTimeline.push(scanHeader);
        }
    });

    const headers = headersWithTimeline;
    let activeHeaderFilter = headers.length ? headers[0] : "__ALL__";
    let activeDateFilter = "";

    const controls = document.createElement("div");
    controls.className = "gantt-controls";

    if (headers.length) {
        const label = document.createElement("label");
        label.setAttribute("for", "ganttHeaderFilter");
        label.textContent = "Filter by header:";

        const select = document.createElement("select");
        select.id = "ganttHeaderFilter";

        headers.forEach(function (header) {
            const option = document.createElement("option");
            option.value = header;
            option.textContent = header;
            select.appendChild(option);
        });

        const allOption = document.createElement("option");
        allOption.value = "__ALL__";
        allOption.textContent = "All headers";
        select.appendChild(allOption);

        controls.appendChild(label);
        controls.appendChild(select);

        select.addEventListener("change", function () {
            activeHeaderFilter = select.value;
            render(activeHeaderFilter, activeDateFilter);
        });
    }

    const dateLabel = document.createElement("label");
    dateLabel.setAttribute("for", "ganttDateFilter");
    dateLabel.textContent = "Filter by date:";

    const dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.id = "ganttDateFilter";

    controls.appendChild(dateLabel);
    controls.appendChild(dateInput);
    container.parentNode.insertBefore(controls, container);

    dateInput.addEventListener("change", function () {
        activeDateFilter = dateInput.value || "";
        render(activeHeaderFilter, activeDateFilter);
    });

    render(activeHeaderFilter, activeDateFilter);

    function getColumnWidths() {
        const viewport = window.innerWidth || document.documentElement.clientWidth;

        if (viewport <= 420) {
            return { activity: 110, day: 56 };
        }
        if (viewport <= 640) {
            return { activity: 130, day: 68 };
        }
        if (viewport <= 900) {
            return { activity: 180, day: 110 };
        }
        return { activity: 320, day: 140 };
    }

    function getFilteredTasksByHeader(selectedHeader) {
        const filtered = [];
        let currentHeader = null;

        tasks.forEach(function (task) {
            if (task.is_group) {
                currentHeader = task.name || null;
                if (selectedHeader === "__ALL__" || currentHeader === selectedHeader) {
                    filtered.push(task);
                }
                return;
            }

            if (selectedHeader !== "__ALL__" && currentHeader !== selectedHeader) {
                return;
            }
            if (!task.start || !task.end) {
                return;
            }
            filtered.push(task);
        });

        return filtered;
    }

    function isTaskOnDate(task, selectedDate) {
        if (!selectedDate || !task.start || !task.end) {
            return true;
        }

        const checkDate = parseDate(selectedDate);
        const start = parseDate(task.start);
        const end = parseDate(task.end);
        const endExclusive = end > start ? end : addDays(start, 1);

        return (checkDate >= start && checkDate < endExclusive) || sameDate(checkDate, start);
    }

    function applyDateFilter(visibleTasks, selectedDate) {
        if (!selectedDate) {
            return visibleTasks;
        }

        const filtered = [];
        let currentGroup = null;
        let currentGroupRows = [];

        function flushGroup() {
            if (!currentGroup) {
                return;
            }
            if (currentGroupRows.length > 0) {
                filtered.push(currentGroup);
                currentGroupRows.forEach(function (row) {
                    filtered.push(row);
                });
            }
            currentGroup = null;
            currentGroupRows = [];
        }

        visibleTasks.forEach(function (task) {
            if (task.is_group) {
                flushGroup();
                currentGroup = task;
                return;
            }

            if (!isTaskOnDate(task, selectedDate)) {
                return;
            }

            if (currentGroup) {
                currentGroupRows.push(task);
            } else {
                filtered.push(task);
            }
        });

        flushGroup();
        return filtered;
    }

    function parseDate(dateString) {
        if (!dateString) {
            return new Date(NaN);
        }

        const raw = String(dateString).trim();
        if (!raw) {
            return new Date(NaN);
        }

        if (raw.includes("T")) {
            const dt = new Date(raw);
            if (!Number.isNaN(dt.getTime())) {
                return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
            }
        }

        const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (match) {
            const year = Number(match[1]);
            const month = Number(match[2]) - 1;
            const day = Number(match[3]);
            return new Date(year, month, day);
        }

        return new Date(raw);
    }

    function formatDate(date) {
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    }

    function addDays(date, days) {
        const next = new Date(date);
        next.setDate(next.getDate() + days);
        return next;
    }

    function getDateRange(minDate, maxDate) {
        const dates = [];
        const cursor = new Date(minDate);
        while (cursor <= maxDate) {
            dates.push(new Date(cursor));
            cursor.setDate(cursor.getDate() + 1);
        }
        return dates;
    }

    function diffDays(a, b) {
        const msPerDay = 24 * 60 * 60 * 1000;
        const utcA = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
        const utcB = Date.UTC(b.getFullYear(), b.getMonth(), b.getDate());
        return Math.round((utcB - utcA) / msPerDay);
    }

    function sameDate(a, b) {
        return a.getFullYear() === b.getFullYear() &&
            a.getMonth() === b.getMonth() &&
            a.getDate() === b.getDate();
    }

    function render(selectedHeader, selectedDate) {
        container.innerHTML = "";
        const visibleTasks = applyDateFilter(
            getFilteredTasksByHeader(selectedHeader),
            selectedDate
        );

        const realTasks = visibleTasks.filter(function (task) {
            return !task.is_group && task.start && task.end;
        });

        if (!realTasks.length) {
            container.innerHTML = selectedHeader === "__ALL__"
                ? "<p>No scheduled activities</p>"
                : "<p>No scheduled activities for selected header</p>";
            if (infoPanel) {
                infoPanel.innerHTML = "";
            }
            return;
        }

        const allDates = realTasks.flatMap(function (task) {
            const start = parseDate(task.start);
            const end = parseDate(task.end);
            const endForRange = end > start ? addDays(end, -1) : start;
            const dates = [endForRange];
            if (task.delay_date && task.delay_status && task.delay_status !== "on_schedule") {
                dates.push(parseDate(task.delay_date));
            }
            return dates;
        });

        const minStartDate = new Date(Math.min.apply(null, realTasks.map(function (task) {
            return parseDate(task.start);
        })));
        const baseStartRaw = container.dataset.startDate || "";
        const baseStartDate = parseDate(baseStartRaw);
        let minDate = minStartDate;
        if (!Number.isNaN(baseStartDate.getTime()) && baseStartDate < minStartDate) {
            minDate = baseStartDate;
        }
        const maxDate = new Date(Math.max.apply(null, allDates));
        const timelineDates = getDateRange(minDate, maxDate);

        const wrap = document.createElement("div");
        wrap.className = "gantt-grid-wrap";
        const table = document.createElement("table");
        table.className = "gantt-grid";
        const colWidths = getColumnWidths();

        const thead = document.createElement("thead");
        const headRow = document.createElement("tr");
        const activityHead = document.createElement("th");
        activityHead.className = "gantt-grid-activity-head";
        activityHead.textContent = "Activity";
        activityHead.style.width = colWidths.activity + "px";
        activityHead.style.minWidth = colWidths.activity + "px";
        headRow.appendChild(activityHead);

        timelineDates.forEach(function (date) {
            const th = document.createElement("th");
            th.className = "gantt-grid-date-head";
            th.textContent = formatDate(date);
            th.style.width = colWidths.day + "px";
            th.style.minWidth = colWidths.day + "px";
            headRow.appendChild(th);
        });

        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        visibleTasks.forEach(function (task) {
            if (task.is_group) {
                const row = document.createElement("tr");
                row.className = "gantt-grid-group-row";

                const label = document.createElement("td");
                label.className = "gantt-grid-group-label";
                label.textContent = task.name || "";
                label.style.width = colWidths.activity + "px";
                label.style.minWidth = colWidths.activity + "px";
                row.appendChild(label);

                timelineDates.forEach(function () {
                    const cell = document.createElement("td");
                    cell.className = "gantt-grid-group-cell";
                    cell.style.width = colWidths.day + "px";
                    cell.style.minWidth = colWidths.day + "px";
                    row.appendChild(cell);
                });

                tbody.appendChild(row);
                return;
            }

            if (!task.start || !task.end) {
                return;
            }

            const row = document.createElement("tr");
            row.className = "gantt-grid-task-row";
            const start = parseDate(task.start);
            const end = parseDate(task.end);
            const endExclusive = end > start ? end : addDays(start, 1);
            const required = Number(task.required || 0);
            const actual = Number(task.actual || 0);
            const delayStatus = task.delay_status || "on_schedule";
            const delayDate = task.delay_date || "";
            const delayDateObj = delayDate ? parseDate(delayDate) : null;

            const label = document.createElement("td");
            label.className = "gantt-grid-task-label";
            if (delayStatus === "significant_delay") {
                label.classList.add("status-delayed");
            } else if (delayStatus === "minor_delay") {
                label.classList.add("status-minor-delay");
            } else if (delayStatus === "on_schedule") {
                label.classList.add("status-ontrack");
            }
            const labelName = document.createElement("div");
            labelName.className = "gantt-task-name";
            labelName.textContent = task.name;
            const indentLevel = Number(task.indent_level || 0);
            if (indentLevel > 0) {
                labelName.style.paddingLeft = `${indentLevel * 18}px`;
            }
            label.appendChild(labelName);
            label.style.width = colWidths.activity + "px";
            label.style.minWidth = colWidths.activity + "px";
            row.appendChild(label);

            timelineDates.forEach(function (date) {
                const cell = document.createElement("td");
                cell.className = "gantt-grid-day";
                cell.style.width = colWidths.day + "px";
                cell.style.minWidth = colWidths.day + "px";

                const isActive = (date >= start && date < endExclusive) || sameDate(date, start);
                if (isActive) {
                    cell.classList.add("is-active");
                    cell.classList.add("is-line-active");
                    if (delayStatus === "significant_delay") {
                        cell.classList.add("is-delayed");
                    } else if (delayStatus === "minor_delay") {
                        cell.classList.add("is-minor-delay");
                    } else if (delayStatus === "on_schedule") {
                        cell.classList.add("is-ontrack");
                    } else {
                        cell.classList.add("is-noprogress");
                    }
                }
                if (delayDateObj && delayStatus !== "on_schedule" && sameDate(date, delayDateObj)) {
                    cell.classList.add("has-delay-date");
                    cell.textContent = delayDate;
                    cell.title = "Delay date: " + delayDate;
                }
                row.appendChild(cell);
            });

            row.addEventListener("click", function () {
                if (!infoPanel) {
                    return;
                }
                infoPanel.innerHTML = `
                    <div class="gantt-info-card">
                        <h3>Task: ${task.name}</h3>
                        <p><strong>Start:</strong> ${task.start}</p>
                        <p><strong>End:</strong> ${task.end}</p>
                        <p><strong>Required Workers:</strong> ${required}</p>
                        <p><strong>Actual Workers:</strong> ${actual}</p>
                        <p><strong>Delay Status:</strong> ${delayStatus.split("_").join(" ").toUpperCase()}</p>
                        ${delayDate ? `<p><strong>Delay Date:</strong> ${delayDate}</p>` : ""}
                        <p><strong>Quantity:</strong> ${task.quantity || 0} ${task.unit || ""}</p>
                    </div>
                `;
            });

            tbody.appendChild(row);
        });

        table.appendChild(tbody);

        const activityColWidth = colWidths.activity;
        const dayColWidth = colWidths.day;
        const baseWidth = activityColWidth + (timelineDates.length * dayColWidth);
        table.style.width = baseWidth + "px";

        wrap.appendChild(table);
        container.appendChild(wrap);

        // Keep first scheduled bars visible only when the timeline starts at the first task.
        const startOffsetDays = Math.max(0, diffDays(minDate, minStartDate));
        const anchorIsEarlier = !Number.isNaN(baseStartDate.getTime()) && baseStartDate < minStartDate;
        if (anchorIsEarlier) {
            wrap.scrollLeft = 0;
        } else {
            wrap.scrollLeft = Math.max(0, (startOffsetDays - 1) * colWidths.day);
        }
    }
});
