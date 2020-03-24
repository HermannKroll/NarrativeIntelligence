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
   /* if (document.getElementById('radio_semmeddb').checked) {
        data_source = "semmeddb"
    } else {
        data_source = "openie"
    }*/

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
                button_string += ' ['
                var_names.forEach(name => {
                    if (i == 0) {
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
            let document_div_string = "";
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
                    '<a href="https://www.ncbi.nlm.nih.gov/pubmed/' + doc_id + '/" ' +
                    'class="list-group-item list-group-item-action" target="_blank">' +
                    'PMID' + doc_id + '<br> Title: ' + title + e_string + '</a>'
            });
            divList.append('<div class="content">' + document_div_string + '</div>');
        });
    } else {
        divList.append('<div class="content"> No Documents </div>');
    }
    return divList;
};

