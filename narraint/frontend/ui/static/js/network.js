var query = "";
var tags;
var predicates;
var mod2 = document.getElementById("mod2");
var mod1 = document.getElementById("mod1");
var mod3 = document.getElementById("mod3");
var pos = 0;
var cursorX = 0;
var cursorY = 0;
var cursorPosition = {'x': 0, 'y': 0};
var oldQuery = "";
var oldQuery = "";


/*$('#mynetwork').click(function(e) {
  //  console.log("x: " + cursorX + ", y: " + cursorY);
  //  console.log(network.DOMtoCanvas({x:e.pageX, y:e.pageY}).x, network.DOMtoCanvas({x:e.pageX, y:e.pageY}).y);
  //    cursorX = network.DOMtoCanvas({x:e.pageX, y:e.pageY}).x;
  //    cursorY = network.DOMtoCanvas({x:e.pageX, y:e.pageY}).y;
  cursorPosition = {'x':e.pageX, 'y':e.pageY};//network.DOMtoCanvas({x:e.pageX, y:e.pageY});
  cursorX = network.CanvastoDOM(cursorPosition).x;
  cursorY = network.CanvastoDOM(cursorPosition).y;
  //console.log("x: " + cursorPosition.x + ", y: " + cursorPosition.y);
})*/

$('#inpnode').keypress(function (e) {
    var key = e.which;
    if (key == 13)  // the enter key code
    {
        $('#btnsub').click();
        return false;
    }
});

$("#inpnode").on("change paste keyup", function () {
    var text = document.getElementById("inpnode").value;
//  console.log(text);
    if (text[0] == "?") {
        if (document.getElementById('checknode').checked == false) {
            document.getElementById("newNodeType").disabled = false;
        } else {
            document.getElementById("newNodeType").disabled = true;
        }
    } else {
        document.getElementById("newNodeType").disabled = true;
    }
});
$("#ex2").on("click", function () {
    var text = document.getElementById("inprename").value;
    console.log(text);
    if (text[0] == "?") {
        if (document.getElementById('checkrename').checked == false) {
            document.getElementById("RenameNodeType").disabled = false;
        } else {
            document.getElementById("RenameNodeType").disabled = true;
        }
    } else {
        document.getElementById("RenameNodeType").disabled = true;
    }
});

$("#inprename").on("change paste keyup", function () {
    var text = document.getElementById("inprename").value;
    console.log(text);
    if (text[0] == "?") {
        if (document.getElementById('checkrename').checked == false) {
            document.getElementById("RenameNodeType").disabled = false;
        } else {
            document.getElementById("RenameNodeType").disabled = true;
        }
    } else {
        document.getElementById("RenameNodeType").disabled = true;
    }
});
$("#renamemod").on("click", function () {
    var text = document.getElementById("inprename").value;
    console.log(text);
    if (text[0] == "?") {
        if (document.getElementById('checkrename').checked == false) {
            document.getElementById("RenameNodeType").disabled = false;
        } else {
            document.getElementById("RenameNodeType").disabled = true;
        }
    } else {
        document.getElementById("RenameNodeType").disabled = true;
    }
});


$('#inpedge').keypress(function (e) {
    var key = e.which;
    if (key == 13)  // the enter key code
    {
        $('#btnsubedge').click();
        return false;
    }
});

$('#inprenameedge').keypress(function (e) {
    var key = e.which;
    if (key == 13)  // the enter key code
    {
        $('#btnsubrenameedge').click();
        return false;
    }
});

$('#inprename').keypress(function (e) {
    var key = e.which;
    if (key == 13)  // the enter key code
    {
        $('#btnsubrename').click();
        return false;
    }
});

$('#inprenamecluster').keypress(function (e) {
    var key = e.which;
    if (key == 13)  // the enter key code
    {
        $('#btnsubrenamecluster').click();
        return false;
    }
});


/*document.getElementById('checknode').onchange = function() {
    document.getElementById('newNodeType').disabled = this.checked;
};

document.getElementById('checkrename').onchange = function() {
    document.getElementById('RenameNodeType').disabled = this.checked;
};*/


