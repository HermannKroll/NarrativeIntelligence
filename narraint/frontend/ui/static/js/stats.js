$(document).ready(function () {
    //$("#stats_form").submit(stats);

    $.ajax({
        url: stats_url,
        dataType: 'json',
        data: {
            query: "stats"
        },
        success: function (response) {
            console.log("Response: " + response);
        }
    })
});