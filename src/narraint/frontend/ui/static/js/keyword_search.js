let networkOptions = {
    autoResize: true,
    interaction: {
        hover: true,
        zoomView: false,
        dragView: false,
        dragNodes: false
    },
    physics: { solver: "forceAtlas2Based" },
    groups: {
        default_ge: {
            color: {
                background: "white",
                hover: {
                    background: "white"
                },
                highlight: {
                    background: "white"
                }
            }
        }
    }
};

let graphs = []

window.addEventListener("DOMContentLoaded", () => {
    $('#search_input').autocomplete({
        minLength: 0,
        autoFocus: true,
        source: async (request, response) => {
            const data = await fetch(autocompletion_url + "?term=" + request.term)
                .then((result) => {
                    return result.json();
                })
                .then((json) => {
                    return json["terms"];
                });
            response(data);
        },
        focus: () => {
            // prevent value inserted on focus
            return false;
        }
    }).on("keydown", (event) => {
        if (event.key === "Enter")
            keywordAdd();
        else if (event.key === "Tab") {
            event.preventDefault();
            keywordAdd();
        }
    })
});


function keywordAdd() {
    const keywordList = document.querySelector("#keyword-list");
    const keywordInput = document.querySelector('#search_input');
    const keywordId = "keyword-tag-" + keywordInput.value.trim().toLowerCase().replace(" ", "-");

    // add keywords only once
    if (Array.from(keywordList.childNodes).some((k) => k.id === keywordId)) {
        keywordInput.value = "";
        return;
    }

    // Don't add the empty keywod
    if (keywordInput.value.trim() === ""){
        return;
    }

    const div = document.createElement("div");
    div.classList.add("text-dark", "bg-light", "border", "rounded", "position-relative", "me-3", "mt-3", "px-2");
    div.innerText = keywordInput.value.trim();
    div.id = keywordId
    const span = document.createElement("span");
    span.setAttribute("role", "button");
    span.classList.add("badge", "position-absolute", "top-0", "start-100", "translate-middle", "bg-danger", "rounded-pill", "pointer")
    span.innerText = "X";
    span.onclick = () => keywordList.removeChild(div);
    div.appendChild(span);
    keywordList.appendChild(div);
    keywordInput.value = "";
}

async function keywordSearch() {
    const keywordDiv = document.querySelector("#keyword-list");
    const keywordInput = document.querySelector("#search_input");
    const keywords = [];
    if (keywordInput.value.trim() !== "")
        keywords.push(keywordInput.value);

    // Substring because the tailing X should be removed (X do remove the keyword)
    keywords.push(...Array.from(keywordDiv.childNodes).map((n) =>
        n.innerText.substring(0, n.innerText.length - 1)));


    const keywordsString = keywords.join("_AND_")
    if (keywordsString === "") {
        const inputAlert = document.getElementById('input_alert');
        inputAlert.classList.toggle('d-none', false);
        setTimeout(() => inputAlert.classList.toggle('d-none', true), 5000);
        return;
    }

    const queryGraphDiv = document.getElementById('query_graphs');
    queryGraphDiv.innerHTML = "";
    document.getElementById('div_documents').innerText = '';

    await fetch(`${url_keyword_search_request}?keywords=${keywordsString}`)
        .then((response) => { return response.json() })
        .then((data) => {
            // format: list[(str, str, str)]
            for (let idx in Object.keys(data['query_graphs'])) {

                const queryGraph = data['query_graphs'][idx];
                if (queryGraph === null) {
                    continue;
                }
                createQueryGraph(queryGraph, queryGraphDiv);
            }
        })
        .catch((e) => console.error(e))
        .finally(() => {
            document.getElementById('query_graph_container').classList.toggle('d-none');
        });
}

/**
 * Function calls all necessary functions to create a graphical representation of the given query-graph.
 * @param statements {[string, string, string]}
 * @param parentDiv {HTMLElement}
 */
function createQueryGraph(statements, parentDiv) {
    const [column, container, graphDiv] = createQueryGraphContainer();
    parentDiv.appendChild(column);

    graphs.push(container);

    addClickEvent(statements, container);
    addTooltipEvent(statements, graphDiv);

    const data = createGraph(statements);
    new vis.Network(graphDiv, data, networkOptions);
}

/**
 * Function returns a query graph url parameter representation
 * @param {Array[Array[string, string, string]]} statements
 * @returns string
 */
