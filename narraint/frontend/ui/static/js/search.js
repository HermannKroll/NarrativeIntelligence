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

    let url_data = "/static/ac_all.txt";

    function isQuoteOpen(query) {
        let matches = query.match(/"/g);
        if (matches === null) {
            return false;
        }
        return matches.length % 2 === 1;
    }

    function split(val) {
        // split string by space but do not split spaces within brackets
        // remove all leading and closing brackets from splits
        let termsCleaned = val.match(/\\?.|^$/g).reduce((p, c) => {
            if (c === '"') {
                p.quote ^= 1;
            } else if (!p.quote && c === ' ') {
                p.a.push('');
            } else {
                p.a[p.a.length - 1] += c.replace(/\\(.)/, "$1");
            }
            return p;
        }, {a: ['']}).a;
        //console.log(val + " converted to " + termsCleaned);
        return termsCleaned;
    }

    function checkIsEntity(query, cursorPos, predicates) {
        // split facts by '.'
        let factPatterns = query.split('.');
        let processedChars = 0;
        // check for each fact
        for (let j = 0; j < factPatterns.length; j++) {
            let pattern = factPatterns[j];
            // check only the pattern in which the cursor is
            processedChars += pattern.length + 1; // each pattern is spit by '.'
            // if we are in the wrong pattern, go to next pattern
            if (processedChars < cursorPos) {
                continue;
            }
            let sub_str = pattern.replace("  ", " ").trim().substring(0, cursorPos);
            // we are at the beginning of a new pattern
            if (sub_str === "") {
                return true;
            }
            let terms = split(sub_str);
            // if we currently have started the new word
            if (query.charAt(cursorPos - 1) !== ' ') {
                // throw one element away (the current written word)
                terms.pop();
            }
            if (terms.length === 0) {
                // if there is no other word to check - we are in entity mode
                return true;
            }
            let potentialPredicate = terms.pop().toLowerCase();
            // match the last word in predicates (single word)
            for (let i = 0; i < predicates.length; i++) {
                if (potentialPredicate === predicates[i]) {
                    // last word was a predicate
                    return true;
                }
            }
            if (terms.length === 0) {
                // the last word was not a predicate, and we have no more words to check
                // the next word should be a predicate
                return false;
            }
            // match he last two words in predicates
            potentialPredicate = terms.pop().toLowerCase() + " " + potentialPredicate;
            for (let i = 0; i < predicates.length; i++) {
                if (potentialPredicate === predicates[i]) {
                    // last two words were a predicate
                    return true;
                }
            }
            // no predicate found - then the next word should be a predicate
            return false;
        }
        // we are potentially at the start of the query
        return true;
    }


    $.ajax({
        url: url_data,
        type: "GET",
        success: function (data) {
            let lines = data.split("\n"); // split data into an array of tags
            let entities = [];
            let predicates = [];
            let varTypes = ["Chemical", "Disease", "Gene", "Species", "DosageForm"];
            for (let i = 0; i < lines.length; i++) { // create key value pairs from the labels and the mesh id's
                let comp = lines[i].split("\t");
                if (comp[1] === "predicate") {
                    predicates.push(comp[0]);
                } else {
                    entities.push(comp[0]);
                }
            }
            entities.sort(); // alphabetical order
            $("#id_keywords")
                .autocomplete({
                    minLength: 0,
                    autoFocus: true,
                    source: function (request, response) {
                        // Use only the last entry from the textarea (exclude previous matches)
                        let cursorPosition = $("#id_keywords").prop("selectionStart");
                        let relevantTerm = request.term.substring(0, cursorPosition);
                        let last_word = "";
                        let hits = [];
                        // if the quote is open everything between the last quote and the end is our current text
                        if (isQuoteOpen(relevantTerm)) {
                            last_word = relevantTerm.substring(relevantTerm.lastIndexOf("\"") + 1).toLowerCase();
                        } else {
                            last_word = split(relevantTerm).pop();
                        }
                        //console.log("last search term is: " + relevantTerm);
                        let lastWordLower = last_word.toLowerCase().trim();

                        if (isQuoteOpen(relevantTerm) || checkIsEntity(relevantTerm, cursorPosition, predicates)) {
                            // check variable
                            if (last_word.startsWith("?") && last_word.length > 1) {
                                let varName = last_word;
                                if (last_word.includes("(")) {
                                    varName = last_word.substring(0, last_word.indexOf("("));

                                }
                                hits.push(varName);
                                for (let i = 0; i < varTypes.length; i++) {
                                    hits.push(varName + "(" + varTypes[i] + ")");
                                }
                            }
                            // check entity name
                            else if (lastWordLower.length > 1) {
                                for (let i = 0; i < entities.length; i++) {
                                    let term = entities[i];
                                    let t_lower = term.toLowerCase();
                                    if (t_lower.startsWith(lastWordLower)) {
                                        hits.push(term);
                                    }
                                    if (hits.length > 15) {
                                        break;
                                    }
                                }
                            }
                        }
                        // check predicate
                        else {
                            for (let i = 0; i < predicates.length; i++) {
                                let term = predicates[i];
                                let t_lower = term.toLowerCase();
                                if (t_lower.startsWith(lastWordLower)) {
                                    hits.push(term);
                                }
                            }
                        }
                        // delegate back to autocomplete, but extract the last term
                        response($.ui.autocomplete.filter(hits, last_word));
                    }
                    ,
                    focus: function () {
                        // prevent value inserted on focus
                        return false;
                    }
                    ,
                    select: function (event, ui) {
                        let cursorPosition = $("#id_keywords").prop("selectionStart");
                        let textAfterCursor = this.value.substring(cursorPosition);
                        let textBeforeCursor = this.value.substring(0, cursorPosition);
                        let termsBeforeCursor = split(textBeforeCursor);

                        // remove last item before autocompletion
                        let lastWord = termsBeforeCursor.pop();
                        let newValue = "";
                        let terms = [];
                        if (termsBeforeCursor.length > 0) {
                            termsBeforeCursor.forEach(t => {
                                // if empty space in string - escape
                                if (t.trim().includes(" ")) {
                                    terms.push("\"" + t + "\"");
                                } else {
                                    terms.push(t);
                                }
                            });
                            // last character should be a space
                            newValue = terms.join(" ") + " ";

                            // remove last started word
                            // newValue = textBeforeCursor.substring(0, textBeforeCursor.length - lastWord.length) + " ";
                        }
                        if (ui.item.value.trim().includes(" ")) {
                            newValue += "\"" + ui.item.value + "\" " + textAfterCursor.trim();
                        } else {
                            newValue += ui.item.value + " " + textAfterCursor.trim();
                        }

                        this.value = newValue;
                        return false;
                    }
                }).on("keydown", function (event) {
                // don't navigate away from the field on tab when selecting an item
                if (event.keyCode === $.ui.keyCode.TAB /** && $(this).data("ui-autocomplete").menu.active **/) {
                    event.preventDefault();
                    return;
                }
            });
        }
    });
});

