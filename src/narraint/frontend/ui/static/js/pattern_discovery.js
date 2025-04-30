let networkOptionsKG = {
    autoResize: true,
    interaction: {
        hover: true,
        zoomView: true,
        dragView: true,
        dragNodes: true
    },
    layout: {
        improvedLayout: true
    },
    physics: {
        solver: "barnesHut",
        barnesHut: {
            gravitationalConstant: -3000,
            centralGravity: 0.0,
            springLength: 140,
            springConstant: 0.03,
            damping: 0.70,
            avoidOverlap: 0.3
        },
    },
};

/**
 * vis.network()
 * @type {undefined}
 */
let discoveryGraph = undefined;

/**
 * vis.network nodes and edges
 * @type {undefined}
 */
let discoveryGraphNodes = undefined;
let discoveryGraphEdges = undefined;


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
    const queryGraphDiv = document.querySelector('#graph-div-path-concepts');
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

    logInputParameters(parameters);
    updateURLParameters(parameters);

    // show loading visuals
    queryGraphContainer.classList.toggle('d-none', true);
    document.getElementById("checkbox-path-concepts").classList.toggle("d-none", true);
    showLoadingScreen();

    // remove old visuals
    queryGraphDiv.innerHTML = "";
    divDocuments.empty();

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
        .catch((e) => showAlert(e));

    // return early if the response failed
    if (!data) {
        hideLoadingScreen();
        return;
    }

    latest_valid_query = parameters["query"];

    sortStrategyUpdate(false);
    sortStrategySet(data["sort_by"]);
    sortOrderSet(data["sort_order"]);

    // update invalid strategies (from URL)
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

    // create and show knowledge graph
    createKnowledgeGraph(data["graph"], queryGraphDiv);
    queryGraphContainer.classList.toggle("d-none", false);

    // create and show documents
    const documentResults = createResultList(data["results"], 0);
    divDocuments.append(documentResults);
    hideLoadingScreen();
}

function createKnowledgeGraph(concept2statements, parentDiv) {
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

    createKnowledgeGraphElements(concept2statements);
    discoveryGraph = new vis.Network(graphDiv, {}, networkOptionsKG);
    discoveryGraph.physics.physicsEnabled = false;
    discoveryGraph.on("click", graphOnClick);
    discoveryGraph.setData({nodes: discoveryGraphNodes, edges: discoveryGraphEdges})
    updateKnowledgeGraph();
}

function updateKnowledgeGraph() {
    const topK = document.getElementById("path-concepts-slider").value;
    document.getElementById("path-concepts-num-edges").innerText = `Top ${topK}`;
    const selectedEntityTypes = getSelectedEntityTypes();
    console.log(selectedEntityTypes);

    discoveryGraph.physics.physicsEnabled = true;
    discoveryGraphNodes.forEach((node) => {
        if (node.index === 0)
            return;
        const nodeTypeSelected = selectedEntityTypes.includes(node.entityType);
        if (node.hidden && node.index < topK && nodeTypeSelected) {
            // show node
            node.hidden = false;
            node.physics = true;
            discoveryGraphNodes.update(node);
        } else if ((!nodeTypeSelected || node.index >= topK) && !node.hidden) {
            // hide node
            node.hidden = true;
            node.physics = false;
            discoveryGraphNodes.update(node);
        }
    });

    discoveryGraph.stabilize(100);
    discoveryGraph.physics.physicsEnabled = false;
    centerPatternDiscovery();
}

function showAlert(message) {
    hideLoadingScreen();
    const inputAlert = document.querySelector('#alert-path-concepts');
    inputAlert.classList.toggle('d-none', false);
    inputAlert.innerText = message;
    setTimeout(() => inputAlert.classList.toggle('d-none', true), 5000);
}

function createEntityTypeButton(entityType) {
    const container = document.getElementById("checkbox-path-concepts");
    const div = document.createElement("div")
    const label = document.createElement("label");
    const input = document.createElement("input");
    const inputId = "checkboxType" + entityType;

    div.style.backgroundColor = TYPE_COLOR_MAP[entityType];
    div.classList.add("d-flex", "rounded", "p-1", "mx-2", "my-1", "align-items-center");

    input.id = inputId;
    input.checked = true;
    input.onchange = updateKnowledgeGraph;
    input.type = "checkbox";
    input.entityType = entityType;
    input.classList.add("mx-1", "form-check-input-wrap")

    label.innerText = entityType;
    label.htmlFor = inputId;

    div.append(input, label);
    container.append(div);
}

function getSelectedEntityTypes() {
    const container = document.getElementById("checkbox-path-concepts");
    const selectedEntityTypes = [];
    for (const child of container.childNodes) {
        if (child.firstChild.checked) {
            selectedEntityTypes.push(child.firstChild.entityType)
        }
    }
    return selectedEntityTypes;
}

function createKnowledgeGraphElements(concept2statements) {
    document.getElementById("checkbox-path-concepts").innerHTML = "";
    document.getElementById("checkbox-path-concepts").classList.toggle("d-none", false);

    const knownEntityTypes = [];
    let index = 1;
    discoveryGraphNodes = new vis.DataSet();
    discoveryGraphEdges = new vis.DataSet();

    function insertNodeElement(entityName, entityType) {
        const color = TYPE_COLOR_MAP[entityType];

        // some entities have two names, just take the right side
        if (entityName.includes("//")) {
            entityName = entityName.split("//", 1)[1];
        }

        // insert node elements only, if they not already exist in the current graph
        if (discoveryGraphNodes.get(entityName) != null) {
            return;
        }

        if (!knownEntityTypes.includes(entityType)) {
            createEntityTypeButton(entityType);
        }

        const node = { id: entityName, label: entityName, color: color, entityType: entityType };

        // highlight concept nodes and set index 0
        if (entityName in concept2statements) {
            node["shape"] = "box";
            node["font"] = { size: 24 }
            node["index"] = 0;
        } else {
            node["index"] = index;
            index++;
        }
        discoveryGraphNodes.add(node);
        knownEntityTypes.push(entityType);
    }

    for (const [_, statement] of Object.entries(concept2statements)) {
        for (const [subjectName, subjectType, objectName, objectType] of statement) {
            insertNodeElement(subjectName, subjectType);
            insertNodeElement(objectName, objectType);
            discoveryGraphEdges.add({
                from: subjectName,
                to: objectName,
                color: '#848484',
            });
        }
        index = 1;
    }
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