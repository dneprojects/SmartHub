const trig_sel = document.getElementById("trigger-select");
trig_sel.addEventListener("change", function () {
    setTriggerSels();
});
const cond_sel = document.getElementById("condition-select");
cond_sel.addEventListener("change", function () {
    setConditionSels();
});
const act_sel = document.getElementById("action-select");
act_sel.addEventListener("change", function () {
    setActionSels();
});
const counter_sel = document.getElementById("counter-select");
counter_sel.addEventListener("change", function () {
    setMaxCount();
});
const rgbled_sel = document.getElementById("rgb-select");
rgbled_sel.addEventListener("change", function () {
    setRGBColorOptions();
});
const rgb_mode = document.getElementById("rgb-opts");
rgb_mode.addEventListener("change", function () {
    setRGBPicker();
});
const act_counter_sel = document.getElementById("counter-act");
act_counter_sel.addEventListener("change", function () {
    setMaxCountAct();
});
const mov_sel = document.getElementById("mov-select");
    mov_sel.addEventListener("change", function () {
        setMovLight();
    });
const sens_sel = document.getElementById("sensor-select");
sens_sel.addEventListener("change", function () {
    setSensorNums();
});
const out_actopt = document.getElementById("outopt-act")
out_actopt.addEventListener("change", function () {
        setActTimeinterval();
    });
const cnt_actopt = document.getElementById("countopt-act")
cnt_actopt.addEventListener("change", function () {
    setActCntval();
});
const dim_actopt = document.getElementById("dimmopt-act")
dim_actopt.addEventListener("change", function () {
    setActDPercval();
});
const cvr_actopt = document.getElementById("covopt-act")
cvr_actopt.addEventListener("change", function () {
    disablePercval();
});
const clim_actopt = document.getElementById("climopt-act")
    clim_actopt.addEventListener("change", function () {
        setActClimate();
    });
const sys_sel = document.getElementById("sys-select")
sys_sel.addEventListener("change", function () {
    setSysTrigger();
});
const tset_actopt = document.getElementById("tsetopt-act")
tset_actopt.addEventListener("change", function () {
    setActTsetval();
});
const ekey_sel = document.getElementById("ekey-select")
ekey_sel.addEventListener("change", function () {
    setEkeyUsrFingers();
});
const ok_butt = document.getElementById("ok_button")
ok_butt.addEventListener("click", function () {
    checkFormEntries();
});
const msg_opt = document.getElementById("msgopt-act")
msg_opt.addEventListener("change", function () {
    setMsgTime();
});

close_err_popup.addEventListener("click", function () {
automtn_err_popup.classList.remove("show");
});
function initUiElements(trg_code, trg_arg1, trg_arg2, cnd_code, act_code, act_args, trg_time) {
    initTrigElements(trg_code, trg_arg1, trg_arg2, trg_time)
    initCondElements(cnd_code)
    initActElements(act_code, act_args)
}

function setElement(id, valueToSet) {    
    let selector = document.getElementById(id);
    selector.value = valueToSet;
}

function setElementVisibility(idStr, newState) {
    const elem = document.getElementById(idStr)
    elem.style.visibility = newState;
    if (newState == "visible") {
        if (elem.type == "select-one")
            if ((elem.childElementCount == 2) & (elem.options[0].value == "") & (elem.selectedIndex == 0))
                elem.selectedIndex = 1
    }
}

function checkFormEntries() {
    const def_form = document.getElementById("automation_def");
    var success = true;
    if (def_form.elements["trigger-select"].value == "")
        success = false
    if (def_form.elements["condition-select"].value == "")
        success = false
    if (def_form.elements["action-select"].value == "")
        success = false
    for (var i = 0; i < def_form.length; i++) {
        if (def_form[i].style.visibility == "visible") {
            var sel_val = def_form[i].value;
            if (sel_val == "") {
                success = false
                break
            }
        }
    }
    if (success) {
        def_form.elements["ok_result"].value = "ok";
        def_form.submit()
    }
    else
        automtn_err_popup.classList.add("show");
}