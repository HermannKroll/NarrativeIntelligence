let networkOptionsKG = {
    autoResize: true,
    interaction: {
        hover: true,
        zoomView: true,
        dragView: true,
        dragNodes: true
    },
    physics: {
            solver: "barnesHut",
    },
};

let discoveryGraph = undefined;


window.addEventListener("DOMContentLoaded", () => {
    $('#input-path-concepts').autocomplete({
        minLength: 0,
        autoFocus: true,
        source: async (request, response) => {
            const data = await fetch(autocompletion_url + "?term=" + request.term)
                .then((result) => {
                    return result.json();
                })
                .then((json) => {
                    return json["terms"];
                });
            response(data);
        },
        focus: () => {
            // prevent value inserted on focus
            return false;
        }
    }).on("keydown", (event) => {
        if (event.key === "Enter") {
            if (document.querySelector("#input-path-concepts").value.trim() === "") {
                // submit on empty input
                searchPatternDiscovery();
            } else {
                addPatternDiscoveryConcept();
            }
        } else if (event.key === "Tab") {
            event.preventDefault();
            addPatternDiscoveryConcept();
        }
    })
});

/**
 * TODO refactor - remove duplicate code
 */
function addPatternDiscoveryConcept(concept = undefined) {
    const keywordList = document.querySelector("#path-concept-list");
    const keywordInput = document.querySelector('#input-path-concepts');

    if (concept) {
        concept = concept[0].toUpperCase() + concept.slice(1);
        keywordInput.value = concept;
    }

    const keywordId = "keyword-tag-" + keywordInput.value.trim().toLowerCase().replace(" ", "-");

    // add keywords only once
    if (Array.from(keywordList.childNodes).some((k) => k.id === keywordId)) {
        keywordInput.value = "";
        return;
    }

    // Don't add the empty keyword
    if (keywordInput.value.trim() === ""){
        return;
    }

    const div = document.createElement("div");
    div.classList.add("text-dark", "bg-light", "border", "rounded", "position-relative", "me-3", "mt-3", "px-2");
    div.innerText = keywordInput.value.trim();
    div.id = keywordId
    const span = document.createElement("span");
    span.setAttribute("role", "button");
    span.classList.add("badge", "position-absolute", "top-0", "start-100", "translate-middle", "bg-danger", "rounded-pill", "pointer")
    span.innerText = "X";
    span.onclick = () => keywordList.removeChild(div);
    div.appendChild(span);
    keywordList.appendChild(div);
    keywordInput.value = "";
}

function getConceptsFromInput() {
    const conceptDiv = document.querySelector("#path-concept-list");
    const conceptInput = document.querySelector("#input-path-concepts");
    let concepts = [];

    // append concept from input if existing
    if (conceptInput.value.trim() !== "")
        concepts.push(conceptInput.value);

    for (const node of conceptDiv.childNodes) {
        let nodeText = node.innerText.substring(0, node.innerText.length - 1);
        nodeText = nodeText.replace('\n', '').trim();
        concepts.push(nodeText);
    }

    return concepts.join("_AND_")
}

async function searchPatternDiscovery(query = undefined) {
    const queryGraphContainer = document.querySelector('#container-div-path-concepts');
    const divDocuments = $('#div_documents');

    // use query from parameter if provided and create from input else
    let conceptString;
    if (query) {
        conceptString = query;
        for (const concept of conceptString.split("_AND_")) {
            addPatternDiscoveryConcept(concept);
        }
    } else {
        conceptString = getConceptsFromInput();
    }

    if (conceptString === "") {
        showAlert("Empty input. Provide keywords to search!");
        return;
    }

    const parameters = getInputParameters(conceptString)

    parameters["num_edges"] = document.getElementById("path-concepts-slider").value;
    document.getElementById("path-concepts-num-edges").innerText = `Top ${parameters["num_edges"]}`;

    logInputParameters(parameters);
    updateURLParameters(parameters);

    queryGraphContainer.classList.toggle('d-none', true);
    showLoadingScreen();

    const queryGraphDiv = document.querySelector('#graph-div-path-concepts');
    queryGraphDiv.innerHTML = "";
    document.getElementById('div_documents').innerText = '';

    const parameterString = createURLParameterString(parameters);

    const data = await fetch(`${url_pattern_discovery}?${parameterString}`)
        .then((response) => {
            if (response.ok)
                return response.json();
            else {
                return response.json().then((d) => {
                    return Promise.reject(d["reason"]);
                })
            }
        })
        .catch((e) => {
            showAlert(e);
        });

    if (!data) {
        hideLoadingScreen();
        return;
    }

    latest_valid_query = parameters["query"];

    sortStrategyUpdate(false);
    sortStrategySet(data["sort_by"]);
    sortOrderSet(data["sort_order"]);

    // required for invalid strategies (from URL)
    if (data["sort_by"] !== parameters["sort_by"])
        updateURLParameter("sort_by", data["sort_by"])

    const results = data["results"];
    const result_size = results["s"];

    document.getElementById("sorting_container").classList.toggle("d-none", false);

    if (result_size !== 0) {
        document.getElementById("input_title_filter").classList.toggle("d-none", false);
        document.getElementById("input_title_filter_label").classList.toggle("d-none", false);
    }

    updateYearFilter(data["year_aggregation"], data["query"]);

    // knowledge graph
    createKnowledgeGraph(data["graph"], data["concepts"], queryGraphDiv);
    queryGraphContainer.classList.toggle("d-none", false);

    // documents
    divDocuments.empty();
    divDocuments.append(createResultList(data["results"], 0));

    hideLoadingScreen();
}

