let latest_valid_query = '';
let latest_query_translation = '';
let DEFAULT_RESULT_DIVS_LIMIT = 500;
let DEFAULT_AGGREGATED_RESULTS_PER_PAGE = 30;
let MAX_SHOWN_ELEMENTS = DEFAULT_AGGREGATED_RESULTS_PER_PAGE;
let recommender_graph = null;
let recommender_papernetwork = null;

const YEAR_RESULT_FILTER_CONFIG = {
    scales: {
        xAxes: [{
            display: false
        }],
        yAxes: [{
            display: false //this will remove all the x-axis grid lines
        }]
    },
    legend: {display: false},
}


function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

$('#btn_search_again').click(() => {
    const predicate_input = document.getElementById('input_predicate');
    predicate_input.selectedIndex = 0;
    refreshSearch();
})

function refreshSearch(fromUrl = false) {
    if (result_present()) {
        let divDocuments = $('#div_documents');
        divDocuments.empty();
        if (fromUrl === false) {
            setCurrentPage(0);
        }
        document.getElementById("btn_search").click();
    }
}

function result_present() {
    return $("#div_documents")[0].hasChildNodes()
}

document.getElementById("select_sorting_year").addEventListener("change", function () {
    document.getElementById("btn_search").click()
});
document.getElementById("select_sorting_freq").addEventListener("change", function () {
    document.getElementById("btn_search").click()
});

const setButtonSearching = isSearching => {
    let btn = $('#btn_search');
    let help = $('#help_search');
    btn.empty();

    if (isSearching) {
        let span = $('<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>');
        btn.append(span)
            .append("Searching")
            .prop("disabled", true);
        help.fadeIn();
    } else {
        btn.append("Search")
            .prop("disabled", false);
        help.fadeOut();
    }
};

$(document).on('keydown', function (e) {
    var $target = $(e.target || e.srcElement);
    if (e.keyCode === 8 && !$target.is('input,[contenteditable="true"],textarea')) {
        e.preventDefault();
    }
})

$(document).ready(function () {

    $("#input_title_filter").on('keyup', function (e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            search(e);
        }
    });

    buildSelectionTrees();

    $("#search_form").submit(search);

    document.getElementById("input_page_no").addEventListener('change', (event) => {
        pageUpdated();
    });

    // Try to initialize from search url parameters if possible
    initFromURLQueryParams();
});


function initFromURLQueryParams() {
    const url = new URL(window.location.href);
    let params = new URLSearchParams(url.search);

    if (params.has("visualization")) {
        let visualization = params.get("visualization");
        if (visualization === "outer_ranking_substitution") {
            document.getElementById('radio_outer_ranking_a').checked = true;
            document.getElementById('radio_outer_ranking_b').checked = false;
        } else {
            document.getElementById('radio_outer_ranking_a').checked = false;
            document.getElementById('radio_outer_ranking_b').checked = true;
        }
    }

    if (params.has("sort_frequency_desc")) {
        let sort_frequency = params.get("sort_frequency_desc");
        document.getElementById('select_sorting_freq').value = sort_frequency;
    }

    if (params.has("sort_year_desc")) {
        let sort_year = params.get("sort_year_desc");
        document.getElementById('select_sorting_year').value = sort_year;
    }

    if (params.has("data_source")) {
        let data_source = params.get("data_source");
        if (data_source === "LongCovid") {
            document.getElementById("radio_long_covid").checked = true;
        } else if (data_source === "LitCovid") {
            document.getElementById("radio_litcovid").checked = true;
        } else if (data_source === "ZBMed") {
            document.getElementById("radio_zbmed").checked = true;
        } else {
            document.getElementById("radio_pubmed").checked = true;
        }
        lastDataSource = data_source;
    }

    if (params.has("start_pos")) {
        setCurrentPage(parseInt(params.get("start_pos")))
    }
    if (params.has("year_start") && params.has("year_end")) {
        document.querySelector('#fromSlider').value = params.get("year_start");
        document.querySelector('#toSlider').value = params.get("year_end");
    }
    if (params.has("title_filter")) {
        let titleFilter = params.get("title_filter");
        if (titleFilter.includes("systemat review")) {
            document.getElementById("checkbox_sys_review").checked = true;
            titleFilter = titleFilter.replace("systemat review", "").trim();
        } else {
            document.getElementById("checkbox_sys_review").checked = false;
        }
        document.getElementById("input_title_filter").value = titleFilter;
    }
    if (params.has("classification_filter")) {
        document.getElementById("checkbox_classification").checked = true;
    }
    if (params.has("query")) {
        let query = params.get("query");
        lastQuery = query;
        document.getElementById("search_input").value = query;
        document.getElementById("btn_search").click();
    }
}

let currentMaxPage = 0;
let lastCurrentPage = 0;

function setCurrentPage(start_pos) {
    let currentPage = 1 + Math.ceil(start_pos / DEFAULT_AGGREGATED_RESULTS_PER_PAGE);
    document.getElementById("input_page_no").value = currentPage.toString();
}

function pageUpdated() {
    let currentPage = parseInt(document.getElementById("input_page_no").value);
    if (currentPage === lastCurrentPage) {
        return;
    }
    if (currentPage < 0) {
        currentPage = 0;
        document.getElementById("input_page_no").value = currentPage.toString();
    } else if (currentPage > currentMaxPage) {
        currentPage = currentMaxPage;
        document.getElementById("input_page_no").value = currentPage.toString();
    }
    lastCurrentPage = currentPage;
    // Trigger the search
    refreshSearch(true);
}

