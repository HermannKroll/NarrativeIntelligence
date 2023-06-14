let networkOptions = {
    autoResize: true,
    interaction: {
        hover: true,
        zoomView: false,
        dragView: false,
        dragNodes: false
    },
    physics: { solver: "forceAtlas2Based" },
    groups: {
        default_ge: {
            color: {
                background: "white",
                hover: {
                    background: "white"
                },
                highlight: {
                    background: "white"
                }
            }
        }
    }
};

let graphs = []

async function search() {
    const keywords = document.getElementById('search_input').value;
    if (keywords === "") {
        const inputAlert = document.getElementById('input_alert');
        inputAlert.classList.toggle('d-none');
        setTimeout(() => inputAlert.classList.toggle('d-none'), 5000);
        return;
    }

    // set search animations
    toggleLoadingScreen();

    const qgDiv = document.getElementById('query_graphs');

    // Reset container
    qgDiv.innerText = '';
    document.getElementById('div_documents').innerText = '';

    await fetch(`${url_keyword_search_request}?keywords=${keywords}`)
        .then((response) => { return response.json() })
        .then((data) => {
            // expect format: qg: dict{terms: list[str], entities: list[str], statements: list[(str, str, str)]}
            for (let idx in Object.keys(data['query_graphs'])) {

                const qg = data['query_graphs'][idx];
                if (qg === null) {
                    continue;
                }
                createQueryGraph(qg, qgDiv);
            }
        })
        .catch((e) => console.error(e))
        .finally(() => {
            toggleLoadingScreen();
            document.getElementById('info_text').classList.toggle('d-none');
        });
}

/**
 * Function alls all relevant sub functions to create a graphical representation of the given query-graph (qg).
 * @param {{terms: string[], entities: string[], statements: [string, string, string]}} qg
 * @param {HTMLElement} parent_div
 */
function createQueryGraph(qg, parent_div) {
    const terms = qg['terms'];
    const entts = qg['entities'];
    const stmts = qg['statements'];

    const [container, graphDiv, tDiv] = createQGContainer();
    parent_div.appendChild(container);

    graphs.push(container);

    addQGTerms(terms, tDiv);
    addQGClickEvent(terms, entts, stmts, container);
    addTooltipEvent(terms, entts, stmts, graphDiv);

    const data = createQGData(entts, stmts);
    const _ = new vis.Network(graphDiv, data, networkOptions);
}

/**
 * Function returns a query graph url parameter representation
 * @param {Array[string]} terms
 * @param {Array[string]} entts
 * @param {Array[Array[string, string, string]]} stmts
 * @returns string
 */
function qgUrlParams(terms, entts, stmts) {
    const urlParams = {};

    if (terms.length > 0)
        urlParams.terms = terms.join(';');
    if (entts.length > 0)
        urlParams.entities = entts.join(';');

    if (stmts.length > 0) {
        const statements = [];
        stmts.forEach(([subj, pred, obj]) => {
            subj = subj.includes(' ') ? `"${subj}"`: subj;
            obj = obj.includes(' ') ? `"${obj}"`: obj;
            statements.push(`${subj} ${pred} ${obj}`);
        });
        urlParams.query = statements.join("_AND_");
    }
    return new URLSearchParams(urlParams).toString();
}

