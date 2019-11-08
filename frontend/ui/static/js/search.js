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
        btn.append("Search patterns")
            .prop("disabled", false);
        help.fadeOut();
    }
};

$(document).ready(function () {
    $("#search_form").submit(search);
});

const search = (event) => {
    event.preventDefault();
    let query = $('#id_keywords').val();
    console.log("Query: " + query);
    setButtonSearching(true);

    let request = $.ajax({
        url: search_url,
        data: {
            query: query
        }
    });

    request.done(function (response) {
        console.log(response);

        // Clear DIVs
        let form = $('#graph-patterns');
        form.empty();
        let divDocuments = $('#div_documents');
        divDocuments.empty();

        // Print query translation
        let query_translation = $("#query_translation");
        let query_trans_string = response["query_translation"];
        query_translation.text(query_trans_string);

        // Print patterns and documents
        response["results"].forEach((item, idx) => {
            let graph = item[0];
            let results = item[1];
            console.log(graph, results);

            // Create graph pattern selection
            createCheckbox(graph, results, idx, form);

            // Create documents DIV
            let divList = createDocumentList(results, idx);
            divDocuments.append(divList);
        });

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

const createDocumentList = (results, idx) => {
    let divList = $(`<div class="list-group list-group-flush" style="display: none;" data-by="p-${idx}" id="d-${idx}"></div>`);
    results.forEach(document => {
        let doc_id = document[0];
        let var_sub = document[1];
        let var_names = document[2];

        divList.append(
            //'<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC' + document[0] + '/" ' +
            '<a href="https://www.ncbi.nlm.nih.gov/pubmed/' + doc_id + '/" ' +
            'class="list-group-item list-group-item-action" target="_blank">' +
            'P' + doc_id + '</a>'
           // 'PMC' + document[0] + '</a>'
        );

        var_names.forEach(name => {
            divList.append(
                '<class="list-group-item">' +
                 name + ' : ' + var_sub[name] +  '</a>'
            );
        }); 

    });
    return divList;
};

/*
const createGraph = (graph, patternIdx, targetContainerId) => {
    let graphId = `graph-${patternIdx}`;
    let divGraph = $(`<div id="${graphId}" class="graph-pattern"></div>`);
    $(`#${targetContainerId}`).append(divGraph);

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
            data: {id: `triple-${tripleIdx}`, source: s, target: o}
        });
    });

    cytoscape({
        container: $(`#${graphId}`),
        elements: elements,
        style: [
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
                    'label': 'data(id)'
                }
            }
        ],
        layout: {
            name: 'circle'
        }
    });
};*/