function computePageInfo(result_size) {
    let pageCount = Math.ceil(parseInt(result_size) / DEFAULT_AGGREGATED_RESULTS_PER_PAGE);
    currentMaxPage = pageCount;

    // handle empty results appropriately to increase UX
    if (pageCount === 0)
        pageCount = 1;

    document.getElementById("input_page_no").max = pageCount;
    document.getElementById("label_max_page").textContent = pageCount.toString();
    document.getElementById("div_input_page").style.display = "block";
}

function getStartPositionBasedOnCurrentPage() {
    return DEFAULT_AGGREGATED_RESULTS_PER_PAGE * (document.getElementById("input_page_no").value - 1);
}

let lastQuery = "";
let lastDataSource = "";


const search = (event) => {
    $('#collapseExamples').collapse('hide');
    $('#modal_empty_result').hide();
    $('#alert_translation').hide();
    let query = document.getElementById("search_input").value;
    console.log(query);

    const parameters = getInputParameters(query);
    setButtonSearching(true);
    logInputParameters(parameters);
    updateURLParameters(parameters);

    submitSearch(parameters)
        .finally(() => setButtonSearching(false));
}

/**
 * Function creates a request including the provided parameters. On success, the response
 * gets parsed appropriately and function to visualize the data is executed. Errors are
 * debug logged so no further errors have to handled while executing this function.
 * @param parameters {{}}
 * @returns {Promise<void | void>}
 */
function submitSearch(parameters) {
    const parameterString = createURLParameterString(parameters);

    return fetch(search_url + "?" + parameterString)
        .then((response) => response.json())
        .then((data) => showResults(data, parameters))
        .catch((e) => console.log(e))
}

/**
 * Function creates a parameter string that has only elements with valid values.
 * @param parameters {{}}
 * @returns {string}
 */
function createURLParameterString(parameters) {
    return Object.entries(parameters).map(([key, value]) => {
        if (value === undefined || value === null) {
            return;
        }
        return key.toString() + "=" + value.toString();
    }).join("&");
}

/**
 * Function to adjusts the current URL based on the provided parameters object.
 * @param parameters {{}}
 */
function updateURLParameters(parameters) {
    const url = new URL(window.location.href);
    url.searchParams.set('query', parameters["query"]);
    url.searchParams.set("data_source", parameters["data_source"]);
    if (parameters["outer_ranking"] !== "outer_ranking_substitution") {
        url.searchParams.set("visualization", parameters["outer_ranking"]);
    } else {
        url.searchParams.delete("visualization");
    }

    if (parameters["freq_sort"] !== "True") {
        url.searchParams.set("sort_frequency_desc", parameters["freq_sort"]);
    } else {
        url.searchParams.delete("sort_frequency_desc");
    }

    if (parameters["year_sort"] !== "True") {
        url.searchParams.set("sort_year_desc", parameters["year_sort"]);
    } else {
        url.searchParams.delete("sort_year_desc");
    }

    if (parameters["start_pos"] !== 0) {
        url.searchParams.set("start_pos", parameters["start_pos"]);
    } else {
        url.searchParams.delete("start_pos");
    }

    //   url.searchParams.set("end_pos", end_pos);
    if (parameters["year_start"] !== undefined && parameters["year_start"] !== document.querySelector("#fromSlider").min) {
        url.searchParams.set("year_start", parameters["year_start"]);
    } else {
        url.searchParams.delete("year_start");
    }
    if (parameters["year_end"] !== undefined && parameters["year_end"] !== document.querySelector("#toSlider").max) {
        url.searchParams.set("year_end", parameters["year_end"]);
    } else {
        url.searchParams.delete("year_end");
    }
    if (parameters["use_sys_review"]) {
        if (!parameters["title_filter"].includes("systemat review")) {
            if (parameters["title_filter"].length > 0)
                parameters["title_filter"] += " ";
            parameters["title_filter"] += "systemat review";
        }
    } else {
        parameters["title_filter"] = parameters["title_filter"].replace("systemat review", "");
    }
    if (parameters["title_filter"].length > 0) {
        url.searchParams.set("title_filter", parameters["title_filter"]);
    } else {
        url.searchParams.delete("title_filter");
    }

    if (parameters["use_classification"]) {
        url.searchParams.set("classification_filter", "PharmaceuticalTechnology");
        parameters["classification_filter"] = "PharmaceuticalTechnology";
    } else {
        url.searchParams.delete("classification_filter");
    }
    window.history.pushState("Query", "Title", "/recommendation" + url.search.toString());
}

/**
 * Function to debug log the provided input parameters.
 * @param parameters {{}}
 */
function logInputParameters(parameters) {
    console.log("Query: " + parameters["query"]);
    console.log("Data source: " + parameters["data_source"]);
    console.log("Outer Ranking: " + parameters["outer_ranking"]);
    console.log("Inner Ranking: " + parameters["inner_ranking"]);
    console.log("Sorting by frequency (desc): " + parameters["freq_sort_desc"]);
    console.log("Sorting by year (desc): " + parameters["year_sort_desc"]);
    console.log("Start position: " + parameters["start_pos"]);
    console.log("End position: " + parameters["end_pos"]);
    console.log("Start year: " + parameters["year_start"]);
    console.log("End year: " + parameters["year_end"]);
    console.log("Title filter: " + parameters["title_filter"]);
    console.log("Classification: " + parameters["use_classification"]);
}

/**
 * Function stores all necessary values of each input filter into one object.
 * @param query {string} formatted query string
 * @returns {{}} object of each filter input element
 */
