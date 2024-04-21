const flash_btn = document.getElementById("flash_button");
const check_boxes = document.getElementsByClassName("mod_chk");
flash_btn.addEventListener("click", function () {
    watchUpdateStatus();
});
for (let i = 0; i < check_boxes.length; i++) {
    check_boxes[i].addEventListener("change", function () {
        control_flashbutton();
    })
}
control_flashbutton();

function control_flashbutton() {
    if (document.getElementById("stat_0") == null)
        flash_btn.disabled = true;  // for modules only
    for (let i = 0; i < check_boxes.length; i++) {
        if (check_boxes[i].checked) {
            flash_btn.disabled = false;
            break;
        }
    }
}

async function watchUpdateStatus() {
    
    await setInterval(function() { 
        // alle 3 Sekunden ausführen 
        getStatus(); 
    }, 3000);
}

function getStatus() {
    const statusUrl = "update_status"
    fetch(statusUrl)
        .then((resp) => resp.text())
        .then(function(text) {
            setStatus(text);
        })
        .catch(function(error) {
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
