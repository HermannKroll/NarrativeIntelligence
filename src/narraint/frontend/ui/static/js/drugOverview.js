let keywordToLog = null;

const overviews = {
    indi: {name: "Indications (Study Phase via <a href='https://clinicaltrials.gov'>clinicaltrials.gov</a>)", predicate: "treats", object: "Disease", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Disease"], createCallback: indiCreateCallback, dataCallback: indiDataCallback},
    admin: {name: "Administration", predicate: "administered", object: "DosageForm", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["DosageForm"]},
    targInter: {name: "Target Interactions", predicate: "interacts", object: "Target", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Gene"]},
    labMeth: {name: "Lab Methods", predicate: "method", object: "LabMethod", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["LabMethod"]},
    species: {name: "Species", predicate: "associated", object: "?X(Species)", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Species"]},
    healthstatus: {name: "HealthStatus", predicate: "associated", object: "?X(HealthStatus)", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["HealthStatus"]},
    drugAssoc: {name: "Drug Associations", predicate: "associated", object: "?X(Drug)", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Drug"]},
    drugInter: {name: "Drug Interactions", predicate: "interacts", object: "Drug", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Drug"]},
    adve: {name: "Adverse Effects (Beta)", predicate: "induces", object: "Disease", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Disease"], createCallback: adveCreateCallback, dataCallback: adveDataCallback},
    tissue: {name: "Tissue", predicate: "associated", object: "?X(Tissue)", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["Tissue"]},
    celllines: {name: "Cell Lines", predicate: "associated", object: "CellLine", numVisible: VISIBLE_ELEMENTS, color: typeColorMap["CellLine"]}
}


buildSite().catch((e) => console.log(e));

/**
 *
 * @returns {Promise<void>}
 */
async function buildSite() {
    networkData = {drug: "drugAssoc", target: "targInter", disease: "indi", phase: true}

    const search = await getSearchParam();
    createDynamicOverviews();

    const keyword = search.split("=")[1];
    document.getElementById('drugInput').value = decodeURI(keyword);

    const chembl_data = await translateToDrugId(keyword);

    if (!chembl_data) {
        resetContainerLoading(keyword)
        return
    }

    logDrugSearch(keywordToLog ? keywordToLog: keyword)
    currentDrugName = decodeURI(keyword);
    currentChemblID = chembl_data.chemblid;

    loadPaperData();
    setStructureImg();
    setDrugData(chembl_data.entity_name);

    await loadWordcloud();
    await loadOverviewData()
        .then(() => createNetworkGraph())
        .catch((e) => console.log(e))
    saveHistoryEntry();
}

/**
 * The function gets and sets the structure img of the drug.
 * @returns {Promise<void>}
 */
async function setStructureImg() {
    //fill in the image via id using fetch to catch potential errors
    const structureImage = document.getElementById('structure');
    fetch(`https://www.ebi.ac.uk/chembl/api/data/image/${currentChemblID}`)
        .then((response) => {
            if (response.ok) {
                response.blob().then((blob) => {
                    structureImage.src = URL.createObjectURL(blob);
                }).catch();
            } else {
                return Promise.reject(); /* no img available */
            }
        }).catch(() => structureImage.hidden = true);

    // set link to source image even if the img does not exist.
    let pubpharm_structure_search_link = "https://www.pubpharm.de/vufind/searchtools?name_param=" + currentDrugName;
    pubpharm_structure_search_link = '<a href="' + pubpharm_structure_search_link + '" target="_blank">PubPharm</a>';
    document.getElementById('drug_structure_search').innerHTML = pubpharm_structure_search_link;
}

/**
 * The function fetches the translation of the entity name with the help of the service.
 * @param keyword
 * @returns {Promise<any>}
 */
async function translateToDrugId(keyword) {
    // translate the key to a drug id via the narrative service
    return fetch(url_term_2_entity + '?expand_by_prefix=false&term=' + keyword)
        .then(response => response.json())
        .then(async data => {
            currentChemblID = null;
            currentDrugName = null;
            if (data.valid === false) {
                resetContainerLoading(keyword);
                return null;
            }
            let chemblid = null;
            let entity_name = null;
            let entities = data["entity"];
            entities.forEach(entity => {
                if (entity.entity_type === 'Drug') {
                    // select smallest chembl id (best match, oldest entry)
                    if (chemblid == null || entity.entity_id.length < chemblid.length ||
                        (entity.entity_id < chemblid && entity.entity_id.length === chemblid.length)) {
                        chemblid = entity.entity_id;
                        entity_name = entity.entity_name;
                    }
                }
            });

            return {
                chemblid: chemblid,
                entity_name: entity_name
            };
        });
}


/**
 * The function tries to get the given search (drug). If no drug was entered, a default drug is set.
 * @returns {Promise<string>}
 */
async function getSearchParam() {
    let search = window.location.search;
    if (search === "") {
        search = "drug=Metformin";
        keywordToLog = "Metformin (default)";
        const url = new URL(window.location.href);
        url.searchParams.set('drug', "Metformin");
        window.history.pushState("Query", "", "/drug_overview/" + url.search.toString());
    } else {
        keywordToLog = null
    }
    return search;
}

/**
 * The functions fetch the drug data of ebi.ac.uk and inserts the corresponding values into the page.
 * @returns {Promise<void>}
 */
async function setDrugData(entity_name) {
    //get drug information via id
    fetch('https://www.ebi.ac.uk/chembl/api/data/drug/' + currentChemblID + '.json')
        .then(response => response.json())
        .then(data2 => {
            document.getElementById('formular').innerText = data2.molecule_properties.full_molformula;
            document.getElementById('mass').innerText = data2.molecule_properties.full_mwt;
            //synonym seems to be correct
            document.getElementById('name').innerText = entity_name;

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

            if (data2.molecule_structures.standard_inchi) {
                document.getElementById('drug_inchi').innerText =
                    data2.molecule_structures.standard_inchi.replace('InChI=', '');
            } else {
                document.getElementById('drug_inchi').innerText = "-";
            }
        }).catch(e => {
            document.getElementById('name').innerText = decodeURI(currentDrugName);
            document.getElementById('formular').innerText = "-";
            document.getElementById('mass').innerText = "-";
            document.getElementById('drug_alogp').innerText = "-";
            document.getElementById('drug_cxlogp').innerText = "-";
            document.getElementById('drug_cx_acid_pka').innerText = "-";
            document.getElementById('drug_cx_basic_pka').innerText = "-";
            document.getElementById('drug_cx_logd').innerText = "-";
            document.getElementById('drug_inchi').innerText = "-";
        })
        .finally(() => {
            if (currentChemblID !== null) {
                const chemblLink = "https://www.ebi.ac.uk/chembl/compound_report_card/" + currentChemblID;
                document.getElementById('drug_chemblid').innerHTML = '<a href="' + chemblLink + '" target="_blank">' + currentChemblID + '</a>';
            } else {
                document.getElementById('drug_chemblid').innerText = '-';
            }

            const pubchemLink = "https://pubchem.ncbi.nlm.nih.gov/compound/" + currentDrugName;
            document.getElementById('drug_pubchem').innerHTML = '<a href="' + pubchemLink + '" target="_blank">' + decodeURI(currentDrugName) + '</a>'
        })
}

/**
 * Function callback for the searchbar submit button. The entered string is set into the url to hotreload the page and
 * to search for the new drug. Nothing happens if the input is empty. Nothing should be changed if the searched drug
 * is already visible.
 */
function searchDrug() {
    var keyword = document.getElementById('drugInput').value;
    if (keyword == "") {
        return;
    }
    window.location.search = "?drug=" + keyword;
}

/**
 * The function deactivates all loading animation in case of an invalid or unknown entity entered by the user.
 * @param keyword inserted entity
 */
function resetContainerLoading(keyword = null) {
    for (const key in overviews) {
        doneLoading(key)
    }
    doneLoading("drugNetwork");
    doneLoading("wordCloud")
    doneLoading("news");
    document.getElementById("structure").hidden = true;
    let text = document.getElementById("unknown_drug_name_tag");
    text.style.setProperty("display","flex", "important");

    if(keyword === null) {
        text.innerText = `Unknown term`;
        return;
    }
    text.innerText = `Drug '${keyword}' is unknown`;
    openDrugSuggestion();
}

/**
 * Callback function which adds a new sort filter. (chembl Phase)
 */
function indiCreateCallback() {
    document.getElementById("indiSort").innerHTML += ("<option value=\"pha\">Phase</option>");
}

/**
 * Callback function which adds a check to show/hide doubled entries in adverse effects.
 */
function adveCreateCallback() {
    const options = document.getElementById("adveOptions");
    const defaultHTML = options.innerHTML;
    const newSettings =
`<div class="input-group-text">
    <input class="form-check-input mt-0 me-1" type="checkbox" onChange="adveSwapData()" id="adveShowAll">
    Show All
</div>`
    options.innerHTML = newSettings + defaultHTML;
}

/**
 * Callback function which gets all known chembl phases for a drug and adds them to the existing dataset.
 * @returns {Promise<void>}
 */
async function indiDataCallback() {
    const prefix = "indi";
    const data = overviews[prefix].fullData;
    const chemblData = [];

    let url = url_clinical_trial_phases + "?molecule_chembl_id=" + currentChemblID;

    await fetch(url)
        .then((result) => {
            return result.json();
        })
        .then((data) => {
            chemblData.push(...data["drug_indications"]);
        })
        .catch((e) => { console.error(e)})

    // match equivalent entities and add chembl phase
    for(let idx in data) {
        let entity = chemblData.find((e) => e["mesh_id"].split(":")[1] === data[idx]["id"].split(":")[1]);
        if(entity) {
            data[idx].max_phase_for_ind = Number.parseInt(entity.max_phase_for_ind);
        } else {
            data[idx].max_phase_for_ind = -1;
        }
    }
    overviews[prefix].numVisibleData = overviews[prefix].fullData
}

/**
 * Event listener function for adverse effect container check-input. By default, only elements which are not
 * contained in indications data are visible. If the check-input is set also doubled elements are shown.
 *
 * DO NOT DELETE THIS FUNCTION! Used by a html element which is not created by default. Only after loading the page.
 */
function adveSwapData() {
    const prefix = "adve";
    const ov = overviews[prefix];

    //reset search text if the dataset is changed
    document.getElementById(prefix + "Search").value = "";

    clearSearchBox(prefix);
    startLoading(prefix);

    //swap data arrays
    const altData = ov.altData;
    ov.altData = ov.fullData;
    ov.fullData = altData;
    ov.visibleData = altData;

    clearSearchBox(prefix);
    fillSearchbox(prefix);
}

/**
 * Callback function which changes the data of adverse effects. Elements which are also contained in indications get
 * removed in the reduced data set.
 * @returns {Promise<void>}
 */
async function adveDataCallback() {
    const prefix = "adve";
    const ov = overviews[prefix];
    const altData = []

    const indiData = overviews["indi"].fullData;
    ov.fullData.forEach((entity) => {
        const obj = indiData.find((element) => entity["name"] === element["name"])

        //only add entities which count is greater than the one stored in
        // indications or not contained in it
        if(!obj || obj["count"] < entity["count"]) {
            altData.push(entity);
        }
    });

    //swap data array with reduced data array
    const fullData = overviews[prefix].fullData;
    overviews[prefix].fullData = altData;
    overviews[prefix].visibleData = altData;
    overviews[prefix].altData = fullData;

    overviews[prefix].count = fullData[0].count;
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

function openDrugSuggestion() {
    document.querySelector("#drug_suggest_button")?.classList.toggle("disabled");

    document.body.style.overflowY = "hidden";
    document.querySelector("#suggested_drug_popup").style.display = "block"
    document.querySelector("#suggested_drug").value = document.querySelector("#drugInput")?.value;
}

async function closeDrugSuggestion(send = false) {
    const suggestedDrugPopup = document.getElementById("suggested_drug_popup");

    if (send) {
        const drugName = document.querySelector("#suggested_drug")?.value;
        const drugDescription = document.querySelector("#suggested_drug_text")?.value;

        const params = {
            drug: drugName,
            description: drugDescription
        };
        const options = {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify(params)
        };
        await fetch(url_suggest_drug_report, options).then(response => {
                if (response.ok) {
                    alert("Suggestion successfully sent!");
                    return;
                }
                alert("Suggestion recommendation has failed!");
            }
        )
    }

    suggestedDrugPopup.style.display = "none";
    document.body.style.overflowY = "auto";
    document.querySelector("#drug_suggest_button")?.classList.toggle("disabled", false);

    document.querySelector("#suggested_drug").value = "";
    document.querySelector("#suggested_drug_text").value = "";
}