$(function () { // function to pull the wordlist from data.txt and save it in variable data

    $.ajax({
        url: "/static/ac_entities.txt",
        type: "GET",
        success: function (data) {
            tags = data.split(",");
            $("#inpnode").autocomplete({ // autocompletion for the new node window
                source: tags,
                appendTo: document.getElementById("ex2"),
                minLength: 3
            });
            $("#inprename").autocomplete({ // autocompletion for the rename window
                source: tags,
                appendTo: document.getElementById("renamemod"),
                minLength: 3
            });
        }
    });
});

$(function () { // pulls the predicate names
    $.ajax({
        url: "/static/ac_predicates.txt",
        type: "GET",
        success: function (data) { // autocompletion for edges
            predicates = data.split(",");
            $("#inpedge").autocomplete({
                source: predicates,
                appendTo: document.getElementById("edgemod"),
                minLength: 1
            });
            $("#inprenameedge").autocomplete({
                source: predicates,
                appendTo: document.getElementById("renameedgemod"),
                minLength: 1
            });
        }
    });
});

var tmpFrom = "";
var tmpTo = "";
var tmpNode = "";
var tmpEdgeRename = "";
var his_undo = [];
var his_redo = [];
var count_undo = 0;
var count_redo = 0;


// create an array with nodes
var nodes = new vis.DataSet([
    /*  {id: 5, label: 'Node 1', 'cid': -1},
      {id: 6, label: 'Node 2', 'cid': -1},
      {id: 3, label: 'Node 3'},
      {id: 4, label: 'Node 4'},
      {id: 5, label: 'Node 5'} */
]);

// create an array with edges
var edges = new vis.DataSet([
    /*{from: 5, to: 6, label: 'edge2', arrows:'to'},
    {from: 1, to: 3, label: 'edge1', arrows:'to'},
    {from: 2, to: 4, label: 'edge3', arrows:'to'},
    {from: 2, to: 5, label: 'edge4', arrows:'to'},
    {from: 3, to: 3, label: 'edge5', arrows:'to'} */
]);

// create a network
var container = document.getElementById('mynetwork');
var data = {
    nodes: nodes,
    edges: edges
};

nodeId = 0;
var options = {
    interaction: {
        multiselect: true,
        hover: true,
    },
    physics: {
        enabled: true,
        barnesHut: {
            gravitationalConstant: -5000,
            centralGravity: 0.0,
            springLength: 100,
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
            nodeData, cid = -1;
            nodeData.id = nodeId;
            console.log(nodeData.id);
            console.log(nodeData);
            var myElement = document.getElementById("mod1");
            console.log(myElement);
            myElement.click();
            network.unselectAll();
            document.getElementById("inpnode").focus();
            document.getElementById("inpnode").value = "";/*
      nodeData.label = prompt("Please enter name of the node", ""); // opens prompt for user input
      if (name != null) {
        nodeId++;
        callback(nodeData);
      }*/
        },
        addEdge: function (edgeData, callback) {
            tmpFrom = edgeData.from;
            tmpTo = edgeData.to;
            mod2.click();
            network.unselectAll();
            document.getElementById("inpedge").focus();
            document.getElementById("inpedge").value = "";
            /*edgeData.arrows = 'to';
              edgeData.label = prompt("Please enter name of the edge", "");
              if (edgeData.label != null && edgeData.label != "") {
                callback(edgeData);
              }*/

        }
    }
};
var network = new vis.Network(container, data, options);

