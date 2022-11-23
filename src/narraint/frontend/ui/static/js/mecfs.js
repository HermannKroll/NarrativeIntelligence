const MECFS_ENTITY = "Chronic Fatigue Syndrome";
const MECFS_ENTITY_ID = "MESH:D015673";

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
    }
}

buildSite().catch((err) => console.log(err));

async function buildSite() {
    networkData = {drug: "drugAssoc", target: "targInter", disease: "adve", phase: false}

    createDynamicOverviews();
    logDrugSearch("ME/CFS Overview");

    currentDrugName = MECFS_ENTITY;
    currentChemblID = MECFS_ENTITY_ID;

    loadPaperData(MECFS_ENTITY_ID, "Disease")
    await loadWordcloud();
    await loadOverviewData()
        .then(() => createNetworkGraph())
        .catch((e) => console.log(e))
}
