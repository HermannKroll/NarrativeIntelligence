let CYTOSCAPE_STYLE = [
    {
        selector: 'node',
        style: {
            'background-color': '#8EB72B',
            'label': 'data(id)'
        }
    },
    {
        selector: 'edge',
        style: {
            'width': 3,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'label': 'data(label)'
        }
    }
];

const setButtonSearching = isSearching => {
    let btn = $('#btn_search');
    let help = $('#help_search');
    btn.empty();

    if (isSearching) {
        let span = $('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>');
        btn.append(span)
            .append(" Searching ...")
            .prop("disabled", true);
        help.fadeIn();
    } else {
        btn.append("Search")
            .prop("disabled", false);
        help.fadeOut();
    }
};

$(document).ready(function () {
    $("#search_form").submit(search);

    $("#id_keywords").keypress(function (e) {
        // enter pressed
        if (e.which === 13 && !e.shiftKey) {
            $(this).closest("form").submit();
            e.preventDefault();
        }
    });

});

const search = (event) => {
    event.preventDefault();
    let query = $('#id_keywords').val();
    let data_source = "trex"

    console.log("Query: " + query);
    console.log("Data source: " + data_source)
    setButtonSearching(true);

    let request = $.ajax({
        url: search_url,
        data: {
            query: query,
            data_source: data_source
        }
    });

    request.done(function (response) {
        console.log(response);

        // Clear DIVs
        let form = $('#graph-patterns');
        form.empty();
        let divDocuments = $('#div_documents');
        divDocuments.empty();


        let query_len = 0;
        // Print query translation
        let query_translation = $("#query_translation");
        let query_trans_string = response["query_translation"];
        query_translation.text(query_trans_string);
        let results = response["results"];
        let result_size = results["size"];
        // Create documents DIV
        let divList = createResultList(results, query_len);
        divDocuments.append(divList);
        // add_collapsable_events();

        let documents_header = $("#header_documents");
        if (result_size >= 0){
            documents_header.html(result_size + " Documents")
        } else {
            documents_header.html("Documents")
        }
        // Disable button
        setButtonSearching(false);
    });

    request.fail(function (result) {
        setButtonSearching(false);
        let documents_header = $("#header_documents");
        documents_header.html("Documents")
        console.log(result);
    });
};

let uniqueAccordionIDCounter = 0;
const getUniqueAccordionID = () => {
    uniqueAccordionIDCounter += 1
    return uniqueAccordionIDCounter;
};

const createResultDocumentElement = (queryResult, query_len, accordionID, headingID, collapseID) => {
    let document_id = queryResult["document_id"];
    let title = queryResult["title"];
    let explanations = queryResult["explanations"];
    let e_string = "";
    let j = 1;
    try {
        explanations.forEach(e => {
        let sentence = e["sentence"];
        // an explanation might have multiple subjects / predicates / objects sperated by //
        e["subject_str"].split('//').forEach(s => {
            let s_reg = new RegExp('('+s+')', 'gi');
            sentence = sentence.replaceAll(s_reg, '<code class="highlighter-rouge">'+s+"</code>")
        });
        e["predicate"].split('//').forEach(p => {
            let p_reg = new RegExp('('+p+')', 'gi');
            sentence = sentence.replaceAll(p_reg, '<mark>'+p+"</mark>")
        });
         e["object_str"].split('//').forEach(o => {
            let o_reg = new RegExp('('+o+')', 'gi');
            sentence = sentence.replaceAll(o_reg, '<code class="highlighter-rouge">'+o+"</code>")
        });

        e_string += j + '. ' + sentence + "<br>[" + e["subject_str"]+ ", " + e["predicate"] +  " -> " +
            e["predicate_canonicalized"] + ", " + e["object_str"]  + ']<br>';
        j += 1;
        if(j-1 === query_len){
            e_string += '<br>';
            j = 1;
        }
    });
    } catch (SyntaxError) {

    }

    let divDoc = $('<div class="card"><div class="card-body"><a class="btn-link" href="https://m.wikidata.org/wiki/Q' + document_id + '" target="_blank">' +
        +
        document_id + '</a>' + '<br><b>' + title  + '</b><br></div></div><br>');
    let divProv = $('<button class="btn btn-light" data-toggle="collapse" data-target="#prov_'+document_id+'">Provenance</button>' +
        '<div id="prov_'+document_id+'" class="collapse">\n' +
         e_string  + '</div>')
    divDoc.append(divProv);
    return divDoc;
};


