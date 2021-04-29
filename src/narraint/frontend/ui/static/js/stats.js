//TODO: "searching" symbol oder so

$(document).ready(function () {
    //$("#stats_form").submit(stats);

    let table = $('#stats_table').DataTable({
        "pageLength": 25,
        "language": {
            "emptyTable": '<div class="spinner-border"></div>'
        },
    });

    $.ajax({
        url: stats_url,
        dataType: 'json',
        data: {
            query: "stats"
        },
        success: function (response) {
            console.log(JSON.stringify(response));
            if (response.hasOwnProperty("results")) {
                let results = response.results;
                for (let i = 0; i  < results.length; i += 1) {
                    
                    //only create/append row if OpenIE and PathIE extraction counts are known, and if at least one of them is larger than 0
                    //if (results[i][1] === "OpenIE" && results[i + 1][1] === "PathIE" && (results[i][2] > 0 || results[i + 1][2])) {
                    if (results[i][1] === "PathIE" && results[i][2] > 0 ) {
                        //rename "null" to "other" so it looks gut
                        let stats_predicate = results[i][0];
                        let stats_pathie_extr = results[i][2].toLocaleString();
                        if (results[i][0] == null) {
                            stats_predicate = "other";
                        }
                        let stats_openie_extr = 0;//results[i][2].toLocaleString();
                        //let stats_pathie_extr = results[i + 1][2].toLocaleString();

                        table.row.add([stats_predicate, stats_pathie_extr, stats_openie_extr]).draw();

                    }
                }
            }
        }
    })
});