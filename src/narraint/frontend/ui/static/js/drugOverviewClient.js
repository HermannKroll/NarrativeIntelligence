let newsData = null;

let currentChemblID = null;
let currentDrugName = null;

/**
 * Data structure of all overviews
 * prefix: {name, predicate, object, data, count, color, ...}
 *
 * createCallback: gets called after creating the overview to change it
 * dataCallback: gets called before data insertion to change the dataset
 */
const overviews = {
    indi: {name: "Indications (Study Phase via ChEMBL)", predicate: "treats", object: "Disease", data: [], count: 0, color: "#aeff9a", createCallback: indiCreateCallback, dataCallback: indiDataCallback},
    admin: {name: "Administration", predicate: "administered", object: "DosageForm", data: [], count: 0, color: "#9189ff"},
    targInter: {name: "Target Interactions", predicate: "interacts", object: "Target", data: [], count: 0, color: "#b88cff"},
    labMeth: {name: "Lab Methods", predicate: "method", object: "LabMethod", data: [], count: 0, color: "#9eb8ff"},
    species: {name: "Species", predicate: "associated", object: "?X(Species)", data: [], count: 0, color: "#b88cff"},
    drugInter: {name: "Drug Interactions", predicate: "interacts", object: "Drug", data: [], count: 0, color: "#ff8181"},
    adve: {name: "Adverse Effects (Beta)", predicate: "induces", object: "Disease", data: [], count: 0, color: "#aeff9a", createCallback: adveCreateCallback, dataCallback: adveDataCallback},
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
    doneLoading("admin");
    doneLoading("adve");
    doneLoading("targInter");
    doneLoading("drugInter");
    doneLoading("labMeth");
    doneLoading("indi");
    doneLoading("news");
    document.getElementById("structure").hidden = true;
    let text = document.getElementById("unknown_drug_name_tag");
    text.style.display = "flex";

    if(keyword === null) {
        text.innerText = `Unknown term`;
        return;
    }
    text.innerText = `Drug '${keyword}' is unknown`;
}

