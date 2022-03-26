var adminData = null;
var indiData = null;
var adveData = null;
var drugInterData = null;
var targInterData = null;
var labMethData = null;
var newsData = null;
var maxCount = {"admin": -1, "indi": -1, "adve": -1, "drugInter": -1, "targInter": -1, "labMeth": -1};
let currentChemblID = null;
let currentDrugName = null;

buildSite();

function searchDrug() {
    var keyword = document.getElementById('drugInput').value;
    if (keyword == "") {
        return;
    }
    window.location.search = "?drug=" + keyword;
}

async function buildSite() {
    var search = window.location.search;
    if (search == "") {
        document.getElementById("loading").style.display = "none"
        return;
    }
    var keyword = search.split("=")[1];
    document.getElementById('drugInput').value = decodeURI(keyword);

    // translate the key to a drug id via the narrative service
    fetch(url_term_2_entity + '?term=' + keyword)
        .then(response => response.json())
        .then(data => {
            currentChemblID = null;
            currentDrugName = null;
            if (data.valid === false) {
                return;
            }
            let chemblid = "";
            let entities = data["entity"];
            entities.forEach(entity => {
                if (entity.entity_type === 'Drug') {
                    chemblid = entity.entity_id;
                    return true;
                }
            });
            currentDrugName = keyword;
            currentChemblID = chemblid;
            console.log("Translated Chembl id: " + chemblid)

            async.parallel([
                async.apply(indi_query_tagging, keyword),
                async.apply(indi_query_chembl, keyword)
            ], function (err, indi_result) {
                chembl_indications(indi_result[0], indi_result[1], chemblid);
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


            //fill in the image via id
            var structureImage = document.getElementById('structure');
            structureImage.src = "https://www.ebi.ac.uk/chembl/api/data/image/" + chemblid;

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

                    if(data2.molecule_properties.cx_logd){
                        document.getElementById('drug_cx_logd').innerText = data2.molecule_properties.cx_logd;
                    } else {
                        document.getElementById('drug_cx_logd').innerText = "-";
                    }

                    let chembl_link = "https://www.ebi.ac.uk/chembl/compound_report_card/" + chemblid;
                    document.getElementById('drug_chemblid').innerHTML = '<a href="'+ chembl_link + '" target="_blank">' + chemblid + '</a>' ;
                 //   document.getElementById('drug_chemblid').href = "v

                }).catch(e => {
                document.getElementById('name').innerText = decodeURI(keyword);
                document.getElementById('formular').innerText = "-";
                document.getElementById('mass').innerText = "-";
                document.getElementById('drug_alogp').innerText = "-";
                document.getElementById('drug_cxlogp').innerText = "-";
                document.getElementById('drug_cx_acid_pka').innerText = "-";
                document.getElementById('drug_cx_basic_pka').innerText = "-";
                document.getElementById('drug_cx_logd').innerText = "-";
                document.getElementById('drug_chemblid').innerText = "-";
            });//just give something to the user, so we can proceed
        })
        .catch();


    fetch(url_query_sub_count + "?query=" + keyword + "+administered+DosageForm&data_source=PubMed")
        .then(response => response.json())
        .then(data => {
            adminData = data.sub_count_list //Object.keys(data).map(function (k) { return data[k] });
            if (adminData.length > 0) {
                document.getElementById("linkAdministration").innerText += `(${adminData.length})`;
                maxCount["admin"] = adminData[0].count;
                fillSearchbox("admin", adminData, maxCount["admin"], -1);
            }
            doneLoading("admin");

            fetch(url_query_sub_count + "?query=" + keyword + "+induces+Disease&data_source=PubMed")
                .then(response => response.json())
                .then(data => {
                    adveData = data.sub_count_list //Object.keys(data).map(function (k) { return data[k] });
                    if (adveData.length > 0) {
                        document.getElementById("linkAdverseEffects").innerText += `(${adveData.length})`;
                        maxCount["adve"] = adveData[0].count;
                        fillSearchbox("adve", adveData, maxCount["adve"], -1);
                    }
                    doneLoading("adve");

                    fetch(url_query_sub_count + "?query=" + keyword + "+interacts+Target&data_source=PubMed")
                        .then(response => response.json())
                        .then(data => {
                            targInterData = data.sub_count_list;
                            if (targInterData.length > 0) {
                                document.getElementById("linkTargetInteractions").innerText += `(${targInterData.length})`;
                                maxCount["targInter"] = targInterData[0].count;
                                fillSearchbox("targInter", targInterData, maxCount["targInter"], -1);
                            }
                            doneLoading("targInter");

                            fetch(url_query_sub_count + "?query=" + keyword + "+interacts+Drug&data_source=PubMed")
                                .then(response => response.json())
                                .then(data => {
                                    drugInterData = data.sub_count_list;
                                    if (drugInterData.length > 0) {
                                        document.getElementById("linkDrugInteractions").innerText += `(${drugInterData.length})`;
                                        maxCount["drugInter"] = drugInterData[0].count;
                                        fillSearchbox("drugInter", drugInterData, maxCount["drugInter"], -1);
                                    }
                                    doneLoading("drugInter");

                                    fetch(url_query_sub_count + "?query=" + keyword + "+method+LabMethod&data_source=PubMed")
                                        .then(response => response.json())
                                        .then(data => {
                                            labMethData = data.sub_count_list;
                                            if (labMethData.length > 0) {
                                                document.getElementById("linkLabMethods").innerText += `(${labMethData.length})`;
                                                maxCount["labMeth"] = labMethData[0].count;
                                                fillSearchbox("labMeth", labMethData, maxCount["labMeth"], -1);
                                            }
                                            doneLoading("labMeth");
                                        });
                                });
                        });

                });
        });


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
                document.getElementById("linkIndications").innerText += `(${data.sub_count_list.length})`
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

function chembl_indications(data_tagging, data_chembl, keyword_id) {
    /*console.log("tagging:")
    console.log(data_tagging)
    console.log("chembl:")
    console.log(data_chembl)*/
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
    maxCount["indi"] = result[0].count;
    indiData = result;
    fillSearchbox("indi", result, maxCount["indi"], -1, keyword_id);
    doneLoading("indi");
}


function searchElements(reference) {
    startLoading(reference);
    var input = document.getElementById(reference + "Search").value.toUpperCase();
    var data = getDataByReference(reference);
    var newData = [];
    if (input == "") {
        newData = data;
    } else if (input.length == 1) {
        for (var item of data) {
            if (item.name.toUpperCase()[0] == input) {
                newData.push(item);
            }
        }
    } else {
        for (var item of data) {
            if (item.name.toUpperCase().includes(input)) {
                newData.push(item);
            }
        }
    }
    clearSearchBox(reference);
    fillSearchbox(reference, newData, maxCount[reference], -1);
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
    //console.log(data);
    clearSearchBox(reference);
    fillSearchbox(reference, data, maxCount[reference], -1);
    doneLoading(reference);
}

function fillSearchbox(reference, data, max, elementCount, chembl_id = 0) {
    searchbox = document.getElementById(reference + "Content");
    if (elementCount == -1 || elementCount > data.length) {
        elementCount = data.length;
    }
    for (var i = 0; i < elementCount; i++) {
        var item = data[i];
        const itemDiv = document.createElement('div');
        const itemImg = document.createElement('img');
        const phaseLink = document.createElement('a');
        const itemTextLink = document.createElement('a');
        const itemText = document.createElement('p');
        const countDiv = document.createElement('div');
        const countLink = document.createElement('a');
        countLink.href = getLinkToQuery(searchbox, item);
        countLink.target = "_blank";
        countLink.textContent = `${item.count}`;
        itemText.textContent = `${item.name}`;
        itemTextLink.href = getLinkToQuery(searchbox, item);
        itemTextLink.style.textDecoration = "none";
        itemTextLink.style.color = "inherit";
        itemTextLink.target = "_blank";
        countDiv.style.backgroundColor = colorInterpolation(94, 94, 94, 34, 117, 189, Math.log10(item.count) / Math.log10(max));
        countDiv.classList.add("count");
        phaseLink.classList.add("phase");
        itemTextLink.append(itemText);
        itemDiv.append(itemTextLink);

        countDiv.append(countLink);
        itemDiv.append(countDiv);

        if (item.max_phase_for_ind >= 0 && item.max_phase_for_ind != null) {
            itemImg.src = url_chembl_phase + item.max_phase_for_ind + ".svg";
            phaseLink.target = "_blank";
            phaseLink.href = "https://www.ebi.ac.uk/chembl/g/#browse/drug_indications/filter/drug_indication.parent_molecule_chembl_id:" + chembl_id + "%20&&%20drug_indication.mesh_id:" + item.id.substring(5, item.id.length);
            phaseLink.append(itemImg)
            itemDiv.append(phaseLink);
        } else if (item.max_phase_for_ind != null) {
            itemImg.src = url_chembl_phase_new;
            phaseLink.append(itemImg)
            itemDiv.append(phaseLink);
        }

        searchbox.append(itemDiv);
    }
}

function getLinkToQuery(searchbox, item) {
    var link = url_query + '?query=';

    var keyword = currentDrugName;
    keyword = keyword.split(' ').join('+');
    link += '"' + keyword + '"';

    var object = item.name;

    var predicate = '+';
    switch (searchbox.id) {
        case "adminContent":
            predicate += "administered";
            break;
        case "indiContent":
            predicate += "treats";
            break;
        case "adveContent":
            predicate += "induces";
            break;
        case "drugInterContent":
            predicate += "interacts";
            break;
        case "targInterContent":
            predicate += "interacts";
            object = object.split("/")[0];
            break;
        case "labMethContent":
            predicate += "method";
        default:
            break;
    }
    link += predicate;

    object = object.split(' ').join('+');
    link += '+"' + object + '"';
    return link;
}

function clearSearchBox(reference) {
    searchbox = document.getElementById(reference + "Content");
    var first = searchbox.firstElementChild;
    while (first) {
        first.remove();
        first = searchbox.firstElementChild;
    }
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
    if(i > 0) {
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
    document.getElementById("newsPopup").style.display = "flex";
    fillPaperDetail(newsData[0].results[id], newsData[0][id]);
}

function hideDetail() {
    document.getElementById("newsPopup").style.display = "none";
}

function getDataByReference(reference) {
    switch (reference) {
        case "admin":
            return adminData;
        case "indi":
            return indiData;
        case "adve":
            return adveData;
        case "drugInter":
            return drugInterData;
        case "targInter":
            return targInterData;
        case "labMeth":
            return labMethData;
        default:
            return null;
    }
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