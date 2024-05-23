const ok_btn = document.getElementById("add-mod-ok");
const type_imgs = document.getElementsByName("add_type_img");
const close_popup = document.getElementById("close-button");
const newmod_popup = document.getElementById("newmod-popup");
const newmod_form = document.getElementById("form-mod-addr");
const new_addr = document.getElementById("mod_addr_input");
const new_ser = document.getElementById("mod_serial_input");
parseNewAddr()

for (let i = 0; i < type_imgs.length; i++) {
    type_imgs[i].addEventListener("click", function () {
        getModuleOptions(type_imgs[i].id);
    })
}

close_popup.addEventListener("click", function () {
    newmod_popup.classList.remove("show");
});

if (new_addr != null) {
    new_addr.addEventListener("change", function () {
        parseNewAddr()
    })
}


if (new_ser != null) {
    new_ser.addEventListener("input", function () {
        parseSerialLength()
    })
}

function getModuleOptions(hdl_id) {
    mod_type = hdl_id.replace('add-type-', '');
    mod_types = mod_type.split("-");
    mod_kind = mod_types[0].padStart(3, '0');
    sub_type = mod_types[1].padStart(3, '0');
    new_ser.value = mod_kind + sub_type;
    newmod_form.action = newmod_form.action + mod_type;
    ok_btn.disabled = true
    newmod_popup.classList.add("show");
};

function parseSerialLength() {
    if (new_ser.value.length == 16) {
        ok_btn.disabled = false
    }
    else {
        ok_btn.disabled = true
    }
}

function parseNewAddr() {
    existing_numbers = mod_addrs;
    min_number = new_addr.min;
    max_number = parseInt(new_addr.max);
    let nn = new_addr.value
    while (existing_numbers.includes(parseInt(nn))) {
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