async function buildSite() {
    var search = window.location.search;
    if (search === "") {
        // redirect to drug_overview_index page
        window.location = url_drug_overview_idx;
        return;
    }

    createDynamicOverviews();

    var keyword = search.split("=")[1];
    document.getElementById('drugInput').value = decodeURI(keyword);

    // translate the key to a drug id via the narrative service
    fetch(url_term_2_entity + '?expand_by_prefix=false&term=' + keyword)
        .then(response => response.json())
        .then(async data => {
            currentChemblID = null;
            currentDrugName = null;
            if (data.valid === false) {
                resetContainerLoading(keyword);
                return;
            }
            let chemblid = "";
            let entities = data["entity"];
            entities.forEach(entity => {
                if (entity.entity_type === 'Drug') {
                    // select smallest chembl id (best match, oldest entry)
                    if (chemblid === "" || entity.entity_id.length < chemblid.length ||
                        (entity.entity_id < chemblid && entity.entity_id.length === chemblid.length)) {
                        chemblid = entity.entity_id;
                    }
                }
            });

            if(chemblid === "") {
                resetContainerLoading();
                return;
            }

            logDrugSearch(keyword)

            currentDrugName = keyword;
            currentChemblID = chemblid;
            console.log("Translated Chembl id: " + chemblid)

            fetch(url_query_document_ids_for_entity + "?entity_id=" + chemblid + "&entity_type=Drug&data_source=PubMed")
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


            //fill in the image via id using fetch to catch potential errors
            const structureImage = document.getElementById('structure');
            fetch(`https://www.ebi.ac.uk/chembl/api/data/image/${chemblid}`)
                .then((response) => {
                    if (response.ok) {
                        response.blob().then((blob) => {
                            structureImage.src = URL.createObjectURL(blob);
                        }).catch();
                    } else {
                        return Promise.reject(); /* no img available */
                    }
                }).catch(() => structureImage.hidden = true);

            //get drug information via id
            fetch('https://www.ebi.ac.uk/chembl/api/data/drug/' + chemblid + '.json')
                .then(response => response.json())
                .then(data2 => {
                    document.getElementById('formular').innerText = data2.molecule_properties.full_molformula;
                    document.getElementById('mass').innerText = data2.molecule_properties.full_mwt;
                    //synonym seems to be correct
                    document.getElementById('name').innerText = data2.synonyms[0].split(" ")[0];

                    if (data2.molecule_properties.alogp) {
                        document.getElementById('drug_alogp').innerText = data2.molecule_properties.alogp;
                    } else {
                        document.getElementById('drug_alogp').innerText = "-";
                    }

                    if (data2.molecule_properties.cx_logp) {
                        document.getElementById('drug_cxlogp').innerText = data2.molecule_properties.cx_logp;
                    } else {
                        document.getElementById('drug_cxlogp').innerText = "-";
                    }

                    if (data2.molecule_properties.cx_most_apka) {
                        document.getElementById('drug_cx_acid_pka').innerText = data2.molecule_properties.cx_most_apka;
                    } else {
                        document.getElementById('drug_cx_acid_pka').innerText = "-";
                    }

                    if (data2.molecule_properties.cx_most_bpka) {
                        document.getElementById('drug_cx_basic_pka').innerText = data2.molecule_properties.cx_most_bpka;
                    } else {
                        document.getElementById('drug_cx_basic_pka').innerText = "-";
                    }

                    if (data2.molecule_properties.cx_logd) {
                        document.getElementById('drug_cx_logd').innerText = data2.molecule_properties.cx_logd;
                    } else {
                        document.getElementById('drug_cx_logd').innerText = "-";
                    }

                    let chembl_link = "https://www.ebi.ac.uk/chembl/compound_report_card/" + chemblid;
                    document.getElementById('drug_chemblid').innerHTML = '<a href="' + chembl_link + '" target="_blank">' + chemblid + '</a>';

                }).catch(e => {
                    document.getElementById('name').innerText = decodeURI(keyword);
                    document.getElementById('formular').innerText = "-";
                    document.getElementById('mass').innerText = "-";
                    document.getElementById('drug_alogp').innerText = "-";
                    document.getElementById('drug_cxlogp').innerText = "-";
                    document.getElementById('drug_cx_acid_pka').innerText = "-";
                    document.getElementById('drug_cx_basic_pka').innerText = "-";
                    document.getElementById('drug_cx_logd').innerText = "-";

                    let chembl_link = "https://www.ebi.ac.uk/chembl/compound_report_card/" + chemblid;
                    document.getElementById('drug_chemblid').innerHTML = '<a href="' + chembl_link + '" target="_blank">' + chemblid + '</a>';
                });//just give something to the user, so we can proceed

            await load_wordcloud();
            //fill the container with fetched tags
            await getOverviewData()
                //calculate the network graph after all overviews are filled
                .then(() => fillDrugNetwork());
        })
        .catch();
}

/**
 * Function tries to fetch specified data for each object in overviews list and
 * fills it into the corresponding overview container.
 * @returns {Promise<void>}
 */
async function getOverviewData() {
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
        overviews[prefix].data = data;
        overviews[prefix].count = data[0].count;

        document.getElementById(prefix + "Link").innerText += `(${length})`;

        //manipulate data if needed
        if(ov.dataCallback) {
            await ov.dataCallback();
        }

        fillSearchbox(prefix);
        doneLoading(prefix);
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

    for(const prefix in overviews) {
        const ov = overviews[prefix];
        const entry =
`<div class="container searchbox" id="${prefix}Overview">
    <div class="top_searchbox">
        <div class="top_searchbox_left">
            <h2>${ov.name}</h2>
        </div>
        <div class="top_searchbox_right" id="${prefix}Options">
            <select class="sortbar" id="${prefix}Sort" onchange="sortElements('${prefix}')">
                <option value="rel">Most Relevant</option>
                <option value="alp">Alphabetical</option>
            </select>
            <input class="filterbar" type="text" id="${prefix}Search" placeholder="Filter..."
                   onkeyup="searchElements('${prefix}')">
        </div>
    </div>
    <div class="loading" id="${prefix}Loading">
        <img src="${url_loading_gif}">
    </div>
    <div class="bottom_searchbox" id="${prefix}Content">
    
    </div>
</div>`;

        const row = //TODO find a way without manipulate name string...
`<div class="link" onClick="scrollToElement('${prefix}Overview')"
     style="background-color: ${ov.color}">
    <div class="sidebar_entry_name">
        ${ov.name.split(" (")[0]}
    </div>
    <div class="sidebar_entry_count" id="${prefix}Link"></div>
</div>`;

        overviewEntries.innerHTML += entry;
        sidebarEntries.innerHTML += row;

        // change overview elements if needed
        if(ov.createCallback) {
            ov.createCallback();
        }
    }
}


