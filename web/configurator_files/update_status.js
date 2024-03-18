const flash_btn = document.getElementById("flash_button");
flash_btn.addEventListener("click", function () {
    watchUpdateStatus();
});
async function watchUpdateStatus() {
    
    await setInterval(function() { 
        // alle 3 Sekunden ausführen 
        getStatus(); 
    }, 1000);
}

function getStatus() {
    const statusUrl = "/update_status"
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

    for (let i = 0; i < modsList.length; i++) {
        modAddr = modsList[i];
        modKey = "mod_" + modAddr;
        modStat = updateStat[modKey];
        prog = modStat.progress;
        console.log("Progress: " + prog);
        success = modStat.success;
        lbl = document.getElementById("stat_" + modAddr);
        if ((upldStat < 100) & (i == 0)) {
            lbl.className = 'fw_subtext_bold';
            lbl.innerText = "Upload: " + upldStat + "%";
        }
        else if (prog < 100) {
            if (i > 0) {
                last_lbl = document.getElementById("stat_" + modsList[i - 1])
                last_lbl.className = 'fw_subtext';
            }
            lbl.className = 'fw_subtext_bold';
            lbl.innerText = "Flashen: " + prog + "%";
        }
        else if (prog == 100) {
            lbl.className = 'fw_subtext_bold';
            lbl.innerText = "Flashen: " + success;
        }
    }
}