function showResults(response, query) {
    let divDocuments = $('#div_documents');
    divDocuments.empty();

    if (response["valid_query"] === "") {
        const alert = document.getElementById('result_alert');//$('#result_alert');
        alert.classList.toggle('d-none');

        setTimeout(() => alert.classList.toggle('d-none'), 5000);
        return;
    }

    let query_len = 0;

    // Hide sort buttons depending on the result
    let is_aggregate = response["is_aggregate"];
    document.getElementById("select_sorting_year").classList.remove("d-none");
    if (is_aggregate === true) {
        document.getElementById("select_sorting_freq").classList.remove("d-none");
    } else {
        document.getElementById("select_sorting_freq").classList.toggle("d-none", false);
    }

    // Print query translation
    // let query_translation = $("#query_translation");
    //let query_trans_string = response["query_translation"];
    // query_translation.text(query_trans_string);
    let query_limit_hit = response["query_limit_hit"];
    let results = response["results"];
    let result_size = results["s"];

    // Show Page only if the result is an aggregated list of variable substitutions
    if (results["t"] === "agg_l") {
        computePageInfo(results["no_subs"]);
    } else {
        document.getElementById("div_input_page").style.display = "none";
    }

    // Create documents DIV
    let divList = createResultList(results, query_len);
    divDocuments.append(divList);

    document.getElementById("result_div").scrollIntoView();

    // let documents_header = $("#header_documents");
    // let document_header_appendix = "";
    // if (query_limit_hit === true) {
    //     document_header_appendix = " (Truncated)"
    // }
    // if (result_size !== 0) {
    //     documents_header.html(result_size + " Documents" + document_header_appendix)
    //     // scroll to results
    //     document.getElementById("result_div").scrollIntoView();
    // } else {
    //     documents_header.html("Documents")
    //
    //     // check if the used predicated is to specific (!= 'associated')
    //     let predicate_input = document.getElementById('input_predicate');
    //     let predicate = predicate_input.options[predicate_input.selectedIndex].value;
    //
    //     if (predicate !== 'associated') {
    //         $('#modal_empty_result').modal("toggle");
    //     }
    // }
}

function resetBorders() {
    graphs.forEach((container) => {
        container.classList.remove('border-danger');
    })
}

function addQGClickEvent(terms, entts, stmts, container) {
    const params = qgUrlParams(terms, entts, stmts);
    console.log(params);
    container.onclick = async () => {
        // check if the requested query is already shown
        if (latest_valid_query === params) {
            return;
        }

        resetBorders();
        latest_valid_query = params;

        toggleLoadingScreen();
        await fetch(`${url_default_query}?${params}&data_source=PubMed`)
            .then((response) => { return response.json(); })
            .then((data) => showResults(data, params))
            .catch((e) => console.log(e))
        toggleLoadingScreen();

        container.classList.add('border-danger');
    }
}

function addTooltipEvent(terms, entts, stmts, div) {
    const tt = document.getElementById('tooltip');
    const statements = [];
    for (const i in stmts) {
        const [s, p, o] = stmts[i];
        statements.push(`"${s}" ${p} "${o}"`);
    }

    let str = "";
    str += '<b>Terms: </b>' + terms.join(', ') + '<br>';
    str += '<b>Entities: </b>' + entts.join(', ') + '<br>';
    str += '<b>Statements: </b><br>&emsp;' + statements.join(' AND<br>&emsp;');

    div.onmouseenter = (ev) => {
        tt.classList.toggle('d-none');
        tt.innerHTML = str;
        tt.style.top = (ev.pageY - tt.offsetHeight) + "px";
        tt.style.left= (ev.pageX) + "px";
    };

    div.onmousemove = (ev) => {
        tt.style.top = (ev.pageY - tt.offsetHeight) + "px";
        tt.style.left= (ev.pageX) + "px";
    };

    div.onmouseleave = () => {
        tt.classList.toggle('d-none');
    };
}

function createQGContainer() {
    const container = document.createElement('div');
    container.classList.add("col-12", "w-100", "w-32", "mx-auto", "mt-1", "p-1", "border", "rounded", "h-auto",
        "d-flex", "flex-wrap", "flex-row", "pc_baseline", "shadow-hov");
    const graph = document.createElement('div');
    graph.classList.add("w-100", "h-250px", "bg-white");
    const terms = document.createElement('div');
    terms.classList.add("w-100", "text-wrap", "border-top");
    container.appendChild(graph);
    container.appendChild(terms);
    return [container, graph, terms];
}

