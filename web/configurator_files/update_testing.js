const refresh_btn = document.getElementById("config_button");
const inp_check_boxes = document.getElementsByClassName("inp_chk");
const out_check_boxes = document.getElementsByClassName("out_chk");
refresh_btn.addEventListener("click", function () {
    watchUpdateStatus();
});
for (let i = 0; i < out_check_boxes.length; i++) {
    out_check_boxes[i].addEventListener("change", function () {
        setOutput(i);
    })
}

async function watchUpdateStatus() {

    await setInterval(function () {
        // alle 3 Sekunden ausführen 
        getStatus();
    }, 3000);
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
    const statusUrl = "update_status"
    fetch(statusUrl)
        .then((resp) => resp.text())
        .then(function (text) {
            setStatus(text);
        })
        .catch(function (error) {
            console.log(error);
        });
}

function setStatus(jsonString) {
    var updateStat = JSON.parse(jsonString);
    upldStat = updateStat.upload;
    modsList = updateStat.modules
    cur_mod = updateStat.cur_mod;

    if (cur_mod < 0) {
        // upload
        lbl = document.getElementById("stat_" + modsList[0]);
        lbl.className = 'fw_subtext_bold';
        lbl.innerText = "Upload: " + upldStat + "%";
    }
    else {
        modKey = "mod_" + cur_mod;
        modStat = updateStat[modKey];
        prog = modStat.progress;
        success = modStat.success;
        lbl = document.getElementById("stat_" + cur_mod);
        if (prog < 100) {
            lbl.className = 'fw_subtext_bold';
            lbl.innerText = "Flashen: " + prog + "%";
        }
        else if ((upldStat == 100) & (prog == 100)) {
            lbl.innerText = "Flashen: " + success;
        }
    }
}
