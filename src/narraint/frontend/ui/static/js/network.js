var query = "";
var tags; // Node labels
var predicates; // predicate labels
var edgeMod = document.getElementById("edgeMod"); // mod for showing the edge create form
var nodeMod = document.getElementById("nodeMod"); // mod for showing the node create form
var renameNodeMod = document.getElementById("renameNodeMod"); // mod for showing the node renaming form
var pos = 0; // used to avoid placing nodes on top of each other
var cursorPosition = {'x': 0, 'y': 0};
var oldquery = "";
var cid = 0; // cluster id
var nodeId = 0;
var tmpFrom = "";
var tmpTo = "";
var tmpNode = "";
var tmpEdgeRename = "";
var url_data = "/static/ac_entities.txt"
var url_predicates = "/static/ac_predicates.txt"
var dict_LabelMesh = {}; // key value pairs for the labels and mesh ID's
var newEdgePrefix = "";
var renameEdgePrefix = "";
var newNodePrefix = "";
var renameNodePrefix = "";
var inpedge = document.getElementById("inpedge");
var inpnode = document.getElementById("inpnode");
var network = document.getElementById("mynetwork");


// array with the undoable actions
var his_undo = [];

// array with the redoable actions
var his_redo = [];

// head in the undo array
var count_undo = 0;

// head in the redo array
var count_redo = 0;


$('#inpnode').keypress(function (e) { // for pressing enter in input field of naming Node
    return clickSubmit("inpnode", e.which);
});

$('#inpedge').keypress(function (e) { // for pressing enter in input field of naming Edge
    return clickSubmit("inpedge", e.which);
});

$('#inprenameedge').keypress(function (e) { // for pressing enter in input field of renaming Edge
    return clickSubmit("inprenameedge", e.which);
});

$('#inprename').keypress(function (e) { // for pressing enter in input field of renaming Node
    return clickSubmit("inprename", e.which);
});

$('#inprenamecluster').keypress(function (e) { // for pressing enter in input field of renaming Cluster
    return clickSubmit("inprenamecluster", e.which);
});

function clickSubmit(whichForm, keyCode) { // switch case for enter in the input fields above
    if (keyCode == 13) {
        switch (whichForm) {
            case "inpnode":
                $('#btnsub').click();
                return false;
            case "inpedge":
                $('#btnsubedge').click();
                return false;
            case "inprenameedge":
                $('#btnsubrenameedge').click();
                return false;
            case "inprename":
                $('#btnsubrename').click();
                return false;
            case "inprenamecluster":
                $('#btnsubrenamecluster').click();
                return false;
        }
    }
}

$(function () { // function to pull the wordlist from url_data and save it in variable data
    $.ajax({
        url: url_data,
        type: "GET",
        success: function (data) {
            tags = data.split("\n"); // split data into an array of tags
            for (i = 0; i < tags.length; i++) { // create key value pairs from the labels and the mesh id's
                dict_LabelMesh[tags[i].split("\t")[0]] = tags[i].split("\t")[1];
                tags[i] = tags[i].split("\t")[0];
            }
            tags.sort(); // alphabetical order
            $("#inpnode").autocomplete({ // autocompletion for the new node window
                source: tags,
                appendTo: document.getElementById("nodemod"),
                minLength: 1
            }).data("ui-autocomplete")._renderMenu = function (ul, items) { // see https://stackoverflow.com/questions/32414466/jquery-ui-autocomplete-alphabetical-ordering-followed-by-matches-in-other-words answer of user guest271314
                var that = this;
                var val = that.element.val();
                newNodePrefix = inpnode.value.toLowerCase();
                items = items.filter(function (value, index, arr) { // filter the list so that only the words are shown that have the exact prefix
                    return value.label.toLowerCase().startsWith(newNodePrefix);
                });
                if (items.length == 0) { // if the input is a substring but no prefix, the input is shown as an autocomplete option
                    items.push({label: inpnode.value, value: inpnode.value});
                } else if (items.length > 5) { // show only five results at a time
                    items.splice(5, items.length - 5);
                }

                $.each(items, function (index, item) {
                    if (items.length != 0) {
                        that._renderItemData(ul, item);
                    }
                });
            };
            $("#inprename").autocomplete({ // autocompletion for the new node window
                source: tags,
                appendTo: document.getElementById("renamemod"),
                minLength: 1
            }).data("ui-autocomplete")._renderMenu = function (ul, items) { // see https://stackoverflow.com/questions/32414466/jquery-ui-autocomplete-alphabetical-ordering-followed-by-matches-in-other-words answer of user guest271314
                var that = this;
                var val = that.element.val();

                renameNodePrefix = document.getElementById("inprename").value.toLowerCase();
                items = items.filter(function (value, index, arr) { // filter the list so that only the words are shown that have the exact prefix
                    return value.label.toLowerCase().startsWith(renameNodePrefix);
                });
                if (items.length == 0) { // if the input is a substring but no prefix, the input is shown as an autocomplete option
                    items.push({
                        label: document.getElementById("inprename").value,
                        value: document.getElementById("inprename").value
                    });
                } else if (items.length > 5) {
                    items.splice(5, items.length - 5);
                }
                $.each(items, function (index, item) {
                    that._renderItemData(ul, item);
                });
            };
        }
    });
});


