let newsData = null;
let network = null;
let networkNodes = null;
let networkEdges = null;
let currentChemblID = null;
let currentDrugName = null;
let scrollUpdateTicking = false;

/**
 * networkData: {
 *  drug: ent_type {String},
 *  target: ent_type {String},
 *  disease: ent_type {String},
 *  phase: {bool}
 * @type {Object}
 */
let networkData = null;

const VISIBLE_ELEMENTS = 50;

/**
 * Generates an overview element and the navbar entry for every object in overviews
 */
function createDynamicOverviews() {
    const overviewEntries = document.getElementById("overview_entries");
    const sidebarEntries = document.getElementById("sidebar_entries");

    overviewEntries.innerHtml = "";
    sidebarEntries.innerHtml = "";

    for (const prefix in overviews) {
        const ov = overviews[prefix];
        const entry =
            `<div class="container border rounded mt-4 bg-dark-grey gx-0 p-1" id="${prefix}Overview">
    <div class="row pb-1 mx-2 gx-5">
        <h5 class="col-xl-6 my-auto fw-bolder gx-2">${ov.name}</h5>
        <div class="col-xl-6 g-0">
            <div class="input-group" id="${prefix}Options">
                <select class="form-select" id="${prefix}Sort" onchange="sortElements('${prefix}')">
                    <option value="rel">Most Relevant</option>
                    <option value="alp">Alphabetical</option>
                </select>
                <input class="form-control" type="text" id="${prefix}Search" placeholder="Filter..."
                       onkeyup="searchElements('${prefix}')">
            </div>
        </div>
    </div>
    <div class="row my-5 align-items-center" id="${prefix}Loading">
        <div class="spinner-border mx-auto my-auto" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    </div>
    <div class="bottom_searchbox mx-2 mb-1 bg-light-grey g-0" id="${prefix}Content"
            onscroll="scrollHandler('${prefix}')"></div>
</div>`;

        const row = //TODO find a way without manipulate name string...
            `<div class="row rounded mt-2 g-0 p-1 d-flex flex-nowrap shadow-sm" onClick="scrollToElement('${prefix}Overview')"
     style="background-color: ${ov.color}">
    <div class="col-8 text-nowrap text-truncate overflow-hidden fs-0-85">
        ${ov.name.split(" (")[0]}
    </div>
    <span class="badge rounded-pill bg-transparent text-dark col-3 w-auto me-auto fs-0-75" id="${prefix}Link"></span>
</div>`;

        overviewEntries.innerHTML += entry;
        sidebarEntries.innerHTML += row;

        // change overview elements if needed
        if (ov.createCallback) {
            ov.createCallback();
        }
    }
}

/**
 * Fetches the paper data from the service and creates the corresponding paper elements.
 * @returns {Promise<void>}
 */
async function loadPaperData(chemblid = currentChemblID, enttype = "Drug") {
    fetch(url_query_document_ids_for_entity + "?entity_id=" + chemblid + "&entity_type=" + enttype + "&data_source=PubMed")
        .then(response => response.json())
        .then(data => {
            if (data.document_ids !== undefined) {
                let meta = null;
                if (data.document_ids.length > 10) {
                    meta = data.document_ids.slice(0, 10);
                } else {
                    meta = data.document_ids;
                }
                if (meta.length > 0) {
                    async.parallel([
                        async.apply(queryHighlight, meta)
                    ], function (err, result) {
                        newsData = result;
                        fillNews(result);
                        doneLoading("news");
                    });
                } else {
                    doneLoading("news");
                }
            }
        })
        .catch((e) => console.log(e));
}

/**
 * Function tries to fetch specified data for each object in overviews list and
 * fills it into the corresponding overview container.
 * @returns {Promise<void>}
 */
async function loadOverviewData() {
    for (let prefix in overviews) {
        const ov = overviews[prefix];

        const url = `${url_query_sub_count}?query=${currentDrugName}+${ov.predicate}+${ov.object}&data_source=PubMed`;
        // use await to request one overview after the other
        const data = await fetch(url)
            .then((response) => {
                return response.json();
            })
            .then((json) => {
                return json["sub_count_list"];
            })
            .catch((e) => {
                console.log(e);
                return null;
            });

        // check if fetch failed to load data
        if (!data) {
            doneLoading(prefix);
            continue;
        }
        // check if the received data is invalid

        const length = data["length"];
        if (length <= 0) {
            doneLoading(prefix);
            continue;
        }
        overviews[prefix].fullData = data;
        overviews[prefix].visibleData = data;
        overviews[prefix].count = data[0].count;

        document.getElementById(prefix + "Link").innerText = length;

        //manipulate data if needed
        if (ov.dataCallback) {
            await ov.dataCallback();
        }

        fillSearchbox(prefix).catch(console.log);
    }
}

