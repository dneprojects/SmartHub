const mod_ids = document.getElementsByClassName("mod_ids");
const mod_chans = document.getElementsByClassName("mod_chans");
const sort_tbl = document.getElementById("sort_table");
const rem_button = document.getElementById("tbl-button");
const chk_boxes = document.getElementsByClassName("mod_sels");
const mod_table = document.getElementById("mod-table")

rem_button.addEventListener("click", function () {
    removeModules()
})

for (let i = 0; i < mod_ids.length; i++) {
    mod_ids[i].addEventListener("change", function () {
        parseModIds(mod_ids[i]);
    })
}

for (let i = 0; i < chk_boxes.length; i++) {
    chk_boxes[i].addEventListener("change", function () {
        controlRemoveButton();
    })
}

function controlRemoveButton() {
    if (rem_button != null) {
        rem_button.disabled = true;  // for modules only
        for (let i = 0; i < chk_boxes.length; i++) {
            if (chk_boxes[i].checked) {
                rem_button.disabled = false;
                break;
            }
        }
    }
}

function removeModules() {
    var no_lines = chk_boxes.length;
    var rem_lines = [];
    for (let i = 0; i < no_lines; i++) {
        if (chk_boxes[i].checked) {
            rem_lines.push(chk_boxes[i].parentElement.parentElement.rowIndex);
        }
    }
    var del_lines = rem_lines.length;
    for (let i = 0; i < del_lines; i++) {
        mod_table.rows[rem_lines.pop()].remove();
    }
    rem_button.disabled = true;
}

function parseModIds(hdl) {
    mod_id = hdl.id.replace('mod-', '');
    existing_numbers = [];
    for (let i = 0; i < mod_ids.length; i++) {
        if (mod_ids[i].id != hdl.id) {
            existing_numbers.push(mod_ids[i].value * 1)
        }
    }
    min_number = parseInt(hdl.min);
    max_number = parseInt(hdl.max);
    let nn = hdl.value
    while (existing_numbers.includes(parseInt(nn))) {
        nn = String(parseInt(nn) + 1);
    }
    if (parseInt(nn) > max_number) {
        nn = String(parseInt(nn) - 1)
        while (existing_numbers.includes(nn)) {
            nn = String(parseInt(nn) - 1);
        }
    }
    hdl.value = nn
};