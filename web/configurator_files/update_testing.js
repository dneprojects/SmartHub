const refresh_btn = document.getElementById("config_button");
const inp_check_boxes = document.getElementsByClassName("inp_chk");
const out_check_boxes = document.getElementsByClassName("out_chk");

const inTable = document.getElementById("mod-inputs-table")
const outTable = document.getElementById("mod-outputs-table")
const evntTable = document.getElementById("mod-events-table")

refresh_btn.addEventListener("click", function () {
    getStatus();
});

for (let i = 0; i < inp_check_boxes.length; i++) {
    inp_check_boxes[i].addEventListener("change", function () {
        undoChecking(i);
    })
}
for (let i = 0; i < out_check_boxes.length; i++) {
    out_check_boxes[i].addEventListener("change", function () {
        setOutput(i);
    })
}

watchEventStatus();

async function watchEventStatus() {

    await setInterval(function () {
        // alle 0.5 Sekunden ausführen 
        getEvents();
    }, 500);
}

function undoChecking(i) {
    inp_check_boxes[i].checked = !inp_check_boxes[i].checked;
}

function setOutput(i) {
    if (out_check_boxes[i].checked)
        val = 1;
    else
        val = 0;
    const statusUrl = "test/set_output?=" + (i + 1) + "-" + val
    fetch(statusUrl)
        .then((resp) => resp.text())
        .catch(function (error) {
            console.log(error);
        });
}

function getStatus() {
    const statusUrl = "test/refresh"
    fetch(statusUrl)
        .then((resp) => resp.text())
        .catch(function (error) {
            console.log(error);
        });
}

function getEvents() {
    const statusUrl = "test/events"
    fetch(statusUrl)
        .then((resp) => resp.text())
        .then(function (text) {
            setEventStatus(text);
        })
        .catch(function (error) {
            console.log(error);
        });
}

function setEventStatus(jsonString) {
    if (inTable) {
        for (let r = 1; r < inTable.rows.length; r++) {
            if (inTable.rows[r].cells[3].innerHTML.slice(0, 2) == "<p")
                inTable.rows[r].cells[3].innerHTML = "Taste"
        }
    }
    if (jsonString == "{}")
        return
    var eventStat = JSON.parse(jsonString);
    outputStat = eventStat.Output;
    buttonsStat = eventStat.Button;
    switchStat = eventStat.Switch;
    coverStat = eventStat.Cover_position;
    blindStat = eventStat.Blind_position;
    fingerStat = eventStat.Ekey_finger;
    irStat = eventStat.IR_command;
    dirStat = eventStat.Direct_command;
    modeStat = eventStat.Mode;
    flagStat = eventStat.Flag;
    if (outputStat) {
        for (let i = 0; i < outputStat.length; i++) {
            row = outTable.rows[outputStat[i][0]];
            if (outputStat[i][1])
                row.cells[3].children[0].checked = true
            else
                row.cells[3].children[0].checked = false
        }
    }
    if (buttonsStat) {
        for (let i = 0; i < buttonsStat.length; i++) {
            row = inTable.rows[buttonsStat[i][0]];
            msg1 = "Taste " + (i + 1).toString() + ": '" + row.cells[1].innerHTML + "'"
            if (buttonsStat[i][1] == 1) {
                cellText = '<p id="button-evnt">kurz</p>'
                msg2 = "kurz"
            }
            if (buttonsStat[i][1] == 2) {
                cellText = '<p id="button-evnt">lang</p>'
                msg2 = "lang"
            }
            if (buttonsStat[i][1] == 3) {
                cellText = '<p id="button-evnt">Ende</p>'
                msg2 = "Ende"
            }
            row.cells[3].innerHTML = cellText
            logEvent(msg1, msg2)
        }
    }
    if (switchStat) {
        for (let i = 0; i < switchStat.length; i++) {
            row = inTable.rows[switchStat[i][0]];
            if (switchStat[i][1])
                row.cells[3].children[0].checked = true
            else
                row.cells[3].children[0].checked = false
        }
    }
    if (coverStat) {
        outIdx = (coverStat[coverStat.length - 1][0] + 1) * 2;
        outName = outTable.rows[outIdx].cells[1].innerHTML
        outParts = outName.split(" ")
        coverName = outName.replace(outParts[outParts.length - 1], "").trim()
        msg1 = "Cover " + (coverStat[coverStat.length - 1][0] + 1).toString() + ": '" + coverName + "'";
        msg2 = coverStat[coverStat.length - 1][1].toString() + "%";
        logEvent(msg1, msg2)
    }
    if (blindStat) {
        outIdx = (blindStat[blindStat.length - 1][0] + 1) * 2;
        outName = outTable.rows[outIdx].cells[1].innerHTML
        outParts = outName.split(" ")
        coverName = outName.replace(outParts[outParts.length - 1], "").trim()
        msg1 = "Cover " + (blindStat[blindStat.length - 1][0] + 1).toString() + ": '" + coverName + "'";
        msg2 = blindStat[blindStat.length - 1][1].toString() + "%";
        logEvent(msg1, msg2)
    }
    if (fingerStat) {
        msg1 = "Fingerprint Person " + fingerStat[fingerStat.length - 1][0].toString();
        msg2 = fingerStat[fingerStat.length - 1][1].toString();
        logEvent(msg1, msg2)
    }
    if (irStat) {
        msg1 = "IR Befehl";
        msg2 = irStat[irStat.length - 1][0].toString() + ", " + irStat[irStat.length - 1][1].toString();
        logEvent(msg1, msg2)
    }
    if (dirStat) {
        msg1 = "Direkt-Befehl " + dirStat[dirStat.length - 1][0].toString();
        msg2 = "";
        logEvent(msg1, msg2)
    }
    if (modeStat) {
        msg1 = "Modus von Gruppe " + modeStat[modeStat.length - 1][0].toString();
        msg2 = modeStat[modeStat.length - 1][1].toString();
        logEvent(msg1, msg2)
    }
    if (flagStat) {
        msg1 = "Merker " + (flagStat[flagStat.length - 1][0] + 1).toString();
        if (flagStat[flagStat.length - 1][1] == 1)
            msg2 = "aktiv";
        else
            msg2 = "inaktiv";
        logEvent(msg1, msg2)
    }
}

function logEvent(msg1, msg2) {

    const d = new Date();
    let time = d.toLocaleString();
    const log_len = 5
    for (let r = log_len; r > 1; r--) {
        for (let c = 0; c < 3; c++) {
            evntTable.rows[r].cells[c].innerHTML = evntTable.rows[r - 1].cells[c].innerHTML;
        }
    }
    evntTable.rows[1].cells[0].innerHTML = time.split(",")[1];
    evntTable.rows[1].cells[1].innerHTML = msg1;
    evntTable.rows[1].cells[2].innerHTML = msg2;

}