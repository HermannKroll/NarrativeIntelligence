async function initRecommendSearchFromURL(documentID, documentCollection) {
    const documentInput = document.getElementById("recommender_input");
    documentInput.value = documentID;
    await loadCollectionDropDownMenu();
    switchTab("#search-type-recommender");
    const dropDownMenu = document.getElementById("input_collection");
    Array.from(dropDownMenu.options).forEach(option => {
        console.log(option);
        option.selected = (option.value === documentCollection);
    });
    await recommenderSearch();
}

async function createDocumentPreview(document_id, document_collection) {
    const url = url_narrative_documents + "?document=" + document_id + "&data_source=" + document_collection;
    const queryResult = await fetch(url)
        .then((response) => {
            if (!response.ok) {
                return {};
            }
            return response.json();
        })
        .then((jsonData) => {
            return jsonData["results"][0];
        })
        .catch(_ => console.log("Could not retrieve document information for preview"));

    const title = queryResult["title"];
    const authors = queryResult["metadata"]["authors"];
    const journals = queryResult["metadata"]["journals"];
    const year = queryResult["metadata"]["publication_year"];
    const collection = document_collection;
    const artificialID = queryResult["id"];
    let month = queryResult["metadata"]["publication_month"];
    if (month === 0) {
        month = "";
    } else {
        month = month + "/";
    }
    // use the original document id if available
    let doiText = "PMID";
    // TODO
    // if (queryResult["org_document_id"] !== null && queryResult["org_document_id"].length > 0) {
    //     document_id = queryResult["org_document_id"];
    //     doiText = "DOI";
    // }

    let doi = queryResult["metadata"]["doi"];

    let divDoc_Card = $('<div class="card"/>');
    let divDoc_Body = $('<div class="card-body"/>');
    let divDoc_Body_Link = $('<a>' + doiText + ": " + '</a><a class="btn-link" href="' + doi + '" target="_blank">' + document_id + '</a>');


    divDoc_Body_Link.click(function () {
        sendDocumentClicked(lastQuery, document_id, collection, doi);
    });
    let divDoc_Image = $('<img src="' + pubpharm_image_url + '" height="25px"/>');

    let divDoc_DocumentGraph = $('<div class="float-end popupButton">' +
        'Document Content' + '<br><img src="' + url_graph_preview + '" height="100px"/>' + '</div>');

    divDoc_DocumentGraph.click(() => {
        showPaperView(artificialID, collection)
    })

    divDoc_Body.append(divDoc_Image);
    divDoc_Body.append(divDoc_DocumentGraph);

    let divDoc_Content = $('<br><b>' + title + '</b><br>' +
        "in: " + journals + " | " + month + year + '<br>' +
        "by: " + authors + '<br>');

    divDoc_Body.append(divDoc_Content);
    divDoc_Card.append(divDoc_Body);
    divDoc_Body.append(divDoc_Body_Link);

    let divFinal = $('<div/>');
    divFinal.append(divDoc_Card);
    divFinal.append($('<br>'));
    return divFinal;
}

async function recommenderSearch() {
    const alertDiv = document.getElementById('alert_recommender');
    alertDiv.innerText = '';

    const documentInput = document.getElementById("recommender_input");
    const documentID = documentInput.value.trim();

    const parameters = getInputParameters(documentID);
    logInputParameters(parameters);
    updateURLParameters(parameters);
    if (documentID.length === 0) {
        alertDiv.innerText = 'Input a document id to retrieve recommendations';
        return;
    }

    setButtonSearching(true, "btn_recommender", "help_recommend");

    const parameterString = createURLParameterString(parameters)

    const fetchUrl = url_recommender_search + "?" + parameterString;
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

    showResults(recommenderData, parameters);

    const previewContainer = document.getElementById('document_preview');
    while (previewContainer.firstChild) {
        previewContainer.removeChild(previewContainer.firstChild);
    }
    const documentPreview = await createDocumentPreview(documentID, parameters["query_col"]);
    previewContainer.appendChild(documentPreview.get(0));

    setButtonSearching(false, "btn_recommender", "help_recommend");
}

function visualizeRecommenderExplanationGraph(document_id, graph_data) {
    let graph_container = document.getElementById(document_id + "_graph")
    graph_container.style.display = "block";

    if (graph_container instanceof HTMLElement) {
        visualizeRecommenderGraph(graph_container, graph_data);
    } else {
        setTimeout(() => {
            visualizeRecommenderGraph(graph_container, graph_data)
        }, 100);
    }
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