/**
 * Event function for scroll events of the entity containers. Only one function call at a time and with a
 * minimum delay of 50ms to reduces the amount of scroll event requests.
 * @param prefix entity container
 */
const scrollHandler = (prefix) => {
    // run only one event call at a time
    if (!scrollUpdateTicking) {
        scrollUpdateTicking = true;
        window.requestAnimationFrame(async () => {
            await scrollUpdateElements(prefix);
            // prevent multiple event calls in a short amount of time
            setTimeout(() => {
                scrollUpdateTicking = false;
            }, 50);
        });
    }
}

/**
 * Scroll the window to the element specified by the parameter 'element_id'.
 * @param element_id
 * @param smooth
 */
function scrollToElement(element_id, smooth = true) {
    const pos = document.getElementById(element_id)
        .getBoundingClientRect().top + window.scrollY;
    window.scrollTo({top: pos, behavior: ((smooth) ? "smooth" : "instant")})
}

/**
 * The function utilizes the service to fetch predefined highlights in the requested
 * papers.
 * @param meta paper data
 * @param callback_document function to call
 */
function queryHighlight(meta, callback_document) {
    var query = url_narrative_documents + "?documents=";
    for (var i = 0; i < meta.length; ++i) {
        query += meta[i] + ";";
    }
    query = query.substring(0, query.length - 1);
    query += "&data_source=PubMed";

    fetch(query)
        .then(response => response.json())
        .then(data => {
            callback_document(null, data);
        });
}

/**
 * Callback for change events in container search inputs. The resulting elements correspond to
 * the input text.
 * @param prefix entity container
 */
function searchElements(prefix) {
    startLoading(prefix);
    document.getElementById(prefix + "Sort").value = "rel";
    const input = document.getElementById(prefix + "Search").value.toUpperCase();
    const data = overviews[prefix].fullData;
    let newData = [];
    if (input === "") {
        newData = overviews[prefix].fullData;
    } else if (input.length === 1) {
        for (let item of data) {
            if (item.name.toUpperCase()[0] === input) {
                newData.push(item);
            }
        }
    } else {
        for (let item of data) {
            if (item.name.toUpperCase().includes(input)) {
                newData.push(item);
            }
        }
    }
    overviews[prefix].visibleData = newData;
    clearSearchBox(prefix);
    fillSearchbox(prefix).catch(console.error);
}

/**
 * Callback for change events in container search inputs. The resulting elements are sorted in
 * order of the corresponding sort-filter.
 * @param prefix entity container
 */
function sortElements(prefix) {
    startLoading(prefix);
    const select = document.getElementById(prefix + "Sort");
    switch (select.value) {
        case "rel":
            overviews[prefix].visibleData.sort(function (a, b) {
                return b.count - a.count;
            });
            break;
        case "alp":
            overviews[prefix].visibleData.sort(function (a, b) {
                if (a.name.toUpperCase() < b.name.toUpperCase()) {
                    return -1;
                }
                if (a.name.toUpperCase() > b.name.toUpperCase()) {
                    return 1;
                }
                return 0;
            });
            break;
        case "pha":
            overviews[prefix].visibleData.sort(function (a, b) {
                return b.max_phase_for_ind - a.max_phase_for_ind;
            });
            break;
    }

    clearSearchBox(prefix);
    fillSearchbox(prefix).catch(console.error);
}

/**
 * The function fills the container of the prefix with the stored data depending on the
 * maximum visible elements.
 * @param prefix entity container
 * @returns {Promise<void>}
 */
