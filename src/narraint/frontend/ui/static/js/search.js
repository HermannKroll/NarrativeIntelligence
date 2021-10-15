let MAX_SHOWN_ELEMENTS = 10;
let latest_valid_query = '';
let DEFAULT_RESULT_DIVS_LIMIT = 500;

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


$('#cookiebtnDeny').click(() => {
    $('.toast').toast('hide')
    let cookie_toast = $('#cookie_toast');
    cookie_toast.hide();
})

$('#cookiebtnAccept').click(() => {
    let userid = uuidv4();
    localStorage.setItem('userid', userid);
    $('.toast').toast('hide')
    let cookie_toast = $('#cookie_toast');
    cookie_toast.hide();
})

function getUserIDFromLocalStorage() {
    if (!localStorage.getItem('userid')) {
        console.log("no user id found in local storage");
        let cookie_toast = $('#cookie_toast');
        cookie_toast.show();
        cookie_toast.toast('show')
        return "cookie";
    }
    return localStorage.getItem('userid');
}


function escapeString(input_string) {
    if (input_string.includes(' ')) {
        return '"' + input_string + '"';
    }
    return input_string;
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
        '    <div class="col-sm"><span class="name">' + subject + '</span></div>' +
        '    <div class="col-sm"><span class="name">' + predicate + '</span></div>' +
        '    <div class="col-sm"><span class="name">' + object + '</span></div>' +
        '    <div class="col-sm"><button class="btn btn-danger btn-xs pull-right remove-item" onclick="' + deleteEvent + '">-</button></div>' +
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
            console.log('translation error:' + answer)
            $('#alert_translation').text(answer);
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
    //document.getElementById('id_keywords').value = search_str;
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
    $("#reportSpinner").addClass("busy");
    const screenshotTarget = document.body;
    let canvas = await html2canvas(screenshotTarget, {scrollX: 0, scrollY: 0})

    const base64image = canvas.toDataURL("image/png");
    let screenshot = $("#screenshot")
    await screenshot.attr("src", base64image);
    $("#feedbackModal").modal("toggle");
    $("#reportSpinner").removeClass("busy");


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

});

