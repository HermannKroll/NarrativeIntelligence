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
        load_from_string(nt_string);

        // Print query translation
        let query_translation = $("#query_translation");
        let query_trans_string = response["query_translation"];
        query_translation.text(query_trans_string);
        let results = response["results"];
        // Create documents DIV
        let divList = createDocumentList(results);
        divDocuments.append(divList);
        add_collapsable_events();
        /*
         // Print patterns and documents
         response["results"].forEach((item, idx) => {
             let graph = item[0];
             let results = item[1];
             console.log(graph, results);

             // Create graph pattern selection
         //    createCheckbox(graph, results, idx, form);

             // Create documents DIV
             let divList = createDocumentList(results, idx);
             divDocuments.append(divList);
         });


         */


        // Disable button
        setButtonSearching(false);
    });

    request.fail(function (result) {
        setButtonSearching(false);
        console.log(result);
    });
};

const createCheckbox = (graph, results, pIdx, targetElement) => {
    let graphId = `graph-${pIdx}`;

    let formDiv = $('<div class="form-check"></div>');
    let input = $(`<input class="form-check-input" type="radio" name="patterns" value="p-${pIdx}" id="p-${pIdx}">`);
    let label = $(`<label class="form-check-label" for="p-${pIdx}">`);
    let divGraph = $(`<div id="${graphId}" class="graph-pattern"></div>`);

    //label.append(results.length + ' documents<br/>');

    label.append(input);
    label.append(divGraph);
    formDiv.append(label);
    formDiv.on('click', event => {
        $('#div_documents div.list-group').hide();
        $('div[data-by=' + event.target.id + ']').show();
    });
    targetElement.append(formDiv);

    // Prepare graph
    let elements = [];
    graph.forEach((triple, tripleIdx) => {
        let s = triple[0];
        let p = triple[1];
        let o = triple[2];

        // Add subject
        if (!elements.includes(s)) {
            elements.push({
                data: {id: s}
            });
        }

        // Add object
        if (!elements.includes(o)) {
            elements.push({
                data: {id: o}
            });
        }

        // Add edge
        elements.push({
            data: {id: `triple-${tripleIdx}`, source: s, target: o, label: p}
        });
    });

    if (graph.length > 0) {
        cytoscape({
            container: $(`#${graphId}`),
            elements: elements,
            style: CYTOSCAPE_STYLE,
            layout: {
                name: 'circle'
            }
        });
    } else {
        divGraph.append("<p><span>Pattern</span><span>not available</span></p>")
    }
};

const createDocumentList = (results) => {
    //let divList = $(`<div class="list-group list-group-flush" style="display: none;" data-by="p-${idx}" id="d-${idx}"></div>`);
    let divList = $(`<div class="list-group list-group-flush"></div>`);
    results.forEach(res => {
        let var_names = res[0];
        let var_subs = res[1];
        let doc_ids = res[2];
        let doc_titles = res[3];
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
        var document_div_string = "";
        doc_ids.forEach(doc_id => {
            let title = doc_titles[i];
            i += 1;
            document_div_string +=
                //'<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC' + document[0] + '/" ' +
                '<a href="https://www.ncbi.nlm.nih.gov/pubmed/' + doc_id + '/" ' +
                'class="list-group-item list-group-item-action" target="_blank">' +
                'P' + doc_id + '<br> ' + title + '</a>'
        });

        divList.append('<div class="content">' + document_div_string + '</div>');

    });
    return divList;
};