function indiCreateCallback() {
    document.getElementById("indiSort").innerHTML += ("<option value=\"pha\">Phase</option>");
}


function adveCreateCallback() {
    const options = document.getElementById("adveOptions");
    const defaultHTML = options.innerHTML;
    const newSettings =
`<div xmlns="http://www.w3.org/1999/html" class="showall">
    <input type="checkbox" onchange="adveSwapData()" id="adveShowAll"><label>Show All</label>
</div>`;
    options.innerHTML = newSettings + defaultHTML;
}


async function indiDataCallback() {
    const prefix = "indi";
    const data = overviews[prefix].data;

    const chemblData = await fetch(`https://www.ebi.ac.uk/chembl/api/data/drug_indication?molecule_chembl_id=${currentChemblID}&limit=2500&format=json`)
        .then((result) => {
            return result.json();
        })
        .then((data) => {return data["drug_indications"]});

    // match equivalent entities and add chembl phase
    for(let idx in data) {
        let entity = chemblData.find((e) => e["mesh_id"] === data[idx]["id"].split(":")[1]);
        if(entity) {
            data[idx].max_phase_for_ind = entity.max_phase_for_ind;
        } else {
            data[idx].max_phase_for_ind = -1;
        }
    }
}


async function adveDataCallback() {
    const prefix = "adve";
    const ov = overviews[prefix];
    const altData = []

    const indiData = overviews["indi"].data;
    ov.data.forEach((entity) => {
        const obj = indiData.find((element) => entity["name"] === element["name"])

        //only add entities which count is greater than the one stored in
        // indications or not contained in it
        if(!obj || obj["count"] < entity["count"]) {
            altData.push(entity);
        }
    });

    //swap data array with reduced data array
    const fullData = overviews[prefix].data;
    overviews[prefix].data = altData;
    overviews[prefix]["altData"] = fullData;

    overviews[prefix].count = fullData[0]["count"];
}


/**
 * Scroll the window to the element specified by the parameter 'element_id'.
 * @param element_id
 */
function scrollToElement(element_id) {
    const y_offset = 80;
    const pos = document.getElementById(element_id)
        .getBoundingClientRect().top + window.scrollY - y_offset;
    window.scrollTo({top: pos, behavior: 'smooth'})
}


