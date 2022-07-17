function init() {
    fetch("/logs ").then((json) => {
            console.log(json)

        })
    fetch("/logs_data").then((json) => {
            json.json().then(r => load_data(r))
        })
}

function load_data(data) {
    let narrative = data["narrative"];
    let overview = data["overview"];
    load_title("Narrative Service");
    load_top_querystring(narrative["topTenQueries"], "Top 100 searched queries");
    load_performed_queries(narrative["amountQueries"], "Performed Queries");
    load_usage_graph(narrative['graphInput'], "performed queries");
    load_title("Drug Overviews");
    load_top_querystring(overview["topTenQueries"], "Top 100 searches");
    load_performed_queries(overview["amountQueries"], "Performed searches");
    load_usage_graph(overview['graphInput'], "performed searches");
}

function load_title(title) {
    let db = document.getElementById("dashboard");
    let titleDiv = document.createElement("div");
    titleDiv.className = "title";
    let text = document.createElement("h1");
    text.innerHTML = title;
    titleDiv.appendChild(text);
    db.appendChild(titleDiv);
}

function load_usage_graph(data, y_label) {
    let db = document.getElementById("dashboard");
    let usage = document.createElement("div");
    usage.className = "section";
    let titleUG = document.createElement("h2");
    titleUG.innerHTML = "Usage in the last";
    let graphInput = document.createElement("input");
    graphInput.className = "slider";
    graphInput.setAttribute("type", "range");
    graphInput.setAttribute("list", "tickmarks");
    graphInput.setAttribute("min", "0");
    graphInput.setAttribute("max", "30");
    let timesList = document.createElement("datalist");
    timesList.setAttribute("id", "tickmarks")
    let elementS = document.createElement("option");
    elementS.setAttribute("value", "0");
    elementS.setAttribute("label", "7 days");
    let elementTO = document.createElement("option");
    elementTO.setAttribute("value", "10");
    elementTO.setAttribute("label", "31 days");
    let elementHE = document.createElement("option");
    elementHE.setAttribute("value", "20");
    elementHE.setAttribute("label", "182 days");
    let elementTSF = document.createElement("option");
    elementTSF.setAttribute("value", "30");
    elementTSF.setAttribute("label", "365 days");
    timesList.appendChild(elementS);
    timesList.appendChild(elementTO);
    timesList.appendChild(elementHE);
    timesList.appendChild(elementTSF);
    usage.appendChild(titleUG);
    usage.appendChild(graphInput);
    usage.appendChild(timesList);
    let chartDiv = document.createElement("div");
    let canvas = document.createElement("canvas");
    canvas.setAttribute("id", "myChart");
    chartDiv.appendChild(canvas);
    let values = getValues(data["365"]);
    console.log(getValues(data["31"]));
    createGraph(values[0], values[1], canvas, y_label);
    usage.appendChild(chartDiv);
    graphInput.oninput = function() {
        if (this.value % 10 !== 0 && this.value != 0){
            let counter_plus = 0;
            let counter_minus = 0;
            let currentValue = parseInt(this.value, 10);
            while (currentValue % 10 != 0 && currentValue != 0) {
                counter_plus = counter_plus + 1;
                currentValue = currentValue + 1;
            }
            currentValue = currentValue - counter_plus;
            while (currentValue % 10 != 0 && currentValue != 0) {
                counter_minus = counter_minus + 1;
                currentValue = currentValue - 1;
            }
            if (counter_minus > counter_plus) {
                this.value = parseInt(this.value, 10) + counter_plus;
            } else {
                this.value= parseInt(this.value, 10) - counter_minus;
            }
        }
        removeAllChildNodes(chartDiv);
        let canvas = document.createElement("canvas");
        canvas.setAttribute("id", "myChart");
        chartDiv.appendChild(canvas);
        if (this.value == 0) {
            let values = getValues(data["7"]);
            createGraph(values[0], values[1], canvas, y_label);
        } else if (this.value == 10) {
            let values = getValues(data["31"]);
            createGraph(values[0], values[1], canvas, y_label);
        } else if (this.value == 20) {
            let values = getValues(data["182"]);
            createGraph(values[0], values[1], canvas, y_label);
        } else if (this.value == 30) {
            let values = getValues(data["365"]);
            createGraph(values[0], values[1], canvas, y_label);
        }
        usage.appendChild(chartDiv);
    }
    db.appendChild(usage);
}