const search = (event) => {
    event.preventDefault();
    let query = $('#id_keywords').val();
    let data_source = "openie"
    if (document.getElementById('radio_pmc').checked) {
        data_source = "PMC"
    } else if(document.getElementById('radio_pubmed').checked) {
        data_source = "PubMed"
    } else if(document.getElementById('radio_pubmed_path').checked) {
        data_source = "PubMed_Path"
    } else {
        data_source = "PMC_Path"
    }

    let outer_ranking = document.querySelector('input[name = "outer_ranking"]:checked').value;
    //let inner_ranking = document.querySelector('input[name = "inner_ranking"]:checked').value;
    let inner_ranking = "NOT IMPLEMENTED";

    console.log("Query: " + query);
    console.log("Data source: " + data_source)
    console.log("Outer Ranking: " + outer_ranking)
    console.log("Inner Ranking: " + inner_ranking)
    setButtonSearching(true);

    let request = $.ajax({
        url: search_url,
        data: {
            query: query,
            data_source: data_source,
            outer_ranking: outer_ranking,
            inner_ranking: inner_ranking
        }
    });

    request.done(function (response) {
        console.log(response);

        // Clear DIVs
        let form = $('#graph-patterns');
        form.empty();
        let divDocuments = $('#div_documents');
        divDocuments.empty();


        // Update graphical network representation
        let nt_string = response["nt_string"];
        let query_len = 0;
        if (nt_string.length > 0) {
            load_from_string(nt_string);
            query_len = nt_string.split(".").length-1;
        }


        // Print query translation
        let query_translation = $("#query_translation");
        let query_trans_string = response["query_translation"];
        query_translation.text(query_trans_string);
        let results = response["results"];
        // Create documents DIV
        let divList = createResultList(results, query_len);
        divDocuments.append(divList);
        // add_collapsable_events();

        // Disable button
        setButtonSearching(false);
    });

    request.fail(function (result) {
        setButtonSearching(false);
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
    let e_string = "<br><br>Provenance: <br>";
    let j = 1;
    explanations.forEach(e => {
        e_string += j + '. ' + e["sentence"] + " (" + e["predicate"] +  " -> " + e["predicate_canonicalized"] + ')<br>';
        j += 1;
        if(j-1 === query_len){
            e_string += '<br>';
            j = 1;
        }
    });
    let divDoc = $('<div><a class="btn-link" href="https://www.ncbi.nlm.nih.gov/pubmed/' + document_id + '/" target="_blank">' +
        '<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/US-NLM-PubMed-Logo.svg/200px-US-NLM-PubMed-Logo.svg.png" width="80px" height="28px">' +
        'PMID: ' + document_id + '</a>' + '<br><b>' + title  + '</b>' + e_string + '<br></div>');
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
        if (ent_name === "Gene" || ent_name === 'Species' || ent_name === 'Disease' || ent_name === 'Chemical'
        || ent_name === 'DosageForm' || ent_name === 'CellLine') {
            var_sub = ent_name;
        }

        if (ent_id.slice(0, 5) === 'MESH:') {
            button_string += ', '.repeat(!!i) + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://meshb.nlm.nih.gov/record/ui?ui=' + ent_id.slice(5) + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else if (ent_type === 'Species') {
            button_string += ', '.repeat(!!i) + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else if (ent_type === 'Gene'){
            button_string += ', '.repeat(!!i) + ent_name + ' (' + ent_type + ' <a onclick="event.stopPropagation()"' +
                'href="https://www.ncbi.nlm.nih.gov/gene/?term=' + ent_id + '" target="_blank"' +
                'style="font-weight:bold;"' + '>' + ent_id + '</a> ' + ')]'
        } else {
            button_string += ', '.repeat(!!i) + var_sub + ']'
        }
        i += 1;
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

