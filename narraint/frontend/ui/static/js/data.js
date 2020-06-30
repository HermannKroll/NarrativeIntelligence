$(document).ready(function () {
    let request = $.ajax({
        url: search_url,
        data: {
            query: query,
            data_source: data_source,
            outer_ranking: outer_ranking,
            inner_ranking: inner_ranking
        }
    });
}