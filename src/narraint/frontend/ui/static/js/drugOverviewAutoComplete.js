

async function getDrugNames(current) {
    return fetch(autocompletion_url + "?term=" + current + "&entity_type=Drug")
        .then(response => response.json())
        .then(data => {
            return data.terms;
        });
    //return ["Aspirin","Ibuprofen","Asopolon","Ibumprumfum","Paracetamol","Pampelmuse"];
}

function autoComplete(input, entity_type) {
    var names;
    var currentFocus;
    input.addEventListener("input", function(e) {
        closeAllLists();
        var value = this.value;
        if (value == "") {
            return false;
        }
        currentFocus = -1;
        var outerDiv = document.createElement("div");
        outerDiv.id = this.id + "autocomplete";
        outerDiv.classList.add("autocomplete-items");
        outerDiv.classList.add("dropdown-menu");
        outerDiv.style.width = `${input.clientWidth}px`;
        this.parentNode.appendChild(outerDiv);
        //names = getDrugNames(value);
        //console.log(names);
        let url_call = autocompletion_url + "?term=" + value;
        if (entity_type) {
            url_call += "&entity_type=" + entity_type;
        }
        fetch(url_call)
        .then(response => response.json())
        .then(data => {
            for (var i = 0; i < data.terms.length; i++) {
                var itemDiv = document.createElement("div");
                itemDiv.innerHTML = "<strong>" + data.terms[i].substring(0, value.length) + "</strong>" + data.terms[i].substring(value.length) + "<input type='hidden' value='" + data.terms[i] + "'>";
                itemDiv.addEventListener("click", function(e) {
                    input.value = this.getElementsByTagName("input")[0].value;
                    closeAllLists();
                });
                outerDiv.appendChild(itemDiv);
            }
        });
    });
    input.addEventListener("keydown", function(e){
        var itemDivs = document.getElementById(this.id + "autocomplete");
        if (itemDivs) {
            itemDivs = itemDivs.getElementsByTagName("div");
        }
        if (e.keyCode == 40) {
            currentFocus++;
            addActive(itemDivs);
        } else if (e.keyCode == 38) {
            currentFocus--;
            addActive(itemDivs);
        } else if (e.keyCode == 13) {
            e.preventDefault();
            if (currentFocus > -1) {
                itemDivs[currentFocus].click();
            }
            searchDrug();
        }
    });
    document.addEventListener("click", function (e) {
        closeAllLists(e.target);
    });
    function addActive(itemDivs) {
        if (!itemDivs){
            return;
        }
        removeActive(itemDivs);
        if (currentFocus >= itemDivs.length) {
            currentFocus = 0;
        } else if (currentFocus < 0) {
            currentFocus = itemDivs.length - 1;
        }
        itemDivs[currentFocus].classList.add("autocomplete-active");
    }
    function removeActive(itemDivs) {
        for (var i = 0; i < itemDivs.length; i++) {
          itemDivs[i].classList.remove("autocomplete-active");
        }
    }
    function closeAllLists(element) {
        var outerDivs = document.getElementsByClassName("autocomplete-items");
        for (var i = 0; i < outerDivs.length; i++) {
            if (element != outerDivs[i] && element != input) {
                outerDivs[i].parentNode.removeChild(outerDivs[i]);
            }
        }
    }
}