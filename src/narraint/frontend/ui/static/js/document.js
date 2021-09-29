

function visualize_document_graph(document_graph) {
    let nodes = document_graph["nodes"];
    let node2id = {};
    let id = 1;
    let nodesToCreate = new vis.DataSet([]);
    nodes.forEach(node => {
        node2id[node] = id;
        let nodeData = {'id': id, 'label': node};
        console.log(nodeData);
        nodesToCreate.add(nodeData);
        id = id + 1;
    });

    let edgesToCreate = new vis.DataSet([]);
    document_graph["facts"].forEach(fact => {
        let subject = node2id[fact['s']];
        let predicate = fact['p'];
        let object = node2id[fact['o']];
        let edgeData = {'from': subject, 'to': object, 'label': predicate};
        console.log(edgeData);
        edgesToCreate.add(edgeData);
    });

    // create a network
    var container = document.getElementById('mynetwork');

    // provide the data in the vis format
    var data = {
        nodes: nodesToCreate,
        edges: edgesToCreate
    };
    var options = {
        interaction: {
            multiselect: true,
            hover: true,
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -3000,
                centralGravity: 0.0,
                springLength: 140,
                springConstant: 0.03,
                damping: 0.70,
                avoidOverlap: 0.3
            },
            stabilization: {
                enabled: true,
                iterations: 1000,
                updateInterval: 100,
                onlyDynamicEdges: false,
                fit: true
            },
        }
    };

    // initialize your network!
    var network = new vis.Network(container, data, options);

}



$(document).ready(function () {
    const queryString = window.location.search;
    console.log(queryString);
    const urlParams = new URLSearchParams(queryString);
    let document_id = urlParams.get('id');
    let request = $.ajax({
        url: document_graph_url,
        data: {
            document: document_id
        }
    });

    request.done(function (response) {
        console.log(response);
        visualize_document_graph(response);
        setButtonSearching(false);

    });

    request.fail(function (result) {
        console.log('error')
        setButtonSearching(false);

    });
});