const search = (event) => {
    $('#collapseExamples').collapse('hide');
    $('#alert_translation').hide();
    event.preventDefault();
    let query = getCurrentQuery();
    let data_source = "PubMed"
    let end_pos = DEFAULT_RESULT_DIVS_LIMIT;
    let freq_element = document.getElementById("select_sorting_freq");
    let freq_sort_desc = freq_element.value;
    let year_element = document.getElementById("select_sorting_year");
    let year_sort_desc = year_element.value;
    /*
    if (document.getElementById('radio_pmc').checked) {
        data_source = "PMC"
    } else if(document.getElementById('radio_pubmed').checked) {
        data_source = "PubMed"
    } */

    let outer_ranking = document.querySelector('input[name = "outer_ranking"]:checked').value;
    //let inner_ranking = document.querySelector('input[name = "inner_ranking"]:checked').value;
    let inner_ranking = "NOT IMPLEMENTED";

    console.log("Query: " + query);
    console.log("Data source: " + data_source)
    console.log("Outer Ranking: " + outer_ranking)
    console.log("Inner Ranking: " + inner_ranking)
    console.log("Sorting by frequency (desc): " + freq_sort_desc)
    console.log("Sorting by year (desc): " + year_sort_desc)
    console.log("Result Divs Limit: " + DEFAULT_RESULT_DIVS_LIMIT)
    setButtonSearching(true);

    let request = $.ajax({
        url: search_url,
        data: {
            query: query,
            data_source: data_source,
            outer_ranking: outer_ranking,
            freq_sort: freq_sort_desc,
            year_sort: year_sort_desc,
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
            latest_valid_query = query

            // Hide sort buttons depending on the result
            let is_aggregate = response["is_aggregate"]
            document.getElementById("select_sorting_year").style.display = "block"
            console.log
            if (is_aggregate === true) {
                document.getElementById("select_sorting_freq").style.display = "block"
            } else {
                document.getElementById("select_sorting_freq").style.display = "none"
            }

            // Print query translation
            let query_translation = $("#query_translation");
            let query_trans_string = response["query_translation"];
            let query_limit_hit = response["query_limit_hit"];
            query_translation.text(query_trans_string);
            let results = response["results"];
            let result_size = results["s"];
            // Create documents DIV
            let divList = createResultList(results, query_len);
            divDocuments.append(divList);
            // add_collapsable_events();

            let documents_header = $("#header_documents");
            let document_header_appendix = "";
            if (query_limit_hit === true) {
                document_header_appendix = " (Truncated)"
            }
            if (result_size >= 0) {
                documents_header.html(result_size + " Documents" + document_header_appendix)
            } else {
                documents_header.html("Documents")
            }

            // scroll to results
            document.getElementById("resultdiv").scrollIntoView();
        } else {
            document.getElementById("select_sorting_year").style.display = "none"
            document.getElementById("select_sorting_freq").style.display = "none"
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

function rateExtraction(correct, predication_ids_str) {
    let userid = getUserIDFromLocalStorage();
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
                if (rateExtraction(true, predication_ids_str)) {
                    $('#' + rate_pos_id).fadeOut();
                    $('#' + rate_neg_id).fadeOut();
                }

            });
            div_rate_neg.click(function () {
                if (rateExtraction(false, predication_ids_str)) {
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

function queryAndVisualizeProvenanceInformation(provenance, unique_div_id) {
    let request = $.ajax({
        url: provenance_url,
        data: {
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

const createResultDocumentElement = (queryResult, query_len, accordionID, headingID, collapseID) => {
    let document_id = queryResult["docid"];
    let title = queryResult["title"];
    let authors = queryResult["authors"];
    let journals = queryResult["journals"];
    let year = queryResult["year"];
    let prov_ids = queryResult["prov"];


    let divDoc = $('<div class="card"><div class="card-body">' +
        '<a class="btn-link" href="https://www.pubpharm.de/vufind/Search/Results?lookfor=NLM' + document_id + '" target="_blank">'+
        '<img src="' + pubpharm_image_url + '" height="25px">' +
        document_id +  '</a>' +

        '<a class="btn-link float-right" href="http://134.169.32.177/document?id=' + document_id + '" target="_blank">'+
        'Document Graph</a>' +

        '<br><b>' + title + '</b><br>' +
        "in: " + journals + " | " + year + '<br>' +
        "by: " + authors + '<br>' +
        '</div></div><br>');

    let unique_div_id = "prov_" + document_id;
    let div_provenance_button = $('<button class="btn btn-light" data-toggle="collapse" data-target="#' + unique_div_id + '">Provenance</button>');
    let div_provenance_collapsable_block = $('<div class="collapse" id="' + unique_div_id + '">');
    div_provenance_button.click(function () {
        if ($('#' + unique_div_id).html() === "") {
            queryAndVisualizeProvenanceInformation(prov_ids, unique_div_id);
        }
    });

    divDoc.append(div_provenance_button);
    divDoc.append(div_provenance_collapsable_block);
    return divDoc;
};


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
    divH2.append('<button class="btn btn-link" type="button" data-toggle="collapse" data-target="#' + collapseID + '" ' +
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


const createDocumentAggregate = (queryAggregate, query_len, accordionID, headingID, collapseID) => {
    let divCard = $('<div class="card"></div>');
    let divCardHeader = $('<div class="card-header" id="' + headingID + '"></div>');
    divCard.append(divCardHeader);
    let divH2 = $('<h2 class="mb-0"></h2>');
    divCardHeader.append(divH2);

    let resultList = queryAggregate["r"];
    let var_names = queryAggregate["v_n"];
    let var_subs = queryAggregate["sub"];
    let result_size = queryAggregate["s"];
    let button_string = result_size + ' Document';
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
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://www.ebi.ac.uk/chembl/compound_report_card/' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else if (ent_id.slice(0, 2) === "DB") {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://go.drugbank.com/drugs/' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else if (ent_id.slice(0, 5) === 'MESH:') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://meshb.nlm.nih.gov/record/ui?ui=' + ent_id.slice(5) + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else if (ent_type === 'Species') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else if (ent_type === 'Gene') {
            button_string += ', '.repeat(!!i) + name + ':= ' + ent_name + ' (' + "Target" + ' <a onclick="event.stopPropagation()"' +
                'href="https://www.ncbi.nlm.nih.gov/gene/?term=' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else {
            button_string += ', '.repeat(!!i) + var_sub + ']'
        }
        i += 1;
    });

    divH2.append('<button class="btn btn-light" type="button" data-toggle="collapse" data-target="#' + collapseID + '" ' +
        'aria-expanded="true" aria-controls="' + collapseID + '">' + button_string + '</button>');
    let divCardEntry = $('<div id="' + collapseID + '" class="collapse" aria-labelledby="' + headingID + '" data-parent="#' + accordionID + '"></div>');
    let divCardBodyID = getUniqueBodyID();
    let divCardBody = $('<div class="card-body"></div>');
    divCardEntry.append(divCardBody);
    divCard.append(divCardEntry);


    globalAccordionDict[divCardBodyID] = [divCardBody, query_len, accordionID, headingID, collapseID, resultList, resultList.length];
    createExpandableAccordion(true, divCardBodyID);

    return divCard;
};

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


function buildATCLevel5Element(data_parent, atc_class) {
    let atc_info = atc_class.split(' - ')[0];
    let atc_label = atc_class.split(' - ')[1];
    atc_label = atc_label.charAt(0).toUpperCase() + atc_label.slice(1);
    let apply_btn_id = "apply_btn" + atc_info;
    document.getElementById(data_parent).insertAdjacentHTML("beforeend", '<div class="card">\n' +
        '                        <div class="card-header">' + atc_info + ' - ' + atc_label + '\n' +
        '                           <button class="btn btn-sm btn-outline-dark float-right" data-dismiss="modal" id="' + apply_btn_id + '">Apply</button>\n' +
        '                        </div>\n' +
        '                    </div>');

    document.getElementById(apply_btn_id).addEventListener("click", function () {
        copySelectedConcept(atc_label);
    });
}

let LAST_INPUT_FIELD = null;

function setConceptInputFieldSubject(){
    LAST_INPUT_FIELD = "input_subject";
}
function setConceptInputFieldObject(){
    LAST_INPUT_FIELD = "input_object";
}

function copySelectedConcept(concept) {
    if (LAST_INPUT_FIELD !== null) {
        let target_element = document.getElementById(LAST_INPUT_FIELD);
        target_element.value = concept;
    }
}


function buildATCHeaderCard(data_parent, atc_class) {
    // atc_class: e.g. "A01AA03 - olaflur" -> atc_info: "A01AA03"
    let atc_info = atc_class.split(' - ')[0];
    let heading_id = "heading" + atc_info;
    let collapse_id = "collapse" + atc_info;
    let child_id = "child" + atc_info;
    let atc_label = atc_class.split(' - ')[1].trim().toLowerCase();
    atc_label = atc_label.charAt(0).toUpperCase() + atc_label.slice(1);
    let apply_btn_id = "apply_btn" + atc_info;

    document.getElementById(data_parent).insertAdjacentHTML("beforeend", '<div class="card">\n' +
        '            <div class="card-header" id="' + heading_id + '">\n' +
        '                <h5 class="mb-0 d-inline">\n' +
        '                    <button class="btn btn-link text-start" data-toggle="collapse" data-target="#' + collapse_id + '" aria-expanded="true" aria-controls="' + collapse_id + '">\n' +
        '                      ' + atc_info + ' - ' + atc_label + '\n' +
        '                    </button>\n' +
        '                    <button class="btn btn-sm btn-outline-dark float-right" data-dismiss="modal" id="' + apply_btn_id + '">Apply</button>\n' +
        '                 </h5>\n' +
        '            </div>' +
        '            <div id="' + collapse_id + '" class="collapse" aria-labelledby="' + heading_id + '" data-parent="#' + data_parent + '">\n' +
        '                <div class="card-body" id="' + child_id + '">\n' +
        '                </div>\n' +
        '            </div>' +
        '</div>'
    );

    document.getElementById(apply_btn_id).addEventListener("click", function () {
        copySelectedConcept( atc_label);
    });
}

function buildATCTree(data_parent, tree, atc_depth) {
    for (var k in tree) {
        let atc_class = tree[k]["name"];
        let atc_info = atc_class.split(' - ')[0];
        let subtree = tree[k]["children"];
        let child_id = "child" + atc_info;
        //console.log(atc_class, atc_info, child_id, subtree);
        if (atc_depth < 5) {
            buildATCHeaderCard(data_parent, atc_class);
            buildATCTree(child_id, subtree, atc_depth + 1);
        } else {
            let lvl5_name_and_desc = atc_class + ' - ' + subtree[0]["name"];
            buildATCLevel5Element(data_parent, lvl5_name_and_desc);
        }
    }

}

// build atc tree for modal
function queryAndBuildATCTree() {
    $('#browseSearch').on('keydown', (e)=>{
        $('#atcModal').modal('handleUpdate')
    })

    let tree = null;

    fetch(atc_tree_url)
        .then(response => response.json())
        .then(result => {
            let atc_tree_data = createTreeDataFromQueryResult(result["chembl_atc_tree"])
            let options = {
                searchBox: $('#browseSearch'),
                searchMinInputLength: 3
            }
            let tree_data = [getVariableData(), {
                label: "ATC Classes",
                value: "",
                children: atc_tree_data
            }]
            tree = $('#browseTree').simpleTree(options, tree_data)
            $('#atcModal').on('show.bs.modal', (e) => {
                tree.clearSelection(false)
                $("#atcTreeOK").addClass("disabled")
            })
            tree.on('simpleTree:change', (node) =>{
                $("#atcTreeOK").removeClass("disabled")
            })
            $("#atcTreeOK").on('click', (e) =>{
                copySelectedConcept(tree.getSelectedNode()["value"])
                $("#atcModal").modal('hide')
            })
            /*for (let k in result)
            {
                buildATCTree("atc_accordion", result[k], 1);
            }*/
        })
        .catch((error) => {
            $('#alert_translation').text('Failed to get atc tree.');
            $('#alert_translation').fadeIn();
            console.log("Failed to get atc tree")
            console.log(error)
        })
    let request = $.ajax({
        url: atc_tree_url
    });

    request.done(function (response) {
        let result = response;

     //   document.getElementById("atcButton").style.display = "block";
    });
}

function createTreeDataFromQueryResult(inputTree) {
    let outputTree= []
    //console.log(inputTree)
    for (let node of inputTree) {
        //console.log(node)
        let out_node = [];
        let name = node["name"]
        if ("children" in node) {
            //console.log(node["children"])
            if ("children" in node["children"][0]) {
                out_node["children"] = createTreeDataFromQueryResult(node["children"])
            }
            else {
                name = node["name"] + " - " +  node["children"][0]["name"]
            }
        }
        out_node["label"] = name
        out_node["value"] = name.split("-")[1]

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
    ];

    let out_tree = []

    for(let v of variables) {
        let node = {}
        node["label"] = v[0] + " ("+ v[1] + ")"
        node["value"] = "?" + v[0]
        out_tree.push(node)
    }
    out_tree = {
        label: "Variables",
        value: "",
        children: out_tree
    }
    return out_tree
}

function buildVariableTreeButton(dataParent, variableName, variableText) {
    let btn_id = "apply_btn" + variableName;

    let rowDiv = $('<div class="row py-1 border"/>');
    let rowText = $('<div class="col"><p class="text-left">'+ variableName + ' (' + variableText+')</p></div>');
    let applyBtn = $('<div class="col-1"><button class="btn btn-sm btn-outline-dark float-right" data-dismiss="modal" id="' + btn_id + '">Apply</button></div>');
    rowDiv.append(rowText);
    rowDiv.append(applyBtn);
    dataParent.append(rowDiv);

    applyBtn.click(function () {
        copySelectedConcept(variableName);
    });
}

function buildVariableTree() {
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
            ];
    let divVariables = $('<div class="grid"/>');
    variables.forEach(variable => {
        buildVariableTreeButton(divVariables, variable[0], variable[1])
    });
    $('#variable_card_body').append(divVariables);

}

function buildSelectionTrees() {
    queryAndBuildATCTree();
    buildVariableTree();
}