function adveSwapData() {
    const prefix = "adve";
    const ov = overviews[prefix];

    //reset search text if the dataset is changed
    document.getElementById(prefix + "Search").value = "";

    clearSearchBox(prefix);
    startLoading(prefix);

    //swap data arrays
    const altData = ov["altData"];
    ov["altData"] = ov.data;
    ov.data = altData;

    fillSearchbox(prefix);
    doneLoading(prefix);
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
    const input = document.getElementById(reference + "Search").value.toUpperCase();
    const data = getDataByReference(reference);
    let newData = [];
    if (input === "") {
        newData = data;
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
    clearSearchBox(reference);
    fillSearchbox(reference, newData);
    doneLoading(reference);
}


function sortElements(reference) {
    startLoading(reference);
    const select = document.getElementById(reference + "Sort");
    const data = getDataByReference(reference);
    document.getElementById(reference + "Search").value = "";
    switch (select.value) {
        case "rel":
            data.sort(function (a, b) {
                return b.count - a.count;
            });
            break;
        case "alp":
            data.sort(function (a, b) {
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
            data.sort(function (a, b) {
                return b.max_phase_for_ind - a.max_phase_for_ind;
            });
            break;
    }

    clearSearchBox(reference);
    fillSearchbox(reference, data);
    doneLoading(reference);
}


function fillSearchbox(reference, data = null) {
    const searchbox = document.getElementById(reference + "Content");
    const maxCount = overviews[reference].count;

    if(data == null) {
        data = overviews[reference].data;
    }

    for (var i = 0; i < data.length; i++) {
        const item = data[i];
        const itemDiv = document.createElement('div');
        const itemImg = document.createElement('img');
        const phaseLink = document.createElement('a');
        const itemTextLink = document.createElement('a');
        const itemText = document.createElement('p');
        const countDiv = document.createElement('div');
        const countLink = document.createElement('a');
        const query = getLinkToQuery(reference, item);
        const stringQuery = query.split('query=')[1].replaceAll('+', ' ')

        countLink.href = query;
        countLink.target = "_blank";
        countLink.textContent = `${item.count}`;
        itemText.textContent = `${item.name}`;
        itemTextLink.href = query;
        itemTextLink.style.textDecoration = "none";
        itemTextLink.style.color = "inherit";
        itemTextLink.target = "_blank";
        let scale = Math.log10(item.count) / Math.log10(maxCount);
        scale = (isNaN(scale)) ? 1 : scale; //scale can be NaN (div by 0) - set it to 1
        countDiv.style.backgroundColor = colorInterpolation(94, 94, 94, 34, 117, 189, scale);
        countDiv.classList.add("count");
        phaseLink.classList.add("phase");
        itemTextLink.append(itemText);
        itemDiv.append(itemTextLink);

        countDiv.append(countLink);
        itemDiv.append(countDiv);

        if (item.max_phase_for_ind >= 0 && item.max_phase_for_ind != null) {
            itemImg.src = url_chembl_phase + item.max_phase_for_ind + ".svg";
            phaseLink.target = "_blank";
            phaseLink.href = "https://www.ebi.ac.uk/chembl/g/#browse/drug_indications/filter/drug_indication.parent_molecule_chembl_id:" + currentChemblID + "%20&&%20drug_indication.mesh_id:" + item.id.substring(5, item.id.length);
            phaseLink.onclick = logChemblPhaseHref.bind(null, currentDrugName, item.name, item.id, stringQuery, item.max_phase_for_ind);
            phaseLink.append(itemImg)
            itemDiv.append(phaseLink);
        } else if (item.max_phase_for_ind != null) {
            itemImg.src = url_chembl_phase_new;
            phaseLink.append(itemImg)
            itemDiv.append(phaseLink);
        }

        //href Logging
        let logFunction = logSubstanceHref.bind(null, currentDrugName, item.name, stringQuery);
        itemTextLink.onclick = logFunction;
        countLink.onclick = logFunction;

        searchbox.append(itemDiv);
    }
}

function getLinkToQuery(reference, item) {
    // return early if the prefix is not known
    if(!(reference in overviews)) {
        return "";
    }

    const subject = currentDrugName.split(' ').join('+');
    const predicate = overviews[reference].predicate;
    const object = item.name.split("//")[0].split(' ').join('+');

    return `${url_query}?query="${subject}"+${predicate}+"${object}"`;
}

function clearSearchBox(reference) {
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

function fillNews(data) {
    var newsDiv = document.getElementById("newsContent");

    let i = data[0].results.length;
    if (i > 0) {
        document.getElementById("linkRecentPapers").innerText += `(${i})`

        let morePaper = document.getElementById("morePaperRef");
        morePaper.href =
            `https://www.pubpharm.de/vufind/Search/Results?lookfor=${currentDrugName}&type=AllFields`;
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

function getDataByReference(reference) {
    if(reference in overviews) {
        return overviews[reference].data;
    }
    return null;
}

function colorInterpolation(r1, g1, b1, r2, g2, b2, scale) {
    var r = Math.trunc(r1 + (r2 - r1) * scale);
    var g = Math.trunc(g1 + (g2 - g1) * scale);
    var b = Math.trunc(b1 + (b2 - b1) * scale);
    return "rgb(" + r + "," + g + "," + b + ")";
}

function rgb(r, g, b) {
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

/**
 * Send chembl-phase-id-clicked logging information to backend
 */
function logChemblPhaseHref(drug, disease_name, disease_id, query, phase) {
    const request = new Request(
        url_chembl_phase_href,
        {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify({
                drug: drug,
                disease_name: disease_name,
                disease_id: disease_id,
                query: query,
                phase: phase
            })
        }
    );
    fetch(request).catch(e => console.log(e))
}

async function load_wordcloud() {
    const data = await fetch(url_keywords + "?substance_id=" + currentChemblID)
        .then(async (response) => {
            return await response.json().then((data) => { return data["keywords"] })
        })
        .catch(() => {
            console.log("No keywords for " + currentDrugName + "available.");
            return null;
        });

    const cloud = document.getElementById("wordCloudContent")

    for(const i in data) {
        const keyword = Object.keys(data[i])[0];
        const number = data[i][keyword];

        const element = `<li data-weight="${number}" class="keyword">${keyword}</li>`;
        cloud.innerHTML += element;
    }
    doneLoading("wordCloud");
}

function fillDrugNetwork() {
    const options = {
        autoResize: true,
        physics: {
            solver: "repulsion",
            /* solvers:
             * 'barnesHut' (default),
             * 'repulsion',
             * 'hierarchicalRepulsion',
             * 'forceAtlas2Based'
             */
            // stabilization: true
            // barnesHut: {
            //     gravitationalConstant: -2000,
            //     centralGravity: 0.75,
            //     springLength: 50, //was 140
            //     springConstant: 0.08,
            //     damping: 0.85,
            //     avoidOverlap: 0.75
            // },
            // stabilization: {
            //     enabled: true,
            //     iterations: 2000,
            //     updateInterval: 100,
            //     onlyDynamicEdges: false,
            //     fit: true
            // },
        },
        interaction: {
            hover: true
        },
        layout: {
            improvedLayout: true
        },
        groups: {
            diseaseNode: {
                color: "#21b900",
                font: {
                    color: "#ffffff",
                    size: 20
                },
                shape: "box"
            },
            targetNode: {
                color: "#00c6ff",
                font: {
                    color: "#ffffff",
                    size: 20
                },
                shape: "box"
            },
            phaseNode: {
                color: {
                    background: "#ffffff",
                    border: "#21b900"
                },
                shape: "circularImage",
                size: 18,
            },
        }
    };
    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();
    const networkContainer = document.getElementById("drugNetworkContent");
    let idx = 2;

    // root node
    nodes.add({id: 1, label: currentDrugName, group: "targetNode"})

    // associated diseases (first 10 elements)
    overviews["indi"].data.slice(0,10).forEach((disease) => {
        const url = (disease.max_phase_for_ind >= 0) ? `${url_chembl_phase}${disease.max_phase_for_ind}.svg`: url_chembl_phase_new;
        nodes.add({id: idx, label: disease.name, group: "diseaseNode"});
        nodes.add({id: (idx * 100),
            image: url,
            group: "phaseNode",
            title: `Phase: ${disease.max_phase_for_ind >= 0 ? disease.max_phase_for_ind: "unknown"}`
        });
        edges.add({
            from: (idx * 100), to: 1,
            title: `${disease.count}`,
            font: { color: "#ffffff", strokeWidth: 0 },
        });
        edges.add({
            from: idx, to: (idx * 100),
            label: `${disease.count}`,
            title: `${disease.count}`,
            font: { color: "#ffffff", strokeWidth: 0 },
        })
        ++idx;
    });

    // associated targets (first 10 elements)
    overviews["targInter"].data.slice(0,10).forEach((target) => {
    // overviews["drugInter"].data.slice(0,10).forEach((target) => {
        const text = target.name.split("//")[0];
        nodes.add({id: idx, label: text, group: "targetNode"});
        edges.add({
            from: idx, to: 1,
            label: `${target.count}`,
            title: `${target.count}`,
            font: { color: "#ffffff", strokeWidth: 0 }
        });
        ++idx;
    });
    const network = new vis.Network(networkContainer, { nodes: nodes, edges: edges }, options)

    network.on("selectEdge", (e) => networkSelectEdgeCallback(e, network) );
    doneLoading("drugNetwork");
    // network.physics.physicsEnabled = false;
}

const networkSelectEdgeCallback = (e, network) => {
    let predicate = "interacts";

    // return early if the root node is selected
    if (e.nodes.length >= 1 && e.nodes[0] === 1) {
        network.unselectAll();
        return;
    }

    // retrieve the adjacent nodes (have to be 2)
    const nodes = network.getConnectedNodes(e.edges[0]);
    if(nodes.length !== 2) {
        network.unselectAll();
        return;
    }

    // if one of them has an id larger than 100 it is most likely the
    // phase node, so we have to correct the id.
    if(nodes[0] > 100 || nodes[1] > 100) {
        predicate = "treats";
    }
    const object = network.body.nodes[(nodes[0] > 100) ? nodes[0] / 100: nodes[0]].options.label

    // open the corresponding query in a new tab
    window.open(`/?query="${currentDrugName}"+${predicate}+"${object}"`, '_blank');
    network.unselectAll();
}