$(function() { // pulls the predicate names
  $.ajax({
    url: url_predicates,
    type: "GET",
    success: function(data) { // autocompletion for edges
      predicates = data.split(",");
      $( "#inpedge" ).autocomplete({
        source: predicates,
        appendTo : document.getElementById("edgemod"),
        minLength: 1
      }).data("ui-autocomplete")._renderMenu = function(ul, items) { // see https://stackoverflow.com/questions/32414466/jquery-ui-autocomplete-alphabetical-ordering-followed-by-matches-in-other-words answer of user guest271314
        var that = this;
        var val = that.element.val();

        newEdgePrefix = inpedge.value.toLowerCase();
        items = items.filter(function(value, index, arr) { // filter the list so that only the words are shown that have the exact prefix
          return value.label.toLowerCase().startsWith(newEdgePrefix);
        });
        if(items.length == 0) { // if the input is a substring but no prefix, the input is shown as an autocomplete option
          items.push({label:inpedge.value, value: inpedge.value});
        } else if(items.length > 5) {
          items.splice(5, items.length-5);
        }
        $.each(items, function(index, item) {
          that._renderItemData(ul, item);
        });
      };
      $( "#inprenameedge" ).autocomplete({
        source: predicates,
        appendTo : document.getElementById("renameedgemod"),
        minLength: 1
      }).data("ui-autocomplete")._renderMenu = function(ul, items) { // see https://stackoverflow.com/questions/32414466/jquery-ui-autocomplete-alphabetical-ordering-followed-by-matches-in-other-words answer of user guest271314
        var that = this;
        var val = that.element.val();

        renameEdgePrefix = document.getElementById("inprenameedge").value.toLowerCase();
        items = items.filter(function(value, index, arr) { // filter the list so that only the words are shown that have the exact prefix
          return value.label.toLowerCase().startsWith(renameEdgePrefix);
        });
        if(items.length == 0) {  // if the input is a substring but no prefix, the input is shown as an autocomplete option
          items.push({label:document.getElementById("inprenameedge").value, value: document.getElementById("inprenameedge").value});
        } else if(items.length > 5) {
          items.splice(5, items.length-5);
        }
        $.each(items, function(index, item) {
          that._renderItemData(ul, item);
        });
      };
    }
  });
});


// create an array with nodes
var nodes = new vis.DataSet([]);

// create an array with edges
var edges = new vis.DataSet([]);

// create a network
var container = document.getElementById('mynetwork');
var data = {
    nodes: nodes,
    edges: edges
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
    },
    manipulation: {
        enabled: true,
        addNode: function (nodeData, callback) {
            nodeData.cid = -1;
            nodeData.id = nodeId;
            nodeMod.click();
            network.unselectAll();
            inpnode.focus();
            inpnode.value = "";
        },
        addEdge: function (edgeData, callback) {
            tmpFrom = edgeData.from;
            tmpTo = edgeData.to;
            edgeMod.click();
            network.unselectAll();
            inpedge.focus();
            inpedge.value = "";
        },
        deleteNode: false
    }
};

