let newsData = null;
let network = null;
let scrollUpdateTicking = false;
const VISIBLE_ELEMENTS = 50;

const COVID_ENTITY = "Covid 19";
const COVID_ENTITY_ID = "MESH:D000086382";

/**
 * Data structure of all overviews
 * prefix: {name, predicate, object, data, count, color, ...}
 *
 * fullData: fetched entity data
 * visibleData: subset of fullData, changed if container search is used
 *
 * createCallback: gets called after creating the overview to change it
 * dataCallback: gets called before data insertion to change the dataset
 */
const overviews = {
    adve: {
        name: "Associated Symptoms/Diseases",
        predicate: "associated",
        object: "Disease",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Disease"]
    },
    indi: {
        name: "Drug Therapies",
        predicate: "treats",
        object: "Drug",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Drug"]
    },
    targInter: {
        name: "Target Associations",
        predicate: "associated",
        object: "Target",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Gene"]
    },
    labMeth: {
        name: "Lab Methods",
        predicate: "method",
        object: "LabMethod",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["LabMethod"]
    },
    species: {
        name: "Species",
        predicate: "associated",
        object: "?X(Species)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Species"]
    },
    drugAssoc: {
        name: "Drug Associations",
        predicate: "associated",
        object: "?X(Drug)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Drug"]
    }
}

buildSite().catch((err) => console.log(err));

function searchDrug() {
    var keyword = document.getElementById('drugInput').value;
    if (keyword == "") {
        return;
    }
    window.location.search = "?drug=" + keyword;
}

function resetContainerLoading(keyword = null) {
    for (const key in overviews) {
        doneLoading(key)
    }
    doneLoading("drugNetwork");
    doneLoading("wordCloud")
    doneLoading("news");
    document.getElementById("structure").hidden = true;
    let text = document.getElementById("unknown_drug_name_tag");
    text.style.setProperty("display", "flex", "important");

    if (keyword === null) {
        text.innerText = `Unknown term`;
        return;
    }
    text.innerText = `Drug '${keyword}' is unknown`;
}

async function buildSite() {
    createDynamicOverviews();
    logDrugSearch("Covid 19 Overview");
    fetch(url_query_document_ids_for_entity + "?entity_id=MESH:C000711409&entity_type=Disease&data_source=PubMed")
        .then(response => response.json())
        .then(data => {
            //console.log(data)
            if (data.document_ids !== undefined) {
                if (data.document_ids.length > 10) {
                    var meta = data.document_ids.slice(0, 10);
                } else {
                    var meta = data.document_ids;
                }
                if (meta.length > 0) {
                    async.parallel([
                        async.apply(query_highlight, meta)
                    ], function (err, result) {
                        newsData = result;
                        fillNews(newsData);
                        doneLoading("news");
                    });
                } else {
                    doneLoading("news");
                }
            }
        });

    await load_wordcloud();
    //fill the container with fetched tags
    await getOverviewData()
        //calculate the network graph after all overviews are filled
        .then(() => createNetworkGraph());


}

/**
 * Function tries to fetch specified data for each object in overviews list and
 * fills it into the corresponding overview container.
 * @returns {Promise<void>}
 */
async function getOverviewData() {
    for (let prefix in overviews) {
        const ov = overviews[prefix];

        const url = `${url_query_sub_count}?query=${COVID_ENTITY}+${ov.predicate}+${ov.object}&data_source=PubMed`;
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

        fillSearchbox(prefix);
    }
}

