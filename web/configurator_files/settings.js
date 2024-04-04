const save_btn = document.getElementById("config_button_sv");
const teach_btn = document.getElementsByName("TeachNewFinger")[0];
const check_boxes = document.getElementsByClassName("sel_element");
const del_btn = document.getElementsByName("ModSettings")[1];
var new_btn = document.getElementsByClassName("new_cntr_button")[0];
if (new_btn == null) {
    new_btn = document.getElementsByClassName("new_button")[0];
}
const max_btn = document.getElementById("max_cnt")
const new_number = document.getElementsByName("new_entry")[0]
const setngs_tbl = document.getElementById("set_tbl");
if (new_number != null) {
    new_number.addEventListener("change", function(){
    parseNewNumber()
    })
}
if (new_btn != null) {
    new_btn.addEventListener("click", function(){
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
        if ((new_number.value != "") & (setngs_tbl.rows.length - 2 < parseInt(new_number.max))) {
                new_btn.disabled = false;
        }
        if (setngs_tbl.rows.length - 2 >= parseInt(new_number.max)) {
            new_number.disabled = true;
        }
    }
    
}
function controlDelButton()  {
    if (del_btn.innerHTML == "entfernen") {
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
    if (new_number.value != "")
        count_popup.classList.add("show");
};
function getMaxCount() {
    max_btn.value += document.getElementById("max_count_input").value
}

function parseNewNumber() {
    controlNewButton()
    existing_numbers = [];
    min_number = new_number.min;
    max_number = parseInt(new_number.max);
    for (var i = 0; i < setngs_tbl.rows.length - 2; i++) {
        lbl = setngs_tbl.rows[i].cells[0].innerText.split(/\s*[\s,]\s*/);
        existing_numbers.push(lbl[lbl.length - 1]);
    }
    let nn = new_number.value
    while (existing_numbers.includes(nn)) {
        nn = String(parseInt(nn) + 1);
    }
    if (parseInt(nn) > max_number) {
        nn = String(parseInt(nn) - 1)
        while (existing_numbers.includes(nn)) {
            nn = String(parseInt(nn) - 1);
        }
    }
    new_number.value = nn
}