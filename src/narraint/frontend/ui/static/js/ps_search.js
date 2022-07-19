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

function replaceDataSourceName(name) {
    if (name === "wikipedia_iraq_ex.jsonl") {
        return "Wikipedia"
    } else {
        return "EuroParl"
    }

}

const ps_search = (event) => {
    console.log('Search invoked')
    setButtonSearching(true);


    let query = document.getElementById("id_query").value;
    let confidence = document.getElementById("confidence_range").value;
    let wikipedia = false;//$('#wikipedia').checked;
    let europarl = true;//$('#europarl:checked').val();
    console.log('Query     : ' + query)
    console.log('Confidence: ' + confidence)
    console.log('Wikipedia : ' + wikipedia)
    console.log('EuroParl  : ' + europarl)
    let request = $.ajax({
        url: ps_search_url,
        data: {
            query: query,
            confidence: confidence,
            sources: "wikipedia;europarl"
        }
    });

    request.done(function (response) {
        setButtonSearching(false);
        console.log(response);

        let counter = 1;
        var tableData = [];
        response["bindings"].forEach(nb => {
                tableData.push({
                    id: counter,
                    confidence: nb["confidence"].toFixed(2),
                    source: replaceDataSourceName(nb["data_source"]),
                    provenance: nb["provenance"]
                })
                counter += 1;
            }
        )
        console.log(tableData);
        $('#id_result_table').bootstrapTable('append', tableData);
    });

    request.fail(function (result) {
        setButtonSearching(false);
        let documents_header = $("#header_documents");
        documents_header.html("Documents")
        console.log(result);
    });

};