/**
 * Generates overview element and the navbar entry for every object in overviews
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

function query_highlight(meta, callback_document) {
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


function searchElements(reference) {
    startLoading(reference);
    document.getElementById(reference + "Sort").value = "rel";
    const input = document.getElementById(reference + "Search").value.toUpperCase();
    const data = overviews[reference].fullData;
    let newData = [];
    if (input === "") {
        newData = overviews[reference].fullData;
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
    overviews[reference].visibleData = newData;
    clearSearchBox(reference);
    fillSearchbox(reference);
}


function sortElements(reference) {
    startLoading(reference);
    const select = document.getElementById(reference + "Sort");
    switch (select.value) {
        case "rel":
            overviews[reference].visibleData.sort(function (a, b) {
                return b.count - a.count;
            });
            break;
        case "alp":
            overviews[reference].visibleData.sort(function (a, b) {
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
            overviews[reference].visibleData.sort(function (a, b) {
                return b.max_phase_for_ind - a.max_phase_for_ind;
            });
            break;
    }

    clearSearchBox(reference);
    fillSearchbox(reference);
}


async function fillSearchbox(prefix) {
    const searchbox = document.getElementById(prefix + "Content");
    const maxCount = overviews[prefix].count;
    const data = overviews[prefix].visibleData;

    const maxLen = (overviews[prefix].numVisible > data.length) ? data.length : overviews[prefix].numVisible;

    for (let i = overviews[prefix].numVisible - VISIBLE_ELEMENTS; i < maxLen; i++) {
        const item = data[i];
        if (item == null) {
            break;
        }

        const itemDiv = document.createElement('div');
        const query = getLinkToQuery(prefix, item);
        const stringQuery = query.split('query=')[1].replaceAll('+', ' ').replaceAll('"', "&quot;");
        let scale = Math.log10(item.count) / Math.log10(maxCount);
        scale = (isNaN(scale)) ? 1 : scale; //scale can be NaN (div by 0) - set it to 1
        const bgColor = colorInterpolation(94, 94, 94, 34, 117, 189, scale);

        const element =
            `<a href=${query} style="text-decoration: none; color: inherit;" onclick="logSubstanceHref('${COVID_ENTITY}','${item.name}','${stringQuery}')" target="_blank">
                <p>${item.name}</p>
            </a>
            <div style="background-color: ${bgColor};" class="count">
                <a href=${query} target="_blank" onclick="logSubstanceHref('${COVID_ENTITY}','${item.name}','${stringQuery}')">${item.count}</a>
            </div>`;


        itemDiv.innerHTML = element;
        searchbox.append(itemDiv);
    }
    // console.log(overviews[prefix].numVisible, "items added to", prefix)
    doneLoading(prefix);
}

function getLinkToQuery(reference, item) {
    const subject = COVID_ENTITY.split(' ').join('+');
    const predicate = overviews[reference].predicate;
    const object = item.name.split("//")[0].split(' ').join('+');

    return `${url_query}?query="${subject}"+${predicate}+"${object}"`;
}

function clearSearchBox(reference) {
    overviews[reference].numVisible = VISIBLE_ELEMENTS;
    const searchbox = document.getElementById(reference + "Content");
    searchbox.innerHTML = "";
}

function startLoading(reference) {
    document.getElementById(reference + "Content").style.display = "none";
    document.getElementById(reference + "Loading").style.display = "flex";
}

function doneLoading(reference) {
    document.getElementById(reference + "Content").style.display = "flex";
    document.getElementById(reference + "Loading").style.display = "none";
}

async function scrollUpdateElements(prefix) {
    // return if the maximum of items is already visible
    if (overviews[prefix].visibleData.length === overviews[prefix].numVisible) {
        return;
    }

    const content = document.getElementById(prefix + "Content");
    const posRel = (content.scrollTop + content.offsetHeight) / content.scrollHeight * 100;

    // add
    if (posRel >= 70) {
        const newEndIdx = overviews[prefix].numVisible + VISIBLE_ELEMENTS;
        const dataLen = overviews[prefix].visibleData.length;

        if (dataLen >= newEndIdx) {
            overviews[prefix].numVisible = overviews[prefix].numVisible + VISIBLE_ELEMENTS;
        } else {
            overviews[prefix].numVisible = dataLen;
        }
        await fillSearchbox(prefix);
    }
}

function fillNews(data) {
    var newsDiv = document.getElementById("newsContent");

    let i = data[0].results.length;
    if (i > 0) {
        document.getElementById("linkRecentPapers").innerText = i;

        let morePaper = document.getElementById("morePaperRef");
        morePaper.href =
            `https://www.pubpharm.de/vufind/Search/Results?lookfor=${COVID_ENTITY}&type=AllFields`;
        morePaper.style.display = 'block';
    }

    for (--i; i >= 0; i--) {
        const itemDiv = document.createElement('div');
        const itemHeader = document.createElement('h2');
        const itemJournal = document.createElement('p');
        const itemDate = document.createElement('p');

        itemHeader.textContent = data[0].results[i].title;
        itemJournal.textContent = data[0].results[i].metadata.journals;
        itemJournal.classList.add("journal");
        if (data[0].results[i].metadata.publication_month !== 0) {
            itemDate.textContent = data[0].results[i].metadata.publication_month + "/" + data[0].results[i].metadata.publication_year;
        } else {
            itemDate.textContent = data[0].results[i].metadata.publication_year;
        }
        itemDate.classList.add("date");
        itemDiv.append(itemHeader);
        itemDiv.append(itemJournal);
        itemDiv.append(itemDate);
        itemDiv.id = "paper" + i;
        itemDiv.addEventListener("click", function () {
            showDetail(itemDiv.id);
        });

        newsDiv.append(itemDiv);
    }
}

function showDetail(paperid) {
    var id = parseInt(paperid.substring(5), 10);
    fillPaperDetail(newsData[0].results[id], newsData[0][id]);
    document.getElementById("newsPopup").style.display = "flex";
}

function hideDetail() {
    document.getElementById("newsPopup").style.display = "none";
}

function colorInterpolation(r1, g1, b1, r2, g2, b2, scale) {
    var r = Math.trunc(r1 + (r2 - r1) * scale);
    var g = Math.trunc(g1 + (g2 - g1) * scale);
    var b = Math.trunc(b1 + (b2 - b1) * scale);
    return "rgb(" + r + "," + g + "," + b + ")";
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


async function load_wordcloud() {
    const data = await fetch(url_keywords + "?substance_id=" + COVID_ENTITY_ID)
        .then(async (response) => {
            return await response.json().then((data) => {
                return data["keywords"]
            })
        })
        .catch(() => {
            console.log("No keywords for " + COVID_ENTITY_ID + "available.");
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
    network.on("selectEdge", (e) => networkSelectEdgeCallback(e, network));
    updateNetworkGraph(true);
}

function updateNetworkGraph(firstInit = false) {
    if (!firstInit) {
        startLoading("drugNetwork");
        network.physics.physicsEnabled = true;
    }

    const topK = document.getElementById("drugNetworkSlider").value;
    const drawDiseases = document.getElementById("drugNetworkCheckboxDisease").checked;
    const drawTargets = document.getElementById("drugNetworkCheckboxTarget").checked;
    const drawDrugs = document.getElementById("drugNetworkCheckboxDrug").checked;

    document.getElementById("drugNetworkAmount").innerText = `Top ${topK}`;


    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();
    let idx = 2;

    // root node
    nodes.add({id: 1, label: COVID_ENTITY, group: "drugAssociationNode"})

    if (drawDiseases) {
        // disease treatments (first 10 elements)
        overviews.adve.fullData.slice(0, topK).forEach((dis) => {
            nodes.add({
                id: idx,
                label: `${dis.name}`,
                object: dis.name,
                group: "indicationNode",
                predicate: overviews.adve.predicate
            });
            edges.add({
                from: idx, to: 1,
                label: `${dis.count}`,
                title: `${dis.count}`,
                font: {color: "#000", strokeWidth: 0},
                length: 500
            });
            ++idx;
        });
    }
    if (drawTargets) {
        // target interactions (first 10 elements)
        overviews.targInter.fullData.slice(0, topK).forEach((target) => {
            const names = target.name.split("//");

            nodes.add({
                id: idx,
                label: (names.length > 1) ? names[1] : names[0],
                title: (names.length > 1) ? names[0] : false,
                object: (names.length > 1) ? names[1] : names[0],
                group: "targetInteractionNode",
                predicate: overviews.targInter.predicate
            });
            edges.add({
                from: idx, to: 1,
                label: `${target.count}`,
                title: `${target.count}`,
                font: {color: "#000", strokeWidth: 0},
                length: 250
            });
            ++idx;
        });
    }

    if (drawDrugs) {
        // associated drugs (first 10 elements)
        overviews.drugAssoc.fullData.slice(0, topK).forEach((drug) => {
            nodes.add({
                id: idx,
                label: drug.name,
                object: drug.name,
                group: "drugAssociationNode",
                predicate: overviews.drugAssoc.predicate
            });
            edges.add({
                from: idx, to: 1,
                label: `${drug.count}`,
                title: `${drug.count}`,
                font: {color: "#000", strokeWidth: 0},
                length: 375
            });
            ++idx;
        });
    }

    network.setData({nodes: nodes, edges: edges});
    doneLoading("drugNetwork");
    network.physics.physicsEnabled = false;
}

const networkSelectEdgeCallback = (e, network) => {
    // return early if the root node is selected
    if (e.nodes.length >= 1 && e.nodes[0] === 1) {
        network.unselectAll();
        return;
    }

    // retrieve the adjacent nodes (have to be 2)
    const nodes = network.getConnectedNodes(e.edges[0]);
    if (nodes.length !== 2) {
        network.unselectAll();
        return;
    }

    const idx = nodes[0];
    const object = network.body.nodes[idx].options.object;
    const predicate = network.body.nodes[idx].options.predicate;

    // open the corresponding query in a new tab
    window.open(`/?query="${COVID_ENTITY}"+${predicate}+"${object}"`, '_blank');
    network.unselectAll();
}