function dialogReName() { // this function is used to rename existing nodes
    var label = document.getElementById("inprename").value;
    if (label != "") {
        if ((tags.includes(label) || label[0] == "?") && !(document.getElementById("checkrename").checked)) {
            if (label[0] == "?") {
                label = label + "(" + document.getElementById("RenameNodeType").value + ")";
            } else {
                label = label //+ "_Type:" +document.getElementById("newNodeType").value;
            }
            initializeUndo();
            let tempNode = nodes.get(tmpNode);
            tempNode.code = 2;
            tempNode.old_label = nodes.get(tmpNode).label;
            tempNode.label = label;
            tempNode.old_color = '#97C2FC';
            tempNode.color = '#97C2FC';
            his_undo[count_undo].push(tempNode);
            count_undo++;
            nodes.update({id: tmpNode, label: label, color: '#97C2FC'});
        } else if (document.getElementById("checkrename").checked) {
            initializeUndo();
            let tempNode = nodes.get(tmpNode);
            tempNode.code = 2;
            tempNode.old_label = nodes.get(tmpNode).label;
            tempNode.label = label;
            tempNode.old_color = '#97C2FC';
            tempNode.color = '#FF3898';
            his_undo[count_undo].push(tempNode);
            count_undo++;
            nodes.update({id: tmpNode, label: label, color: '#FF3898'});
        } else {
            setTimeout(function () {
                    alert('Der Name muss in der Liste der Wörter enthalten sein!');
                    mod1.click();
                    document.getElementById("inpnode").focus();
                }
                , 1);
        }
    } else {
        setTimeout(function () {
                alert('Der Name des Knotens darf nicht leer sein!');
                mod1.click();
                document.getElementById("inpnode").focus();
            }
            , 1);
    }
    $("#checkrename").removeAttr("checked");
    createQuery();
    console.log(query);
}

function deleteNode() { //delete node
    network.deleteSelected();
}

function dialogRenameCluster() {
    var label = document.getElementById("inprenamecluster").value;
    if (label != "") {
        initializeUndo();
        let tempNode = nodes.get(tmpNode);
        tempNode.code = 2;
        tempNode.old_label = nodes.get(tmpNode).label;
        tempNode.label = label;
        tempNode.old_color = '#97C2FC';
        tempNode.color = '#97C2FC';
        his_undo[count_undo].push(tempNode);
        count_undo++;
        nodes.update({id: tmpNode, label: label, color: '#97C2FC', cid: nodes.get(tmpNode).cid});

    } else {
        setTimeout(function () {
                alert('Der Name des Clusters darf nicht leer sein!');
                mod1.click();
                document.getElementById("inprenamecluster").focus();
            }
            , 1);
    }
    createQuery();
    console.log(query);
}

function dialogNameNode() { // this function is used to name a new node
    var label = document.getElementById("inpnode").value;
    if (label != "") {
        if ((tags.includes(label) || label[0] == "?") && !(document.getElementById("checknode").checked)) {
            initializeUndo();
            if (label[0] == "?") {
                label = label + "(" + document.getElementById("newNodeType").value + ")";
            } else {
                label = label //+ "_Type:" +document.getElementById("newNodeType").value;
            }
            let node = {'id': nodeId, 'label': label, 'cid': -1, 'x': cursorPosition.x, 'y': cursorPosition.y};
            pos += 40;
            network.fit()
            //console.log("before add")
            nodes.add(node);
            //console.log("after add")
            let tempNode = node;
            tempNode.code = 1;
            his_undo[count_undo].push(tempNode);
            count_undo++;
            nodeId++;
        } else if (document.getElementById("checknode").checked) {
            initializeUndo();
            let node = {
                'id': nodeId,
                'label': label,
                'cid': -1,
                color: '#FF3898',
                'x': cursorPosition.x,
                'y': cursorPosition.y
            };
            nodes.add(node);
            cursorPosition.x += 40;
            cursorPosition.y += 40;
            setTimeout(function () {
                    centerNetwork()
                }
                , 600);
            let tempNode = node;
            tempNode.code = 1;
            his_undo[count_undo].push(tempNode);
            count_undo++;
            nodeId++;
        } else {
            setTimeout(function () {
                    alert('Der Name muss in der Liste der Wörter enthalten sein!');
                    mod1.click();
                    document.getElementById("inpnode").focus();
                }
                , 1);
        }
    } else {
        setTimeout(function () {
                alert('Der Name des Knotens darf nicht leer sein!');
                mod1.click();
                document.getElementById("inpnode").focus();
            }
            , 1);
    }
    $("#checknode").removeAttr("checked");
    createQuery();

    //console.log(query);
}

function centerNetwork() {
    network.fit({
        animation: true
    })
}

