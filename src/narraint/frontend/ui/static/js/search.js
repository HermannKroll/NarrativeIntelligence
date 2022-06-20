let latest_valid_query = '';
let DEFAULT_RESULT_DIVS_LIMIT = 500;
let DEFAULT_AGGREGATED_RESULTS_PER_PAGE = 30;
let MAX_SHOWN_ELEMENTS = DEFAULT_AGGREGATED_RESULTS_PER_PAGE;

let CYTOSCAPE_STYLE = [
    {
        selector: 'node',
        style: {
            'background-color': '#8EB72B',
            'label': 'data(id)'
        }
    },
    {
        selector: 'edge',
        style: {
            'width': 3,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'label': 'data(label)'
        }
    }
];

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

$('#cookiebtnDeny').click(() => {
    $('.toast').toast('hide')
    let cookie_toast = $('#cookie_toast');
    cookie_toast.hide();
})

const cookieAcceptBtnHandler = (callback) => {
    let userid = uuidv4();
    localStorage.setItem('userid', userid);
    $('.toast').toast('hide');
    let cookie_toast = $('#cookie_toast');
    cookie_toast.hide();
    callback();
}

function getUserIDFromLocalStorage(callback) {
    if (!localStorage.getItem('userid')) {
        console.log("no user id found in local storage");

        //remove previously stored events and add the new callback event
        $('#cookiebtnAccept').off('click').click(() => {
            cookieAcceptBtnHandler(callback);
        })

        let cookie_toast = $('#cookie_toast');
        cookie_toast.show();
        cookie_toast.toast('show');
        return "cookie";
    }
    return localStorage.getItem('userid');
}


function escapeString(input_string) {
    if (input_string.includes(' ')) {
        return '"' + input_string + '"'.trim();
    }
    return input_string.trim();
}

function getTextOrPlaceholderFromElement(element_id) {
    let text = document.getElementById(element_id).value;
    if (text.length > 0) {
        return text;
    } else {
        return "";
    }

}


let uniqueListID = 0;
const getUniqueListID = () => {
    uniqueListID += 1;
    return 'li_' + uniqueListID;
}

let queryPatternDict = {};

function addQueryPattern(id, subject, predicate, object) {
    queryPatternDict[id] = [subject, predicate, object];
}

function removeQueryPattern(id) {
    delete queryPatternDict[id];
}

function removeAllQueryPatterns() {
    let ids = Object.keys(queryPatternDict);
    ids.forEach(id => {
        removeQueryPattern(id);
    });
}

function getCurrentQuery() {
    let subject = escapeString(getTextOrPlaceholderFromElement('input_subject'));
    let predicate_input = document.getElementById('input_predicate');
    let predicate = predicate_input.options[predicate_input.selectedIndex].value;
    let object = escapeString(getTextOrPlaceholderFromElement('input_object'));

    let query = "";
    if (subject.length > 0 && object.length > 0) {
        query = (subject + ' ' + predicate + ' ' + object);
    }

    Object.values(queryPatternDict).forEach(val => {
        // do not add this pattern twice
        if (val[0] !== subject || val[1] !== predicate || val[2] !== object) {
            query = (val[0] + ' ' + val[1] + ' ' + val[2] + '_AND_') + query;
        }
    });

    return query;
}

function createQueryListItem(subject, predicate, object) {
    let uniqueListItemID = getUniqueListID();
    addQueryPattern(uniqueListItemID, subject, predicate, object);
    let deleteEvent = '$(\'#' + uniqueListItemID + '\').remove();removeQueryPattern(\'' + uniqueListItemID + '\');'
    let listItem = $('<li id="' + uniqueListItemID + '" class="list-group-item">'
        + '<div class="container">' +
        '  <div class="row">' +
        '    <div class="col-4" style="padding-left: 0"><span class="name">' + subject + '</span></div>' +
        '    <div class="col-2"><span class="name">' + predicate + '</span></div>' +
        '    <div class="col-4"><span class="name">' + object + '</span></div>' +
        '    <div class="col-1"><button class="btn btn-danger remove-item" onclick="' + deleteEvent + '">-</button></div>' +
        '  </div>' +
        '</div>' +
        '</li>');
    $('#query_builder_list').append(listItem);
    document.getElementById('input_subject').value = "";
    document.getElementById('input_predicate').options[0].selected = true;
    document.getElementById('input_object').value = "";
}