async function fillSearchbox(prefix) {
    const searchbox = document.getElementById(prefix + "Content");
    const maxCount = overviews[prefix].count;
    const data = overviews[prefix].visibleData;

    const endIndex = Math.min(overviews[prefix].numVisible, data.length);
    const startIndex = searchbox.children.length

    for (let i = startIndex; i < endIndex; i++) {
        const item = data[i];
        if (item == null) {
            break;
        }

        const itemDiv = document.createElement('div');
        const query = getLinkToQuery(prefix, item);
        const stringQuery = query.split('query=')[1]
            .replaceAll('+', ' ').replaceAll('"', "&quot;");
        let scale = Math.log10(item.count) / Math.log10(maxCount);
        scale = (isNaN(scale)) ? 1 : scale; //scale can be NaN (div by 0) - set it to 1
        const bgColor = colorInterpolation(94, 94, 94, 34, 117, 189, scale);

        const itemTextBody = document.createElement("a");
        itemTextBody.href = query;
        itemTextBody.style.textDecoration = "none";
        itemTextBody.style.color = "inherit";
        itemTextBody.onclick = () => logSubstanceHref(currentDrugName, item.name, stringQuery);
        itemTextBody.target = "_blank";

        const itemText = document.createElement("p");
        itemText.title = "Search in Narrative Service";
        itemText.innerText = item.name;
        itemTextBody.appendChild(itemText);

        const itemCountBody = document.createElement("div");
        itemCountBody.style.backgroundColor = bgColor;
        itemCountBody.classList.add("count");
        itemCountBody.title = `Search in Narrative Service"`;

        const itemCount = document.createElement("a");
        itemCount.href = query;
        itemCount.target = "_blank";
        itemCount.onclick = () => logSubstanceHref(currentDrugName, item.name, stringQuery);
        itemCount.innerText = item.count;
        itemCountBody.appendChild(itemCount);
        itemDiv.appendChild(itemTextBody);
        itemDiv.appendChild(itemCountBody);

        if (item.max_phase_for_ind != null) {
            const phaseImgSrc = (item.max_phase_for_ind >= 0) ? url_chembl_phase + item.max_phase_for_ind + ".svg" : url_chembl_phase_new;
            const phaseBody = document.createElement("a");
            phaseBody.classList.add("phase");
            phaseBody.target = "_blank";
            phaseBody.onclick = () => logChemblPhaseHref(currentDrugName, item.name, item.id, stringQuery, item.max_phase_for_ind);
            phaseBody.title = "Search in clinicaltrials.gov";
            phaseBody.href = `https://clinicaltrials.gov/search?cond=${item.name}&viewType=Table&term=${currentDrugName}`;
            const phaseImg = document.createElement("img");
            phaseImg.src = phaseImgSrc;
            phaseImg.alt = `Phase ${(item.max_phase_for_ind >= 0) ? item.max_phase_for_ind : "unknown"}`
            phaseBody.appendChild(phaseImg);
            itemDiv.appendChild(phaseBody);
        }
        searchbox.append(itemDiv);
    }
    doneLoading(prefix);
}

/**
 * The function returns a concatenated string as an url which leads to the corresponding
 * query of the narrative service.
 * @param prefix entity container
 * @param item entity that corresponds with the current entity
 * @returns {string}
 */
function getLinkToQuery(prefix, item) {
    const subject = currentDrugName.split(' ').join('+');
    const predicate = overviews[prefix].predicate;
    const object = item.name.split("//")[0].split(' ').join('+');

    return `${url_query}?query="${subject}"+${predicate}+"${object}"`;
}

/**
 * Function returns an interpolated value of a color.
 * @param r1
 * @param g1
 * @param b1
 * @param r2
 * @param g2
 * @param b2
 * @param scale
 * @returns {string}
 */
function colorInterpolation(r1, g1, b1, r2, g2, b2, scale) {
    var r = Math.trunc(r1 + (r2 - r1) * scale);
    var g = Math.trunc(g1 + (g2 - g1) * scale);
    var b = Math.trunc(b1 + (b2 - b1) * scale);
    return "rgb(" + r + "," + g + "," + b + ")";
}

/**
 * The function resets the content of the entity container and the maximum visible entities.
 * @param prefix entity container
 */
function clearSearchBox(prefix) {
    overviews[prefix].numVisible = VISIBLE_ELEMENTS;
    const searchbox = document.getElementById(prefix + "Content");
    searchbox.innerHTML = "";
}

/**
 * The function hides the container and shows the loading animation.
 * @param prefix entity container/container
 */
function startLoading(prefix) {
    document.getElementById(prefix + "Content").style.display = "none";
    document.getElementById(prefix + "Loading").style.display = "flex";
}

/**
 * The function shows the container and hides the loading animation.
 * @param prefix
 */
function doneLoading(prefix) {
    document.getElementById(prefix + "Content").style.display = "flex";
    document.getElementById(prefix + "Loading").style.display = "none";
}

/**
 * The function updates the visible elements of an element container after a scroll
 * event got registered.
 * @param prefix entity container
 * @returns {Promise<void>}
 */