var network = new vis.Network(container, data, options);

function dialogReName() { // this function is used to rename existing nodes
    var label = document.getElementById("inprename").value;
    if (label != "" && label != "?") { // if there is no text in the textfield
        if (tags.includes(label) || label[0] == "?") {
            if (label[0] == "?") { // if it's a variable
                label = label + "(" + document.getElementById("RenameNodeType").value + ")";
            } else {  // if it's an entity
                label = label
            }
            initializeUndo();
            let tempNode = nodes.get(tmpNode);
            tempNode.code = 2;
            tempNode.old_label = nodes.get(tmpNode).label;
            tempNode.label = label;
            tempNode.old_color = nodes.get(tmpNode).color;
            tempNode.color = '#97C2FC';
            his_undo[count_undo].push(tempNode);
            count_undo++;
            nodes.update({id: tmpNode, label: label, color: '#97C2FC', 'title': dict_LabelMesh[label]}); // update the node
        }  else {
            setTimeout(function () { // show an alert
                    alert('The label should be in the list.');
                    renameNodeMod.click();
                    document.getElementById("inprename").focus();
                }
                , 1);
        }
    } else {
        setTimeout(function () { // show an alert
                alert('The label cannot be empty.');
                renameNodeMod.click();
                document.getElementById("inprename").focus();
            }
            , 1);
    }
    createQuery();
}

function dialogRenameCluster() {
    var label = document.getElementById("inprenamecluster").value;
    if (label != "") {
        initializeUndo();
        let tempNode = nodes.get(tmpNode);
        tempNode.code = 2;
        tempNode.old_label = nodes.get(tmpNode).label;
        tempNode.label = label;
        tempNode.old_color = nodes.get(tmpNode).color;
        tempNode.color = '#97C2FC';
        his_undo[count_undo].push(tempNode);
        count_undo++;
        nodes.update({id: tmpNode, label: label, color: '#97C2FC', cid: nodes.get(tmpNode).cid});
    } else {
        setTimeout(function () {
                alert('The label of the clusters cannot be empty.');
                renameClusterMod.click();
                document.getElementById("inprenamecluster").focus();
            }
            , 1);
    }
    createQuery();
}

function dialogNameNode() { // this function is used to name a new node
    var label = inpnode.value;
    if (label != "" && label != "?") {
        if (tags.includes(label) || label[0] == "?") {
            initializeUndo();
            if (label[0] == "?") {
                label = label + "(" + document.getElementById("newNodeType").value + ")";
            } else {
                label = label;
            }
            let node = {
                'id': nodeId,
                'label': label,
                'cid': -1,
                color: '#97C2FC',
                'x': cursorPosition.x,
                'y': cursorPosition.y,
                'title': dict_LabelMesh[label]
            };

            cursorPosition.x += 40;
            cursorPosition.y += 40;
            network.fit()
            nodes.add(node);
            let tempNode = node;
            tempNode.code = 1;
            his_undo[count_undo].push(tempNode);
            count_undo++;
            nodeId++;
        } else {
            setTimeout(function () {
                    alert('The label should be in the list.');
                    nodeMod.click();
                    inpnode.focus();
                }
                , 1);
        }
    } else {
        setTimeout(function () {
                alert('The label cannot be empty.');
                nodeMod.click();
                inpnode.focus();
            }
            , 1);
    }
    createQuery();
}

function centerNetworkDelayed() {
    setTimeout(centerNetwork, 1000);
}

// places the network in the middle of the working space
function centerNetwork() {
    network.fit({
        animation: true
    })
}