function getInputParameters(query) {
    const obj = {};

    obj["query"] = query;
    adjustSelectedPage(obj);
    obj["freq_sort"] = document.getElementById("select_sorting_freq").value;
    obj["year_sort"] = document.getElementById("select_sorting_year").value;
    if (obj["year_sort"] === "Relevance") {
        obj["year_sort"] = "Latest Publications First";
    }
    let data_source = document.querySelector('input[name = "data_source"]:checked').value;
    lastDataSource = data_source;
    obj["data_source"] = data_source;
    obj["outer_ranking"] = document.querySelector('input[name = "outer_ranking"]:checked').value;
    //let inner_ranking = document.querySelector('input[name = "inner_ranking"]:checked').value;
    //dict["inner_ranking"] = "NOT IMPLEMENTED";
    obj["title_filter"] = document.getElementById("input_title_filter").value.trim();

    if (latest_query_translation === query) {
        // add year filter params only if the filter already contains valid years (of the current search)
        obj["year_start"] = document.querySelector("#fromSlider").value;
        obj["year_end"] = document.querySelector("#toSlider").value;
    } else {
        // remove filter if the query contains a new search
        document.getElementById("checkbox_classification").checked = false;
        document.getElementById("checkbox_sys_review").checked = false;
    }

    obj["use_classification"] = document.getElementById("checkbox_classification").checked;
    obj["use_sys_review"] = document.getElementById("checkbox_sys_review").checked;

    obj["classification_filter"] = null;
    return obj;
}

/**
 * Function resets the visible page of the result window depending on the provided query.
 * Additionally, the `start_pos` and `end_pos` are added to the parameters object.
 * @param parameters {{}}
 */
function adjustSelectedPage(parameters) {
    let start_pos = getStartPositionBasedOnCurrentPage();
    // consider start pos only if query isn't changed
    if (lastQuery !== parameters["query"]) {
        document.getElementById("input_title_filter").value = "";
        start_pos = 0;
        setCurrentPage(0);
        lastQuery = parameters["query"];
    }
    let end_pos = start_pos + DEFAULT_AGGREGATED_RESULTS_PER_PAGE;
    parameters["start_pos"] = start_pos;
    parameters["end_pos"] = end_pos;
}

/**
 * Function processes the response object, retrieved from the request, and creates all relevant
 * result elements based on the previously provided input parameters object.
 * @param response {{}}
 * @param parameters {{}}
 */
function showResults(response, parameters) {
    // Clear DIVs
    let form = $('#graph-patterns');
    form.empty();
    let divDocuments = $('#div_documents');
    divDocuments.empty();

    let valid_query = response["valid_query"];
    if (valid_query !== true) {
        document.getElementById("select_sorting_year").style.display = "none";
        document.getElementById("select_sorting_freq").style.display = "none";
        document.getElementById("div_input_page").style.display = "none";
        document.getElementById("input_title_filter").style.display = "none";
        document.getElementById("input_title_filter_label").style.display = "none";
        let query_trans_string = response["query_translation"];
        console.log('translation error:' + query_trans_string)
        $('#alert_translation').text(query_trans_string);
        $('#alert_translation').fadeIn();
        return;
    }

    latest_query_translation = lastQuery;

    let query_len = 0;
    latest_valid_query = parameters["query"];

    // Hide sort buttons depending on the result
    let is_aggregate = response["is_aggregate"];
    document.getElementById("select_sorting_year").style.display = "block";
    if (is_aggregate === true) {
        document.getElementById("select_sorting_freq").style.display = "block";
    } else {
        document.getElementById("select_sorting_freq").style.display = "none";
    }

    // Print query translation
    let query_translation = $("#query_translation");
    let query_trans_string = response["query_translation"];
    let query_limit_hit = response["query_limit_hit"];
    query_translation.text(query_trans_string);
    let results = response["results"];
    let result_size = results["s"];

    // Show Page only if the result is a aggregated list of variable substitutions
    if (parameters["outer_ranking"] !== "outer_ranking_ontology" && results["t"] === "agg_l") {
        computePageInfo(results["no_subs"]);
    } else {
        document.getElementById("div_input_page").style.display = "none";
    }

    // Create documents DIV
    let divList = createResultList(results, query_len);
    divDocuments.append(divList);

    let documents_header = $("#header_documents");
    let document_header_appendix = "";
    if (query_limit_hit === true) {
        document_header_appendix = " (Truncated)"
    }
    if (result_size !== 0) {
        document.getElementById("input_title_filter").classList.toggle("d-none", false);
        document.getElementById("input_title_filter_label").classList.toggle("d-none", false);

        documents_header.html(result_size + " Documents" + document_header_appendix)
        // scroll to results
        document.getElementById("resultdiv").scrollIntoView();
    } else {
        documents_header.html("Documents")

        // check if the used predicated is to specific (!= 'associated')
        let predicate_input = document.getElementById('input_predicate');
        let predicate = predicate_input.options[predicate_input.selectedIndex].value;

        if (predicate !== 'associated') {
            $('#modal_empty_result').modal("toggle");
        }
    }
    // let docids = [];

    // if (response && response["results"] && response["results"]["r"]) {
    //     response["results"]["r"].forEach(function (item) {
    //         if (item && item["t"] === "doc" && item["docid"]) {
    //             createRecommenderGraph(item["docid"])
    //             // docids.push(item["docid"]);
    //         }
    //     });
    // }
    createRecommenderGraph(results["r"]);


    updateYearFilter(response["year_aggregation"], query_trans_string);
}


