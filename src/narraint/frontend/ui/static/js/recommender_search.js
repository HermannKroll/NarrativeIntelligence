

function initRecommendSearchFromURL() {

}

async function recommenderSearch() {
    const alertDiv = document.getElementById('alert_recommender');
    alertDiv.innerText = '';

    const documentInput = document.getElementById("recommender_input");
    const documentID = documentInput.value.trim();
    const dataSource = getSelectedDataSources()[0];

    if (documentID.length === 0) {
        alertDiv.innerText = 'Input a document id to retrieve recommendations';
        return;
    }

    setButtonSearching(true, "btn_recommender", "help_recommend");

    const fetchUrl = url_recommender_search + "?document_id=" + documentID + "&document_collection=" + dataSource;
    const recommenderData = await fetch(fetchUrl)
        .then((response) => {
            return response.json();
        })
        .then((data) => {
            if (data["error_msg"]) {
                alertDiv.innerText = data["error_msg"];
                return undefined;
            } else {
                return data;
            }
        })
        .catch((e) => console.log(e))

    // TODO what to to with the query ??
    showResultsRecommender(recommenderData, {query: undefined, state: "recommend"});
    setButtonSearching(false, "btn_recommender", "help_recommend");
}


function showResultsRecommender(response, parameters) {
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
    let divList = createResultListRecommender(results, query_len);
    divDocuments.append(divList);

    results["r"].forEach(function (item) {
        if (item && item["t"] === "doc" && item["docid"] && item["graph_data"]) {
            let document_id = item["docid"];
            let graph_data = item["graph_data"];
            let container = document.getElementById(document_id + "_graph");
            if (container) {
                visualizeRecommenderGraph(container, graph_data);
            }
        }
    });

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
    updateYearFilter(response["year_aggregation"], query_trans_string);
    updateExplanationPopover();
    latest_query_translation = query_trans_string.split("----->")[0].trim();
    saveHistoryEntry({size: result_size, filterOptions: parameters});
}


function createResultDocumentElementRecommender(queryResult) {
    let document_id = queryResult["docid"];
    let graph_data = queryResult["graph_data"];
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

    divDoc_Body.append(divDoc_Image);
    divDoc_Body.append(divDoc_DocumentGraph);

    let divDoc_Content = $('<br><b>' + title + '</b><br>' +
        "in: " + journals + " | " + month + year + '<br>' +
        "by: " + authors + '<br>');

    divDoc_Body.append(divDoc_Content);

    let divDocRecommenderLink = $('<br><a class="btn-link" href="/?state=recommend&document_id=' + document_id + '" target="_blank">Show similar articles</a>');

    divDoc_Card.append(divDoc_Body);
    divDoc_Body.append(divDoc_Body_Link);
    divDoc_Body.append(divDocRecommenderLink);


    let div_provenance_button = $('<button class="btn btn-light" data-bs-toggle="collapse">Explanation Excerpt</button>');
    divDoc_Card.append(div_provenance_button);

    let divDoc_RecommenderGraph = $('<div class="graph rounded border w-100" style="height:600px" id="' + document_id + '_graph"></div>');
    divDoc_Card.append(divDoc_RecommenderGraph);

    let divFinal = $('<div/>');
    divFinal.append(divDoc_Card);
    divFinal.append($('<br>'));
    return divFinal;
}


function createExpandListElementRecommender(divID, next_element_count) {
    let btnid = 'exp' + divID
    let cardid = 'exp_card_' + divID
    let divExpand = $('<div class="card" id="' + cardid + '"><div class="card-body">' +
        '<button class="btn btn-link" id="' + btnid + '">... click to expand (' + next_element_count + " left)" + '</button>' +
        '</div></div>');
    $(document).on('click', '#' + btnid, function () {
        createExpandableAccordionRecommender(false, divID)
    });
    return divExpand;
}


function createExpandableAccordionRecommender(first_call, divID) {
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
            current_div.append(createDivListForResultElementRecommender(res, query_len, accordionID, headingID + j, collapseID + j));
        } else {
            nextResultList.push(res);
        }
    });
    // add a expand button
    if (i > MAX_SHOWN_ELEMENTS) {
        current_div.append(createExpandListElementRecommender(divID, nextResultList.length));
    }
    globalAccordionDict[divID] = [current_div, query_len, accordionID, headingID, collapseID, nextResultList, global_result_size + i];
}


function createDocumentListRecommender(results, query_len) {
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
    createExpandableAccordionRecommender(true, divCardBodyID);
    return divAccordion;
}


function createResultListRecommender(results, query_len) {
    let divList = $(`<div></div>`);
    divList.append(createDivListForResultElementRecommender(results, query_len, null, null, null));
    return divList;
}


function createDivListForResultElementRecommender(result, query_len, accordionID, headingID, collapseID) {
    let typeOfRes = result["t"];
    if (typeOfRes === "doc") {
        return (createResultDocumentElementRecommender(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "doc_l") {
        return (createDocumentListRecommender(result, query_len, accordionID, headingID, collapseID));
    }
    console.log("ERROR - does not recognize result type: " + typeOfRes);
    return null;
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