function dialogNameEdge() { // name a new edges
    var label = inpedge.value; // get the input text
    if (label != "") { // if the textfield is empty
        // if(predicates.includes(label)) { // if label is in list of predicates
        initializeUndo();
        let edge = {from: tmpFrom, to: tmpTo, label: label, arrows: 'to'}; // create the edge
        edges.add(edge);
        let tempEdge = edge;
        tempEdge.code = 1;
        his_undo[count_undo].push(tempEdge);
        count_undo++;
        /*}  else {
          setTimeout(function() { // alert if name is not in list
            alert('The label should be in the list!');
            edgeMod.click();
            inpedge.focus();
          }
          , 1);
        } */
    } else {
        setTimeout(function () { // alert if input is empty
                alert('The label cannot be empty.');
                edgeMod.click();
                inpedge.focus();
            }
            , 1);
    }
    createQuery();
}

function dialogRenameEdge() { //rename existing edge
    var label = document.getElementById("inprenameedge").value;
    if (label != "") {
        //if(predicates.includes(label)) {

        initializeUndo();
        let edge_temp = edges.get(tmpEdgeRename);
        edge_temp.code = 2;
        edge_temp.old_label = edge_temp.label;
        edge_temp.label = label;
        his_undo[count_undo].push(edge_temp);
        count_undo++;
        edges.update({label: label, id: tmpEdgeRename});

        /*  } else {
            setTimeout(function() {
              alert('The label should be in the list.');
              renameEdgeMod.click();
              document.getElementById("inprenameedge").focus();
            }
            , 1);
          } */
    } else {
        setTimeout(function () {
                alert('The label cannot be empty.');
                renameEdgeMod.click();
                document.getElementById("inprenameedge").focus();
            }
            , 1);
    }
    createQuery();
}