/**
 * Function edits the year input filter based on the received year aggregation list and translation string.
 * @param year_aggregation {[number]}
 * @param query_trans_string {string}
 */
function updateYearFilter(year_aggregation, query_trans_string) {
    let year_filter_container = document.getElementById("year-filter");
    if (JSON.stringify(year_aggregation) !== '{}') {
        year_filter_container.style.display = "block";
    } else {
        year_filter_container.style.display = "none";
    }
    const fromSlider = document.querySelector('#fromSlider');
    const toSlider = document.querySelector('#toSlider');
    let xValues = [];
    let yValues = [];
    for (const year in year_aggregation) {
        xValues.push(year);
        yValues.push(year_aggregation[year]);
    }

    initializeValues(fromSlider, xValues[0], xValues[0], xValues[xValues.length - 1]);
    initializeValues(toSlider, xValues[xValues.length - 1], xValues[0], xValues[xValues.length - 1]);

    fillSlider(fromSlider, toSlider, '#C6C6C6', '#0d6efd', toSlider);
    setToggleAccessible(toSlider, toSlider.min);
    setValue(toSlider, 'rangeTo');
    setValue(fromSlider, 'rangeFrom');
    let chart = document.getElementById("myChart");
    if (chart !== undefined) {
        let slider_control = document.querySelector(".sliders_control");
        let chart_container = document.querySelector("#range_container")
        chart.remove();
        const new_chart = document.createElement("canvas");
        new_chart.id = "myChart";
        //chart_container.append(new_chart);
        chart_container.insertBefore(new_chart, slider_control);
    }
    let barChart = new Chart("myChart", {
        type: "bar",
        data: {
            labels: xValues,
            datasets: [{
                backgroundColor: [],
                data: yValues,
            }]
        },
        options: YEAR_RESULT_FILTER_CONFIG
    });
    updateBarChart(barChart, fromSlider, fromSlider.value, toSlider.value);
    fromSlider.oninput = () => controlFromSlider(barChart, fromSlider, toSlider);
    toSlider.oninput = () => controlToSlider(barChart, fromSlider, toSlider);
    fromSlider.onchange = () => refreshSearch();
    toSlider.onchange = () => refreshSearch();
}

let uniqueAccordionIDCounter = 0;
const getUniqueAccordionID = () => {
    uniqueAccordionIDCounter += 1
    return uniqueAccordionIDCounter;
};

let uniqueBodyIDCounter = 0;
const getUniqueBodyID = () => {
    uniqueBodyIDCounter += 1;
    return 'card_body_' + uniqueBodyIDCounter;
}

let globalAccordionDict = {};

const createExpandListElement = (divID, next_element_count) => {
    let btnid = 'exp' + divID
    let cardid = 'exp_card_' + divID
    let divExpand = $('<div class="card" id="' + cardid + '"><div class="card-body">' +
        '<button class="btn btn-link" id="' + btnid + '">... click to expand (' + next_element_count + " left)" + '</button>' +
        '</div></div>');
    $(document).on('click', '#' + btnid, function () {
        createExpandableAccordion(false, divID)
    });
    return divExpand;
}

const createExpandableAccordion = (first_call, divID) => {
    let current_div = globalAccordionDict[divID][0];
    let query_len = globalAccordionDict[divID][1];
    let accordionID = globalAccordionDict[divID][2];
    let headingID = globalAccordionDict[divID][3];
    let collapseID = globalAccordionDict[divID][4];
    let resultList = globalAccordionDict[divID][5];
    let global_result_size = globalAccordionDict[divID][6];
    let i = 0;
    // remove the last expand button
    if (first_call === false) {
        $('#' + 'exp_card_' + divID).remove();
    }

    let nextResultList = [];
    resultList.forEach(res => {
        i += 1;
        if (i < MAX_SHOWN_ELEMENTS) {
            let j = i + global_result_size;
            current_div.append(createDivListForResultElement(res, query_len, accordionID, headingID + j, collapseID + j));
        } else {
            nextResultList.push(res);
        }
    });
    createRecommenderGraph(resultList);
    // add a expand button
    if (i > MAX_SHOWN_ELEMENTS) {
        current_div.append(createExpandListElement(divID, nextResultList.length));
    }
    globalAccordionDict[divID] = [current_div, query_len, accordionID, headingID, collapseID, nextResultList, global_result_size + i];
}

let rateButtonID = 0;
const getUniqueRateButtonID = () => {
    rateButtonID += 1;
    return 'rb_' + rateButtonID;
}

function rateExtraction(correct, predication_ids_str, callback) {
    let userid = getUserIDFromLocalStorage(callback);
    if (userid === "cookie") {
        console.log("waiting for cookie consent")
        return false;
    }
    console.log('nice user ' + userid + '  - has rated: ' + correct + ' for ' + predication_ids_str);

    const options = {
        method: 'POST',
        headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
        mode: 'same-origin',
        body: JSON.stringify({
            predicationids: predication_ids_str,
            query: latest_valid_query,
            rating: correct,
            userid: userid
        })
    };

    fetch(feedback_url, options)
        .then(response => {
            if (response.ok) {
                showInfoAtBottom("Thank you for your Feedback!")
            } else {
                showInfoAtBottom("Your feedback couldn't be transferred - please try again")
            }
        });

    return true;
}


function sendDocumentClicked(query, document_id, data_source, document_link) {
    const options = {
        method: 'POST',
        headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
        mode: 'same-origin',
        body: JSON.stringify({
            query: query,
            document_id: document_id,
            data_source: data_source,
            link: document_link
        })
    };

    fetch(document_clicked_url, options)
        .then(response => {
            if (response.ok) {
                console.log("Sent document clicked info")
            } else {
                showInfoAtBottom("Query for provenance failed - please try again")
            }
        });
}

