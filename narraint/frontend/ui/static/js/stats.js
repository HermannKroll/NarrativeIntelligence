$(document).ready(function () {
    $("#stats_form").submit(stats);
});

const stats = (event) => {
    console.log("CP1");
    event.preventDefault();
    let request = $.ajax({
        url: stats_url
    });
    request.done(function (response) {
        console.log("Success: " + response);
    });
    request.fail(function (result) {
        console.log("Fail: " + result);
    });
};