function dialogNameEdge() { // name a new edges
    var label = document.getElementById("inpedge").value;
    if (label != "") {
        if (predicates.includes(label)) {
            initializeUndo();
            let edge = {from: tmpFrom, to: tmpTo, label: label, arrows: 'to'};
            edges.add(edge);
            let tempEdge = edge;
            tempEdge.code = 1;
            his_undo[count_undo].push(tempEdge);
            count_undo++;
        } else {
            setTimeout(function () {
                    alert('Der Name muss in der Liste der Wörter enthalten sein!');
                    mod2.click();
                    document.getElementById("inpedge").focus();
                }
                , 1);
        }
    } else {
        setTimeout(function () {
                alert('Der Name der Kante darf nicht leer sein!');
                mod2.click();
                document.getElementById("inpedge").focus();
            }
            , 1);
    }
    createQuery();
    console.log(query);
}

function dialogRenameEdge() { //rename existing edge
    var label = document.getElementById("inprenameedge").value;
    if (label != "") {
        if (predicates.includes(label)) {

            initializeUndo();
            let edge_temp = edges.get(tmpEdgeRename);
            edge_temp.code = 2;
            edge_temp.old_label = edge_temp.label;
            edge_temp.label = label;
            his_undo[count_undo].push(edge_temp);
            count_undo++;
            edges.update({label: label, id: tmpEdgeRename});

        } else {
            setTimeout(function () {
                    alert('Der Name muss in der Liste der Wörter enthalten sein!');
                    mod4.click();
                    document.getElementById("inprenameedge").focus();
                }
                , 1);
        }
    } else {
        setTimeout(function () {
                alert('Der Name der Kante darf nicht leer sein!');
                mod4.click();
                document.getElementById("inprenameedge").focus();
            }
            , 1);
    }
    createQuery();
    console.log(query);
}

function calculateCenterX() {
    var tmpx = 0;
    if (nodes.length == 0) {
        tmpx = 0;
    } else if (nodes.length == 1) {
        tmpx = nodes.get(0).x + 20;
    } else {
        for (i of nodes.getIds()) { // iterate over all nodes
            tmpx += nodes.get(i).x;
        }
        tmpx /= nodes.length;
    }
    return tmpx;
}

function calculateCenterY() {
    var tmpy = 0;
    if (nodes.length == 0) {
        tmpy = 0;
    } else if (nodes.length == 1) {
        tmpy = nodes.get(0).y + 20;
    } else {
        console.log("test1");
        for (i of nodes.getIds()) { // iterate over all nodes
            console.log("test" + i);
            tmpy += nodes.get(i).y;
        }
        console.log("last");
        tmpy /= nodes.length;
    }
    console.log("lastlast");
    return tmpy;
}

