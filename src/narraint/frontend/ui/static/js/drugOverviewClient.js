let newsData = null;

let currentChemblID = null;
let currentDrugName = null;

const overviews = { // prefix: {name, predicate, object, data, count}
    //dynamically created overviews
    admin: {name: "Administration", predicate: "administered", object: "DosageForm", data: null, count: null, color: "#9189ff"},
    targInter: {name: "Target Interactions", predicate: "interacts", object: "Target", data: null, count: null, color: "#b88cff"},
    labMeth: {name: "Lab Methods", predicate: "method", object: "LabMethod", data: null, count: null, color: "#9eb8ff"},
    species: {name: "Species", predicate: "associated", object: "?X(Species)", data: null, count: null, color: "#b88cff"},
    drugInter: {name: "Drug Interactions", predicate: "interacts", object: "Drug", data: null, count: null, color: "#ff8181"},
    adve: {name: "Adverse Effects (Beta)", predicate: "induces", object: "Disease", data: null, count: null, color: "#aeff9a"},

    //statically created overviews (add "isStatic: true")
    indi: {name: "Indications", predicate: "treats", data: null, count: null, isStatic: true}
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

            async.parallel([
                async.apply(indi_query_tagging, keyword),
                async.apply(indi_query_chembl, keyword)
            ], function (err, indi_result) {
                chembl_indications(indi_result[0], indi_result[1]);
            });

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

            /* fill the container with fetched tags */
            await tryFillDynamicOverviews()
        })
        .catch();
}

/**
 * Function tries to fetch specified data for each object in overviews list and
 * fills it into the corresponding overview container.
 * @returns {Promise<void>}
 */
async function tryFillDynamicOverviews() {
    for (let prefix in overviews) {
        // skip static overviews
        if(overviews[prefix].isStatic) {
            continue;
        }

        const ov = overviews[prefix];
        const url = `${url_query_sub_count}?query=${currentDrugName}+${ov.predicate}+${ov.object}&data_source=PubMed`;
        // use await to request one overview after the other
        await fetch(url)
            .then((response) => {
                return response.json();
            })
            .then((json) => {
                const data = json["sub_count_list"];
                if (!data) {
                    doneLoading(prefix);
                    return;
                }
                ov.data = data;

                const length = data["length"];
                if (length <= 0) {
                    return;
                }

                document.getElementById(prefix + "Link").innerText += `(${length})`;
                overviews[prefix].count = data[0].count;
                fillSearchbox(prefix);
                doneLoading(prefix);
            })
            .catch((e) => {
                console.log(e);
                doneLoading(prefix);
            });
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
        //skip static overviews
        if(overviews[prefix].isStatic) {
            continue;
        }

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
    }
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

function query_highlight(meta, callback_document) {
    var query = url_narrative_documents + "?documents=";
    //console.log(meta)
    for (var i = 0; i < meta.length; ++i) {
        query += meta[i] + ";";
    }
    query = query.substring(0, query.length - 1);
    query += "&data_source=PubMed";
    //console.log(query)
    fetch(query)
        .then(response => response.json())
        .then(data => {
            //console.log(data)
            callback_document(null, data);
        });
}

function indi_query_tagging(keyword, callback_indi_tagging) {
    var query = url_query_sub_count + "?query=" + keyword + "+treats+Disease&data_source=PubMed";
    fetch(query)
        .then(response => response.json())
        .then(data => {
            if (data.sub_count_list.length > 0) {
                document.getElementById("indiLink").innerText += `(${data["sub_count_list"].length})`
                callback_indi_tagging(null, data);
            } else {
                doneLoading("indi");
            }

        });
}

function indi_query_chembl(keyword, callback_indi_chembl) {
    //TODO: ändern wenn query funktioniert
    var query = url_query_chembl_indication + "?drug=" + keyword;
    fetch(query)
        .then(response => response.json())
        .then(data => {
            callback_indi_chembl(null, data);
        });
}

function chembl_indications(data_tagging, data_chembl) {
    const prefix = "indi";
    if (data_tagging.sub_count_list != null) {
        // Set um mit chembl abzugleichen
        var chembl_set = new Set();
        var phase_dict = {};
        for (var i = 0; i < data_chembl.results.length; i++) {
            if (data_chembl.results[i].mesh_id != null) {
                var chemblDisease = data_chembl.results[i].mesh_id;
                chembl_set.add(chemblDisease);
                if (data_chembl.results[i].max_phase_for_ind != null) {
                    phase_dict[chemblDisease] = data_chembl.results[i].max_phase_for_ind;
                }
            }
        }
    }
    //format into json
    var result = [];
    for (var i = 0; i < data_tagging.sub_count_list.length; i++) {
        var taggingDisease = data_tagging.sub_count_list[i].id;

        if (chembl_set.has(taggingDisease) && taggingDisease in phase_dict) {
            result[i] = {
                "name": data_tagging.sub_count_list[i].name,
                "count": data_tagging.sub_count_list[i].count,
                "max_phase_for_ind": phase_dict[taggingDisease],
                "id": taggingDisease
            };

        } else {
            result[i] = {
                "name": data_tagging.sub_count_list[i].name,
                "count": data_tagging.sub_count_list[i].count,
                "max_phase_for_ind": -1,
                "id": taggingDisease
            };
        }
    }
    overviews[prefix].count = result[0].count;
    overviews[prefix].data = result;
    fillSearchbox(prefix);
    doneLoading(prefix);
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
    fillSearchbox(reference, newData, overviews[reference].count);
    doneLoading(reference);
}


function sortElements(reference) {
    startLoading(reference);
    var select = document.getElementById(reference + "Sort");
    var data = getDataByReference(reference);
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
    fillSearchbox(reference, data, overviews[reference].count);
    doneLoading(reference);
}


function fillSearchbox(reference, data = null, max = null) {
    let searchbox = document.getElementById(reference + "Content");

    if(data == null && max == null) {
        data = overviews[reference].data;
        max = overviews[reference].count;
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
        let scale = Math.log10(item.count) / Math.log10(max);
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
    const url = url_drug_search + '?drug=' + drug;
    fetch(url).catch();
}

/**
 * Send substation/interaction-clicked logging information to backend
 */
function logSubstanceHref(drug, substance, query) {
    const url = url_substance_href + '?drug=' + drug
        + '&substance=' + substance
        + '&query=' + query;
    fetch(url).catch();
}

/**
 * Send chembl-phase-id-clicked logging information to backend
 */
function logChemblPhaseHref(drug, disease_name, disease_id, query, phase) {
    const url = url_chembl_phase_href + '?drug=' + drug
        + '&disease_name=' + disease_name
        + '&disease_id=' + disease_id
        + '&query=' + query
        + '&phase=' + phase;
    fetch(url).catch();
}
