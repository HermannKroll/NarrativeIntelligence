if (window.historyQueryKey === undefined) {
    window.historyQueryKey = ""
}


/**
 * Object structure to store one searched query of the current session
 */
class HistoryEntry {
    /**
     * Create a history element
     * @param rawQuery {string} query string of the URL
     * @param options {{}} additional column options
     */
    constructor(rawQuery, options = {}) {
        this.raw = rawQuery
        this.query = new URLSearchParams(window.location.search).get(historyQueryKey);
        const date = new Date(Date.now());
        this.timestamp = date.toLocaleDateString() + " " + date.toLocaleTimeString();
        this.options = options;
    }
}

/**
 * Create an HTML table-row from a HistoryEntry
 * @param entry {HistoryEntry}
 * @returns {HTMLTableRowElement}
 */
function historyToTableRow(entry) {
    const tableRow = document.createElement("tr");
    const dateCell = document.createElement("td");
    const queryCell = document.createElement("td");
    const queryAnchor = document.createElement("a");

    dateCell.innerText = entry.timestamp;
    queryAnchor.innerText = entry.query
        .replace("+", " ")
        .replace("_AND_", " AND\n ");
    queryAnchor.href = entry.raw;

    queryCell.appendChild(queryAnchor);
    tableRow.appendChild(dateCell);
    tableRow.appendChild(queryCell);

    if (entry.options.filterOptions !== undefined) {
        const filterOptions = entry.options.filterOptions;
        const restrictionCell = document.createElement("td");
        let restrictionText = "";
        if (filterOptions.title_filter !== undefined && filterOptions.title_filter.length > 0) {
            let titleFilter = filterOptions.title_filter;
            let useSysReview = false;

            if (titleFilter.includes("systemat review")) {
                titleFilter = titleFilter.replace("systemat review", "").trim();
                useSysReview = true;
            }

            if (titleFilter.length > 0)
                restrictionText += "<strong>Title-Filter</strong>: " + titleFilter.toString() + "<br>";

            if (useSysReview)
                restrictionText += "<strong>Other</strong>: systematic review<br>"
        }

        if (filterOptions.use_classification)
            restrictionText += "<strong>Other</strong>: pharm. technology<br>"

        if (filterOptions.state === "recommend")
            restrictionText += "recommended documents<br>"
        // insert further restrictions / filter options

        // remove the break at the end
        restrictionText = restrictionText.replace(/<br>$/i, "");
        restrictionCell.innerHTML = restrictionText;
        tableRow.appendChild(restrictionCell);
    }

    if (entry.options.size !== undefined) {
        const resultsCell = document.createElement("td");
        resultsCell.innerText = entry.options.size.toString();
        tableRow.appendChild(resultsCell);
    }

    return tableRow;
}

function closeHistory() {
    document.querySelector("#historyModal")?.classList.toggle("d-flex");
}

function openHistory() {
    loadHistory();
    document.querySelector("#historyModal")?.classList.toggle("d-flex");
}

/**
 * Load the session based history from the sessionStorage and create the corresponding
 * HTML list of searched elements.
 */
function loadHistory() {
    const historyList = document.querySelector("#historyTable");
    const key = "history" + window.location.pathname.replace("/", "_");
    const value = window.sessionStorage.getItem(key);

    if (!value)
        return;

    const history = JSON.parse(value);
    historyList.innerHTML = "";

    history.reverse().forEach((e) => historyList.appendChild(historyToTableRow(e)));
}

/**
 * Add the newly searched term to the history if not already contained.
 * Therefore, the complete `query string` of the URL has to be the same.
 * The resulting HistoryEntry instance is inserted into the sessionStorage
 * and can be retrieved using the key consisting of "history" + `URL.path`.
 */
function saveHistoryEntry(options) {
    const key = "history" + window.location.pathname.replace("/", "_");
    const queryObj = new HistoryEntry(window.location.search, options);
    const value = window.sessionStorage.getItem(key);

    if (!value) {
        window.sessionStorage.setItem(key, JSON.stringify([queryObj]));
        return;
    }

    const history = JSON.parse(value);
    if (history.some((e) => e.raw === queryObj.raw))
        return;

    history.push(queryObj);
    window.sessionStorage.setItem(key, JSON.stringify(history));
}
