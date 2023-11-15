let networkOptions = {
    autoResize: true,
    interaction: {
        hover: true,
        zoomView: false,
        dragView: false,
        dragNodes: false
    },
    physics: {
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
            springLength: 125,
            avoidOverlap: 1
        }
    },
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
        if (event.key === "Enter") {
            if (document.querySelector("#search_input").value.trim() === "") {
                // submit on empty input
                keywordSearch();
            } else {
                keywordAdd();
            }
        } else if (event.key === "Tab") {
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
    const queryGraphContainer = document.querySelector('#query_graph_container');
    const keywordDiv = document.querySelector("#keyword-list");
    const keywordInput = document.querySelector("#search_input");
    const keywords = [];
    if (keywordInput.value.trim() !== "")
        keywords.push(keywordInput.value);

    // Substring because the tailing X should be removed (X do remove the keyword)
    keywords.push(...Array.from(keywordDiv.childNodes).map((n) =>
        n.innerText.substring(0, n.innerText.length - 1).replace('\n', '').trim()));

    const keywordsString = keywords.join("_AND_")
    if (keywordsString === "") {
        showAlert("Empty input. Provide keywords to search!");
        return;
    }

    queryGraphContainer.classList.toggle('d-none', true);
    showLoadingScreen();

    const queryGraphDiv = document.getElementById('query_graphs');
    queryGraphDiv.innerHTML = "";
    document.getElementById('div_documents').innerText = '';

    await fetch(`${url_keyword_search_request}?keywords=${keywordsString}`)
        .then((response) => {
            if (response.status === 200)
                return response.json();
            else if (response.status === 500) {
                return response.json().then((d) => {
                    return Promise.reject(d["reason"]);
                })
            }
            return Promise.reject("Unable to request graph queries");
        })
        .then((data) => {
            // format: list[(str, str, str)]
            for (let idx in Object.keys(data['query_graphs'])) {
                const queryGraph = data['query_graphs'][idx];
                if (queryGraph === null) {
                    continue;
                }
                createQueryGraph(queryGraph, queryGraphDiv);
            }
            queryGraphContainer.classList.toggle('d-none', false);
        })
        .catch((e) => {
            showAlert(e);
        })
        .finally(() => {
            hideLoadingScreen();
        });
}

function showAlert(message) {
    hideLoadingScreen();
    const inputAlert = document.querySelector('#input_alert');
    inputAlert.classList.toggle('d-none', false);
    inputAlert.innerText = message;
    setTimeout(() => inputAlert.classList.toggle('d-none', true), 5000);
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
    return statementStrings.join("_AND_");
}

/**
 * Function resets all visual elements of the keyword tab to default.
 * Existing data is cleared. A new keyword query request is required
 * to show entries of the tab again.
 */
function resetKeywordSearch() {
    // clear graphs array
    graphs.length = 0;

    document.querySelector("#keyword-list").innerHTML = "";
    document.querySelector("#query_graphs").innerHTML = "";
    document.querySelector("#search_input").value = "";
    document.querySelector("#query_graph_container").classList.toggle("d-none", true);
}

function resetBorders() {
    graphs.forEach((container) => {
        container.classList.remove('border-danger');
    })
}

function addClickEvent(statements, container) {
    const query = queryGraphURL(statements);

    container.onclick = async () => {
        // check if the requested query is already shown
        if (latest_valid_query === query) {
            return;
        }

        resetBorders();
        showLoadingScreen();

        const parameters = getInputParameters(query);
        initQueryBuilderFromString(query);
        logInputParameters(parameters);
        updateURLParameters(parameters);
        submitSearch(parameters)
            .finally(() => hideLoadingScreen());
    }
}

function showLoadingScreen() {
    document.documentElement.scrollIntoView({behavior: "instant"});
    document.body.scrollIntoView({behavior: "instant"});
    document.body.classList.toggle("overflow-hidden", true);
    document.querySelector("#loading_screen").classList.toggle("d-none", false);
}

function hideLoadingScreen() {
    document.body.classList.toggle("overflow-hidden", false);
    document.querySelector("#loading_screen").classList.toggle("d-none", true);
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
            smooth: { enabled: false },
            font: { align: 'top'}
        });
    });
    return { nodes: nodes, edges: edges };
}