async function scrollUpdateElements(prefix) {
    // return if the maximum of items is already visible
    if (overviews[prefix].visibleData.length === overviews[prefix].numVisible) {
        return;
    }

    const content = document.getElementById(prefix + "Content");
    const relativePosition = (content.scrollTop + content.offsetHeight) / content.scrollHeight;

    // check the current scroll position and add additional items if the user
    // scrolled more than (>=) 70% of the containers' height.
    if (relativePosition >= 0.7) {
        const newIdxVisible = overviews[prefix].numVisible + VISIBLE_ELEMENTS;
        const maxIdxVisible = overviews[prefix].visibleData.length;
        overviews[prefix].numVisible = Math.min(newIdxVisible, maxIdxVisible);
        fillSearchbox(prefix).catch(console.error);
    }
}

/**
 * The function creates the paper elements of the last container.
 * @param data paper content, text (abstract) highlighted
 */
function fillNews(data) {
    var newsDiv = document.getElementById("newsContent");
    let i = data[0].results.length;
    if (i > 0) {
        document.getElementById("linkRecentPapers").innerText = i;

        let morePaper = document.getElementById("morePaperRef");
        morePaper.href =
            `https://www.pubpharm.de/vufind/Search/Results?lookfor=${currentDrugName}&type=AllFields`;
        morePaper.style.display = 'block';
    }

    for (--i; i >= 0; i--) {
        if (data[0].results[i].metadata == null) {
            continue;
        }

        const itemDiv = document.createElement('div');
        const itemHeader = document.createElement('h2');
        const itemJournal = document.createElement('p');
        const itemDate = document.createElement('p');

        itemHeader.textContent = data[0].results[i].title;
        itemDiv.append(itemHeader);


        itemJournal.textContent = data[0].results[i].metadata.journals;
        itemJournal.classList.add("journal");
        if (data[0].results[i].metadata.publication_month !== 0) {
            itemDate.textContent = data[0].results[i].metadata.publication_month + "/" + data[0].results[i].metadata.publication_year;
        } else {
            itemDate.textContent = data[0].results[i].metadata.publication_year;
        }
        itemDate.classList.add("date");

        itemDiv.append(itemJournal);
        itemDiv.append(itemDate);


        itemDiv.id = "paper" + i;
        itemDiv.addEventListener("click", function () {
            showDetail(itemDiv.id);
        });

        newsDiv.append(itemDiv);
    }
}

/**
 * Event callback for paper elements of the last container. The paper view gets opened in front
 * of the overview.
 * @param paperid
 */
function showDetail(paperid) {
    var id = parseInt(paperid.substring(5), 10);
    fillPaperDetail(newsData[0].results[id], newsData[0][id]);
    document.getElementById("newsPopup").style.display = "flex";
}

/**
 * Event callback to close the paper view.
 */
function hideDetail() {
    document.getElementById("newsPopup").style.display = "none";
}

/**
 * Send drug-search logging information to backend
 */
function logDrugSearch(drug) {
    const request = new Request(
        url_drug_search,
        {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify({drug: drug})
        }
    );
    fetch(request).catch(e => console.log(e))
}

/**
 * Send substation/interaction-clicked logging information to backend
 */
function logSubstanceHref(drug, substance, query) {
    const request = new Request(
        url_substance_href,
        {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify({
                drug: drug,
                substance: substance,
                query: query
            })
        }
    );
    fetch(request).catch(e => console.log(e))
}

/**
 * The function gets the keywords of the corresponding entity from the service.
 * @returns {Promise<void>}
 */
async function loadWordcloud() {
    const data = await fetch(url_keywords + "?substance_id=" + currentChemblID)
        .then(async (response) => {
            return await response.json().then((data) => {
                return data["keywords"]
            })
        })
        .catch(() => {
            console.log("No keywords for " + currentDrugName + "available.");
            return null;
        });

    const cloud = document.getElementById("wordCloudContent")

    for (const i in data) {
        const keyword = Object.keys(data[i])[0];
        const number = data[i][keyword];

        const element = `<li data-weight="${number}" class="keyword">${keyword}</li>`;
        cloud.innerHTML += element;
    }
    doneLoading("wordCloud");
}

/**
 * The function creates the drug overview network graph with the given options.
 */
