const typeColorMap = {
    "Disease": "#aeff9a",
    "Drug": "#ff8181",
    "Species": "#b88cff",
    "Excipient": "#ffcf97",
    "LabMethod": "#9eb8ff",
    "Chemical": "#fff38c",
    "Gene": "#87e7ff",
    "Target": "#1fe7ff",
    "Method": "#7897ff",
    "DosageForm": "#9189ff",
    "Mutation": "#8cffa9",
    "ProteinMutation": "#b9ffcb",
    "DNAMutation": "#4aff78",
    "Variant": "#ffa981",
    "CellLine": "#ce41ff",
    "SNP": "#fd83ca",
    "DomainMotif": "#f383fd",
    "Plant": "#dcfd83",
    "Strain": "#75c4c7",
    "Vaccine": "#c7767d",
    "HealthStatus": "#bbaabb",
    "Organism": "#00bc0f",
    "Tissue": "#dc8cff"
}


var markInstance = null;
var tagsArray = null;
var activeTypeMap = null;
var document_graph = null;
let documentCollection = null;
let papernetwork = null;

function queryGraph(document_id) {
    const query = url_document_graph + "?document=" + document_id + "&data_source=" + documentCollection;
    fetch(query)
        .then(response => response.json())
        .then(data => {
            data.meta = document_id;
            document_graph = data;
            const graphDiv = document.getElementById("paperGraph");
            visualize_document_graph(graphDiv);
        });
}

const emptyGraph = Object();
emptyGraph["nodes"] = [];
emptyGraph["facts"] = [];

function queryAndFilterPaperDetail(document_id, document_collection) {
    documentCollection = document_collection
    async.parallel([
        async.apply(query_highlight, document_id, document_collection)
    ], function (err, result) {
        fillPaperDetail(result[0].results[0]);

        document.getElementById("newsPopup").style.setProperty("display", "flex", "important");
        document.body.style.overflowY = "hidden";
    });

    function query_highlight(document_id, document_collection, callback_document) {
        var query = url_narrative_documents + "?documents=" + document_id + "&data_source=" + document_collection;
        fetch(query)
            .then(response => response.json())
            .then(data => {
                callback_document(null, data);
            });
    }
}

function fillPaperNewTabView(href) {
    const anchor = document.getElementById("paperTab");
    if(anchor) {
        anchor.setAttribute("href", href);
        anchor.setAttribute("target", "_blank");
    }
}

function fillPaperDetail(contentData) {
    // initialize var with default value
    if(documentCollection === null) {
        documentCollection = "PubMed";
    }

    const graphDiv = document.getElementById("paperGraph");
    document_graph = emptyGraph;
    visualize_document_graph(graphDiv);

    const title = document.getElementById("paperTitle");
    const abstract = document.getElementById("paperAbstract");
    const date = document.getElementById("paperDate");
    const author = document.getElementById("paperAuthor");
    const journal = document.getElementById("paperJournal");
    const link = document.getElementById("paperLink");
    title.textContent = contentData.title;
    abstract.textContent = contentData.abstract;
    author.textContent = contentData.metadata.authors;
    journal.textContent = contentData.metadata.journals;

    if (contentData.metadata.publication_month !== 0) {
        date.textContent = contentData.metadata.publication_month + "/" + contentData.metadata.publication_year;
    } else {
        date.textContent = contentData.metadata.publication_year;
    }

    link.href = contentData.metadata.doi;
    link.target = "_blank";

    queryGraph(contentData.id);


    markInstance = new Mark([title, abstract]);
    tagsArray = contentData.tags;
    var typeArray = ["All"];
    for (var j = 0; j < tagsArray.length; j++) {
        if (tagsArray[j].type === "PlantFamily/Genus") {
            tagsArray[j].type = "Plant"
        }
        var startIndex = tagsArray[j].start >= title.textContent.length ? tagsArray[j].start - 1 : tagsArray[j].start;
        markInstance.markRanges([{
            start: startIndex,
            length: tagsArray[j].end - tagsArray[j].start
        }], {
            "element": "a",
            "each": function (e) {
                e.href = markLink(tagsArray[j]);
                if (e.href != "javascript:;") {
                    e.target = "_blank"
                }
                e.style.backgroundColor = typeColorMap[tagsArray[j].type];
            },
        });
        if (!typeArray.includes(tagsArray[j].type)) {
            typeArray.push(tagsArray[j].type);
        }
    }
    initCheckbox(typeArray);

    fillClassifications(contentData["classification"], contentData["id"]);

    const href = `/document/?document_id=${contentData.id}&data_source=${documentCollection}`;
    fillPaperNewTabView(href);
    sendPaperViewLog(contentData.id);
}


