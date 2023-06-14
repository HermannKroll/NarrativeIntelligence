const LONG_COVID_ENTITY = "Long Covid";
const LONG_COVID_ENTITY_ID = "MESH:D000094024";

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
    drugAssoc: {
        name: "Drug Associations",
        predicate: "associated",
        object: "?X(Drug)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Drug"]
    },
    species: {
        name: "Species",
        predicate: "associated",
        object: "?X(Species)",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["Species"]
    },
    healthstatuts: {
        name: "HealthStatus",
        predicate: "associated",
        object: "HealthStatus",
        numVisible: VISIBLE_ELEMENTS,
        color: typeColorMap["HealthStatus"]
    }
}

buildSite().catch((err) => console.log(err));

async function buildSite() {
    networkData = {drug: "drugAssoc", target: "targInter", disease: "adve", phase: false}

    createDynamicOverviews();
    logDrugSearch("Covid 19 Overview");

    currentDrugName = LONG_COVID_ENTITY;
    currentChemblID = LONG_COVID_ENTITY_ID;

    loadPaperData("MESH:D000094024", "Disease");
    await loadWordcloud();
    await loadOverviewData()
        .then(() => createNetworkGraph())
        .catch((e) => console.log(e))
}
