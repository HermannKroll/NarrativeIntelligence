async function loadPeopleJSON(url) {
    const res = await fetch(url);
    return await res.json();
}

async function sendJsonRequest(person_name) {
    try {
        const response = await $.ajax({
            url: people_url,
            data: {person: person_name}
        });
        return response;
    } catch (error) {
        console.log(error);
    }
}

loadPeopleJSON('/static/people.json').then(data => {
    if (localStorage.getItem("current_person") == "" || localStorage.getItem("current_person") == undefined) {
        localStorage.setItem("current_person", data[0]);
        sendJsonRequest(data[0]).then(received_data => {
            received_data.people = data;
            loadPage(received_data);
        });
    } else {
        sendJsonRequest(localStorage.getItem("current_person")).then(received_data => {
            received_data.people = data;
            loadPage(received_data);
        });
    }

});


function loadPage(data) {
    let navbarHeaderTemplate = Handlebars.compile($('#navbar-header-template').html());
    $('#navbar-header').html(navbarHeaderTemplate(data));
    setHeader(data.name);
    setPersonEventListener(data.people);
    setRolesEventListener(data.roles);
    // let sectionTemplate = Handlebars.compile($('#sections-template').html());
    // $('#sections').html(sectionTemplate({sections: refactorSections(data.roles[0].section_data)}));
    // initializeNewsArticle();
    document.getElementById(stringToLowerWithoutSpaces(data.roles[0].name)).click();
}

function stringToLowerWithoutSpaces(str, replacement = "") {
    return str.toLowerCase().replace(/ /g, replacement);
}

function dropdownRoleId(str) {
    return "nav-" + stringToLowerWithoutSpaces(str, "-");
}

function navbarId(str) {
    return stringToLowerWithoutSpaces(str, "-") + "-item";
}

function roleButtonId(str) {
    return "input-" + stringToLowerWithoutSpaces(str);
}

function dropdownPersonId(str) {
    return "person-" + stringToLowerWithoutSpaces(str, "-");
}

function setHeader(name) {
    document.getElementById("headline").innerHTML = name;
}

Handlebars.registerHelper('toLowerCaseWithoutSpaces', function (str) {
    return stringToLowerWithoutSpaces(str);
});

Handlebars.registerHelper('toLowerCaseWithHyphen', function (str) {
    return stringToLowerWithoutSpaces(str, "-")
});

Handlebars.registerHelper('dropdownRole', function (str) {
    return dropdownRoleId(str)
});

Handlebars.registerHelper('dropdownPerson', function (str) {
    return dropdownPersonId(str)
});

Handlebars.registerHelper('navbarItem', function (str) {
    return navbarId(str);
});

Handlebars.registerHelper('roleButton', function (str) {
    return roleButtonId(str);
});

function setRolesEventListener(roles) {
    roles.forEach(role => {
        document.getElementById(dropdownRoleId(role.name)).addEventListener("click", function () {
            document.getElementById(stringToLowerWithoutSpaces(role.name)).click();
        });
        document.getElementById(stringToLowerWithoutSpaces(role.name)).addEventListener("click", function () {
            if (!document.getElementById(roleButtonId(role.name)).checked) {
                const relevant_section_data = role.section_data;
                let sectionTemplate = Handlebars.compile($('#sections-template').html());
                $('#sections').html(sectionTemplate({sections: refactorSections(relevant_section_data)}));

            }
        });
    })
}


function setPersonEventListener(people) {
    people.forEach(person => {
        document.getElementById(dropdownPersonId(person)).addEventListener("click", function () {
            loadPeopleJSON('/static/people.json').then(data => {
                localStorage.setItem("current_person", person);
                sendJsonRequest(person).then(received_data => {
                    received_data.people = data;
                    loadPage(received_data);
                });
            });
        });
    })
}


function refactorSections(sections) {
    sections.forEach(section => {
        let newArticles = [];
        let currentItem = -1;
        section.articles.forEach((article, index) => {
            if ((index + 5) % 5 == 0) {
                currentItem++;
                newArticles.push([]);
            }
            let newArticle = {};
            newArticle["newspaper"] = article.newspaper;
            newArticle["headline"] = article.headline;
            newArticle["text"] = article.text;
            newArticle["url"] = article.url;
            newArticles[currentItem].push(newArticle);
        });
        section.articlesform = newArticles;
    });
    return sections;
}

function initializeNewsArticle() {
    if (screen.availWidth - window.innerWidth === 0) {
        let newspaperCarousel = document.getElementsByClassName("carousel-inner")[0];
        let carouselWidth = newspaperCarousel.offsetWidth;
        let newspaperCardWidth = carouselWidth * 0.186;
        let newsArticle = document.getElementsByClassName("news-article");
        for (let i = 0; i < newsArticle.length; i++) {
            newsArticle[i].style.cssText = 'max-width: ' + newspaperCardWidth.toString() + 'px !important';

        }
    }
}

window.onresize = (event) => {
    initializeNewsArticle();
};
