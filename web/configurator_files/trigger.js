const flag_trg = new Set([6])
const logic_trg = new Set([8])
const count_trg = new Set([9])
const output_trg = new Set([10])
const remote_trg = new Set([23])
const viscmd_trg = new Set([31])
const move_trg = new Set([40, 41])
const collcmd_trg = new Set([50])
const mode_trg = new Set([137])
const dimm_trg = new Set([149])
const button_trg = new Set([150, 151, 154])
const switch_trg = new Set([152, 153])
const ekey_trg = new Set([169])
const time_trg = new Set([170])
const sensor_trg = new Set([201, 202, 203, 204, 205, 213, 214, 215, 216, 217, 218, 219])
const temp_sens = new Set([201, 213])
const perc_sens = new Set([202, 215, 217])
const light_sens = new Set([203, 216])
const wind_sens = new Set([204])
const rain_sens = new Set([205])
const ad_sens = new Set([218, 219])
const climate_trg = new Set([220, 221, 222])
const sys_trg = new Set([12, 101, 249])
const dircmd_trg = new Set([253])

function initTrigElements(trg_code, trg_arg1, trg_arg2, trg_time) {
    if (button_trg.has(trg_code)) {
        setElement("trigger-select", 150);
        setElement("button-select", trg_arg1);
        setElement("shortlong-select", trg_code - 149);
    }
    else if (switch_trg.has(trg_code)) {
        setElement("trigger-select", 152);
        setElement("switch-select", trg_arg1);
        setElement("onoff-select", trg_code - 151);
    }
    else if (dimm_trg.has(trg_code)) {
        setElement("trigger-select", 149);
        setElement("button-select", trg_arg1);
    }
    else if (remote_trg.has(trg_code)) {
        setElement("trigger-select", 23);
        setElement("ir-high", trg_arg1);
        setElement("ir-low", trg_arg2);
    }
    else if (output_trg.has(trg_code)) {
        setElement("trigger-select", 10);
        setElement("output-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("onoff-select", 1);
        else
            setElement("onoff-select", 2);
    }
    else if (climate_trg.has(trg_code)) {
        setElement("trigger-select", 220);
        setElement("clim-sens-select", trg_code - 220);
        setElement("clim-mode-select", trg_arg1);
    }
    else if (dircmd_trg.has(trg_code)) {
        setElement("trigger-select", 253);
        setElement("dircmd-select", trg_arg1);
    }
    else if (collcmd_trg.has(trg_code)) {
        setElement("trigger-select", 50);
        setElement("collcmd-select", trg_arg1);
    }
    else if (viscmd_trg.has(trg_code)) {
        setElement("trigger-select", 31);
        setElement("viscmd-select", trg_arg1 * 256 + trg_arg2);
    }
    else if (flag_trg.has(trg_code)) {
        setElement("trigger-select", 6);
        setElement("flag-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("flag2-select", 1);
        else
            setElement("flag2-select", 2);
    }
    else if (logic_trg.has(trg_code)) {
        setElement("trigger-select", 8);
        setElement("logic-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("logic2-select", 1);
        else
            setElement("logic2-select", 2);
    }
    else if (mode_trg.has(trg_code)) {
        setElement("trigger-select", 137);
        setElement("mode-select", trg_arg2 & 0xF8);
        setElement("mode2-select", trg_arg2 & 0x07);
    }
    else if (ekey_trg.has(trg_code)) {
        setElement("trigger-select", 169);
        setEkeyUser(trg_arg1);
        setElement("finger-select", trg_arg2);
    }
    else if (move_trg.has(trg_code)) {
        setElement("trigger-select", 40);
        if (trg_arg2 == 0) {
            setElement("mov-select", 0);
            setElement("mov-intens", trg_arg1);
        }
        else {
            setElement("mov-select", trg_code - 39);
            setElement("mov-intens", trg_arg1);
            setElement("mov-light", trg_arg2 * 10);
        }

    }
    else if (sensor_trg.has(trg_code)) {
        setElement("trigger-select", 203);
        setElement("sensor-select", trg_code);
        if (temp_sens.has(trg_code)) {
            setElement("sens-low-temp", u2sign7(trg_arg1));
            setElement("sens-high-temp", u2sign7(trg_arg2));
        }
        if (perc_sens.has(trg_code)) {
            setElement("sens-low-perc", trg_arg1);
            setElement("sens-high-perc", trg_arg2);
        }
        if (light_sens.has(trg_code)) {
            setElement("sens-low-lux", trg_arg1 * 10);
            setElement("sens-high-lux", trg_arg2 * 10);
        }
        if (wind_sens.has(trg_code)) {
            setElement("sens-low-wind", trg_arg1);
            setElement("sens-high-wind", trg_arg2);
        }
        if (rain_sens.has(trg_code)) {
            setElement("rain-select", trg_arg1);
        }
        if (ad_sens.has(trg_code)) {
            setElement("sens-low-ad", trg_arg1 / 25);
            setElement("sens-high-ad", trg_arg2 / 25);
        }
    }
    else if (count_trg.has(trg_code)) {
        setElement("trigger-select", 9);
        var counter_no = Math.floor((trg_arg1 - 96) / 16);
        var count_val = trg_arg1 - 95 - counter_no * 16
        setElement("counter-select", counter_no + 1);
        setElement("count-vals", count_val);
    }
    else if (time_trg.has(trg_code)) {
        setElement("trigger-select", 170);
        setElement("day-vals", trg_arg1);
        setElement("month-vals", trg_arg2);
        setElement("time-vals", trg_time);
    }
    else if (sys_trg.has(trg_code)) {
        setElement("trigger-select", 249);
        setElement("sys-select", trg_code);
        if (trg_code == 12) {
            setElement("supply-select", trg_arg1);
        }
        else if (trg_code == 101) {
            setElement("syserr-no", trg_arg1 * 256 + trg_arg2);
        }
    }
    trig_sel.dispatchEvent(new Event("change"));
}

function setTriggerSels() {
    var idx = trig_sel.selectedIndex
    var selectn = trig_sel[idx].value
    setElementVisibility("button-select", "hidden");
    setElementVisibility("switch-select", "hidden");
    setElementVisibility("output-select", "hidden");
    setElementVisibility("flag-select", "hidden");
    setElementVisibility("flag2-select", "hidden");
    setElementVisibility("logic-select", "hidden");
    setElementVisibility("logic2-select", "hidden");
    setElementVisibility("mode-select", "hidden");
    setElementVisibility("mode2-select", "hidden");
    setElementVisibility("viscmd-select", "hidden");
    setElementVisibility("collcmd-select", "hidden");
    setElementVisibility("dircmd-select", "hidden");
    setElementVisibility("sensor-select", "hidden");
    setElementVisibility("counter-select", "hidden");
    setElementVisibility("mov-select", "hidden");
    setElementVisibility("mov-params", "hidden");
    setElementVisibility("mov-light", "hidden");
    setElementVisibility("mov-light-lbl", "hidden");
    setElementVisibility("shortlong-select", "hidden");
    setElementVisibility("onoff-select", "hidden");
    setElementVisibility("count-vals", "hidden");
    setElementVisibility("sens-lims-wind", "hidden");
    setElementVisibility("sens-lims-lux", "hidden");
    setElementVisibility("sens-lims-temp", "hidden");
    setElementVisibility("sens-lims-perc", "hidden");
    setElementVisibility("rain-select", "hidden");
    setElementVisibility("sens-lims-ad", "hidden");
    setElementVisibility("time-vals", "hidden");
    setElementVisibility("day-vals", "hidden");
    setElementVisibility("month-vals", "hidden");
    setElementVisibility("ekey-select", "hidden");
    setElementVisibility("finger-select", "hidden");
    setElementVisibility("clim-sens-select", "hidden");
    setElementVisibility("clim-mode-select", "hidden");
    setElementVisibility("remote-codes", "hidden");
    setElementVisibility("sys-select", "hidden");
    setElementVisibility("supply-select", "hidden");
    setElementVisibility("syserr-div", "hidden");

    if (selectn == "150") {
        setElementVisibility("button-select", "visible");
        setElementVisibility("shortlong-select", "visible");
    }
    if (selectn == "152") {
        setElementVisibility("switch-select", "visible");
        setElementVisibility("onoff-select", "visible");
    }
    if (selectn == "149") {
        setElementVisibility("button-select", "visible");
    }
    if (selectn == "23") {
        setElementVisibility("remote-codes", "visible");
    }
    if (selectn == "10") {
        setElementVisibility("output-select", "visible");
        setElementVisibility("onoff-select", "visible");
    }
    if (selectn == "50") {
        setElementVisibility("collcmd-select", "visible");
    }
    if (selectn == "31") {
        setElementVisibility("viscmd-select", "visible");
    }
    if (selectn == "253") {
        setElementVisibility("dircmd-select", "visible");
    }
    if (selectn == "6") {
        setElementVisibility("flag-select", "visible");
        setElementVisibility("flag2-select", "visible");
    }
    if (selectn == "8") {
        setElementVisibility("logic-select", "visible");
        setElementVisibility("logic2-select", "visible");
    }
    if (selectn == "137") {
        setElementVisibility("mode-select", "visible");
        setElementVisibility("mode2-select", "visible");
    }
    if (selectn == "203") {
        setElementVisibility("sensor-select", "visible");
        setSensorNums();
    }
    if (selectn == "9") {
        setElementVisibility("counter-select", "visible");
        setElementVisibility("count-vals", "visible");
        setMaxCount()
    }
    if (selectn == "40") {
        setElementVisibility("mov-select", "visible");
        setElementVisibility("mov-params", "visible");
        setMovLight();
    }
    if (selectn == "169") {
        setElementVisibility("ekey-select", "visible");
        setElementVisibility("finger-select", "visible");
        setEkeyUsrFingers();
    }
    if (selectn == "170") {
        setElementVisibility("time-vals", "visible");
        setElementVisibility("day-vals", "visible");
        setElementVisibility("month-vals", "visible");
    }
    if (selectn == "220") {
        setElementVisibility("clim-sens-select", "visible");
        setElementVisibility("clim-mode-select", "visible");
    }
    if (selectn == "249") {
        setElementVisibility("sys-select", "visible");
        setSysTrigger()
    }
}

function setMaxCount() {
    var idx = counter_sel.selectedIndex
    var max_cnt_val = max_count[idx - 1]
    var cnt_sel = document.getElementById("count-vals")
    for (var i = 0; i < cnt_sel.length; i++) {
        if (i > max_cnt_val)
            cnt_sel.options[i].disabled = true;
        else
            cnt_sel.options[i].disabled = false;
    }
    if (cnt_sel.selectedIndex > max_cnt_val)
        cnt_sel.selectedIndex = 0
};

function setEkeyUser(sel_usr) {
    for (var i = 0; i < ekey_sel.length; i++) {
        selectn = ekey_sel[i].value;
        if (selectn.split("-")[0] == sel_usr) {
            ekey_sel.value = selectn;
            break;
        }
    }
}
function setEkeyUsrFingers() {
    var idx = ekey_sel.selectedIndex;
    var selectn = ekey_sel[idx].value;
    var usr_parts = selectn.split("-");
    var finger_mask = usr_parts[1]
    var finger_sel = document.getElementById("finger-select")
    for (var i = 0; i < 10; i++) {
        var mask = 1 << i;
        if (finger_mask & mask)
            finger_sel.options[i + 1].disabled = false;
        else
            finger_sel.options[i + 1].disabled = true;
    }
    if (finger_sel.options[finger_sel.selectedIndex].disabled)
        finger_sel.selectedIndex = 0
    if (usr_parts[0] == 255)
        finger_sel.style.visibility = "hidden";
    else
        finger_sel.style.visibility = "visible";
}
function setSysTrigger() {
    var idx = sys_sel.selectedIndex;
    var selectn = sys_sel[idx].value;
    if (selectn == 249) {
        setElementVisibility("supply-select", "hidden");
        setElementVisibility("syserr-div", "hidden");
    }
    else if (selectn == 12) {
        setElementVisibility("supply-select", "visible");
        setElementVisibility("syserr-div", "hidden");
    }
    else if (selectn == 101) {
        setElementVisibility("supply-select", "hidden");
        setElementVisibility("syserr-div", "visible");
    }
}

function u2sign7(uint_in) {
    if (uint_in > 60) {
        return uint_in - 128
    }
    return uint_in
}
