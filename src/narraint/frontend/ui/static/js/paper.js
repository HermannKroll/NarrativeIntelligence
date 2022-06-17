const typeColorMap = {
    "Disease": "#aeff9a",
    "Drug": "#ff8181",
    "Species": "#b88cff",
    "Excipient": "#ffcf97",
    "LabMethod": "#9eb8ff",
    "Chemical": "#fff38c",
    "Gene": "#87e7ff",
    "Method": "#7897ff",
    "DosageForm": "#9189ff",
    "Mutation": "#8cffa9",
    "ProteinMutation": "#b9ffcb",
    "DNAMutation": "#4aff78",
    "Variant": "#ffa981",
    "CellLine": "#729e64",
    "SNP": "#fd83ca",
    "DomainMotif": "#f383fd",
    "Plant": "#dcfd83",
    "Strain": "#75c4c7",
    "Vaccine": "#c7767d"
}


var markInstance = null;
var tagsArray = null;
var activeTypeMap = null;
var document_graph = null;

function queryGraph(document_id) {
    var query = url_document_graph + "?document=" + document_id + "&data_source=PubMed"; // real shit
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
    async.parallel([
        async.apply(query_highlight, document_id, document_collection)
    ], function (err, result) {
        console.log(result)
        fillPaperDetail(result[0].results[0]);

        document.getElementById("newsPopup").style.display = "flex";
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

    fillClassifications(contentData.classification);

    const href = `/document/?document_id=${contentData.id}&data_source=PubMed`;
    fillPaperNewTabView(href);
}

function fillClassifications(classifications) {
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
        value = value.replaceAll(' ', '').replaceAll(';', ', ')
        const classBox = document.createElement("div");
        const tags = document.createElement('div');
        const header = document.createElement('div');
        classBox.classList.add('classTags');
        header.classList.add('classTagsHeader');
        header.innerText = key + ':';
        tags.innerText = value;

        classBox.append(header, tags);
        classDiv.append(classBox);
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
    let nodes = document_graph["nodes"];
    let node2id = {};
    let id = 1;
    let nodesToCreate = new vis.DataSet([]);
    nodes.forEach(node => {
        let colorLabel = node.slice(node.indexOf("(") + 1, node.indexOf(")"));
        if (colorLabel == "PlantFamily/Genus") {
            colorLabel = "Plant"
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
    document_graph["facts"].forEach(fact => {
        let subject = node2id[fact['s']];
        let predicate = fact['p'];
        let object = node2id[fact['o']];
        let edgeData = {'from': subject, 'to': object, 'label': predicate};
        //console.log(edgeData);
        edgesToCreate.add(edgeData);
    });

    // create a netwok
    // provide the data in the vis format
    var data = {
        nodes: nodesToCreate,
        edges: edgesToCreate
    };
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

    // initialize your network!
    var network = new vis.Network(container, data, options);
    /* this would stop the physics engine once and for all, so dragging only drags one node aswell
    network.on("stabilizationIterationsDone", function () {
        network.setOptions( { physics: false } );
    });
    */
}