function load_from_string(input_string) {
    var allLines = input_string.split(/\r\n|\n/); // Split the nt file at all lines
    var chid = 0;
    clear_all(); // delete Current Graph
    count_undo--;
    var labels = new Set(); // Create a set for the labels to check if a node already exists
    var tmpid1;
    var tmpid2;
    allLines.forEach((line) => {
        let a = line.split('\t'); // split the lines at tab
        if (a.length == 4) { // if the line is a correct NT line
            if (a[0].includes("<")) { // if the subject is an entity
                var string1 = a[0];
                string1 = string1.replace('<', '');
                string1 = string1.replace('>', '');
                if (!labels.has(string1)) { // if the node doesnt exist yet we create it
                    let node = {'id': nodeId, 'label': string1, 'cid': -1, 'title': dict_LabelMesh[string1]};
                    nodes.add(node);
                    //add to undo array
                    node.code = 1;
                    his_undo[count_undo].push(node);
                    tmpid1 = nodeId;
                    nodeId++;
                    labels.add(string1);
                } else { // else we search the node
                    for (i of nodes.getIds()) { // iterate over all nodes
                        if (nodes.get(i).label == string1) {
                            tmpid1 = i;
                        }
                    }
                }
                if (a[2].includes("<")) { // if the object is an entity
                    string1 = a[2];
                    string1 = string1.replace('<', '');
                    string1 = string1.replace('>', '');
                    if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                        if (a[1].replace('<', '').replace('>', '') == 'part_of') { //is the entity a cluster?
                            let node = {'id': nodeId, 'label': string1, 'cid': cid}; // new clusternode
                            nodes.add(node);
                            node.code = 1; // node was added
                            his_undo[count_undo].push(node); //add to undo array
                            cid++;
                            tmpid2 = nodeId;
                            nodeId++;
                            labels.add(string1); // add the node label to the Set
                        } else { // if not
                            let node = {'id': nodeId, 'label': string1, 'cid': -1, 'title': dict_LabelMesh[string1]} // new entity
                            nodes.add(node);
                            node.code = 1; // node was added
                            his_undo[count_undo].push(node); //add to undo array
                            tmpid2 = nodeId;
                            nodeId++;
                            labels.add(string1); // add the node label to the Set
                        }
                    } else { // if node already exists
                        for (i of nodes.getIds()) { // iterate over all nodes
                            if (nodes.get(i).label == string1) {
                                tmpid2 = i;
                            }
                        }
                    }
                    let edge = {from: tmpid1, to: tmpid2, label: a[1].replace('<', '').replace('>', ''), arrows: 'to'}; // create edge
                    edges.add([edge]);
                    edge.code = 1; // edge was added
                    his_undo[count_undo].push(edge); //add to undo array
                } else { //if the object is a literal
                    string1 = a[2];
                    string1 = string1.replace('<', '');
                    string1 = string1.replace('>', '');
                    if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                        let node = {'id': nodeId, 'label': string1, 'cid': -1, color: '#FF3898'};
                        nodes.add(node);
                        node.code = 1; // node was added
                        his_undo[count_undo].push(node);  //add to undo array
                        tmpid2 = nodeId;
                        nodeId++;
                        labels.add(string1);
                    } else {
                        for (i of nodes.getIds()) { // iterate over all nodes
                            if (nodes.get(i).label == string1) {
                                tmpid2 = i;
                            }
                        }
                    }
                    let edge = {from: tmpid1, to: tmpid2, label: a[1].replace('<', '').replace('>', ''), arrows: 'to'};
                    edges.add([edge]);
                    edge.code = 1; // edge was added
                    his_undo[count_undo].push(edge); //add to undo array
                }
            } else { // if the subject is a literal
                var string1 = a[0];
                string1 = string1.replace('<', '');
                string1 = string1.replace('>', '');
                if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                    let node = {'id': nodeId, 'label': string1, 'cid': -1, color: '#FF3898'};
                    nodes.add(node);
                    node.code = 1; // node was added
                    his_undo[count_undo].push(node);   //add to undo array
                    tmpid1 = nodeId;
                    nodeId++;
                    labels.add(string1);
                } else { // else we search the node
                    for (i of nodes.getIds()) { // iterate over all nodes
                        if (nodes.get(i).label == string1) {
                            tmpid1 = i;
                        }
                    }
                }
                if (a[2].includes("<")) { // if the object is an entity
                    string1 = a[2];
                    string1 = string1.replace('<', '');
                    string1 = string1.replace('>', '');
                    if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                        if (a[1].replace('<', '').replace('>', '') == 'part_of') { //is the entity a cluster?
                            let node = {'id': nodeId, 'label': string1, 'cid': cid};
                            nodes.add(node);
                            node.code = 1; // node was added
                            his_undo[count_undo].push(node); //add to undo array
                            cid++;
                            tmpid2 = nodeId;
                            nodeId++;
                            labels.add(string1);
                        } else { // if not
                            let node = {'id': nodeId, 'label': string1, 'cid': -1, 'title': dict_LabelMesh[string1]};
                            nodes.add(node);
                            node.code = 1; // node was added
                            his_undo[count_undo].push(node); //add to undo array
                            tmpid2 = nodeId;
                            nodeId++;
                            labels.add(string1);
                        }
                    } else {
                        for (i of nodes.getIds()) { // iterate over all nodes
                            if (nodes.get(i).label == string1) {
                                tmpid2 = i;
                            }
                        }
                    }
                    let edge = {from: tmpid1, to: tmpid2, label: a[1].replace('<', '').replace('>', ''), arrows: 'to'};
                    edges.add([edge]);
                    edge.code = 1; // edge was added
                    his_undo[count_undo].push(edge);  //add to undo array

                } else { //if the object is a literal
                    string1 = a[2];
                    string1 = string1.replace('<', '');
                    string1 = string1.replace('>', '');
                    if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                        let node = {'id': nodeId, 'label': string1, 'cid': -1, color: '#FF3898'};
                        nodes.add(node);
                        node.code = 1; // node was added
                        his_undo[count_undo].push(node); //add to undo array

                        tmpid2 = nodeId;
                        nodeId++;
                        labels.add(string1);
                    } else {
                        for (i of nodes.getIds()) { // iterate over all nodes
                            if (nodes.get(i).label == string1) {
                                tmpid2 = i;
                            }
                        }
                    }

                    let edge = {from: tmpid1, to: tmpid2, label: a[1].replace('<', '').replace('>', ''), arrows: 'to'};
                    edges.add([edge]);
                    edge.code = 1; // edge was added
                    his_undo[count_undo].push(edge); //add to undo array
                }
            }

        }
    });
    // Reading line by line
    createQuery(); // update the query
    count_undo++;
}