function load() { // load a graph from an NT file
    var cid = 0;
    /*
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
        */
    clear_all();
    count_undo--;

    var labels = new Set();
    var tmpid1;
    var tmpid2;
    const file = document.getElementById('tFile').files[0];
    console.log(file);
    const reader = new FileReader();

    reader.onload = (event) => {
        const file = event.target.result;
        const allLines = file.split(/\r\n|\n/);
        // Reading line by line
        allLines.forEach((line) => {
            let a = line.split('\t');
            console.log(a);
            if (a.length == 4) {
                if (a[0].includes("<")) { // if the subject is an entity
                    var string1 = a[0];
                    string1 = string1.replace('<', '');
                    string1 = string1.replace('>', '');
                    if (!labels.has(string1)) { // if the node doesnt exist yet we create it
                        let node = {'id': nodeId, 'label': string1, 'cid': -1};
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
                                let node = {'id': nodeId, 'label': string1, 'cid': cid};
                                nodes.add(node);

                                //add to undo array
                                node.code = 1;
                                his_undo[count_undo].push(node);

                                cid++;
                                tmpid2 = nodeId;
                                nodeId++;
                                labels.add(string1);
                            } else { // if not
                                let node = {'id': nodeId, 'label': string1, 'cid': -1}
                                nodes.add(node);

                                //add to undo array
                                node.code = 1;
                                his_undo[count_undo].push(node);

                                tmpid2 = nodeId;
                                nodeId++;
                                labels.add(string1);
                            }
                            for (i of nodes.getIds()) { // iterate over all nodes
                                if (nodes.get(i).label == string1) {
                                    tmpid2 = i;
                                }
                            }
                        }
                        let edge = {
                            from: tmpid1,
                            to: tmpid2,
                            label: a[1].replace('<', '').replace('>', ''),
                            arrows: 'to'
                        };
                        edges.add([edge]);

                        //add to undo array
                        edge.code = 1;
                        his_undo[count_undo].push(edge);

                    } else { //if the object is a literal
                        string1 = a[2];
                        string1 = string1.replace('<', '');
                        string1 = string1.replace('>', '');
                        if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                            let node = {'id': nodeId, 'label': string1, 'cid': -1, color: '#FF3898'};
                            nodes.add(node);

                            //add to undo array
                            node.code = 1;
                            his_undo[count_undo].push(node);

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
                        let edge = {
                            from: tmpid1,
                            to: tmpid2,
                            label: a[1].replace('<', '').replace('>', ''),
                            arrows: 'to'
                        };
                        edges.add([edge]);

                        //add to undo array
                        edge.code = 1;
                        his_undo[count_undo].push(edge);

                    }

                } else { // if the subject is a literal

                    var string1 = a[0];
                    string1 = string1.replace('<', '');
                    string1 = string1.replace('>', '');
                    if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                        let node = {'id': nodeId, 'label': string1, 'cid': -1, color: '#FF3898'};
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
                                let node = {'id': nodeId, 'label': string1, 'cid': cid};
                                nodes.add(node);

                                //add to undo array
                                node.code = 1;
                                his_undo[count_undo].push(node);

                                cid++;
                                tmpid2 = nodeId;
                                nodeId++;
                                labels.add(string1);
                            } else { // if not
                                let node = {'id': nodeId, 'label': string1, 'cid': -1};
                                nodes.add(node);

                                //add to undo array
                                node.code = 1;
                                his_undo[count_undo].push(node);

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
                        let edge = {
                            from: tmpid1,
                            to: tmpid2,
                            label: a[1].replace('<', '').replace('>', ''),
                            arrows: 'to'
                        };
                        edges.add([edge]);

                        //add to undo array
                        edge.code = 1;
                        his_undo[count_undo].push(edge);

                    } else { //if the object is a literal
                        string1 = a[2];
                        string1 = string1.replace('<', '');
                        string1 = string1.replace('>', '');
                        if (!labels.has(string1)) { // if the node doesnt exist yet we ceate it
                            let node = {'id': nodeId, 'label': string1, 'cid': -1, color: '#FF3898'};
                            nodes.add(node);

                            //add to undo array
                            node.code = 1;
                            his_undo[count_undo].push(node);

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

                        let edge = {
                            from: tmpid1,
                            to: tmpid2,
                            label: a[1].replace('<', '').replace('>', ''),
                            arrows: 'to'
                        };
                        edges.add([edge]);

                        //add to undo array
                        edge.code = 1;
                        his_undo[count_undo].push(edge);

                    }
                }

            }
        });
        createQuery();
        console.log(query);

        count_undo++;
    };
    reader.onerror = (event) => {
        alert(event.target.error.name);
    };

    reader.readAsText(file);


}

function save() { // downloading the current Graph in NT format
    var text = "";
    for (i of edges.getIds()) { // iterate over all edges
        if (nodes.get(edges.get(i).from).color == '#FF3898') {
            text = text.concat(nodes.get(edges.get(i).from).label)
            text = text + "\t<"
        } else {
            nodeId.code = 0;
            text = text + "<"
            text = text.concat(nodes.get(edges.get(i).from).label)
            text = text + ">\t<"
        }
        text = text.concat(edges.get(i).label)
        text = text + ">\t"

        if (nodes.get(edges.get(i).to).color == '#FF3898') {
            text = text.concat(nodes.get(edges.get(i).to).label)
            text = text + "\t.\n"
        } else {
            text = text + "<"
            text = text.concat(nodes.get(edges.get(i).to).label)
            text = text + ">\t.\n"
        }


        var file_name_to_download = "graph"
        var file = new File([text], file_name_to_download + ".nt", {type: "application/octet-stream"}); // create a file for the download
        var blobUrl = (URL || webkitURL).createObjectURL(file);
        window.location = blobUrl;
    }
}