function createNetworkGraph() {
    const options = {
        autoResize: true,
        physics: {
            solver: "repulsion",//barnesHut,repulsion,hierarchicalRepulsion,forceAtlas2Based
        },
        interaction: {
            hover: true,
            zoomView: false,
        },
        layout: {
            improvedLayout: true
        },
        groups: {
            indicationNode: {
                color: overviews.adve.color,
                font: {
                    color: "#000",
                    size: 20
                },
                shape: "box"
            },
            targetInteractionNode: {
                color: overviews.targInter.color,
                font: {
                    color: "#000",
                    size: 20
                },
                shape: "box"
            },
            drugAssociationNode: {
                color: overviews.drugAssoc.color,
                font: {
                    color: "#000",
                    size: 20
                },
                shape: "box"
            }
        }
    };

    const networkContainer = document.getElementById("drugNetworkContent");
    network = new vis.Network(networkContainer, {}, options)
    network.on("click", networkOnClick);
    initializeNetworkGraph();
}

function getEntityNameForNetwork(entity_name, entity) {
    const phaseMap = ["?", "0", "I", "II", "III", "IV"];
    if (entity_name.includes("//")) {
        return entity_name.split("//")[1];
    } else if (entity !== null && entity.max_phase_for_ind) {
        return entity_name.concat(` (${phaseMap[entity.max_phase_for_ind + 1]})`);
    } else {
        return entity_name;
    }
}

/**
 * This function initializes the network by creating all possible nodes and the default edges between them.
 * Therefore, the global vis.DataSet list networkNodes and networkEdges get created and filled.
 */
function initializeNetworkGraph() {
    const maxEntities = 20;
    const options = {
        drug: {group: "drugAssociationNode", edgeLen: 200},
        target: {group: "targetInteractionNode", edgeLen: 50},
        disease: {group: "indicationNode", edgeLen: 400},
    };

    networkNodes = new vis.DataSet();
    networkEdges = new vis.DataSet();

    // root node
    let rect = document.getElementById("drugNetworkContent").getBoundingClientRect();
    const currentDrug = currentDrugName[0].toUpperCase() + currentDrugName.slice(1);
    networkNodes.add({
        id: currentDrugName,
        label: getEntityNameForNetwork(currentDrug, null),
        group: options.drug.group,
        x: rect.x / 2, y: rect.y / 2,
        fixed: {x: true, y: true},
        assocEdges: true
    });

    for (const entType in options) {
        const entTypeTl = networkData[entType];
        const entTypeObj = overviews[entTypeTl];

        // skip if no data is available
        if (!entTypeObj || !entTypeObj["fullData"]) {
            continue;
        }

        const endIdx = (entTypeObj.fullData.length < maxEntities) ? entTypeObj.fullData.length : maxEntities;
        for (let i = 0; i < endIdx; ++i) {
            const entity = entTypeObj.fullData[i];

            // prevent same nodes visible twice
            if (networkNodes.get(entity.name) != null) {
                continue;
            }

            let node = {
                id: entity.name,
                idx: i,
                type: entType,
                group: options[entType].group,
                predicate: entTypeObj.predicate,
                assocEdges: false,
                label: getEntityNameForNetwork(entity.name, entity),
            }
            let nodeName = entity.name;
            if (entity.name.includes("//")) {
                let names = entity.name.split('//');
                node.title = names[0];
                node.id = names[1];
                nodeName = names[1];
            }
            networkNodes.add(node);


            networkEdges.add({
                from: nodeName, to: currentDrugName,
                label: `${entity.count}`,
                title: "Search in Narrative Service",
                font: {color: "#000", strokeWidth: 0},
                length: options[entType].edgeLen,
                width: 2.0,
                rootNode: true,
            });
        }
    }
    network.physics.physicsEnabled = false;
    network.setData({nodes: networkNodes, edges: networkEdges});
    updateNetworkGraph();
}

/**
 * The function updates the visibility of each non-adjacent edge based on the state of
 * the checkboxes above the graph and the input slider below.
 */
function updateNetworkGraph() {
    startLoading("drugNetwork");
    const options = {
        disease: document.getElementById("drugNetworkCheckboxDisease").checked,
        target: document.getElementById("drugNetworkCheckboxTarget").checked,
        drug: document.getElementById("drugNetworkCheckboxDrug").checked
    };

    const topK = document.getElementById("drugNetworkSlider").value;
    document.getElementById("drugNetworkAmount").innerText = `Top ${topK}`;

    networkNodes.forEach(function (node) {
        if (!node.type) {
            return;
        }

        if (options[node.type] && node.hidden && node.idx < topK) {
            node.hidden = false;
            node.physics = true;
            networkNodes.update(node);
        } else if ((!options[node.type] || node.idx >= topK) && !node.hidden) {
            node.hidden = true;
            node.physics = false;
            networkNodes.update(node);
        }
    });

    network.stabilize(100);
    network.physics.physicsEnabled = false;
    doneLoading("drugNetwork");
    centerNetwork(network);
}