function load() { // load a graph from an NT file
    const file = document.getElementById('tFile').files[0]; // load file from input
    const reader = new FileReader();
    reader.onload = (event) => {
        const file = event.target.result;
        const file_content = file;
        load_from_string(file_content);

    };
    reader.onerror = (event) => { // if something goes wrong
        alert(event.target.error.name);
    };

    reader.readAsText(file);
}

function save() { // downloading the current Graph in NT format
    var text = "";
    for (i of edges.getIds()) { // iterate over all edges
        if (nodes.get(edges.get(i).from).color == '#FF3898') { // if first node is a literal
            text = text.concat(nodes.get(edges.get(i).from).label)
            text = text + "\t<"
        } else { // if first node is Entity
            text = text + "<"
            text = text.concat(nodes.get(edges.get(i).from).label)
            text = text + ">\t<"
        }
        text = text.concat(edges.get(i).label) // save the edge
        text = text + ">\t"
        if (nodes.get(edges.get(i).to).color == '#FF3898') { // if second node is literal
            text = text.concat(nodes.get(edges.get(i).to).label)
            text = text + "\t.\n"
        } else { // if second node is entity
            text = text + "<"
            text = text.concat(nodes.get(edges.get(i).to).label)
            text = text + ">\t.\n"
        }
    }
    var filename = "Graph"
    var file = new File([text], filename + ".nt", {type: "application/octet-stream"}); // create a file for the download
    var blobUrl = (URL || webkitURL).createObjectURL(file);
    window.onbeforeunload = null;
    window.location = blobUrl;
    window.onbeforeunload = function () {
        return "You are about to refresh the page and all progress will be lost, are you sure?";
    }
}

// cluster the selected nodes
function clusterSelected() {
    if (network.getSelectedNodes().length < 2) {
        return;
    }
    initializeUndo();
    var node = {id: nodeId, label: "cluster " + cid, cid: cid,};
    nodes.add(node);
    node.code = 1; //hinzufügen
    his_undo[count_undo].push(node);
    for (i of network.getSelectedNodes()) {
        var edge = {from: i, to: nodeId, label: "part_of", arrows: 'to'};
        edges.add([edge]);
        edge.code = 1; //hinzufügen
        his_undo[count_undo].push(edge);
    }

    nodeId++;
    cid++;

    count_undo++;

    // print
    for (var i = 0; i < nodes.length; i++) {
        var node = nodes.get(i);
    }

}

// create a subarray in the undo array and the redo array
function initializeUndo() {
    if (!his_undo[count_undo]) {
        his_undo[count_undo] = [];
    }
    his_redo = [];
    count_redo = 0;
}

// create a subarray in the redo array
function initializeRedo() {
    if (!his_redo[count_redo]) {
        his_redo[count_redo] = [];
    }
}