// cluster the selected nodes (hold to multiple select)
var cid = 0;

function clusterSelected() {
    if (network.getSelectedNodes().length < 2) {
        console.log("not enough nodes");
        return;
    }
    initializeUndo();
    var node = {id: nodeId, label: "cluster " + cid, cid: cid,};
    nodes.add(node);
    node.code = 1; //hinzufügen
    his_undo[count_undo].push(node);
    console.log("cluster mit cid " + nodes.get(nodeId).cid + " hinzugefügt")
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
        console.log(node);
    }

}

function initializeUndo() {
    if (!his_undo[count_undo]) {
        his_undo[count_undo] = [];
        console.log("Initialization of Undo successful");
    }
    // TODO: clean redo when und is initialized
    his_redo = [];
    count_redo = 0;
}

function initializeRedo() {
    if (!his_redo[count_redo]) {
        his_redo[count_redo] = [];
        console.log("Initialization of Redo successful");
    }
}

// Delete with backspace/delete button
document.addEventListener('keydown', function (params) {
    if (event.keyCode == 8 || event.keyCode == 46) {
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
            console.log(network.getSelectedEdges(0));
            for (let i = network.getSelectedEdges().length - 1; i >= 0; i--) {
                tempEdge = edges.get(network.getSelectedEdges()[0]);
                tempEdge.code = 0;
                his_undo[count_undo].push(tempEdge);
                edges.remove(network.getSelectedEdges(i)[0]);
            }
            count_undo++;
        }

    } else if (event.keyCode == 88) {
        console.log("Count Undo: " + count_undo);

        console.log("his_undo");
        console.log(his_undo);

        for (let i = 0; i < count_undo; i++) {
            for (let j = 0; j < his_undo[i].length; j++) {
                console.log("i: " + i + " j: " + j);
                console.log(his_undo[i][j]);
            }
        }

        console.log("Count Redo: " + count_redo);

        console.log("his_redo");
        console.log(his_redo);

        for (let i = 0; i < count_redo; i++) {
            for (let j = 0; j < his_redo[i].length; j++) {
                console.log("i: " + i + " j: " + j);
                console.log(his_redo[i][j]);
            }
        }
    } else if (event.keyCode == 78 && !(document.activeElement == document.getElementById("inpnode")) && !(document.activeElement == document.getElementById("inprename")) && !(document.activeElement == document.getElementById("inprenameedge")) && !(document.activeElement == document.getElementById("inpedge")) && !(document.activeElement == document.getElementById("inprenamecluster"))) {
        var myElement = document.getElementById("mod1");
        myElement.click();
        network.unselectAll();
        document.getElementById("inpnode").focus();
        setTimeout(function () {
                document.getElementById("inpnode").value = "";
            }
            , 1);
    } else if (event.keyCode == 69 && !(document.activeElement == document.getElementById("inpnode")) && !(document.activeElement == document.getElementById("inprename")) && !(document.activeElement == document.getElementById("inprenameedge")) && !(document.activeElement == document.getElementById("inpedge")) && !(document.activeElement == document.getElementById("inprenamecluster"))) {
        network.addEdgeMode();
    } else if (event.keyCode == 27) {
        network.disableEditMode();
    }

    // add to cluster
    else if (event.keyCode == 66 || event.keyCode == 32) {
        clusterSelected();
    }

    createQuery();
});