function addQueryPart() {
    let subject = escapeString(getTextOrPlaceholderFromElement('input_subject'));
    let predicate_input = document.getElementById('input_predicate');
    let predicate = predicate_input.options[predicate_input.selectedIndex].value;
    let object = escapeString(getTextOrPlaceholderFromElement('input_object'));
    let query_text = subject + ' ' + predicate + ' ' + object;

    if (subject.length === 0) {
        $('#alert_translation').text('subject is empty');
        $('#alert_translation').fadeIn();
        return;
    }
    if (object.length === 0) {
        $('#alert_translation').text('object is empty');
        $('#alert_translation').fadeIn();
    }

    let request = $.ajax({
        url: query_check_url,
        data: {
            query: query_text
        }
    });

    request.done(function (response) {
        let answer = response['valid']
        if (answer === "True") {
            $('#alert_translation').hide();
            createQueryListItem(subject, predicate, object)
        } else {
            console.log('translation error:' + response["query"])
            $('#alert_translation').text(response["query"]);
            $('#alert_translation').fadeIn();
        }
    });

    request.fail(function (result) {
        $('#alert_translation').text('connection issues (please reload website)');
        $('#alert_translation').fadeIn();
    });
}


function clearQueryBuilder() {
    removeAllQueryPatterns();
    let queryBuilder = document.getElementById('query_builder_list');
    while (queryBuilder.firstChild) {
        queryBuilder.removeChild(queryBuilder.firstChild);
    }
}

function split(val) {
    // split string by space but do not split spaces within brackets
    // remove all leading and closing brackets from splits
    //console.log(val + " converted to " + termsCleaned);
    return val.match(/\\?.|^$/g).reduce((p, c) => {
        if (c === '"') {
            p.quote ^= 1;
        } else if (!p.quote && c === ' ') {
            p.a.push('');
        } else {
            p.a[p.a.length - 1] += c.replace(/\\(.)/, "$1");
        }
        return p;
    }, {a: ['']}).a;
}

let optionMapping = {
    "associated": 0,
    "administered": 1,
    "compares": 2,
    "decreases": 3,
    "induces": 4,
    "interacts": 5,
    "inhibits": 6,
    "metabolises": 7,
    "method": 8,
    "treats": 9
}

function example_search(search_str) {
    $('#collapseExamples').collapse('hide');
    clearQueryBuilder();
    console.log(search_str);
    let first = true;
    search_str.split('_AND_').forEach(comp => {
        let triple = split(comp.trim());
        if (first === false) {
            let subject = escapeString(getTextOrPlaceholderFromElement('input_subject'));
            let predicate_input = document.getElementById('input_predicate');
            let predicate = predicate_input.options[predicate_input.selectedIndex].value;
            let object = escapeString(getTextOrPlaceholderFromElement('input_object'));
            createQueryListItem(subject, predicate, object);
        }
        document.getElementById('input_subject').value = triple[0];
        document.getElementById('input_predicate').options[optionMapping[triple[1]]].selected = true;
        document.getElementById('input_object').value = triple[2];
        first = false;
    });

    document.getElementById("btn_search").click();
    $('html,body').scrollTop(0);
}

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

let imgrect = {width: 0, height: 0};
document.getElementById("screenshot").addEventListener('load', (e) => {
    imgrect = e.target.getBoundingClientRect();
});