function addQGTerms(terms, div) {
    // TODO maybe return early if no terms exist
    div.innerHTML = "<b>Terms: </b>" + terms.join(', ');
}

function createQGData(entities, statements) {
    const statement_entities = []

    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();

    // insert node elements only, if they not already exist in the current graph
    function insertNodeElement(element) {
        if (statement_entities.indexOf(element) >= 0) {
            return;
        }
        nodes.add({ id: element, label: element, group: 'default_ge'});
        statement_entities.push(element);
    }

    statements.forEach(([s, p, o]) => {
        insertNodeElement(s);
        insertNodeElement(o);

        edges.add({
            from: s,
            to: o,
            label: p,
            arrows: { to: { enabled: true } },
            smooth: { enabled: false },
            font: { align: 'top'}
        });
    });

    entities.forEach((e) => {
        insertNodeElement(e);
    });
    return { nodes: nodes, edges: edges };
}

async function toggleLoadingScreen() {
    // TODO: somehow wait for end of scroll
    window.scrollTo({top: 0});

    document.getElementById('loading_screen').classList.toggle('d-none');
    document.body.classList.toggle('stop-scrolling');
}

function createHTMLElement(type, id=null, classList=null, attributes=null) {
    // console.log(type, id, classList, attributes);
    const element = document.createElement(type);
    if (id)
        element.id = id;
    if (classList)
        element.classList.add(classList);
    if (attributes)
        Object.entries(attributes).forEach(([k, v]) => element.setAttribute(k, v));
    return element;
}

// =====================================================================================================================
// =====================================================================================================================
// =====================================================================================================================
// =====================================================================================================================
// =====================================================================================================================

let latest_valid_query = '';
let DEFAULT_AGGREGATED_RESULTS_PER_PAGE = 30;
let MAX_SHOWN_ELEMENTS = DEFAULT_AGGREGATED_RESULTS_PER_PAGE;

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

document.getElementById("select_sorting_year").addEventListener("change", function () {
    document.getElementById("btn_search").click()
});
document.getElementById("select_sorting_freq").addEventListener("change", function () {
    document.getElementById("btn_search").click()
});

let currentMaxPage = 0;

function computePageInfo(result_size) {
    let pageCount = Math.ceil(parseInt(result_size) / DEFAULT_AGGREGATED_RESULTS_PER_PAGE);
    currentMaxPage = pageCount;
    document.getElementById("label_max_page").textContent = pageCount.toString();
    document.getElementById("div_input_page").style.display = "block";
}

let lastQuery = "";

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
    } catch (error) {
        console.log(error)
    }
    return div_provenance_all;
}

function queryAndVisualizeProvenanceInformation(query, document_id, data_source, provenance, unique_div_id) {
    const params = {
        query: query,
        document_id: document_id,
        data_source: data_source,
        prov: JSON.stringify(provenance)
    }

    fetch(url_provenance + "?" + new URLSearchParams(params).toString())
        .then((response) => {
            return response.json();
        })
        .then((jsonData) => {
            let explanations = jsonData["result"]["exp"];
            let prov_div = createProvenanceDivElement(explanations);
            $('#' + unique_div_id).append(prov_div);
        })
        .catch((e) => console.log(e));
}

let uniqueProvenanceID = 1;
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

    divDoc_DocumentGraph.click(() => {showPaperView(art_doc_id, collection)})

    divDoc_Body.append(divDoc_Image);
    divDoc_Body.append(divDoc_DocumentGraph);

    let divDoc_Content = $('<br><b>' + title + '</b><br>' +
        "in: " + journals + " | " + month + year + '<br>' +
        "by: " + authors + '<br>');

    divDoc_Body.append(divDoc_Content);

    //let
    divDoc_Card.append(divDoc_Body);
    divDoc_Body.append(divDoc_Body_Link);

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
    if(url_str) {
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

function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
