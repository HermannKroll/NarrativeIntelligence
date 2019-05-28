$(document).ready(function (event) {
    // $("#btn_search").on('click', search);
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

    request.done(function (result) {
        console.log(result);
    });

    request.fail(function (result) {
        console.log(result);
    });
};