function createKnowledgeGraph(statements, concepts, parentDiv) {
    const column = document.createElement('div');
    column.classList.add("col-12");
    const container = document.createElement('div');
    container.classList.add("d-flex", "h-auto", "flex-wrap", "flex-row", "m-auto");
    const graphDiv = document.createElement('div');
    graphDiv.classList.add("w-100","bg-white");
    graphDiv.style.height = "600px"
    container.appendChild(graphDiv);
    column.appendChild(container)
    parentDiv.appendChild(column);

    // graphs.push(container);

    // addClickEvent(statements, container);

    const data = createKnowledgeGraphElements(statements, concepts);
    const graph = new vis.Network(graphDiv, data, networkOptionsKG);

    graph.physics.physicsEnabled = false;
    graph.on("click", graphOnClick);
    discoveryGraph = graph;
}

function showAlert(message) {
    hideLoadingScreen();
    const inputAlert = document.querySelector('#alert-path-concepts');
    inputAlert.classList.toggle('d-none', false);
    inputAlert.innerText = message;
    setTimeout(() => inputAlert.classList.toggle('d-none', true), 5000);
}

function createKnowledgeGraphElements(statements, concepts) {
    const statementEntities = {}

    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();

    // insert node elements only, if they not already exist in the current graph
    function insertNodeElement(entityId, entityType) {
        const color = TYPE_COLOR_MAP[entityType];
        if (entityId in statementEntities)
            return;

        const needHighlight = entityId in concepts;
        const node = { id: entityId, label: entityId, color: color };

        if (needHighlight) {
            node["shape"] = "box";
            node["font"] = { size: 24 }
        }

        nodes.add(node);
        statementEntities[entityId] = entityType;
    }

    statements.forEach(([subjectID, subjectType, predicate, objectID, objectType]) => {
        insertNodeElement(subjectID, subjectType);
        insertNodeElement(objectID, objectType);

        edges.add({
            from: subjectID,
            to: objectID,
            color: '#848484',
            // label: predicate,
            // smooth: { enabled: false },
            // font: { align: 'top'}
        });
    });
    return { nodes: nodes, edges: edges };
}

async function initPatternDiscoveryFromURL(query) {
    switchTab("#search-type-pattern-discovery");
    await searchPatternDiscovery(query);
}

function centerPatternDiscovery() {
    if (!discoveryGraph) {
        return;
    }

    discoveryGraph.fit({
        animation: true
    })
}

async function graphOnClick(e) {
    // check if either a node or an edge is selected
    if (e.edges.length > 0) {
        graphSelectEdge(e);
    }
}

function graphSelectEdge(e) {
    const nodes = discoveryGraph.getConnectedNodes(e.edges[0]);
    // return early if the root node is selected or there are not exactly 2 adjacent nodes
    if ((e.nodes.length >= 1 && e.nodes[0] === 1) || nodes.length !== 2) {
        discoveryGraph.unselectAll();
        return;
    }

    const subject = discoveryGraph.body.nodes[nodes[1]].options.id;
    const object = discoveryGraph.body.nodes[nodes[0]].options.id;

    // open the corresponding query in a new tab
    window.open(`/?query="${subject}"+associated+"${object}"`, '_blank');
    discoveryGraph.unselectAll();
}