$(document).ready(function () {
    //$("#stats_form").submit(stats);

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
                for (let i = 0; i + 1 < results.length; i += 2) {

                    //only create/append row if OpenIE and PathIE extraction counts are known, and if at least one of them is above 0
                    if (results[i][1] === "OpenIE" && results[i + 1][1] === "PathIE" && (results[i][2] > 0 || results[i + 1][2])) {
                        let stats_table_row = document.createElement("tr");

                        //prepare DOM elements for single row
                        let stats_position = document.createElement("td");
                        let stats_predicate = document.createElement("th");
                        stats_predicate.setAttribute("scope", "row");
                        let stats_openie_extr = document.createElement("td");
                        let stats_pathie_extr = document.createElement("td");

                        //fill cells of single row
                        stats_position.textContent = (i/2+1).toLocaleString();
                        //rename "null" to "other" so it looks gut
                        if (results[i][0] == null) {
                            stats_predicate.textContent = "other";
                        } else {
                            stats_predicate.textContent = results[i][0];
                        }
                        stats_openie_extr.textContent = results[i][2].toLocaleString();
                        stats_pathie_extr.textContent = results[i + 1][2].toLocaleString();

                        //append to table
                        stats_table_row.appendChild(stats_position);
                        stats_table_row.appendChild(stats_predicate);
                        stats_table_row.appendChild(stats_openie_extr);
                        stats_table_row.appendChild(stats_pathie_extr);
                        document.getElementById("stats_table").appendChild(stats_table_row);
                    }
                }
            }
        }
    })
})
;