async function openFeedback() {
    $("#feedbackbtn_text").html("Generating Screenshot (may take a while)");
    $("#reportSpinner").addClass("busy");
    $("#feedback_button").addClass("disabled")
    await new Promise(r => setTimeout(r, 10));
    const screenshotTarget = document.body;
    let canvas = await html2canvas(screenshotTarget, {scrollX: 0, scrollY: 0})

    const base64image = canvas.toDataURL("image/png");
    let screenshot = $("#screenshot")
    await screenshot.attr("src", base64image);
    $("#feedbackModal").modal("toggle");
    $("#reportSpinner").removeClass("busy");
    $("#feedback_button").removeClass("disabled")
    $("#feedbackbtn_text").html("Feedback");


    $("#screenshotCanvas").remove();

    $("#screenshotContainer").append('<canvas class="coveringCanvas" id="screenshotCanvas"></canvas>')

    let screenshotCanvas = $("#screenshotCanvas");
    screenshotCanvas.attr('width', canvas.width);
    screenshotCanvas.attr('height', canvas.height);
    let pos = {x: 0, y: 0};
    screenshotCanvas.mousemove(draw);
    screenshotCanvas.mousedown(setPosition);
    screenshotCanvas.mouseenter(setPosition);
    screenshotCanvas.mouseenter(() => {
        document
    })
    let ctx = screenshotCanvas[0].getContext('2d')


    function draw(e) {

        console.log("draw")
        if (e.buttons !== 1) return;

        ctx.beginPath();

        ctx.lineWidth = 5;
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#c0392b';

        ctx.moveTo(pos.x, pos.y);
        setPosition(e);
        ctx.lineTo(pos.x, pos.y);

        ctx.stroke();
    }

    function setPosition(e) {
        console.log("setposition")
        let rect = e.target.getBoundingClientRect();
        pos.x = (e.clientX - rect.left) * canvas.width / imgrect.width;
        pos.y = (e.clientY - rect.top) * canvas.height / imgrect.height;
    }
}

function closeFeedback(send = false) {
    if (send) {
        let combine_canvas = document.createElement("canvas");
        let dim = document.getElementById('screenshotCanvas');
        combine_canvas.width = dim.width;
        combine_canvas.height = dim.height;
        let ctx = combine_canvas.getContext('2d')
        ctx.drawImage(document.getElementById('screenshot'), 0, 0)
        ctx.drawImage(document.getElementById('screenshotCanvas'), 0, 0)

        const params = {
            description: $("#feedbackText").val(),
            img64: combine_canvas.toDataURL("image/png")
        };
        const options = {
            method: 'POST',
            body: JSON.stringify(params)
        };
        fetch(report_url, options).then(response => {
                if (response.ok) {
                    alert("Report successfully sent!");
                    $("#feedbackModal").modal("toggle");
                    $("#feedbackText").val("");
                } else {
                    alert("Sending report has failed!");
                }
            }
        )
    } else {
        $("#feedbackModal").modal("toggle");
    }
}

const reset_scanvas = () => {
    const canvas = document.getElementById("screenshotCanvas");
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}

