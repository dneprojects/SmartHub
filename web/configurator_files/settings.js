const save_btn = document.getElementById("config_button_sv");
const teach_btn = document.getElementsByName("TeachNewFinger")[0];
const check_boxes = document.getElementsByClassName("sel_element");
const settngs_buttons = document.getElementsByName("ModSettings");
for (let i = 0; i < settngs_buttons.length; i++) {
    if (settngs_buttons[i].innerHTML == "entfernen") {
        del_btn = settngs_buttons[i];
        break;
    }
}
var new_cntr_btn = document.getElementsByClassName("new_cntr_button")[0];
if (new_cntr_btn == null) {
    new_btn = document.getElementsByClassName("new_button")[0];
}
else {
    new_btn = new_cntr_btn;
}
const max_btn = document.getElementById("max_cnt")
const new_addr = document.getElementsByName("new_entry")[0]
const setngs_tbl = document.getElementById("set_tbl");
if (new_addr != null) {
    new_addr.addEventListener("change", function(){
    parseNewAddr()
    })
}
if (new_cntr_btn != null) {
    new_cntr_btn.addEventListener("click", function(){
    getCounterOptions()
    })
}
max_btn.addEventListener("click", function(){
    getMaxCount()
    })
for (let i = 0; i < check_boxes.length; i++) {
    check_boxes[i].addEventListener("change", function () {
        controlDelButton();
    })
}
controlNewButton();
controlDelButton();

function controlNewButton()  {
    if (new_btn != null) {
        new_btn.disabled = true;  // for modules only
        if ((new_addr.value != "") & (setngs_tbl.rows.length - 2 < parseInt(new_addr.max))) {
                new_btn.disabled = false;
        }
        if (setngs_tbl.rows.length - 2 >= parseInt(new_addr.max)) {
            new_addr.disabled = true;
        }
    }
    
}
function controlDelButton()  {
    if (del_btn != null) {
        del_btn.disabled = true;  // for modules only
        for (let i = 0; i < check_boxes.length; i++) {
            if (check_boxes[i].checked) {
                del_btn.disabled = false;
                break;
            }
        }
    }
}

var fngrNames = {}
if (save_btn != null) {
    save_btn.addEventListener("click", function () {
    openMsgPopup();
    });
}
if (teach_btn != null) {
    teach_btn.addEventListener("click", function () {
    openTeachPopup();
    });
}
close_popup.addEventListener("click", function () {
    teach_popup.classList.remove("show");
});

function openMsgPopup() {
    sav_popup.classList.add("show");
};
function openTeachPopup() {
    fngrNmbr = settings_table.elements["new_entry"].value;
    fngr_nmbr_2_teach.value = fngrNmbr + ' ' + fngrNames[fngrNmbr];
    teach_start.value = teach_start.value.slice(0, -1) + fngrNmbr;
    teach_popup.classList.add("show");
};
function getCounterOptions() {
    if (new_addr.value != "")
        count_popup.classList.add("show");
};
function getMaxCount() {
    max_btn.value += document.getElementById("max_count_input").value
}

function parseNewAddr() {
    controlNewButton()
    existing_numbers = [];
    min_number = new_addr.min;
    max_number = parseInt(new_addr.max);
    for (var i = 0; i < setngs_tbl.rows.length - 2; i++) {
        lbl = setngs_tbl.rows[i].cells[0].innerText.split(/\s*[\s,]\s*/);
        existing_numbers.push(lbl[lbl.length - 1]);
    }
    let nn = new_addr.value
    while (existing_numbers.includes(nn)) {
        nn = String(parseInt(nn) + 1);
    }
    if (parseInt(nn) > max_number) {
        nn = String(parseInt(nn) - 1)
        while (existing_numbers.includes(nn)) {
            nn = String(parseInt(nn) - 1);
        }
    }
    new_addr.value = nn
}