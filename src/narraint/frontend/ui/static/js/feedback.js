let imgrect = {width: 0, height: 0};
document.getElementById("screenshot").addEventListener('load', (e) => {
    imgrect = e.target.getBoundingClientRect();
});

async function openFeedback() {
    console.log("click")

    const feedbackBtnTxt = document.getElementById("feedbackbtn_text");
    feedbackBtnTxt.innerText = "Generating Screenshot (may take a while)";
    document.getElementById("feedbackText").value = "";

    await new Promise(r => setTimeout(r, 10));

    let canvas = await html2canvas(document.body, {scrollX: 0, scrollY: 0, logging:false})

    const base64image = canvas.toDataURL("image/png");
    const screenshot = document.getElementById("screenshot");

    screenshot.src = base64image;

    document.body.style.overflowY = "hidden";
    const popup = document.getElementById("feedbackPopup");
    popup.style.display = "block"

    feedbackBtnTxt.innerText = "Feedback";

    document.getElementById("screenshotCanvas").remove();

    let screenshotCanvas = document.createElement("canvas");
    screenshotCanvas.id = "screenshotCanvas";
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

    const combine_canvas = document.createElement("canvas");
    const drawCanvas = document.getElementById("screenshotCanvas");
    const screenshot = document.getElementById("screenshot");
    const textArea = document.getElementById("feedbackText");
    combine_canvas.width = drawCanvas.width;
    combine_canvas.height = drawCanvas.height;
    let ctx = combine_canvas.getContext('2d')
    ctx.drawImage(screenshot, 0, 0)
    ctx.drawImage(drawCanvas, 0, 0)

    const params = {
        description: textArea.value,
        img64: combine_canvas.toDataURL("image/png")
    };
    const options = {
        method: 'POST',
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