const createResultDocumentElement = (queryResult, query_len, accordionID, headingID, collapseID) => {
    let document_id = queryResult["docid"];
    let art_doc_id = document_id;
    let title = queryResult["title"];
    let authors = queryResult["authors"];
    let journals = queryResult["journals"];
    let year = queryResult["year"];
    let month = queryResult["month"];
    let collection = queryResult["collection"];

    if (month === 0) {
        month = "";
    } else {
        month = month + "/";
    }
    // use the original document id if available
    let doiText = "PMID";
    if (queryResult["org_document_id"] !== null && queryResult["org_document_id"].length > 0) {
        document_id = queryResult["org_document_id"];
        doiText = "DOI";
    }

    let prov_ids = queryResult["prov"];
    let doi = queryResult["doi"];

    let divDoc_Card = $('<div class="card"/>');
    let divDoc_Body = $('<div class="card-body"/>');
    //let divDoc_Body_Link = $('<a class="btn-link" href="' + doi + '" target="_blank">' + document_id + '</a>');
    let divDoc_Body_Link = $('<a>' + doiText + ": " + '</a><a class="btn-link" href="' + doi + '" target="_blank">' + document_id + '</a>');


    divDoc_Body_Link.click(function () {
        sendDocumentClicked(lastQuery, document_id, collection, doi);
    });
    let divDoc_Image = $('<img src="' + pubpharm_image_url + '" height="25px"/>');

    let divDoc_DocumentGraph = $('<div class="float-end popupButton">' +
        'Document Content' + '<br><img src="' + url_graph_preview + '" height="100px"/>' + '</div>');

    divDoc_DocumentGraph.click(() => {
        showPaperView(art_doc_id, collection)
    })

    /*let divDoc_DocumentGraph = $('<a class="btn-link float-right" target="_blank">Document Content</a>');
    divDoc_DocumentGraph.click(function () {
        self.frames["paper_frame"].location.href = "http://localhost:8000/document" + '?document_id=' + art_doc_id + '&data_source=' + collection;
    }) */

    divDoc_Body.append(divDoc_Image);
    divDoc_Body.append(divDoc_DocumentGraph);

    let divDoc_Content = $('<br><b>' + title + '</b><br>' +
        "in: " + journals + " | " + month + year + '<br>' +
        "by: " + authors + '<br>');

    divDoc_Body.append(divDoc_Content);

    //let
    divDoc_Card.append(divDoc_Body);
    divDoc_Body.append(divDoc_Body_Link);


    /*
    let divDoc = $('<div class="card"><div class="card-body">' +
        '<a class="btn-link" href="' + doi + '" onclick="sendDocumentClicked("' + document_id + '","' + doi + '");" target="_blank">' +
        '<img src="' + pubpharm_image_url + '" height="25px">' +
        document_id + '</a>' +

        '<a class="btn-link float-right" href="http://134.169.32.177/document?id=' + art_doc_id + '&data_source=' + collection + '" target="_blank">' +
        'Document Graph</a>' +

        '<br><b>' + title + '</b><br>' +
        "in: " + journals + " | " + month + year + '<br>' +
        "by: " + authors + '<br>' +
        '</div></div><br>'); */

    let divDoc_RecommenderGraph = $('<div class="graph rounded border w-100" style="height:500px" id="' + document_id + '_graph"></div>');
    divDoc_Card.append(divDoc_RecommenderGraph);
    let divFinal = $('<div/>');
    divFinal.append(divDoc_Card);
    divFinal.append($('<br>'));
    return divFinal;

};

function createRecommenderGraph(results) {
    results.forEach(function (item) {
        if (item && item["t"] === "doc" && item["docid"] && item["graph_data"]) {
            let document_id = item["docid"];
            let graph_data = item["graph_data"];
            let container = document.getElementById(document_id + "_graph");
            if (container) {
                visualizeRecommenderGraph(container, graph_data);
            }
        }
    });
}

function visualizeRecommenderGraph(container, data) {
    var options = {
        interaction: {
            multiselect: true,
            hover: true,
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -3000,
                centralGravity: 0.5,
                springLength: 80, //was 140
                springConstant: 0.03,
                damping: 0.70,
                avoidOverlap: 0.3
            },
            stabilization: {
                enabled: true,
                iterations: 1000,
                updateInterval: 100,
                onlyDynamicEdges: false,
                fit: true
            },
        },
        layout: {
            randomSeed: 1
        }
    };
    var network = new vis.Network(container, data, options);
}

const hidePaperView = () => {
    document.getElementById("newsPopup").style.display = "none";
    document.body.style.overflowY = "scroll";
}

const showPaperView = (document_id, collection) => {
    queryAndFilterPaperDetail(document_id, collection);
}

