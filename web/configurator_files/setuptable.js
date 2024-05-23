const mod_ids = document.getElementsByClassName("mod_ids");
const mod_chans = document.getElementsByClassName("mod_chans");
const sort_tbl = document.getElementById("sort_table")

for (let i = 0; i < mod_ids.length; i++) {
    mod_ids[i].addEventListener("change", function () {
        parseModIds(mod_ids[i]);
    })
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