/**
 * Click event callback for the DTD-network which calls the appropriate function based on
 * the given data in the event object.
 * @param e {object} event
 */
const networkOnClick = async (e) => {
    // check if either a node or an edge is selected
    if (e.nodes.length > 0) {
        await networkSelectNode(e);
    } else if (e.edges.length > 0) {
        networkSelectEdge(e);
    }
}

/**
 * Callback function for the drug overview network nodes. The function shows all adjacent edges
 * to the selected node and hide all others.
 * @param e {object} vis event
 */
const networkSelectNode = async (e) => {
    const nodeId = e.nodes[0];
    const node = networkNodes.get(nodeId);
    if (!node.assocEdges) {
        startLoading("drugNetwork");
        await retrieveAdditionalEdges(node.id, node.type);
        node.assocEdges = true;
        doneLoading("drugNetwork");
    }

    const adjEdges = network.getConnectedEdges(nodeId)
    networkEdges.forEach((edge) => {
        // skip edges adjacent to the root
        if (edge.to === currentDrugName)
            return;
        // is adjacent and directed away from the node
        const visible = adjEdges.includes(edge.id) && (edge.from === nodeId || edge.rootNode);
        if (visible && edge.hidden) {
            edge.hidden = false;
            networkEdges.update(edge);
        } else if (!visible && !edge.hidden) {
            edge.hidden = true;
            networkEdges.update(edge);
        }
    });
    centerNetwork(network);
    network.unselectAll();
}

/**
 * The function retrieves additional edge data for the selected node. Therefore,
 * depending on the type of the node, one or two API-request are made.
 *
 * @param entity {String}
 * @param type {String}
 */
async function retrieveAdditionalEdges(entity, type) {
    const startTime = Date.now()
    let entities = []
    if (type === "drug") {
        let result = await fetch(`${url_query_sub_count}?query=${entity}+interacts+Target&data_source=PubMed`)
            .then((response) => {
                return response.json();
            }).catch((e) => console.log(e));
        entities.push(...result["sub_count_list"]);

        result = await fetch(`${url_query_sub_count}?query=${entity}+associated+Disease&data_source=PubMed`)
            .then((response) => {
                return response.json();
            }).catch((e) => console.log(e));
        entities.push(...result["sub_count_list"]);

    } else { // target or disease
        const predicate = (type === "target") ? "interacts" : "associated"; // TODO use this? then use it above too!
        let result = await fetch(`${url_query_sub_count}?query=Drug+${predicate}+${entity}&data_source=PubMed`)
            .then((response) => {
                return response.json();
            }).catch((e) => console.log(e));
        entities.push(...result["sub_count_list"]);
    }

    for (const i in entities) {
        // is the entity no part of the network or the root
        if (networkNodes.get(entities[i].name) == null
            || entities[i].name === currentDrugName) {
            continue;
        }

        networkEdges.add({
            from: entity, to: entities[i].name,
            label: `${entities[i].count}`,
            title: `${entities[i].count}`,
            font: {color: "#000000", strokeWidth: 0},
            color: {color: "#565656", opacity: 0.6},
            width: 1.5,
            physics: false,
            smooth: {enabled: false},
        });
    }
    console.log("Elapsed time:", Date.now() - startTime, "ms")
}

/**
 * Callback function for the drug overview network edges. The function opens a new tab which shows the
 * corresponding query of the edge.
 * @param e event
 */
const networkSelectEdge = (e) => {
    const nodes = network.getConnectedNodes(e.edges[0]);
    // return early if the root node is selected or there are not exactly 2 adjacent nodes
    if ((e.nodes.length >= 1 && e.nodes[0] === 1) || nodes.length !== 2) {
        network.unselectAll();
        return;
    }

    const subject = network.body.nodes[nodes[1]].options.id;
    const predicate = network.body.nodes[nodes[0]].options.predicate;
    const object = network.body.nodes[nodes[0]].options.id;

    // open the corresponding query in a new tab
    window.open(`/?query="${subject}"+${predicate}+"${object}"`, '_blank');
    network.unselectAll();
}