const createDocumentList = (results, query_len) => {
    let accordionID = "accordion" + getUniqueAccordionID();
    let headingID = accordionID + "heading" + 1;
    let collapseID = accordionID + "collapse" + 1;

    let divAccordion = $('<div class="accordion" id="' + accordionID + '"></div>');
    let divCard = $('<div class="card"></div>');
    divAccordion.append(divCard);
    let divCardHeader = $('<div class="card-header" id="' + headingID + '"></div>');
    divCard.append(divCardHeader);
    let divH2 = $('<h2 class="mb-0"></h2>');
    divCardHeader.append(divH2);

    let resultList = results["r"];
    let resultSize = results["s"];
    let button_string = resultSize + ' Document';
    if (resultSize > 1) {
        button_string += 's'
    }
    ;
    divH2.append('<button class="btn btn-link" type="button"data-bs-toggle="collapse" data-bs-target="#' + collapseID + '" ' +
        'aria-expanded="true" aria-controls="' + collapseID + '">' + button_string + '</button>');
    let divCardEntry = $('<div id="' + collapseID + '" class="collapse show" aria-labelledby="' + headingID + '" data-parent="#' + accordionID + '"></div>');
    // tbd: grid
    let divCardBodyID = getUniqueBodyID();
    let divCardBody = $('<div class="card-body" id="' + divCardBodyID + '"></div>');
    divCardEntry.append(divCardBody);
    divCard.append(divCardEntry);


    globalAccordionDict[divCardBodyID] = [divCardBody, query_len, accordionID, headingID, collapseID, resultList, resultList.length];
    createExpandableAccordion(true, divCardBodyID);
    return divAccordion;
};


let globalDocumentAggregateLazyCreated = {};

const createDocumentAggregateLazy = (divCardBodyID) => {
    if (!globalDocumentAggregateLazyCreated[divCardBodyID]) {
        createExpandableAccordion(true, divCardBodyID);
        globalDocumentAggregateLazyCreated[divCardBodyID] = true;
    }
};


const createDocumentAggregate = (queryAggregate, query_len, accordionID, headingID, collapseID) => {
    let divCard = $('<div class="card"></div>');
    let divCardHeader = $('<div class="card-header" style="display: flex" id="' + headingID + '"></div>');
    divCard.append(divCardHeader);
    let divH2 = $('<h2 class="mb-0 subgroupHeader"></h2>');
    divCardHeader.append(divH2);

    let rate_pos_id = getUniqueRateButtonID()
    let imgAggrRatePos = $('<img class="subgroupRatingImg"' +
        ' id="' + rate_pos_id + '" src="' + ok_symbol_url + '" height="30px">');
    let rate_neg_id = getUniqueRateButtonID()
    let imgAggrRateNeg = $('<img class="subgroupRatingImg" ' +
        ' id="' + rate_neg_id + '" src="' + cancel_symbol_url + '" height="30px">');

    imgAggrRatePos.click(() => {
        let subgroup = queryAggregate.sub;
        if (rateSubGroupExtraction(true, subgroup, () => imgAggrRatePos.trigger('click'))) {
            $('#' + rate_pos_id).fadeOut();
            $('#' + rate_neg_id).fadeOut();
        }
    });

    imgAggrRateNeg.click(() => {
        let subgroup = queryAggregate.sub;
        if (rateSubGroupExtraction(false, subgroup, () => imgAggrRateNeg.trigger('click'))) {
            $('#' + rate_pos_id).fadeOut();
            $('#' + rate_neg_id).fadeOut();
        }
    });

    let divRateBtns = $('<div class="subgroupRatingDiv"></div>')
    divRateBtns.append(imgAggrRatePos, imgAggrRateNeg)
    divCardHeader.append(divRateBtns)

    let resultList = queryAggregate["r"];
    let var_names = queryAggregate["v_n"];
    let var_subs = queryAggregate["sub"];
    let result_size = queryAggregate["s"];
    let button_string = result_size + ' Document';
    let url_str = null;
    if (result_size > 1) {
        button_string += 's'
    }
    button_string += ' [';
    let i = 0;
    var_names.forEach(name => {
        let entity_substitution = var_subs[name];
        let ent_str = entity_substitution["s"];
        let ent_id = entity_substitution["id"];
        let ent_type = entity_substitution["t"];
        let ent_name = entity_substitution["n"];
        let var_sub = name + ':= ' + ent_name + " (" + ent_id + " " + ent_type + ")";
        // support ontological header nodes
        if (ent_name === ent_type) {
            var_sub = ent_name;
        }
        if (ent_id.slice(0, 6) === "CHEMBL") {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id;
            url_str = "https://www.ebi.ac.uk/chembl/compound_report_card/" + ent_id;
        } else if (ent_id.slice(0, 2) === "DB") { //
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id;
            url_str = 'https://go.drugbank.com/drugs/' + ent_id;
        } else if (ent_id.slice(0, 5) === 'MESH:') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id;
            url_str = 'https://meshb.nlm.nih.gov/record/ui?ui=' + ent_id.slice(5);
        } else if (ent_type === 'Species') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id;
            url_str = 'https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + ent_id;
        } else if (ent_type === 'Gene') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + "Target" + ' ' + ent_id;
            url_str = 'https://www.ncbi.nlm.nih.gov/gene/?term=' + ent_id;
        } else if (ent_id.slice(0, 1) === "Q") {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id;
            url_str = 'https://www.wikidata.org/wiki/' + ent_id;
        } else {
            button_string += ', '.repeat(!!i) + var_sub + ']'
        }
        i += 1;
    });

    const btn = $('<button class="btn btn-light" type="button" data-bs-toggle="collapse" data-bs-target="#' + collapseID + '" ' +
        'style="padding-right: 0" ' +
        'aria-expanded="true" aria-controls="' + collapseID + '">' + button_string + '</button>');

    divH2.append(btn)

    //check if an url is used
    if (url_str) {
        const link = ('<a class="subgroupLinkImg" href=' + url_str + ' target="_blank"' +
            ' onclick="event.stopPropagation()">' +
            '<img height="18px" src=' + search_icon_url + '></a>')
        const filler = $('<button class="btn btn-light" type="button" data-bs-toggle="collapse" data-bs-target="#' + collapseID + '" ' +
            'style="padding-left: 0" ' +
            'aria-expanded="true" aria-controls="' + collapseID + '">)]</button>');
        divH2.append(link, filler);
    }

    let divCardEntry = $('<div id="' + collapseID + '" class="collapse" aria-labelledby="' + headingID + '" data-parent="#' + accordionID + '"></div>');
    let divCardBodyID = getUniqueBodyID();
    let divCardBody = $('<div class="card-body"></div>');
    divCardEntry.append(divCardBody);
    divCard.append(divCardEntry);


    globalAccordionDict[divCardBodyID] = [divCardBody, query_len, accordionID, headingID, collapseID, resultList, resultList.length];

    // generate the content lazy
    divH2.click(function () {
        createDocumentAggregateLazy(divCardBodyID);
    });

    return divCard;
};