const createDocumentList = (results, query_len) => {
    let accordionID = "accordion" + getUniqueAccordionID();
    let headingID = accordionID + "heading" + 1;
    let collapseID = accordionID + "collapse" + 1;

    let divAccordion = $('<div class="accordion" id="'+ accordionID +'"></div>');
    let divCard = $('<div class="card"></div>');
    divAccordion.append(divCard);
    let divCardHeader = $('<div class="card-header" id="'+headingID+'"></div>');
    divCard.append(divCardHeader);
    let divH2 = $('<h2 class="mb-0"></h2>');
    divCardHeader.append(divH2);

    let resultList = results["results"];
    let resultSize = results["size"];
    let button_string = resultSize + ' Document';
    if (resultSize > 1) {button_string += 's'};
    divH2.append('<button class="btn btn-link" type="button" data-toggle="collapse" data-target="#'+collapseID+'" ' +
        'aria-expanded="true" aria-controls="'+collapseID+'">' + button_string + '</button>');
    let divCardEntry = $('<div id="'+collapseID+'" class="collapse show" aria-labelledby="'+headingID+'" data-parent="#'+accordionID+'"></div>');
    // tbd: grid
    let divCardBody = $('<div class="card-body"></div>');
    divCardEntry.append(divCardBody);
    divCard.append(divCardEntry);

    let i = 0;
    resultList.forEach(res => {
        divCardBody.append(createDivListForResultElement(res, query_len, accordionID, headingID+i,collapseID+i));
        i += 1;
    });
    return divAccordion;
};


const createDocumentAggregate = (queryAggregate, query_len, accordionID, headingID, collapseID) => {
    let divCard = $('<div class="card"></div>');
    let divCardHeader = $('<div class="card-header" id="'+headingID+'"></div>');
    divCard.append(divCardHeader);
    let divH2 = $('<h2 class="mb-0"></h2>');
    divCardHeader.append(divH2);

    let resultList = queryAggregate["results"];
    let var_names = queryAggregate["variable_names"];
    let var_subs = queryAggregate["substitution"];
    let result_size = queryAggregate["size"];
    let button_string = result_size + ' Document';
    if(result_size > 1) {button_string += 's'}
    button_string += ' [';
    let i = 0;
    var_names.forEach(name => {
        let entity_substitution = var_subs[name];
        let ent_str = entity_substitution["entity_str"];
        let ent_id = entity_substitution["entity_id"];
        let ent_type = entity_substitution["entity_type"];
        let ent_name = entity_substitution["entity_name"];
        let var_sub = ent_name + " (" + ent_id + " " + ent_type + ")";
        button_string += ', '.repeat(!!i) + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://www.wikidata.org/wiki/' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'

    });

    divH2.append('<button class="btn btn-light" type="button" data-toggle="collapse" data-target="#'+collapseID+'" ' +
        'aria-expanded="true" aria-controls="'+collapseID+'">' + button_string + '</button>');
    let divCardEntry = $('<div id="'+collapseID+'" class="collapse" aria-labelledby="'+headingID+'" data-parent="#'+accordionID+'"></div>');
    let divCardBody = $('<div class="card-body"></div>');
    divCardEntry.append(divCardBody);
    divCard.append(divCardEntry);
    resultList.forEach(res => {
        divCardBody.append(createDivListForResultElement(res, query_len, accordionID, headingID, collapseID));
    });
    return divCard;
};


const createDocumentAggregateList = (results, query_len) => {
    let accordionID = "accordion" + getUniqueAccordionID();
    let headingID = accordionID + "heading" + 1;
    let collapseID = accordionID + "collapse" + 1;
    let divAccordion = $('<div class="accordion" id="'+ accordionID +'"></div>');

    let resultList = results["results"];

    let i = 0;
    resultList.forEach(res => {
        divAccordion.append(createDivListForResultElement(res, query_len, accordionID, headingID+i,collapseID+i));
        i += 1;
    });
    return divAccordion;
};


const createDivListForResultElement = (result, query_len, accordionID, headingID, collapseID) => {
    let typeOfRes = result["type"];
    if (typeOfRes === "doc") {
        return (createResultDocumentElement(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "doc_list") {
        return (createDocumentList(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "aggregate") {
        return (createDocumentAggregate(result, query_len, accordionID, headingID, collapseID));
    } else if (typeOfRes === "aggregate_list") {
        return (createDocumentAggregateList(result, query_len, accordionID, headingID, collapseID));
    }
    console.log("ERROR - does not recognize result type: " + typeOfRes);
    return null;
}


const createResultList = (results, query_len) => {
    let divList = $(`<div></div>`);
    divList.append(createDivListForResultElement(results, query_len, null, null, null));
    return divList;
};