// Shortcuts
document.addEventListener('keydown', function (params) {
    // check whether the network has the focus
    if (document.activeElement !== network && document.activeElement.className !== "vis-network")
        return;

    // Keycode for deleting nodes/edges (delete/backspace)
    if (event.keyCode === 8 || event.keyCode === 46) {
        if (network.getSelectedNodes().length > 1) {
            initializeUndo();
            for (let i = network.getSelectedNodes().length - 1; i >= 0; i--) {
                let nodeId = network.getSelectedNodes()[0];
                let tempNode = nodes.get(network.getSelectedNodes()[0]);
                tempNode.code = 0;
                his_undo[count_undo].push(tempNode);
                nodes.remove(nodeId);

                // Entfernen von Array
                for (e of edges.getIds()) {
                    if (edges.get(e).from == nodeId || edges.get(e).to == nodeId) {
                        let tempEdge = edges.get(e);
                        tempEdge.code = 0;
                        his_undo[count_undo].push(tempEdge);
                        edges.remove(e);
                    }
                }
            }
            count_undo++;
        } else if (network.getSelectedNodes().length == 1) {
            initializeUndo();
            let nodeId = network.getSelectedNodes()[0];
            let tempNode = nodes.get(nodeId);
            tempNode.code = 0;
            his_undo[count_undo].push(tempNode);
            nodes.remove(nodeId);

            // Entfernen von Array
            for (e of edges.getIds()) {
                if (edges.get(e).from == nodeId || edges.get(e).to == nodeId) {
                    let tempEdge = edges.get(e);
                    tempEdge.code = 0;
                    his_undo[count_undo].push(tempEdge);
                    edges.remove(e);
                }
            }
            count_undo++;
        } else if (network.getSelectedEdges().length == 1) {
            initializeUndo();
            let edgeId = network.getSelectedEdges()[0];
            let tempEdge = edges.get(edgeId);
            tempEdge.code = 0;
            his_undo[count_undo].push(tempEdge);
            edges.remove(edgeId);
            count_undo++;
        } else if (network.getSelectedEdges().length > 1) {
            initializeUndo();
            let tempEdge;
            for (let i = network.getSelectedEdges().length - 1; i >= 0; i--) {
                tempEdge = edges.get(network.getSelectedEdges()[0]);
                tempEdge.code = 0;
                his_undo[count_undo].push(tempEdge);
                edges.remove(network.getSelectedEdges(i)[0]);
            }
            count_undo++;
        }

    }
    // Keycode for adding new node (n)
    else if(event.keyCode == 78 && !(document.activeElement == inpnode) && !(document.activeElement == document.getElementById("inprename")) && !(document.activeElement == document.getElementById("inprenameedge")) && !(document.activeElement == inpedge) && !(document.activeElement == document.getElementById("inprenamecluster"))) {
      var myElement = document.getElementById("nodeMod");
      myElement.click();
      network.unselectAll();
      inpnode.focus();
      setTimeout(function() {
        inpnode.value = "";
      }
      , 1);
    }
    // Keycode for adding new edge (e)
    else if(event.keyCode == 69 && !(document.activeElement == inpnode) && !(document.activeElement == document.getElementById("inprename")) && !(document.activeElement == document.getElementById("inprenameedge")) && !(document.activeElement == inpedge) && !(document.activeElement == document.getElementById("inprenamecluster"))) {
      network.addEdgeMode();
    }
    createQuery();
});

//Rename node or edge with double click
network.on('doubleClick', function (properties) {
    if (network.getSelectedNodes().length == 1) {
        tmpNode = network.getSelectedNodes()[0];
        if (nodes.get(tmpNode).cid > -1) {
            var myElement = document.getElementById("renameClusterMod");
            myElement.click();
            network.unselectAll();
            document.getElementById("inprenamecluster").focus();
            document.getElementById("inprenamecluster").value = nodes.get(tmpNode).label;

        } else {
            var myElement = document.getElementById("renameNodeMod");
            myElement.click();
            network.unselectAll();
            document.getElementById("inprename").focus();
            document.getElementById("inprename").value = nodes.get(tmpNode).label.replace('(Any)', '').replace('(Any)', '').replace('(Disease)', '').replace('(Chemical)', '').replace('(Gene)', '').replace('(Species)', '').replace('(Mutation)', '').replace('(CellLine)', '');
        }
    } else if (edges.get(network.getSelectedEdges()[0]).label == "part_of") {
        return 0;
    } else if (network.getSelectedEdges().length == 1) {
        //var edgeId = network.getSelectedEdges()[0];
        tmpEdgeRename = network.getSelectedEdges()[0];
        var myElement = document.getElementById("renameEdgeMod");
        myElement.click();
        network.unselectAll();
        document.getElementById("inprenameedge").focus();
        document.getElementById("inprenameedge").value = edges.get(tmpEdgeRename).label;
    }
});

