const nt_prefix = "narrative"
const ov_prefix = "overview"

function init() {
    fetch("/logs_data").then((json) => {
            json.json().then(r => load_data(r))
        }).catch((e) => console.log(e))
}

function load_data(data) {
    const narrative = data[nt_prefix];
    const overview = data[ov_prefix];
    load_top_querystring(narrative["topQueries"], nt_prefix);
    load_performed_queries(narrative["amountQueries"], nt_prefix);
    load_usage_graph(narrative['graphInput'], "performed queries", nt_prefix);
    load_top_querystring(overview["topQueries"], ov_prefix);
    load_performed_queries(overview["amountQueries"], ov_prefix);
    load_usage_graph(overview['graphInput'], "performed queries",ov_prefix);
}

function load_usage_graph(data, y_label, prefix) {
    const graphInput = document.getElementById(prefix+"_graph_input")
    const container = document.getElementById(prefix+"_graph_container")
    let chartDiv = document.createElement("div");
    let canvas = document.createElement("canvas");
    canvas.setAttribute("id", "myChart");
    chartDiv.appendChild(canvas);
    let values = getValues(data["365"]);
    createGraph(values[0], values[1], canvas, y_label);
    container.appendChild(chartDiv);
    graphInput.oninput = function() {
        chartDiv.innerHTML = ""

        let canvas = document.createElement("canvas");
        canvas.setAttribute("id", "myChart");
        chartDiv.appendChild(canvas);

        let values;

        switch (graphInput.value) {
            case "0":
                values = getValues(data["7"]);
                createGraph(values[0], values[1], canvas, y_label);
                break;
            case "1":
                values = getValues(data["31"]);
                createGraph(values[0], values[1], canvas, y_label);
                break;
            case "2":
                values = getValues(data["182"]);
                createGraph(values[0], values[1], canvas, y_label);
                break;
            case "3":
                values = getValues(data["365"]);
                createGraph(values[0], values[1], canvas, y_label);
                break;
            default:
                break;
        }
    }
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
        x_values.push(obj);
        y_values.push(data[obj]);
    }
    values.push(x_values.reverse());
    values.push(y_values.reverse());
    return values
}

function load_performed_queries(data, prefix) {
    const time_map = {
        "t":"Today",
        "tw":"This week",
        "tm":"This month",
        "lm":"Last month",
        "ty":"This year",
        "ly":"Last year"
    }

    let tbody = document.getElementById(prefix+"_table_perf_queries");
    for (let obj in data) {
        let tableLine = document.createElement("tr");
        let queryName = document.createElement("td");
        let queryAmount = document.createElement("td");
        queryName.innerHTML = time_map[obj];
        queryAmount.innerHTML = data[obj];
        tableLine.appendChild(queryName);
        tableLine.appendChild(queryAmount);
        tbody.appendChild(tableLine);
    }
}


function change_table_data(prefix, suffix, data) {
    const input = document.getElementById(prefix+"_input_"+suffix);
    let tbody = document.getElementById(prefix+"_table_"+suffix);

    tbody.innerHTML = "";

    switch (input.value) {
        case "0":
            iterateThroughData(data, "t", tbody);
            break;
        case "1":
            iterateThroughData(data, "tw", tbody);
            break;
        case "2":
            iterateThroughData(data, "tm", tbody);
            break;
        case "3":
            iterateThroughData(data, "ty", tbody);
            break;
        case "4":
            iterateThroughData(data, "a", tbody);
            break;
        default:
            break;
    }
}


function load_top_querystring(data, prefix) {
    let tbody = document.getElementById(prefix+"_table_top_hundred");
    iterateThroughData(data, "a", tbody);

    let input = document.getElementById(prefix+"_input_top_hundred");
    input.oninput = () => change_table_data(prefix, "top_hundred", data);
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

document.body.onload = () => init();