function queryGraphURL(statements) {
    const statementStrings = [];
    statements.forEach(([subj, pred, obj]) => {
        subj = subj.includes(' ') ? `"${subj}"`: subj;
        obj = obj.includes(' ') ? `"${obj}"`: obj;
        statementStrings.push(`${subj} ${pred} ${obj}`);

    });
    const query = statementStrings.join("_AND_");

    return new URLSearchParams({ query: query }).toString();
}

function showResults(response) {
    let divDocuments = $('#div_documents');
    divDocuments.empty();

    if (response["valid_query"] === "") {
        const alert = document.getElementById('result_alert');//$('#result_alert');
        alert.classList.toggle('d-none');

        setTimeout(() => alert.classList.toggle('d-none'), 5000);
        return;
    }

    let query_len = 0;

    // Hide sort buttons depending on the result
    let is_aggregate = response["is_aggregate"];
    document.getElementById("select_sorting_year").classList.remove("d-none");
    if (is_aggregate === true) {
        document.getElementById("select_sorting_freq").classList.remove("d-none");
    } else {
        document.getElementById("select_sorting_freq").classList.toggle("d-none", false);
    }

    let results = response["results"];
    let result_size = results["s"];

    // Show Page only if the result is an aggregated list of variable substitutions
    if (results["t"] === "agg_l") {
        computePageInfo(results["no_subs"]);
    } else {
        document.getElementById("div_input_page").style.display = "none";
    }

    // Create documents DIV
    let divList = createResultList(results, query_len);
    divDocuments.append(divList);

    saveHistoryEntry(result_size);
    document.getElementById("resultdiv").scrollIntoView();
}

function updateURLParams(query) {
    window.history.replaceState({}, null, "/?" + query + "&data_source=PubMed");
}

function resetBorders() {
    graphs.forEach((container) => {
        container.classList.remove('border-danger');
    })
}

function addClickEvent(statements, container) {
    const params = queryGraphURL(statements);

    container.onclick = async () => {
        // check if the requested query is already shown
        if (latest_valid_query === params) {
            return;
        }

        resetBorders();
        latest_valid_query = params;

        fetch(`${search_url}?${params}&data_source=PubMed`)
            .then((response) => { return response.json(); })
            .then((data) => {
                updateURLParams(params)
                showResults(data, params);
                container.classList.add('border-danger');
            })
            .catch((e) => console.log(e))
    }
}

function addTooltipEvent(statements, div) {
    const tooltip = document.getElementById('tooltip');
    const statementStrings = [];
    for (const i in statements) {
        const [s, p, o] = statements[i];
        statementStrings.push(`"${s}" ${p} "${o}"`);
    }

    let str = "";
    str += statementStrings.join(' AND<br><br>');

    div.onmouseover = (e) => {
        tooltip.classList.toggle('d-none', false);
        tooltip.innerHTML = str;
        tooltip.style.top = (e.pageY - tooltip.offsetHeight) + "px";
        tooltip.style.left= (e.pageX) + "px";
    };

    div.onmousemove = (e) => {
        tooltip.classList.toggle('d-none', false);
        tooltip.style.top = (e.pageY - tooltip.offsetHeight) + "px";
        tooltip.style.left= (e.pageX) + "px";
    };

    div.onmouseleave = () => {
        tooltip.classList.toggle('d-none', true);
    };
}

function createQueryGraphContainer() {
    const column = document.createElement('div');
    column.classList.add("col-12", "col-lg-4");
    const container = document.createElement('div');
    container.classList.add("btn", "rounded", "border", "d-flex", "h-auto", "flex-wrap", "flex-row", "m-auto");
    const graph = document.createElement('div');
    graph.classList.add("w-100","bg-white");
    graph.style.height = "250px"
    container.appendChild(graph);
    column.appendChild(container)
    return [column, container, graph];
}

function createGraph(statements) {
    const statement_entities = []

    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();

    // insert node elements only, if they not already exist in the current graph
    function insertNodeElement(element) {
        if (statement_entities.indexOf(element) >= 0) {
            return;
        }
        nodes.add({ id: element, label: element, group: 'default_ge'});
        statement_entities.push(element);
    }

    statements.forEach(([s, p, o]) => {
        insertNodeElement(s);
        insertNodeElement(o);

        edges.add({
            from: s,
            to: o,
            label: p,
            arrows: { to: { enabled: true } },
            smooth: { enabled: false },
            font: { align: 'top'}
        });
    });
    return { nodes: nodes, edges: edges };
}