function createGraph(x_values, y_values, canvas, y_label) {
    let y_max = 0;
    for (let i in y_values) {
        if (parseInt(i, 10) > y_max) {
            y_max = parseInt(i, 10);
        }
    }
    new Chart(canvas, {
        type: "line",
        data: {
            labels: x_values,
            datasets: [{
                fill: false,
                lineTension: 0,
                pointBackgroundColor: "rgb(0,152,121)",
                borderColor: "rgb(0,152,121, 0.7)",
                data: y_values
            }]
        },
        options:{
            legend: {display: false},
            scales: {
                xAxes: [{scaleLabel: {
                            display: true,
                            labelString: 'days before today'},
                        ticks: {min: x_values.length, max:0}}],
                yAxes: [{scaleLabel: {
                            display: true,
                            labelString: y_label},
                        ticks: {min: 0, max:y_max.length}}],
            }
        }
    });
}

function getValues(data) {
    let x_values = [];
    let y_values = [];
    let values = [];
    for (let obj in data) {
        console.log(obj);
        console.log(data[obj]);
        x_values.push(obj);
        y_values.push(data[obj]);
    }
    values.push(x_values.reverse());
    values.push(y_values.reverse());
    return values
}

function load_performed_queries(data,title) {
    let db = document.getElementById("dashboard");
    let performedQueries = document.createElement("div");
    performedQueries.className = "section";
    let titlePQ = document.createElement("h2");
    titlePQ.innerHTML = title;
    let fixTableHeads = document.createElement("div");
    fixTableHeads.className = "tableFixHead";
    let amountTable = document.createElement("table");
    amountTable.className = "queryTable";
    let tHeader = document.createElement("thead");
    let tableHeader = document.createElement("tr");
    let queryHeaderName = document.createElement("th");
    queryHeaderName.innerHTML = "Time";
    let queryHeaderAmount = document.createElement("th");
    queryHeaderAmount.innerHTML = "Number";
    tableHeader.appendChild(queryHeaderName);
    tableHeader.appendChild(queryHeaderAmount);
    tHeader.appendChild(tableHeader);
    amountTable.appendChild(tHeader);
    let tbody = document.createElement("tbody");
    for (let obj in data) {
        let tableLine = document.createElement("tr");
        let queryName = document.createElement("td");
        let queryAmount = document.createElement("td");
        let time = "";
        if (obj == "t") {
            time = "Today";
        } else if (obj == "tw") {
            time = "This week";
        } else if (obj == "tm") {
            time = "This month";
        } else if (obj == "lm") {
            time = "Last Month";
        } else if (obj == "ty") {
            time = "This year";
        } else if (obj == "ly") {
            time = "Last year";
        }
        queryName.innerHTML = time;
        queryAmount.innerHTML = data[obj];
        tableLine.appendChild(queryName);
        tableLine.appendChild(queryAmount);
        tbody.appendChild(tableLine);
    }
    amountTable.appendChild(tbody);
    performedQueries.appendChild(titlePQ);
    fixTableHeads.appendChild(amountTable)
    performedQueries.appendChild(fixTableHeads);
    db.appendChild(performedQueries);
}

