const logic_trg = new Set([6])
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
        setElement("dircmd-select", trg_arg1 * 256 + trg_arg2);
    }
    else if (logic_trg.has(trg_code)) {
        setElement("trigger-select", 6);
        setElement("mode-select", trg_arg1 + trg_arg2);
        if (trg_arg1 > 0)
            setElement("flag2-select", 1);
        else
            setElement("flag2-select", 2);
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
    document.getElementById("button-select").style.visibility = "hidden";
    document.getElementById("switch-select").style.visibility = "hidden";
    document.getElementById("output-select").style.visibility = "hidden";
    document.getElementById("flag-select").style.visibility = "hidden";
    document.getElementById("flag2-select").style.visibility = "hidden";
    document.getElementById("mode-select").style.visibility = "hidden";
    document.getElementById("mode2-select").style.visibility = "hidden";
    document.getElementById("viscmd-select").style.visibility = "hidden";
    document.getElementById("collcmd-select").style.visibility = "hidden";
    document.getElementById("dircmd-select").style.visibility = "hidden";
    document.getElementById("sensor-select").style.visibility = "hidden";
    document.getElementById("counter-select").style.visibility = "hidden";
    document.getElementById("mov-select").style.visibility = "hidden";
    document.getElementById("mov-params").style.visibility = "hidden";
    document.getElementById("mov-light").style.visibility = "hidden";
    document.getElementById("mov-light-lbl").style.visibility = "hidden";
    document.getElementById("shortlong-select").style.visibility = "hidden";
    document.getElementById("onoff-select").style.visibility = "hidden";
    document.getElementById("count-vals").style.visibility = "hidden";
    document.getElementById("sens-lims-wind").style.visibility = "hidden";
    document.getElementById("sens-lims-lux").style.visibility = "hidden";
    document.getElementById("sens-lims-temp").style.visibility = "hidden";
    document.getElementById("sens-lims-perc").style.visibility = "hidden";
    document.getElementById("rain-select").style.visibility = "hidden";
    document.getElementById("sens-lims-ad").style.visibility = "hidden";
    document.getElementById("time-vals").style.visibility = "hidden";
    document.getElementById("day-vals").style.visibility = "hidden";
    document.getElementById("month-vals").style.visibility = "hidden";
    document.getElementById("ekey-select").style.visibility = "hidden";
    document.getElementById("finger-select").style.visibility = "hidden";
    document.getElementById("clim-sens-select").style.visibility = "hidden";
    document.getElementById("clim-mode-select").style.visibility = "hidden";
    document.getElementById("remote-codes").style.visibility = "hidden";
    document.getElementById("sys-select").style.visibility = "hidden";
    document.getElementById("supply-select").style.visibility = "hidden";
    document.getElementById("syserr-div").style.visibility = "hidden";
    
    if (selectn == "150") {
        document.getElementById("button-select").style.visibility = "visible";
        document.getElementById("shortlong-select").style.visibility = "visible";
    }
    if (selectn == "152") {
        document.getElementById("switch-select").style.visibility = "visible";
        document.getElementById("onoff-select").style.visibility = "visible";
    }
    if (selectn == "149") {
        document.getElementById("button-select").style.visibility = "visible";
    }
    if (selectn == "23") {
        document.getElementById("remote-codes").style.visibility = "visible";
    }
    if (selectn == "10") {
        document.getElementById("output-select").style.visibility = "visible";
        document.getElementById("onoff-select").style.visibility = "visible";
    }
    if (selectn == "50") {
        document.getElementById("collcmd-select").style.visibility = "visible";
    }
    if (selectn == "31") {
        document.getElementById("viscmd-select").style.visibility = "visible";
    }
    if (selectn == "253") {
        document.getElementById("dircmd-select").style.visibility = "visible";
    }
    if (selectn == "6") {
        document.getElementById("flag-select").style.visibility = "visible";
        document.getElementById("flag2-select").style.visibility = "visible";
    }
    if (selectn == "137") {
        document.getElementById("mode-select").style.visibility = "visible";
        document.getElementById("mode2-select").style.visibility = "visible";
    }
    if (selectn == "203") {
        document.getElementById("sensor-select").style.visibility = "visible";
        setSensorNums();
    }
    if (selectn == "9") {
        document.getElementById("counter-select").style.visibility = "visible";
        document.getElementById("count-vals").style.visibility = "visible";
    }
    if (selectn == "40") {
        document.getElementById("mov-select").style.visibility = "visible";
        document.getElementById("mov-params").style.visibility = "visible";
        setMovLight();
    }
    if (selectn == "169") {
        document.getElementById("ekey-select").style.visibility = "visible";
        document.getElementById("finger-select").style.visibility = "visible";
        setEkeyUsrFingers();
    }
    if (selectn == "170") {
        document.getElementById("time-vals").style.visibility = "visible";
        document.getElementById("day-vals").style.visibility = "visible";
        document.getElementById("month-vals").style.visibility = "visible";
    }
    if (selectn == "220") {
        document.getElementById("clim-sens-select").style.visibility = "visible";
        document.getElementById("clim-mode-select").style.visibility = "visible";
    }
    if (selectn == "249") {
        document.getElementById("sys-select").style.visibility = "visible";
        setSysTrigger()
    }
}

function setMaxCount() {
    var idx = counter_sel.selectedIndex
    var max_cnt_val = max_count[idx-1]
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
            finger_sel.options[i+1].disabled = false;
        else
            finger_sel.options[i+1].disabled = true;
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
        document.getElementById("supply-select").style.visibility = "hidden";
        document.getElementById("syserr-div").style.visibility = "hidden";
    }
    else if (selectn == 12) {
        document.getElementById("supply-select").style.visibility = "visible";
        document.getElementById("syserr-div").style.visibility = "hidden";
    }
    else if (selectn == 101) {
        document.getElementById("supply-select").style.visibility = "hidden";
        document.getElementById("syserr-div").style.visibility = "visible";
    }
}

function u2sign7(uint_in) {
    if (uint_in > 60) {
        return uint_in - 128
    }
    return uint_in 
}
