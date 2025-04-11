let networkOptionsKG = {
    autoResize: true,
    interaction: {
        hover: true,
        zoomView: true,
        dragView: true,
        dragNodes: true
    },
    physics: {
            solver: "barnesHut",//barnesHut,repulsion,hierarchicalRepulsion,forceAtlas2Based
    },
    // physics: {
    //     solver: "forceAtlas2Based",
    //     forceAtlas2Based: {
    //         springLength: 125,
    //         avoidOverlap: 1
    //     }
    // },
    // groups: {
    //     default_ge: {
    //         color: {
    //             background: "white",
    //             hover: {
    //                 background: "white"
    //             },
    //             highlight: {
    //                 background: "white"
    //             }
    //         }
    //     }
    // }
};


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
function addPatternDiscoveryConcept() {
    const keywordList = document.querySelector("#path-concept-list");
    const keywordInput = document.querySelector('#input-path-concepts');
    const keywordId = "keyword-tag-" + keywordInput.value.trim().toLowerCase().replace(" ", "-");

    // add keywords only once
    if (Array.from(keywordList.childNodes).some((k) => k.id === keywordId)) {
        keywordInput.value = "";
        return;
    }

    // Don't add the empty keywod
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

async function searchPatternDiscovery() {
    const queryGraphContainer = document.querySelector('#container-div-path-concepts');
    const conceptDiv = document.querySelector("#path-concept-list");
    const conceptInput = document.querySelector("#input-path-concepts");
    const concepts = [];
    if (conceptInput.value.trim() !== "")
        concepts.push(conceptInput.value);

    // Substring because the tailing X should be removed (X do remove the keyword)
    concepts.push(...Array.from(conceptDiv.childNodes).map((n) =>
        n.innerText.substring(0, n.innerText.length - 1).replace('\n', '').trim()));

    const conceptString = concepts.join("_AND_")
    if (conceptString === "") {
        showAlert("Empty input. Provide keywords to search!");
        return;
    }

    queryGraphContainer.classList.toggle('d-none', true);
    showLoadingScreen();

    const queryGraphDiv = document.querySelector('#graph-div-path-concepts');
    queryGraphDiv.innerHTML = "";
    document.getElementById('div_documents').innerText = '';

    await fetch(`${url_pattern_discovery}?concepts=${conceptString}`)
        .then((response) => {
            if (response.ok)
                return response.json();
            else {
                return response.json().then((d) => {
                    return Promise.reject(d["reason"]);
                })
            }
        })
        .then((data) => {
            createKnowledgeGraph(data["graph"], data["concepts"], queryGraphDiv);
            queryGraphContainer.classList.toggle("d-none", false);

            let divDocuments = $('#div_documents');
            divDocuments.empty();
            divDocuments.append(createResultList(data["results"], 0));
        })
        .catch((e) => {
            showAlert(e);
        })
        .finally(() => {
            hideLoadingScreen();
        });
}

function createKnowledgeGraph(statements, concepts, parentDiv) {
    const column = document.createElement('div');
    column.classList.add("col-12");
    const container = document.createElement('div');
    container.classList.add("btn", "rounded", "border", "d-flex", "h-auto", "flex-wrap", "flex-row", "m-auto");
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