function rateSubGroupExtraction(correct, subgroup, callback) {
    let userid = getUserIDFromLocalStorage(callback);
    if (userid === "cookie") {
        console.log("waiting for cookie consent")
        return false;
    }
    let variable = Object.keys(subgroup)[0];
    console.log('nice user ' + userid + '  - has rated: ' + correct + ' for ' + variable);

    const options = {
        method: 'POST',
        headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
        mode: 'same-origin',
        body: JSON.stringify({
            variable_name: variable,
            entity_name: subgroup[variable].n,
            entity_id: subgroup[variable].id,
            entity_type: subgroup[variable].t,
            query: latest_valid_query,
            rating: correct,
            userid: userid
        })
    };

    fetch(subgroup_feedback_url, options)
        .then(response => {
            if (response.ok) {
                showInfoAtBottom("Thank you for your Feedback!")
            } else {
                showInfoAtBottom("Your feedback couldn't be transferred - please try again")
            }
        });
    return true;
}

const createDocumentAggregateList = (results, query_len) => {
    let accordionID = "accordion" + getUniqueAccordionID();
    let headingID = accordionID + "heading" + 1;
    let collapseID = accordionID + "collapse" + 1;
    let divAccordion = $('<div class="accordion" id="' + accordionID + '"></div>');
    let resultList = results["r"];

    globalAccordionDict[accordionID] = [divAccordion, query_len, accordionID, headingID, collapseID, resultList, resultList.length];
    createExpandableAccordion(true, accordionID);

    return divAccordion;
};


