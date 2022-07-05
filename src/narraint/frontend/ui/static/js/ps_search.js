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





const ps_search = (event) => {
    console.log('Search invoked')
    setButtonSearching(true);


    let query = document.getElementById("id_query").value;
    let confidence = document.getElementById("confidence_range").value;
    console.log('Query     : ' + query)
    console.log('Confidence: ' + confidence)
    let request = $.ajax({
        url: ps_search_url,
        data: {
            query: query,
            confidence: confidence
        }
    });

    request.done(function (response) {
        setButtonSearching(false);
        console.log(response);
    });

    request.fail(function (result) {
        setButtonSearching(false);
        let documents_header = $("#header_documents");
        documents_header.html("Documents")
        console.log(result);
    });

};