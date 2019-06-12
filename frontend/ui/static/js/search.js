$(document).ready(function () {
    $("#search_form").submit(search);
});

const search = (event) => {
    event.preventDefault();
    let query = $('#id_keywords').val();
    console.log("Query: " + query);
    let request = $.ajax({
        url: search_url,
        data: {
            query: query
        }
    });

    request.done(function (response) {
        console.log(response);

        let form = $('#div_patterns form');
        form.empty();
        $('#div_documents > div').empty();

        let query_translation = $("#query_translation");
        let query_trans_string = response["query_translation"];
        query_translation.text(query_trans_string);

        response["results"].forEach((item, idx) => {
            let graph = item[0];
            let results = item[1];

            // Create graph pattern selection DIV
            let formDiv = $('<div class="form-check"></div>');
            let input = $('<input class="form-check-input" type="radio" name="patterns" value="p' + idx + '" id="p' + idx + '">');
            let label = $('<label class="form-check-label" for="p' + idx + '">');
            label.append(results.length + ' documents<br/>');
            graph.forEach(triple => {
                label.append(triple[0] + ' - ' + triple[1] + ' - ' + triple[2] + '<br/>')
            });
            formDiv.append(input);
            formDiv.append(label);
            form.append(formDiv);
            formDiv.on('click', event => {
                $('#div_documents div.list-group').hide();
                $('div[data-by=' + event.target.id + ']').show();
            });

            // Create documents DIV
            let divList = $('<div class="list-group" style="display: none;" data-by="p' + idx + '" id="d' + idx + '"></div>');
            results.forEach(document => {
                divList.append(
                    '<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC' + document[0] + '/" ' +
                    'class="list-group-item list-group-item-action" target="_blank">' +
                    'PMC' + document[0] + '</a>'
                )
            });
            $('#div_documents > div').append(divList);

            console.log(item[0], item[1])
        });
    });

    request.fail(function (result) {
        console.log(result);
    });
};