//Rename node or edge with double click
network.on('doubleClick', function (properties) {
    if (network.getSelectedNodes().length == 1) {
        tmpNode = network.getSelectedNodes()[0];
        if (nodes.get(tmpNode).cid > -1) {
            var myElement = document.getElementById("mod5");
            console.log(myElement);
            myElement.click();
            network.unselectAll();
            document.getElementById("inprenamecluster").focus();
            document.getElementById("inprenamecluster").value = nodes.get(tmpNode).label;

        } else {
            var myElement = document.getElementById("mod3");
            console.log(myElement);
            myElement.click();
            network.unselectAll();
            document.getElementById("inprename").focus();
            document.getElementById("inprename").value = nodes.get(tmpNode).label.replace('(Any)', '').replace('(Any)', '').replace('(Disease)', '').replace('(Drug)', '').replace('(Gene)', '').replace('(Species)', '').replace('(Mutation)', '').replace('(CellLine)', '');
            //var name = prompt("Enter new name of node: ");
            //nodes.update({id: nodeId, label: name});
        }
    } else if (edges.get(network.getSelectedEdges()[0]).label == "part_of") {
        console.log("nothing happens");
        return 0;
    } else if (network.getSelectedEdges().length == 1) {
        console.log("testets");
        //var edgeId = network.getSelectedEdges()[0];
        tmpEdgeRename = network.getSelectedEdges()[0];
        var myElement = document.getElementById("mod4");
        myElement.click();
        network.unselectAll();
        document.getElementById("inprenameedge").focus();
        document.getElementById("inprenameedge").value = edges.get(tmpEdgeRename).label;
        /*
        let tempEdge = edges.get(edgeId);
        var name = prompt("Enter new name of edge: ");
        if (name != null && name != "") {
          edges.update({label: name,  id: edgeId});
          initializeUndo();
          his_undo[count_undo].push(tempEdge);
          count_undo++;
        }*/
    }
});

function undo() {
    if (his_undo.length == 0) {
        console.log("nothing to undo");
        return;
    }

    initializeRedo();

    for (e of his_undo.pop()) {
        console.log("e.id, pushed to redo: " + e.id);
        switch (e.code) {
            case 0:
                if (e.id > -1) {
                    nodes.add(e);
                    his_redo[count_redo].push(e);
                } else {
                    edges.add(e);
                    his_redo[count_redo].push(e);
                }
                break;
            case 1:
                if (e.id > -1) {
                    console.log("e.id, removed id: " + e.id);
                    nodes.remove(e);
                    his_redo[count_redo].push(e);
                } else {
                    edges.remove(e);
                    his_redo[count_redo].push(e);
                }
                break;
            case 2:
                if (e.id > -1) {
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
                    his_redo[count_redo].push(e);
                } else {
                    console.log("e.id, updated id: " + e.id);

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

function redo() {
    if (his_redo.length == 0) {
        console.log("nothing to redo");
        return;
    }
    console.log("his_redo");
    console.log(his_redo);

// initialize undo
    if (!his_undo[count_undo]) {
        his_undo[count_undo] = [];
        console.log("Initialization of Undo successful");
    }

    for (e of his_redo.pop()) {
        console.log(e);
        switch (e.code) {
            case 0:
                if (e.id > -1) {
                    console.log("e.id, removed id, redo: " + e.id);
                    nodes.remove(e);
                    his_undo[count_undo].push(e);
                } else {
                    console.log("e.id, removed id, redo: " + e.id);
                    edges.remove(e);
                    his_undo[count_undo].push(e);
                }
                break;
            case 1:
                if (e.id > -1) {
                    console.log("e.id, removed id, redo: " + e.id);
                    nodes.add(e);
                    his_undo[count_undo].push(e);
                } else {
                    console.log("e.id, removed id, redo: " + e.id);
                    edges.add(e);
                    his_undo[count_undo].push(e);
                }
                break;
            case 2:

                if (e.id > -1) { // e is node
                    console.log("e.id, updated id, redo: " + e.id);

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
                    console.log("e.id, updated id, redo: " + e.id);

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

network.on('click', function (params) {
    cursorPosition = {'x': params.pointer.canvas.x, 'y': params.pointer.canvas.y};

    console.log("x: " + cursorPosition.x + ", y: " + cursorPosition.y);
})

function createQuery() {
    query = "";
    for (i of edges.getIds()) { // iterate over all edges
        query = query.concat(nodes.get(edges.get(i).from).label.replace(' ', '_'))
        query = query + " "
        query = query.concat(edges.get(i).label)
        query = query + " "
        query = query.concat(nodes.get(edges.get(i).to).label.replace(' ', '_'))
        query = query + ";"
    }
    // remove last ;
    query = query.substring(0, query.length - 1);
    if (query != oldQuery) {

        document.getElementById("id_keywords").value = query;
        oldQuery = query;
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
}