const setButtonSearching = isSearching => {
    let btn = $('#btn_search');
    let help = $('#help_search');
    btn.empty();

    if (isSearching) {
        let span = $('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>');
        btn.append(span)
            .append(" Searching ...")
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

    buildSelectionTrees();

    $("#search_form").submit(search);

    $('#input_subject').autocomplete({
        minLength: 0,
        autoFocus: true,
        source: function (request, response) {
            let relevantTerm = request.term;
            $.ajax({
                type: "GET",
                url: autocompletion_url,
                data: {
                    term: relevantTerm
                },
                success: function (data) {
                    // delegate back to autocomplete, but extract the last term
                    response(data["terms"]);
                }
            });
        }
        ,
        focus: function () {
            // prevent value inserted on focus
            return false;
        }
        ,
        select: function (event, ui) {
            this.value = ui.item.value.trim();
            return false;
        }
    }).on("keydown", function (event) {
        // don't navigate away from the field on tab when selecting an item
        if (event.keyCode === $.ui.keyCode.TAB /** && $(this).data("ui-autocomplete").menu.active **/) {
            event.preventDefault();
        }
    });


    $('#input_object').autocomplete({
        minLength: 0,
        autoFocus: true,
        source: function (request, response) {
            let relevantTerm = request.term;
            $.ajax({
                type: "GET",
                url: autocompletion_url,
                data: {
                    term: relevantTerm
                },
                success: function (data) {
                    // delegate back to autocomplete, but extract the last term
                    response(data["terms"]);
                }
            });
        }
        ,
        focus: function () {
            // prevent value inserted on focus
            return false;
        }
        ,
        select: function (event, ui) {
            this.value = ui.item.value.trim();
            return false;
        }

    }).on("keydown", function (event) {
        // don't navigate away from the field on tab when selecting an item
        if (event.keyCode === $.ui.keyCode.TAB /** && $(this).data("ui-autocomplete").menu.active **/) {
            event.preventDefault();
        }
    });

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

    if (params.has("query")) {
        let query = params.get("query");
        lastQuery = query;
        example_search(query);
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
    event.preventDefault();
    let query = getCurrentQuery();

    let start_pos = getStartPositionBasedOnCurrentPage();
    // consider start pos only if query isn't changed
    if (lastQuery !== query) {
        start_pos = 0;
        setCurrentPage(0);
        lastQuery = query;
    }
    let end_pos = start_pos + DEFAULT_AGGREGATED_RESULTS_PER_PAGE;

    let freq_element = document.getElementById("select_sorting_freq");
    let freq_sort_desc = freq_element.value;
    let year_element = document.getElementById("select_sorting_year");
    let year_sort_desc = year_element.value;

    let data_source = document.querySelector('input[name = "data_source"]:checked').value;
    lastDataSource = data_source;
    let outer_ranking = document.querySelector('input[name = "outer_ranking"]:checked').value;
    //let inner_ranking = document.querySelector('input[name = "inner_ranking"]:checked').value;
    let inner_ranking = "NOT IMPLEMENTED";

    console.log("Query: " + query);
    console.log("Data source: " + data_source)
    console.log("Outer Ranking: " + outer_ranking)
    console.log("Inner Ranking: " + inner_ranking)
    console.log("Sorting by frequency (desc): " + freq_sort_desc)
    console.log("Sorting by year (desc): " + year_sort_desc)
    console.log("Start position: " + start_pos)
    console.log("End position: " + end_pos)
    setButtonSearching(true);

    const url = new URL(window.location.href);
    url.searchParams.set('query', query);
    url.searchParams.set("data_source", data_source);
    url.searchParams.set("visualization", outer_ranking);
    url.searchParams.set("sort_frequency_desc", freq_sort_desc);
    url.searchParams.set("sort_year_desc", year_sort_desc);
    url.searchParams.set("start_pos", start_pos);
    //   url.searchParams.set("end_pos", end_pos);
    window.history.pushState("Query", "Title", "/" + url.search.toString());

    let request = $.ajax({
        url: search_url,
        data: {
            query: query,
            data_source: data_source,
            outer_ranking: outer_ranking,
            freq_sort: freq_sort_desc,
            year_sort: year_sort_desc,
            start_pos: start_pos,
            end_pos: end_pos,
            /*,
            inner_ranking: inner_ranking*/
        }
    });

    request.done(function (response) {
        console.log(response);

        // Clear DIVs
        let form = $('#graph-patterns');
        form.empty();
        let divDocuments = $('#div_documents');
        divDocuments.empty();

        let valid_query = response["valid_query"];
        if (valid_query === true) {
            let query_len = 0;
            latest_valid_query = query;

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
            if (outer_ranking !== "outer_ranking_ontology" && results["t"] === "agg_l") {
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
        } else {
            document.getElementById("select_sorting_year").style.display = "none";
            document.getElementById("select_sorting_freq").style.display = "none";
            document.getElementById("div_input_page").style.display = "none";
            let query_trans_string = response["query_translation"];
            console.log('translation error:' + query_trans_string)
            $('#alert_translation').text(query_trans_string);
            $('#alert_translation').fadeIn();
        }

        // Disable button
        setButtonSearching(false);

    });

    request.fail(function (result) {
        setButtonSearching(false);
        let documents_header = $("#header_documents");
        documents_header.html("Documents")
        console.log(result);
    });
};


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
    let request = $.ajax({
        url: feedback_url,
        data: {
            predicationids: predication_ids_str,
            query: latest_valid_query,
            rating: correct,
            userid: userid
        }
    });

    request.done(function (response) {
        showInfoAtBottom("Thank you for your Feedback!")
    });

    request.fail(function (result) {
        showInfoAtBottom("Your feedback couldn't be transferred - please try again")
    });


    return true;
}

const createProvenanceDivElement = (explanations) => {
    let div_provenance_all = $('<div>');
    let j = -1;
    try {
        explanations.forEach(e => {
            let sentence = e["s"];
            let predication_ids_str = e['ids'];
            // an explanation might have multiple subjects / predicates / objects separated by //
            e["s_str"].split('//').forEach(s => {
                let s_reg = new RegExp('(' + s + '[a-z]*)', 'gi');
                sentence = sentence.replaceAll(s_reg, '<code class="highlighter-rouge">$1</code>')
            });
            e["p"].split('//').forEach(p => {
                let p_reg = new RegExp('(' + p + '[a-z]*)', 'gi');
                sentence = sentence.replaceAll(p_reg, "<mark>$1</mark>")
            });
            e["o_str"].split('//').forEach(o => {
                let o_reg = new RegExp('(' + o + '[a-zg]*)', 'gi');
                sentence = sentence.replaceAll(o_reg, '<code class="highlighter-rouge">$1</code>')
            });

            if (j === -1) {
                j = parseInt(e["pos"]) + 1;
            }
            if (j !== parseInt(e["pos"]) + 1) {
                div_provenance_all.append($('<br>'));
                j = parseInt(e["pos"]) + 1;
            }

            let rate_pos_id = getUniqueRateButtonID();
            let div_rate_pos = $('<img style="cursor: pointer" id="' + rate_pos_id + '" src="' + ok_symbol_url + '" height="30px">');
            let rate_neg_id = getUniqueRateButtonID();
            let div_rate_neg = $('<img style="cursor: pointer" id="' + rate_neg_id + '" src="' + cancel_symbol_url + '" height="30px">');

            div_rate_pos.click(function () {
                if (rateExtraction(true, predication_ids_str, () => div_rate_pos.trigger('click'))) {
                    $('#' + rate_pos_id).fadeOut();
                    $('#' + rate_neg_id).fadeOut();
                }

            });
            div_rate_neg.click(function () {
                if (rateExtraction(false, predication_ids_str, () => div_rate_neg.trigger('click'))) {
                    $('#' + rate_pos_id).fadeOut();
                    $('#' + rate_neg_id).fadeOut();
                }
            });

            let div_col_rating = $('<div class="col-1">');
            div_col_rating.append(div_rate_pos);
            div_col_rating.append(div_rate_neg);


            let div_provenance = $('<div class="col-11">' +
                j + '. ' + sentence + "<br>[" + e["s_str"] + ", " + e["p"] + " -> " +
                e["p_c"] + ", " + e["o_str"] + ']' + "<small><i> - confidence: " + e["conf"] + "</i></small>" +
                '</div>');

            let div_prov_example = $('<div class="container">');
            let div_prov_example_row = $('<div class="row">');

            div_prov_example_row.append(div_provenance);
            div_prov_example_row.append(div_col_rating);
            div_prov_example.append(div_prov_example_row);

            div_provenance_all.append(div_prov_example);


        });
    } catch (SyntaxError) {

    }
    return div_provenance_all;
}

function queryAndVisualizeProvenanceInformation(query, document_id, data_source, provenance, unique_div_id) {
    let request = $.ajax({
        url: provenance_url,
        data: {
            query: query,
            document_id: document_id,
            data_source: data_source,
            prov: JSON.stringify(provenance)
        }
    });

    request.done(function (response) {
        let explanations = response["result"]["exp"];
        let prov_div = createProvenanceDivElement(explanations);
        $('#' + unique_div_id).append(prov_div);
    });

    request.fail(function (result) {
        showInfoAtBottom("Query for provenance failed - please try again")
    });
}

let uniqueProvenanceID = 1;

function sendDocumentClicked(query, document_id, data_source, document_link) {
    let request = $.ajax({
        url: document_clicked_url,
        data: {
            query: query,
            document_id: document_id,
            data_source: data_source,
            link: document_link
        }
    });

    request.done(function (response) {
        console.log("Sent document clicked info")
    });

    request.fail(function (result) {
        showInfoAtBottom("Query for provenance failed - please try again")
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

    divDoc_DocumentGraph.click(() => {showPaperView(art_doc_id, collection)})

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

    let unique_div_id = "prov_" + uniqueProvenanceID;
    uniqueProvenanceID = uniqueProvenanceID + 1;
    let div_provenance_button = $('<button class="btn btn-light" data-bs-toggle="collapse" data-bs-target="#' + unique_div_id + '">Provenance</button>');
    let div_provenance_collapsable_block = $('<div class="collapse" id="' + unique_div_id + '">');
    div_provenance_button.click(function () {
        if ($('#' + unique_div_id).html() === "") {
            queryAndVisualizeProvenanceInformation(lastQuery, document_id, collection, prov_ids, unique_div_id);
        }
    });

    divDoc_Card.append(div_provenance_button);
    divDoc_Card.append(div_provenance_collapsable_block);

    let divFinal = $('<div/>');
    divFinal.append(divDoc_Card);
    divFinal.append($('<br>'));
    return divFinal;
};

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
    let url_str;
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
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id + ' )]';
            url_str = "https://www.ebi.ac.uk/chembl/compound_report_card/" + ent_id;
        } else if (ent_id.slice(0, 2) === "DB") { //
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id + ' )]';
            url_str = 'https://go.drugbank.com/drugs/' + ent_id;
        } else if (ent_id.slice(0, 5) === 'MESH:') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id + ' )]';
            url_str = 'https://meshb.nlm.nih.gov/record/ui?ui=' + ent_id.slice(5);
        } else if (ent_type === 'Species') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id + ' )]';
            url_str = 'https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + ent_id;
        } else if (ent_type === 'Gene') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + "Target" + ' ' + ent_id + ' )]';
            url_str = 'https://www.ncbi.nlm.nih.gov/gene/?term=' + ent_id;
        } else if (ent_id.slice(0, 1) === "Q") {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' ' + ent_id + ' )]';
            url_str = 'https://www.wikidata.org/wiki/' + ent_id;
        } else {
            button_string += ', '.repeat(!!i) + var_sub + ']'
        }
        i += 1;
    });

    divH2.append('<button class="btn btn-light" type="button" data-bs-toggle="collapse" data-bs-target="#' + collapseID + '" ' +
        'aria-expanded="true" aria-controls="' + collapseID + '">' + button_string + '</button>');
    divH2.append('<a href=' + url_str + ' target="_blank"><img height="20px" src=' + search_icon_url + '></a>')
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
    let request = $.ajax({
        url: subgroup_feedback_url,
        data: {
            variable_name: variable,
            entity_name: subgroup[variable].n,
            entity_id: subgroup[variable].id,
            entity_type: subgroup[variable].t,
            query: latest_valid_query,
            rating: correct,
            userid: userid
        }
    });

    request.done(function (response) {
        showInfoAtBottom("Thank you for your Feedback!")
    });

    request.fail(function (result) {
        showInfoAtBottom("Your feedback couldn't be transferred - please try again")
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
    //console.log(inputTree)
    for (let node of inputTree) {
        //console.log(node)
        let out_node = [];
        let name = node["name"]
        if ("children" in node) {
            //console.log(node["children"])
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
        ['LabMethod', "more specific labor methods, e.g. mass spectrometry"],
        ['Method', "common applied methods"],
        ['PlantFamily', "plant families, e.g. Digitalis, Cannabis"],
        ['Species', "target groups, e.g. human, rats, etc."],
        ['Target', "gene/enzyme, e.g. cyp3a4, mtor"],
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