function load_top_querystring(data, title) {
    let db = document.getElementById("dashboard");
    let topTenQueries = document.createElement("div");
    topTenQueries.className = "section";
    let titleTFQ = document.createElement("h2");
    titleTFQ.innerHTML = title;
    let input = document.createElement("input");
    input.className = "slider";
    input.setAttribute("type", "range");
    input.setAttribute("list", "tickmarks");
    input.setAttribute("min", "0");
    input.setAttribute("max", "40");
    let timesList = document.createElement("datalist");
    timesList.setAttribute("id", "tickmarks")
    let elementToday = document.createElement("option");
    elementToday.setAttribute("value", "0");
    elementToday.setAttribute("label", "Today");
    let elementWeek = document.createElement("option");
    elementWeek.setAttribute("value", "10");
    elementWeek.setAttribute("label", "This week");
    let elementMonth = document.createElement("option");
    elementMonth.setAttribute("value", "20");
    elementMonth.setAttribute("label", "This month");
    let elementYear = document.createElement("option");
    elementYear.setAttribute("value", "30");
    elementYear.setAttribute("label", "This year");
    let elementAll = document.createElement("option");
    elementAll.setAttribute("value", "40");
    elementAll.setAttribute("label", "Overall");
    timesList.appendChild(elementToday);
    timesList.appendChild(elementWeek);
    timesList.appendChild(elementMonth);
    timesList.appendChild(elementYear);
    timesList.appendChild(elementAll);
    topTenQueries.appendChild(titleTFQ);
    topTenQueries.appendChild(input);
    topTenQueries.appendChild(timesList);
    let fixTableHeads = document.createElement("div");
    fixTableHeads.className = "tableFixHead";
    let queryTable = document.createElement("table");
    queryTable.className = "queryTable";
    let theader = document.createElement("thead");
    let tableHeader = document.createElement("tr");
    let queryHeaderName = document.createElement("th");
    queryHeaderName.innerHTML = "Query";
    let queryHeaderAmount = document.createElement("th");
    queryHeaderAmount.innerHTML = "Number";
    tableHeader.appendChild(queryHeaderName);
    tableHeader.appendChild(queryHeaderAmount);
    theader.appendChild(tableHeader);
    queryTable.appendChild(theader);
    let tbody = document.createElement("tbody");
    tbody.setAttribute("id", "tbody");
    iterateThroughData(data, "a", tbody);
    queryTable.appendChild(tbody);
    input.oninput = function() {
        if(this.value % 10 != 0 && this.value != 0){
            let counter_plus = 0;
            let counter_minus = 0;
            let currentValue = parseInt(this.value, 10);
            while (currentValue % 10 != 0 && currentValue != 0) {
                counter_plus = counter_plus + 1;
                currentValue = currentValue + 1;
            }
            currentValue = currentValue - counter_plus;
            while (currentValue % 10 != 0 && currentValue != 0) {
                counter_minus = counter_minus + 1;
                currentValue = currentValue - 1;
            }
            if (counter_minus > counter_plus) {
                this.value = parseInt(this.value, 10) + counter_plus;
            } else {
                this.value= parseInt(this.value, 10) - counter_minus;
            }
        }
        removeAllChildNodes(tbody);
        if (this.value == 0) {

            iterateThroughData(data, "t", tbody);
        } else if (this.value == 10) {

            iterateThroughData(data, "tw", tbody);
        } else if (this.value == 20) {

            iterateThroughData(data, "tm", tbody);
        } else if (this.value == 30) {

            iterateThroughData(data, "ty", tbody);
        } else if (this.value == 40) {

            iterateThroughData(data, "a", tbody);
        }
        queryTable.appendChild(tbody);
    }
    fixTableHeads.appendChild(queryTable);
    topTenQueries.appendChild(fixTableHeads);
    db.appendChild(topTenQueries);
}

function iterateThroughData(data, time, element) {
    for (let obj in data[time]) {
        let tableLine = document.createElement("tr");
        let queryName = document.createElement("td");
        let queryAmount = document.createElement("td");
        queryName.innerHTML = obj;
        queryAmount.innerHTML = data[time][obj];
        tableLine.appendChild(queryName);
        tableLine.appendChild(queryAmount);
        element.appendChild(tableLine);
    }
}

function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}

init();