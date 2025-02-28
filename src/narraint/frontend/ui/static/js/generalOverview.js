let keywordToLog = null;

autoComplete(document.getElementById("drugInput"));

const overviews = {
    drugAssoc: {
        name: "Associated Drugs",
        nav_bar_name: "Drugs",
        predicate: "associated",
        object: "?X(Drug)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Drug"]
    },
    indi: {
        name: "Associated Diseases",
        nav_bar_name: "Diseases",
        predicate: "associated",
        object: "Disease",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Disease"]
    },
    admin: {
        name: "Associated Dosage Forms",
        nav_bar_name: "Dosage Forms",
        predicate: "associated",
        object: "DosageForm",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["DosageForm"]
    },
    targInter: {
        name: "Associated Targets",
        nav_bar_name: "Targets",
        predicate: "associated",
        object: "Target",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Gene"]
    },
    labMeth: {
        name: "Associated Lab Methods",
        nav_bar_name: "Lab Methods",
        predicate: "method",
        object: "LabMethod",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["LabMethod"]
    },
    species: {
        name: "Associated Species",
        nav_bar_name: "Species",
        predicate: "associated",
        object: "?X(Species)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Species"]
    },
    healthstatus: {
        name: "Associated HealthStatus",
        nav_bar_name: "HealthStatus",
        predicate: "associated",
        object: "?X(HealthStatus)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["HealthStatus"]
    },
    tissue: {
        name: "Associated Tissues",
        nav_bar_name: "Tissues",
        predicate: "associated",
        object: "?X(Tissue)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Tissue"]
    },
    celllines: {
        name: "Associated Cell Lines",
        nav_bar_name: "Cell Lines",
        predicate: "associated",
        object: "CellLine",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["CellLine"]
    },
    plants: {
        name: "Associated Plant Family/Genus",
        nav_bar_name: "Plant Family",
        predicate: "associated",
        object: "?X(PlantFamily)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Plant"]
    }
}


buildSite().catch((e) => console.log(e));

window.addEventListener('popstate', () => {
    buildSite().catch((e) => console.log(e));
});


async function buildSite() {
    networkData = {drug: "drugAssoc", target: "targInter", disease: "indi", phase: true}

    const search = await getSearchParam();
    createDynamicOverviews();

    const keyword = search.split("=")[1];
    const keywordDecoded = decodeURI(keyword);
    document.getElementById('drugInput').value = keywordDecoded;

        // Matomo Tracking
    _paq.push(['trackSiteSearch', keywordDecoded, "General"]);

    logEntitySearch(keywordToLog ? keywordToLog : keyword)
    currentDrugName = keywordDecoded;


    await loadOverviewData()
        .catch((e) => console.log(e))
    saveHistoryEntry();
}


/**
 * The function tries to get the given search (drug). If no drug was entered, a default drug is set.
 * @returns {Promise<string>}
 */
async function getSearchParam() {
    let search = window.location.search;
    if (search === "") {
        search = "entity=CYP3A4";
        keywordToLog = "CYP3A4 (default)";
        const url = new URL(window.location.href);
        url.searchParams.set('entity', "CYP3A4");
        window.history.pushState("Query", "", "/overview/" + url.search.toString());
    } else {
        keywordToLog = null
    }
    return search;
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
    window.location.search = "?entity=" + keyword;
}


function logEntitySearch(entity) {
    const request = new Request(
        url_entity_search,
        {
            method: 'POST',
            headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
            mode: 'same-origin',
            body: JSON.stringify({entity: entity})
        }
    );
    fetch(request).catch(e => console.log(e))
}