const createDivListForResultElement = (result, query_len, accordionID, headingID, collapseID) => {
    let typeOfRes = result["t"];
    if (typeOfRes === "doc") {
        return (createResultDocumentElement(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "doc_l") {
        return (createDocumentList(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "agg") {
        return (createDocumentAggregate(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "agg_l") {
        return (createDocumentAggregateList(result, query_len, accordionID, headingID, collapseID));
    }
    console.log("ERROR - does not recognize result type: " + typeOfRes);
    return null;
};


const createResultList = (results, query_len) => {
    let divList = $(`<div></div>`);
    divList.append(createDivListForResultElement(results, query_len, null, null, null));
    return divList;
};

let LAST_INPUT_FIELD = null;

function setConceptInputFieldSubject() {
    LAST_INPUT_FIELD = "input_subject";
}

function setConceptInputFieldObject() {
    LAST_INPUT_FIELD = "input_object";
}

function copySelectedConcept(concept) {
    if (LAST_INPUT_FIELD !== null) {
        let target_element = document.getElementById(LAST_INPUT_FIELD);
        target_element.value = concept;
    }
}

function addTreeData(atcTreeData, meshTreeData) {
    let options = {
        searchBox: $('#browseSearch'),
        searchMinInputLength: 3
    }
    let tree_data = [getVariableData(), {
        label: "ATC Classes",
        value: "",
        children: atcTreeData
    }, {
        label: "MeSH Diseases",
        value: "",
        children: meshTreeData

    }]
    let tree = $('#browseTree').simpleTree(options, tree_data)
    $('#atcModal').on('show.bs.modal', (e) => {
        tree.clearSelection(false)
        $("#atcTreeOK").addClass("disabled")
    })
    tree.on('simpleTree:change', (node) => {
        $("#atcTreeOK").removeClass("disabled")
    })
    $("#atcTreeOK").on('click', (e) => {
        copySelectedConcept(tree.getSelectedNode()["value"])
        $("#atcModal").modal('hide')
    })
}

// build atc tree for modal
function queryAndBuildConceptTree() {
    $('#browseSearch').on('keydown', (e) => {
        $('#atcModal').modal('handleUpdate')
    })

    fetch(tree_info_url + '?tree=atc')
        .then(response => response.json())
        .then(result => {
            let atc_tree_data = createTreeDataFromQueryResult(result["tree"])
            fetch(tree_info_url + '?tree=mesh_disease')
                .then(response => response.json())
                .then(result => {
                    let mesh_tree_data = createTreeDataFromQueryResult(result["tree"])
                    addTreeData(atc_tree_data, mesh_tree_data);
                })
                .catch((error) => {
                    $('#alert_translation').text('Failed to get MeSH Disease tree.');
                    $('#alert_translation').fadeIn();
                    console.log("Failed to get MeSH Disease tree")
                    console.log(error)
                })

        })
        .catch((error) => {
            $('#alert_translation').text('Failed to get atc tree.');
            $('#alert_translation').fadeIn();
            console.log("Failed to get atc tree")
            console.log(error)
        })


}

function createTreeDataFromQueryResult(inputTree) {
    let outputTree = []
    for (let node of inputTree) {
        let out_node = [];
        let name = node["name"]
        if ("children" in node) {
            if ("children" in node["children"][0]) {
                out_node["children"] = createTreeDataFromQueryResult(node["children"])
            } else {
                name = node["name"] + " - " + node["children"][0]["name"]
            }
        }
        out_node["label"] = name

        if (name.includes('MESH')) {
            // MeSH Case
            if (name.includes('- (MESH')) {
                out_node["value"] = name.split(' - (MESH')[0];
            } else {
                out_node["value"] = name.split(' (MESH')[0];
            }

        } else {
            // ATC Case
            out_node["value"] = name.split("-")[1]
        }


        outputTree.push(out_node)
    }
    return outputTree
}

function getVariableData() {
    let variables = [
        ['Chemical', "substance/molecule/element"],
        ['Disease', "disease/illness/side effect, e.g. Diabetes Mellitus"],
        ['DosageForm', "dosage form/delivery form, e.g. tablet or injection"],
        ['Drug', "active ingredients, e.g. Metformin or Simvastatin"],
        ['Excipient', "transport/carrier substances, e.g. methyl cellulose"],
        ['HealthStatus', "information about target groups, e.g. women, man, children, etc."],
        ['LabMethod', "more specific labor methods, e.g. mass spectrometry"],
        ['Method', "common applied methods"],
        ['PlantFamily/Genus', "plant families, e.g. Digitalis, Cannabis"],
        ["Organism", "organisms, e.g. bacterias and viruses"],
        ['Species', "target groups, e.g. human and rats"],
        ['Target', "gene/enzyme, e.g. cyp3a4 and mtor"],
        ['Tissue', "tissues, e.g. muscle and membranes"],
        ["Vaccine", "used vaccines"]
    ];

    let out_tree = []

    for (let v of variables) {
        let node = {}
        node["label"] = v[0] + " (" + v[1] + ")"
        node["value"] = v[0]
        out_tree.push(node)
    }
    out_tree = {
        label: "Variables",
        value: "",
        children: out_tree
    }
    return out_tree
}


function buildSelectionTrees() {
    queryAndBuildConceptTree();
}

function controlFromSlider(barChart, fromSlider, toSlider) {
    const [from, to] = getParsed(fromSlider, toSlider);
    fillSlider(fromSlider, toSlider, '#C6C6C6', '#0d6efd', toSlider);
    if (from > to) {
        fromSlider.value = to;
    }
    updateBarChart(barChart, fromSlider, fromSlider.value, toSlider.value);
    setValue(fromSlider, 'rangeFrom');
}

function controlToSlider(barChart, fromSlider, toSlider) {
    const [from, to] = getParsed(fromSlider, toSlider);
    fillSlider(fromSlider, toSlider, '#C6C6C6', '#0d6efd', toSlider);
    setToggleAccessible(toSlider, toSlider.min);
    if (from >= to) {
        toSlider.zIndex = 1;
        fromSlider.zIndex = 0;
    } else {
        toSlider.zIndex = 0;
        fromSlider.zIndex = 1;
    }
    if (from <= to) {
        toSlider.value = to;
    } else {
        toSlider.value = from;
    }
    updateBarChart(barChart, fromSlider, fromSlider.value, toSlider.value);
    setValue(toSlider, 'rangeTo');
}

function setValue(range, rangeValue) {
    let rangeV = document.getElementById(rangeValue);
    const newValue = Number((range.value - range.min) * 100 / (range.max - range.min));
    const newPosition = 10 - (newValue * 0.2);
    rangeV.innerHTML = `<span>${range.value}</span>`;
    rangeV.style.left = `calc(${newValue}% + (${newPosition}px))`;
}

function getParsed(currentFrom, currentTo) {
    const from = parseInt(currentFrom.value, 10);
    const to = parseInt(currentTo.value, 10);
    return [from, to];
}

function fillSlider(from, to, sliderColor, rangeColor, controlSlider) {
    const rangeDistance = to.max - to.min;
    const fromPosition = from.value - to.min;
    const toPosition = to.value - to.min;
    controlSlider.style.background = `linear-gradient(
      to right,
      ${sliderColor} 0%,
      ${sliderColor} ${(fromPosition) / (rangeDistance) * 100}%,
      ${rangeColor} ${((fromPosition) / (rangeDistance)) * 100}%,
      ${rangeColor} ${(toPosition) / (rangeDistance) * 100}%, 
      ${sliderColor} ${(toPosition) / (rangeDistance) * 100}%, 
      ${sliderColor} 100%)`;
}

function setToggleAccessible(currentTarget, min) { //in case toSlider and fromSilder on 0 --> tSlider needs to Overlap fromSlider
    const toSlider = document.querySelector('#toSlider');
    if (Number(currentTarget.value) <= Number(min)) {
        toSlider.style.zIndex = 2;
    } else {
        toSlider.style.zIndex = 0;
    }
}

function updateBarChart(barChart, fromSlider, from, to) {
    //const barChart = document.querySelector('#myChart');
    for (let i = 0; i <= parseInt(fromSlider.max, 10) - parseInt(fromSlider.min, 10); i++) {
        if (i >= from - parseInt(fromSlider.min, 10) && i <= to - parseInt(fromSlider.min, 10)) {
            barChart.data.datasets[0].backgroundColor[i] = "#0d6def";
        } else {
            barChart.data.datasets[0].backgroundColor[i] = "#C6C6C6";
        }
    }
    barChart.update();
}

function initializeValues(slider, value, min, max) {
    slider.max = max;
    slider.min = min;
    slider.value = value;
}