// Undoes the last action
function undo() {
    if (his_undo.length == 0) {
        return;
    }

    initializeRedo();

    for (e of his_undo.pop()) {
        switch (e.code) {
            case 0: // deleted
                if (e.id > -1) {
                    nodes.add(e);
                    his_redo[count_redo].push(e);
                } else {
                    edges.add(e);
                    his_redo[count_redo].push(e);
                }
                break;
            case 1: // added
                if (e.id > -1) {
                    nodes.remove(e);
                    his_redo[count_redo].push(e);
                } else {
                    edges.remove(e);
                    his_redo[count_redo].push(e);
                }
                break;
            case 2: // edited
                if (e.id > -1) {
                    //color
                    if
                    (e.old_color != "") {
                        let temp_color = e.color;
                        e.color = e.old_color;
                        e.old_color = temp_color;
                    }

                    //label
                    if (e.old_label != "") {
                        let temp_label = e.label;
                        e.label = e.old_label;
                        e.old_label = temp_label;
                    }

                    nodes.update(e);
                    his_redo[count_redo].push(e);
                } else {
                    //label
                    if (e.old_label != "") {
                        let temp_label = e.label;
                        e.label = e.old_label;
                        e.old_label = temp_label;
                    }

                    edges.update(e);
                    his_redo[count_redo].push(e);
                }
                break;
        }
    }
    if (count_undo > 0) {
        count_undo--;
    }
    count_redo++;
    createQuery();
}

// Redoes the last undo
function redo() {
    if (his_redo.length == 0) {
        return;
    }

    // initialize undo
    if (!his_undo[count_undo]) {
        his_undo[count_undo] = [];
    }

    for (e of his_redo.pop()) {
        switch (e.code) {
            case 0: // deleted
                if (e.id > -1) {
                    nodes.remove(e);
                    his_undo[count_undo].push(e);
                } else {
                    edges.remove(e);
                    his_undo[count_undo].push(e);
                }
                break;
            case 1: // added
                if (e.id > -1) {
                    nodes.add(e);
                    his_undo[count_undo].push(e);
                } else {
                    edges.add(e);
                    his_undo[count_undo].push(e);
                }
                break;
            case 2: // renamed

                if (e.id > -1) { // e is node

                    //color
                    if (e.old_color != "") {
                        let temp_color = e.color;
                        e.color = e.old_color;
                        e.old_color = temp_color;
                    }

                    //label
                    if (e.old_label != "") {
                        let temp_label = e.label;
                        e.label = e.old_label;
                        e.old_label = temp_label;
                    }

                    nodes.update(e);
                    his_undo[count_undo].push(e);
                } else { // e is edge

                    //label
                    if (e.old_label != "") {
                        let temp_label = e.label;
                        e.label = e.old_label;
                        e.old_label = temp_label;
                    }

                    edges.update(e);
                    his_undo[count_undo].push(e);
                }
                break;
        }
    }
    if (count_redo > 0) {
        count_redo--;
    }
    count_undo++;
    createQuery();
}

function escapeTripleSequence(str){
    if(str.includes(" ")){
        return "\"" + str + "\"";
    } else {
        return str;
    }
}

function createQuery() {
    query = "";
    for (i of edges.getIds()) { // iterate over all edges
        let s = escapeTripleSequence(nodes.get(edges.get(i).from).label);
        let p = escapeTripleSequence(edges.get(i).label);
        let o = escapeTripleSequence(nodes.get(edges.get(i).to).label);
        query += s + " " + p + " " + o + ". ";
    }
    query = query.replace('(Any)', '');
    //remove last
    query = query.substring(0, query.length - 2);
    if (query != oldquery) {
        document.getElementById("id_keywords").value = query;
        oldquery = query;
    }
}

// delete all the nodes and edges on the screen
function clear_all() {
    initializeUndo();
    for (i of edges.getIds()) { // iterate over all edges
        let edge = edges.get(i);
        edge.code = 0;
        his_undo[count_undo].push(edge);
        edges.remove(i);
    }
    for (i of nodes.getIds()) { // iterate over all edges
        let node = nodes.get(i);
        node.code = 0;
        his_undo[count_undo].push(node);
        nodes.remove(i);
    }
    count_undo++;
    createQuery();
}

//drag dialog windows
$(function () {
    $("#nodemod").draggable();
});

$(function () {
    $("#renamemod").draggable();
});

$(function () {
    $("#renameedgemod").draggable();
});

$(function () {
    $("#edgemod").draggable();
});

$(function () {
    $("#nodemod").draggable();
});

$(function () {
    $("#renamecluster").draggable();
});