function sendPaperViewLog(docID) {
    const request = new Request(
        url_paper_view_log,
        {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify({
                doc_id: docID,
                doc_collection: documentCollection,
            })
        }
    );
    fetch(request).catch(e => console.log(e))
}


function sendPaperClassificationFeedback(documentID, classification, isPositive, containerId) {
    const request = new Request(
        url_document_classification_feedback,
        {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify({
                doc_id: documentID,
                doc_collection: documentCollection,
                classification: classification,
                rating: isPositive,
            })
        }
    );
    fetch(request)
        .then(response => {
            if (response.ok) {
                showInfoAtBottom("Thank you for your Feedback!");
                document.getElementById(containerId).classList.add("feedbackButtonHide");
            } else {
                showInfoAtBottom("Your feedback couldn't be transferred - please try again")
            }
        })
        .catch(e => console.log(e))
}


function fillClassifications(classifications, documentID) {
    const classDiv = document.getElementById('classificationDiv');
    const classInfo = document.getElementById('classificationInfo');

    // paper has no classification data
    if (Object.keys(classifications).length === 0) {
        classInfo.style.display = 'None';
        return;
    }

    //clear previous stored classification data
    classDiv.replaceChildren();

    Object.entries(classifications).forEach(([key, value]) => {
        value = value.replaceAll(';', ', ')
        const classContainer = document.createElement("div");
        const classText = document.createElement("div");
        const classFeedback = document.createElement('div');
        const tags = document.createElement('div');
        const header = document.createElement('div');
        const positive = document.createElement("img");
        const negative = document.createElement("img");

        classContainer.classList.add('classTags');
        classFeedback.classList.add('classFeedback');
        classFeedback.id = "classFeedback" + key;

        header.classList.add('classTagsHeader');
        header.innerText = key + ':';

        tags.innerText = value;

        positive.src = ok_symbol_url;
        positive.classList.add("feedbackButton");
        positive.title = "correct classification";
        positive.onclick = () => sendPaperClassificationFeedback(key, documentID, true, classFeedback.id);

        negative.src = cancel_symbol_url;
        negative.classList.add("feedbackButton");
        negative.title = "wrong classification";
        negative.onclick = () => sendPaperClassificationFeedback(key, documentID, false, classFeedback.id);

        classFeedback.append(positive, negative);
        classText.append(header, tags);
        classContainer.append(classText, classFeedback);
        classDiv.append(classContainer);
    })
    classInfo.style.display = 'Block';
}

function markLink(tags) {
    if (tags.id.substring(0, 4) == "MESH") {
        var meshId = tags.id.substring(5, tags.id.length);
        return "https://meshb.nlm.nih.gov/record/ui?ui=" + meshId;
    } else if (tags.id.substring(0, 6) == "CHEMBL") {
        return "https://www.ebi.ac.uk/chembl/compound_report_card/" + tags.id + "/";
    } else if (tags.type == "Gene") {
        return "https://www.ncbi.nlm.nih.gov/gene/" + tags.id;
    } else if (tags.type == "Species") {
        return "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=" + tags.id;
    } else {
        return "javascript:;";
    }
}

function initCheckbox(typeArray) {
    typeArray.sort(function (a, b) {
        if (a.toUpperCase() < b.toUpperCase()) {
            return -1;
        }
        if (a.toUpperCase() > b.toUpperCase()) {
            return 1;
        }
        return 0;
    });
    const checkBoxDiv = document.getElementById("newsCheckbox");
    while (checkBoxDiv.firstChild) {
        checkBoxDiv.removeChild(checkBoxDiv.lastChild);
    }

    activeTypeMap = new Map();
    for (let item of typeArray) {
        const checkbox = document.createElement("input");
        const label = document.createElement("label");
        const connector = document.createElement("div");
        checkbox.type = "checkbox";
        checkbox.checked = true;
        checkbox.id = item;
        checkbox.name = item;
        if (item == "All") {
            checkbox.addEventListener("click", function () {
                checkboxActionAll();
            });
        } else {
            checkbox.addEventListener("click", function () {
                checkboxAction();
            });
        }
        label.innerHTML = item;
        label.for = item;
        connector.style.backgroundColor = typeColorMap[item];
        connector.append(checkbox);
        connector.append(label);
        checkBoxDiv.append(connector);

        activeTypeMap.set(checkbox.id, checkbox.checked);
    }

    function checkboxActionAll() {
        const checkboxAll = document.getElementById("All");
        var checkboxes = document.getElementById("newsCheckbox").getElementsByTagName("input");
        for (let item of checkboxes) {
            item.checked = checkboxAll.checked;
        }
        checkboxAction();
    }

    function checkboxAction() {
        var checkboxes = document.getElementById("newsCheckbox").getElementsByTagName("input");
        const title = document.getElementById("paperTitle");
        activeTypeMap = new Map();
        for (let item of checkboxes) {
            activeTypeMap.set(item.id, item.checked);
        }
        markInstance.unmark();
        for (var j = 0; j < tagsArray.length; j++) {
            var startIndex = tagsArray[j].start >= title.textContent.length ? tagsArray[j].start - 1 : tagsArray[j].start;
            if (activeTypeMap.get(tagsArray[j].type)) {
                markInstance.markRanges([{
                    start: startIndex,
                    length: tagsArray[j].end - tagsArray[j].start
                }], {
                    "element": "a",
                    "each": function (e) {
                        e.href = markLink(tagsArray[j]);
                        if (e.href != "javascript:;") {
                            e.target = "_blank"
                        }
                        e.style.backgroundColor = typeColorMap[tagsArray[j].type];
                    },
                });

            }
        }
        visualize_document_graph(document.getElementById("paperGraph"));
    }

}

