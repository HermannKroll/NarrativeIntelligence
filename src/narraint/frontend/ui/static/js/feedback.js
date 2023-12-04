let imgrect = {width: 0, height: 0};
document.getElementById("screenshot").addEventListener('load', (e) => {
    imgrect = e.target.getBoundingClientRect();
});

async function openFeedback() {
    const spinner = document.getElementById("reportSpinner");
    const buttonText = document.getElementById("feedbackbtn_text");
    const button = document.getElementById("feedback_button");
    buttonText.innerText = "Generating Screenshot (may take a while)";
    spinner.style.display = "inline-block";
    button.classList.add("disabled");

    await new Promise(r => setTimeout(r, 10));

    let canvas = await html2canvas(document.body, {scrollX: 0, scrollY: 0, logging:false})
        .catch((e) => console.log(e));
    if (!canvas) {
        buttonText.innerText = "Feedback";
        spinner.style.display = "none";
        button.classList.remove("disabled");
        return;
    }

    const base64image = canvas.toDataURL("image/png");
    const screenshot = document.getElementById("screenshot");

    screenshot.src = base64image;

    document.body.style.overflowY = "hidden";
    const popup = document.getElementById("feedbackPopup");
    popup.style.display = "block"

    buttonText.innerText = "Feedback";
    spinner.style.display = "none";
    button.classList.remove("disabled");

    document.getElementById("screenshotCanvas").remove();

    let screenshotCanvas = document.createElement("canvas");
    screenshotCanvas.id = "screenshotCanvas";
    screenshotCanvas.classList.add("coveringCanvas");
    document.getElementById("screenshotContainer").append(screenshotCanvas);

    screenshotCanvas.setAttribute('width', canvas.width);
    screenshotCanvas.setAttribute('height', canvas.height);

    screenshotCanvas.onmousemove = (e) => draw(e)
    screenshotCanvas.onmousedown = (e) => setPosition(e);
    screenshotCanvas.onmouseenter = (e) => setPosition(e);

    let ctx = screenshotCanvas.getContext('2d')


    let pos = {x: 0, y: 0};
    function draw(e) {
        if (e.buttons !== 1) {
            return;
        }
        ctx.beginPath();

        ctx.lineWidth = 5;
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#c0392b';

        ctx.moveTo(pos.x, pos.y);
        setPosition(e);
        ctx.lineTo(pos.x, pos.y);

        ctx.stroke();
    }

    function setPosition(e) {
        let rect = e.target.getBoundingClientRect();
        pos.x = (e.clientX - rect.left) * canvas.width / imgrect.width;
        pos.y = (e.clientY - rect.top) * canvas.height / imgrect.height;
    }
}

async function closeFeedback(send = false) {
    const feedbackPopup = document.getElementById("feedbackPopup");

    if(!send) {
        feedbackPopup.style.display = "none";
        document.body.style.overflowY = "auto";
        return;
    }

    const combineCanvas = document.createElement("canvas");
    const drawCanvas = document.getElementById("screenshotCanvas");
    const screenshot = document.getElementById("screenshot");
    const textArea = document.getElementById("feedbackText");
    const MAX_WIDTH = 1920;
    // resize if the screenwidth is larger than 1920px
    const targetWidth = (drawCanvas.width > MAX_WIDTH) ? MAX_WIDTH: drawCanvas.width;
    const targetHeight = (drawCanvas.width > MAX_WIDTH) ? drawCanvas.height * (MAX_WIDTH / drawCanvas.width): drawCanvas.height;

    combineCanvas.width = targetWidth;
    combineCanvas.height = targetHeight;
    let ctx = combineCanvas.getContext('2d')
    ctx.drawImage(screenshot, 0, 0, targetWidth, targetHeight)
    ctx.drawImage(drawCanvas, 0, 0, targetWidth, targetHeight)

    const params = {
        description: textArea.value,
        img64: combineCanvas.toDataURL("image/png")
    };
    const options = {
        method: 'POST',
        headers: {'X-CSRFToken': csrftoken, "Content-type": "application/json"},
        mode: 'same-origin',
        body: JSON.stringify(params)
    };
    await fetch(url_feedback_report, options).then(response => {
            if (response.ok) {
                alert("Report successfully sent!");
                return;
            }

            alert("Sending report has failed!");
        }
    )
    feedbackPopup.style.display = "none";
    document.body.style.overflowY = "auto";
}

function resetCanvas() {
    const canvas = document.getElementById("screenshotCanvas");
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
}
