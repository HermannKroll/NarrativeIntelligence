$(document).ready(function () {
    $("#stats_form").submit(stats);
});

const stats = (event) => {
    console.log("CP1");
    event.preventDefault();
    let request = $.ajax({
        url: stats_url,
        data: {

        }
    });
    request.done(function (response) {
        console.log("Success: " + response + " End of Response");
    });
    request.fail(function (result) {
        console.log("Fail: " + result);
    });
};