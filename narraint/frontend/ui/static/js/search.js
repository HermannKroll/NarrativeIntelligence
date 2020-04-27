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

function add_collapsable_events() {
    var coll = document.getElementsByClassName("collapsible");
    var i;
    for (i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function () {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.maxHeight) {
                content.style.maxHeight = null;
            } else {
                content.style.maxHeight = content.scrollHeight + "px";
            }
        });
    }
}

const search = (event) => {
    event.preventDefault();
    let query = $('#id_keywords').val();
    let data_source = "openie"
    if (document.getElementById('radio_pmc').checked) {
        data_source = "PMC"
    } else {
        data_source = "PubMed"
    }

    let outer_ranking = document.querySelector('input[name = "outer_ranking"]:checked').value;
    let inner_ranking = document.querySelector('input[name = "inner_ranking"]:checked').value;

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
        if (nt_string.length > 0) {
            load_from_string(nt_string);
        }


        // Print query translation
        let query_translation = $("#query_translation");
        let query_trans_string = response["query_translation"];
        query_translation.text(query_trans_string);
        let results = response["results"];
        // Create documents DIV
        let divList = createDocumentList(results);
        divDocuments.append(divList);
        add_collapsable_events();

        // Disable button
        setButtonSearching(false);
    });

    request.fail(function (result) {
        setButtonSearching(false);
        console.log(result);
    });
};


const createDocumentList = (results) => {
    let divList = $(`<div class="list-group list-group-flush"></div>`);
    if (results.length > 0) {
        results.forEach(res => {
            let var_names = res[0];
            let var_subs = res[1];
            let doc_ids = res[2];
            let doc_titles = res[3];
            let explanations = res[4];
            let i = 0;
            let button_string = doc_ids.length + ' Documents';
            if (var_names.length > 0) {
                button_string += ' [';
                var_names.forEach(name => {
                    if (i === 0) {
                        button_string += name + ': ' + var_subs[i];
                    } else {
                        button_string += ', ' + name + ': ' + var_subs[i];
                    }

                    i += 1;
                });
                button_string += ']';
            }
            divList.append('<button class="collapsible">' + button_string + '</button>');

            i = 0;
            let document_div_string = "<br>";
            doc_ids.forEach(doc_id => {
                let title = doc_titles[i];
                let explanations_for_doc = explanations[i];
                i += 1;
                let e_string = "<br><br>Provenance: <br>";
                let j = 1;
                explanations_for_doc.forEach(e => {
                    e_string += j + '. ' + e + '<br>';
                    j += 1;
                });
                document_div_string +=
                    //'<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC' + document[0] + '/" ' +
                    '<a href="https://www.ncbi.nlm.nih.gov/pubmed/' + doc_id + '/" target="_blank">' +
                    'PMID' + doc_id + '</a>' + '<br> Title: ' + title + e_string + '<hr>'
            });
            divList.append('<div class="content">' + document_div_string + '</div>');
        });
    } else {
        divList.append('<button class="collapsible"> No Documents</button>');
        divList.append('<div class="content">  No Documents </div>');
    }
    return divList;
};