function visualize_document_graph(container) {
    const nodes = document_graph["nodes"];
    const facts = document_graph["facts"];
    const node2id = {};
    const fact2text = {};

    const nodesToCreate = new vis.DataSet();
    const edgesToCreate = new vis.DataSet();

    const maxSliderValue = facts.length;
    const networkSlider = document.getElementById("paperNetworkSlider")
    networkSlider.max = maxSliderValue;
    if (maxSliderValue < 10) {
        networkSlider.value = maxSliderValue;
        document.getElementById("paperNetworkAmount").innerText = `Top ${maxSliderValue}`;
    } else {
        networkSlider.value = "10";
        document.getElementById("paperNetworkAmount").innerText = `Top 10`;
    }

    nodes.forEach((node, id) => {
        let colorLabel = node.slice(node.indexOf("(") + 1, node.indexOf(")"));
        if (colorLabel === "PlantFamily/Genus") {
            colorLabel = "Plant"
        }
        if (!activeTypeMap.get(colorLabel)) {
            return;
        }
        node2id[node] = id;
        const color = typeColorMap[colorLabel];
        nodesToCreate.add({'id': id, 'label': node.slice(0, node.indexOf("(")), 'color': color});
    });

    facts.forEach(fact => {
        const subjectId = node2id[fact['s']];
        const predicate = fact['p'];
        const objectId = node2id[fact['o']];
        edgesToCreate.add({'from': subjectId, 'to': objectId, 'label': predicate});

        const subjectText = fact['s'].slice(0, fact['s'].indexOf("("))
        const objectText = fact['o'].slice(0, fact['o'].indexOf("("))
        fact2text[[subjectText, objectText]] = fact['text'];
        fact2text[[objectText, subjectText]] = fact['text'];
    });

    // create a network
    let options = {
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

    papernetwork = new vis.Network(container, {nodes: nodesToCreate, edges: edgesToCreate}, options);
    papernetwork.on("hoverEdge", (e => {
        const edge = papernetwork.body.edges[e["edge"]];
        const text = fact2text[[edge["from"]["options"]["label"], edge["to"]["options"]["label"]]];
        const title = document.getElementById("paperTitle");
        const abstract = document.getElementById("paperAbstract");
        const documentText = title.textContent + abstract.textContent;

        if (!documentText.includes(text)) {
            return;
        }

        const startPos = documentText.indexOf(text);
        markInstance.markRanges([{
                start: startPos,
                length: text.length,
            }],
            {
                className: "document-highlight",
                element: "A",
                each: (e) => {
                    e.style.backgroundColor = "#fffa88";
                    e.style.textDecoration = "none";
                    e.style.color = "#000"
                }
            }
        );
    }));

    papernetwork.on("blurEdge", (_) => {
        markInstance.unmark({className: "document-highlight"});
    });

    updatePaperNetworkGraph();
    /* this would stop the physics engine once and for all, so dragging only drags one node aswell
    network.on("stabilizationIterationsDone", function () {
        network.setOptions( { physics: false } );
    });
    */
}

function toggleFullscreenNetworkGraph(prefix, closeOnly=false) {
    const networkDiv = document.getElementById(`${prefix}Container`);
    if (!networkDiv)
        return;

    if (document.fullscreenElement?.id !== `${prefix}Container` && !closeOnly) {
        const reqFullscreen = networkDiv.requestFullscreen || networkDiv.webkitRequestFullScreen || networkDiv.msRequestFullScreen;
        reqFullscreen.call(networkDiv)
            .then(() => {
                document.getElementById(`${prefix}Fullscreen`).innerText = "Close";
                currentFullscreenPrefix = prefix;
            })
            .catch((e) => console.log(e));
    } else if (document.fullscreenElement?.id === `${prefix}Container` || closeOnly) {
        const closeFullScreen = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
        closeFullScreen.call(document)
            .catch((e) => {}/* potential TypeError: Not in fullscreen mode */)
            .finally(() => {
                // use finally to close the fullscreen even if the user closed the
                // fullscreen mode by clicking F11 earlier
                document.getElementById(`${prefix}Fullscreen`).innerText = "Fullscreen";
                currentFullscreenPrefix = null;
            });
    }
    setTimeout(centerNetwork, 250, (prefix === "drugNetwork")? network: papernetwork);
}

function centerNetwork(network) {
    network.fit({
        animation: true
    })
}

function updatePaperNetworkGraph() {
    const topK = document.getElementById("paperNetworkSlider").value;
    document.getElementById("paperNetworkAmount").innerText = `Top ${topK}`;

    let usedNodes = new Set();
    document_graph["facts"].slice(0, topK).forEach(fact => {
        usedNodes.add(fact['s']);
        usedNodes.add(fact['o']);
    });

    let filteredNodes = document_graph["nodes"].filter(node => usedNodes.has(node));

    let nodesToCreate = new vis.DataSet([]);
    let node2id = {};
    let id = 1;

    filteredNodes.forEach(node => {
        let colorLabel = node.slice(node.indexOf("(") + 1, node.indexOf(")"));
        if (colorLabel == "PlantFamily/Genus") {
            colorLabel = "Plant";
        }
        if (!activeTypeMap.get(colorLabel)) {
            return;
        }
        node2id[node] = id;
        let color = typeColorMap[colorLabel];
        let nodeData = {'id': id, 'label': node.slice(0, node.indexOf("(")), 'color': color};
        nodesToCreate.add(nodeData);
        id = id + 1;
    });

    let edgesToCreate = new vis.DataSet([]);
    document_graph["facts"].slice(0, topK).forEach(fact => {
        if (node2id[fact['s']] && node2id[fact['o']]) {
            let edgeData = {'from': node2id[fact['s']], 'to': node2id[fact['o']], 'label': fact['p']};
            edgesToCreate.add(edgeData);
        }
    });

    papernetwork.setData({nodes: nodesToCreate, edges: edgesToCreate});
    papernetwork.stabilize(100);
    papernetwork.physics.physicsEnabled = false;
}

function loadGraphTemplate(options) {
    const template = `
        <div class="graphContainer" id="graphContainer">
            <div class="graphNetwork" id="paperGraph"></div>
            <div class="graphFooter">
                <div class="input-group mx-auto mb-auto me-sm-0 w-auto h-fc graphFooter">
                    <span class="input-group-text ml-auto" id="paperNetworkAmount"></span>
                    <div class="input-group-text">
                        <input type="range" class="form-range mx-0 mx-sm-0" id="paperNetworkSlider" min="1" step="1" oninput="updatePaperNetworkGraph()">
                    </div>
                </div>
                <button class="btn btn-secondary" onclick="centerNetwork(papernetwork)">
                    Center
                </button>
                <button class="btn btn-secondary" onclick="toggleFullscreenNetworkGraph('graph')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrows-fullscreen mb-1" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M5.828 10.172a.5.5 0 0 0-.707 0l-4.096 4.096V11.5a.5.5 0 0 0-1 0v3.975a.5.5 0 0 0 .5.5H4.5a.5.5 0 0 0 0-1H1.732l4.096-4.096a.5.5 0 0 0 0-.707zm4.344 0a.5.5 0 0 1 .707 0l4.096 4.096V11.5a.5.5 0 1 1 1 0v3.975a.5.5 0 0 1-.5.5H11.5a.5.5 0 0 1 0-1h2.768l-4.096-4.096a.5.5 0 0 1 0-.707zm0-4.344a.5.5 0 0 0 .707 0l4.096-4.096V4.5a.5.5 0 1 0 1 0V.525a.5.5 0 0 0-.5-.5H11.5a.5.5 0 0 0 0 1h2.768l-4.096 4.096a.5.5 0 0 0 0 .707zm-4.344 0a.5.5 0 0 1-.707 0L1.025 1.732V4.5a.5.5 0 0 1-1 0V.525a.5.5 0 0 1 .5-.5H4.5a.5.5 0 0 1 0 1H1.732l4.096 4.096a.5.5 0 0 1 0 .707z"></path>
                    </svg>
                    <span type="button" id="graphFullscreen">Fullscreen</span>
                </button>
            </div>
        </div>
    `;
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;

    const targetContainer = document.getElementById(options.targetContainer);

    while (tempDiv.firstChild) {
        targetContainer.appendChild(tempDiv.firstChild);
    }
}