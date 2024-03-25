const switching_act = new Set([1, 2, 3, 9, 111, 112, 113, 114]);
const counter_act = new Set([6, 118, 119]);
const buzzer_act = new Set([10]);
const cover_act = new Set([17, 18])
const dimm_act = new Set([20, 22, 23, 24]);
const rgb_act = new Set([35]);
const ccmd_act = new Set([50]);
const mode_act = new Set([64]);
const msg_act = new Set([56, 57, 58]);
const climate_act = new Set([220, 221, 222]);
const ambient_act = new Set([240]);

function initActElements(act_code, act_args) {
    if (switching_act.has(act_code)) {
        var out_no = 0
        if (act_code > 110) {
            act_code -= 110;
        }
        if (act_code < 4) {
            out_no = act_args[0];
        }
        else {
            out_no = act_args[3]
            setElement("timeinterv-val", act_args[1]);
            if (new Set([2, 12, 22]).has(act_args[0]))
                setElement("timeunit-act", "2");
            else
                setElement("timeunit-act", "1");
        }
        if (out_no < 16) {
            setElement("action-select", 1)
            setElement("output-act", out_no);
        }
        else if (out_no < 25) {
            setElement("action-select", 2)
            setElement("led-act", out_no);
        }
        else {
            setElement("action-select", 111);
            if (out_no > 100)
                out_no -= 100
            else if (out_no < 33)
                out_no -= 24
            setElement("flag-act", out_no);
        }
        if (act_code == 9) {
            if (act_args[2] == 255)
                setElement("outopt-act", 6);
            else if ((act_args[0] == 1) | (act_args[0] == 2))
                setElement("outopt-act", 4);
            else if ((act_args[0] == 11) | (act_args[0] == 12))
                setElement("outopt-act", 5);
            else if ((act_args[0] == 21) | (act_args[0] == 22))
                setElement("outopt-act", 7);
        }
        else
            setElement("outopt-act", act_code);
    }
    else if (dimm_act.has(act_code)) {
        setElement("action-select", 20)
        setElement("dimmout-act", act_args[0]);
        setElement("dimmopt-act", act_code);
        if (act_code == 20) {
            setElement("perc-val", act_args[1]);
        }
    }
    else if (rgb_act.has(act_code)) {
        setElement("action-select", 35)
        setElement("rgb-select", act_args[2]);
        setRGBColorOptions()
        rd = act_args[3]
        gn = act_args[4]
        bl = act_args[5]
        sel_col = [rd, gn, bl].toString()

        if (act_args[2] == 100) {
            if (act_args[0] == 2)
                setElement("rgb-opts", 2)
            else {
                if (sel_col == amb_white.toString()) 
                    setElement("rgb-opts", 11)
                else if (sel_col == amb_warm.toString())
                    setElement("rgb-opts", 12)
                else if (sel_col == amb_cool.toString())
                    setElement("rgb-opts", 13)
                else {
                    setElement("rgb-opts", 4);
                    col_str = colArray2StrConv([act_args[3], act_args[4], act_args[5]]);
                    document.getElementById("rgb-colorpicker").value = col_str;
                }
            }
        }
        else {
            if (act_args[0] == 2)
                setElement("rgb-opts", 2)
            else {
                if (sel_col == col_red.toString())
                    setElement("rgb-opts", 5)
                else if (sel_col == col_green.toString())
                    setElement("rgb-opts", 6)
                else if (sel_col == col_blue.toString())
                    setElement("rgb-opts", 7)
                else if (sel_col == col_white.toString())
                    setElement("rgb-opts", 10)
                else {
                    setElement("rgb-opts", 4);
                    col_str = colArray2StrConv([act_args[3], act_args[4], act_args[5]]);
                    document.getElementById("rgb-colorpicker").value = col_str;
                }
            }
        }
    }
    else if (cover_act.has(act_code)) {
        setElement("action-select", 17)
        setElement("cover-act", act_args[1]);
        if (act_args[2] == 255) {
            setElement("covopt-act", act_args[0] + 10);
        }
        else {
            setElement("covopt-act", act_args[0]);
            setElement("perc-val", act_args[2]);
        }
        
    }
    else if (ccmd_act.has(act_code)) {
        setElement("action-select", 50)
        setElement("collcmd-act", act_args[0]);
    }
    else if (climate_act.has(act_code)) {
        setElement("action-select", 220)
        if(act_code > 220) {
            setElement("climopt-act", (act_code - 200));
            setElement("climoutput-act", act_args[1]);
        }
        else {
            var cl_md = act_args[0]
            if ((cl_md > 10) & (cl_md < 15))
                setElement("climopt-act", cl_md);
            else if (cl_md > 20) {
                cl_md -= 20
                setElement("climopt-act", "2");
                setElement("tset-val", act_args[1] / 10);
                setElement("tsetopt-act", cl_md);
            }
            else {
                setElement("climopt-act", "1");
                setElement("tset-val", act_args[1] / 10);
                setElement("tsetopt-act", cl_md);
            }
        }
    }
    else if (mode_act.has(act_code)) {
        setElement("action-select",64)
        setElement("mode-low", act_args[0]);
        setElement("mode-high", act_args[1]);
    }
    else if (counter_act.has(act_code)) {
        setElement("action-select", 6)
        if (act_code > 6) {
            var cnt_no = Math.floor((act_args[0] - act_code - 47) / 8) + 1;
            setElement("countopt-act", act_code - 117);
        }
        else {
            var cnt_no = act_args[0];
            setElement("countopt-act", "3")
            setElement("cnt-val", act_args[2])
        setElement("counter-act", cnt_no)
        }   
    }
    else if (ambient_act.has(act_code)) {
        setElement("action-select", 240)
        setElement("modlite-time", act_args[0]);
    }
    else if (msg_act.has(act_code)) {
        setElement("action-select", 56)
        setElement("msgopt-act", act_code);
        setElement("msg-act", act_args[0]);
        if (act_code == 58) {
            setElement("msgset-time", act_args[1]);
        }
    }
    else if (buzzer_act.has(act_code)) {
        setElement("action-select", 10)
        setElement("buzz-freq", act_args[0]);
        setElement("buzz-dur", act_args[1]);
        setElement("buzz-rep", act_args[2]);
    }
    act_sel.dispatchEvent(new Event("change"));
}
function setActionSels() {
    var idx = act_sel.selectedIndex
    var selectn = act_sel[idx].value
    setElementVisibility("output-act", "hidden");
    setElementVisibility("led-act", "hidden");
    setElementVisibility("collcmd-act", "hidden");
    setElementVisibility("flag-act", "hidden");
    setElementVisibility("counter-act", "hidden");
    setElementVisibility("countopt-act", "hidden");
    setElementVisibility("outopt-act", "hidden");
    setElementVisibility("rgb-select", "hidden");
    setElementVisibility("rgb-opts", "hidden");
    setElementVisibility("rgb-colorpicker", "hidden");
    setElementVisibility("cover-act", "hidden");
    setElementVisibility("covopt-act", "hidden");
    setElementVisibility("dimmout-act", "hidden");
    setElementVisibility("dimmopt-act", "hidden");
    setElementVisibility("climopt-act", "hidden");
    setElementVisibility("tsetopt-act", "hidden");
    setElementVisibility("climoutput-act", "hidden");
    setElementVisibility("tset-val", "hidden");
    setElementVisibility("cnt-val", "hidden");
    setElementVisibility("perc-val", "hidden");
    setElementVisibility("timeinterv-val", "hidden");
    setElementVisibility("timeunit-act", "hidden");
    setElementVisibility("buzz-pars", "hidden");
    setElementVisibility("buzz-pars2", "hidden");
    setElementVisibility("modlite-pars", "hidden");
    setElementVisibility("mode-low", "hidden");
    setElementVisibility("mode-high", "hidden");
    setElementVisibility("msg-act", "hidden");
    setElementVisibility("msgopt-act", "hidden");
    setElementVisibility("msgset-time", "hidden");
    if (selectn == "1") {
        setElementVisibility("output-act", "visible");
        setElementVisibility("outopt-act", "visible"); 
        setActTimeinterval();
    }
    if (selectn == "2") {
        setElementVisibility("led-act", "visible");
        setElementVisibility("outopt-act", "visible");
        setActTimeinterval();
    }
    if (selectn == "20") {
        setElementVisibility("dimmout-act", "visible");
        setElementVisibility("dimmopt-act", "visible");
        setActDPercval();
    }
    if (selectn == "17") {
        setElementVisibility("cover-act", "visible");
        setElementVisibility("covopt-act", "visible");
        setElementVisibility("perc-val", "visible");
        disablePercval()
    }
    if (selectn == "35") {
        setElementVisibility("rgb-select", "visible");
        setElementVisibility("rgb-opts", "visible");
        setRGBPicker()
    }
    if (selectn == "220") {
        setElementVisibility("climopt-act", "visible");
        setActClimate();
    }
    if (selectn == "50") {
        setElementVisibility("collcmd-act", "visible");
    }
    if (selectn == "56") {
        setElementVisibility("msg-act", "visible");
        setElementVisibility("msgopt-act", "visible");
        setMsgTime()
    }
    if (selectn == "111") {
        setElementVisibility("flag-act", "visible");
        setElementVisibility("outopt-act", "visible"); 
        setActTimeinterval();
    }
    if (selectn == "6") {
        setElementVisibility("counter-act", "visible");
        setElementVisibility("countopt-act", "visible");
        setActCntval();
    }
    if (selectn == "10") {
        setElementVisibility("buzz-pars", "visible");
        setElementVisibility("buzz-pars2", "visible");
    }
    if (selectn == "64") {
        setElementVisibility("mode-low", "visible");
        setElementVisibility("mode-high", "visible");
    }
    if (selectn == "240") {
        setElementVisibility("modlite-pars", "visible");
    }
}

function setMovLight(){
    var idx = mov_sel.selectedIndex
    setElementVisibility("mov-light", "hidden");
    setElementVisibility("mov-light-lbl", "hidden");
    if (idx <= 1) {
        setElementVisibility("mov-light", "hidden");
        setElementVisibility("mov-light-lbl", "hidden");
    }
    if (idx > 1) {
        setElementVisibility("mov-light", "visible");
        setElementVisibility("mov-light-lbl", "visible");
    }
}

function setActCntval() {
    var idx = cnt_actopt.selectedIndex
    setElementVisibility("cnt-val", "hidden");
    if (idx == 3){
        setElementVisibility("cnt-val", "visible");
        setMaxCountAct()
    }
}
function setActDPercval() {
    var idx = dim_actopt.selectedIndex
    setElementVisibility("perc-val", "hidden");
    if (idx == 1) {
        setElementVisibility("perc-val", "visible");
    }
}
function setActTimeinterval() {
    var idx = out_actopt.selectedIndex
    setElementVisibility("timeinterv-val", "hidden");
    setElementVisibility("timeunit-act", "hidden");
    if (idx > 3) {
        setElementVisibility("timeinterv-val", "visible");
        setElementVisibility("timeunit-act", "visible");
        if (act_sel.value == "act-111") {
            var flg_sel = document.getElementById("flag-act")
            for (var i = 0; i < flg_sel.length; i++) {
                var flg_idx = flg_sel[i].value.split("-")[1]
                if ((flg_idx > 8) & (flg_idx < 17))
                    flg_sel.options[i].disabled = true;
                else if (flg_idx > 40)
                    flg_sel.options[i].disabled = true;
            }
            flg_idx = flg_sel[flg_sel.selectedIndex].value.split("-")[1]
            if ((flg_idx > 8) & (flg_idx < 17))
                flg_sel.selectedIndex = 0
            else if (flg_idx > 40)
                flg_sel.selectedIndex = 0
        }
    }
    else {
        if (act_sel.value == "act-111") {
            var flg_sel = document.getElementById("flag-act")
            for (var i = 0; i < flg_sel.length; i++) {
                flg_sel.options[i].disabled = false;
            }
        }
    }
}
function setActFTimeinterval() {
    var idx = flag_actopt.selectedIndex
    setElementVisibility("timeinterv-act", "hidden");
    setElementVisibility("timeunit-act", "hidden");
    if (idx == 1) {
        setElementVisibility("timeinterv-val", "visible");
        setElementVisibility("timeunit-act", "visible");
    }
}
function setActClimate() {
    var idx = clim_actopt.selectedIndex
    setElementVisibility("tsetopt-act", "hidden");
    setElementVisibility("climoutput-act", "hidden");
    setElementVisibility("tset-val", "hidden");
    if ((idx == 1) || (idx == 2)) {
        setElementVisibility("tsetopt-act", "visible");
        setActTsetval()
    }
    if ((idx == 3) || (idx == 4)) {
        setElementVisibility("climoutput-act", "visible");
    }
}
function setActTsetval() {
    var idx = tset_actopt.selectedIndex
    setElementVisibility("tset-val", "hidden");
    if ((idx == 1) || (idx == 2)) {
        setElementVisibility("tset-val", "visible");
    }
}

function disablePercval() {
    var cvr_opt = cvr_actopt.value
    if (cvr_opt > 10)
        setElementVisibility("perc-val", "hidden");
    else
        setElementVisibility("perc-val", "visible");
}

function setSensorNums() {
    var idx = sens_sel.selectedIndex
    var selectn = sens_sel[idx].value
    setElementVisibility("sens-lims-wind", "hidden");
    setElementVisibility("sens-lims-lux", "hidden");
    setElementVisibility("sens-lims-temp", "hidden");
    setElementVisibility("sens-lims-perc", "hidden");
    setElementVisibility("rain-select", "hidden");
    setElementVisibility("sens-lims-ad", "hidden");
    if ((selectn == "218") || (selectn == "219")) {
        setElementVisibility("sens-lims-ad", "visible");
    }
    if (selectn == "204") {
        setElementVisibility("sens-lims-wind", "visible");
    }
    if ((selectn == "203") || (selectn == "216")) {
        setElementVisibility("sens-lims-lux", "visible");
    } 
    if ((selectn == "201") || (selectn == "213")) {
        setElementVisibility("sens-lims-temp", "visible");
    } 
    if ((selectn == "202") || (selectn == "215")) {
        setElementVisibility("sens-lims-perc", "visible");
    } 
    if (selectn == "205") {
        setElementVisibility("rain-select", "visible");
    }
    if (selectn == "217") {
        setElementVisibility("sens-lims-perc", "visible");
    }
}

function setMaxCountAct() {
    var idx = act_counter_sel.selectedIndex
    var max_cnt_val = max_count[idx - 1]
    var cnt_val = document.getElementById("cnt-val")
    cnt_val.max = max_cnt_val;
    if (cnt_val.value > max_cnt_val)
        cnt_val.value = max_cnt_val
};

function setRGBColorOptions() {
    const out_selval = document.getElementById("rgb-select").value
    const col_sel = document.getElementById("rgb-opts")
    const col_pick = document.getElementById("rgb-colorpicker")
    if (out_selval == 100) {
        disableOption("rgb-opts", 5);
        disableOption("rgb-opts", 6);
        disableOption("rgb-opts", 7);
        disableOption("rgb-opts", 10);
        enableOption("rgb-opts", 11);
        enableOption("rgb-opts", 12);
        enableOption("rgb-opts", 13);
    }
    else {
        enableOption("rgb-opts", 5);
        enableOption("rgb-opts", 6);
        enableOption("rgb-opts", 7);
        enableOption("rgb-opts", 10);
        disableOption("rgb-opts", 11);
        disableOption("rgb-opts", 12);
        disableOption("rgb-opts", 13);
    }
    if (col_sel.options[col_sel.selectedIndex].disabled) {
        if (col_sel.value == 5)
            col_str = colArray2StrConv(col_red)
        else if (col_sel.value == 6)
            col_str = colArray2StrConv(col_green)
        else if (col_sel.value == 7)
            col_str = colArray2StrConv(col_blue)
        else if (col_sel.value == 10)
            col_str = colArray2StrConv(col_white)
        else if (col_sel.value == 11)
            col_str = colArray2StrConv(amb_white)
        else if (col_sel.value == 12)
            col_str = colArray2StrConv(amb_warm)
        else if (col_sel.value == 13)
            col_str = colArray2StrConv(amb_cool)
        col_sel.value = 4
        col_pick.value = col_str
        col_pick.style.visibility = "visible";
    }
}

function colArray2Str(col) {
    
    return "#" + ("0" + col[0].toString(16)).slice(-2) + ("0" + col[1].toString(16)).slice(-2) + ("0" + col[2].toString(16)).slice(-2);
}

function colArray2StrConv(col) {
    col_str = "#"
    for (var i = 0; i < 3; i++) {
        col_val = col[i]
        col_str += ("0" + (col_val).toString(16)).slice(-2)
    }
    return col_str
}

function setRGBPicker() {
    if (document.getElementById("rgb-opts").value == 4)
        setElementVisibility("rgb-colorpicker", "visible");
    else
        setElementVisibility("rgb-colorpicker", "hidden");
}
    
function disableOption(elem, opt) {
    const selector = document.getElementById(elem)
    for (var i= 0; i<selector.options.length; i++) {
        if (selector.options[i].value==opt) {
            selector.options[i].disabled = true;
            break;
        }
    }  
}

function enableOption(elem, opt) {
    const selector = document.getElementById(elem)
    for (var i= 0; i<selector.options.length; i++) {
        if (selector.options[i].value==opt) {
            selector.options[i].disabled = false;
            break;
        }
    }  
}
function setMsgTime() {
    if (document.getElementById("msgopt-act").value == 58)
        setElementVisibility("msgset-time", "visible");
    else
        setElementVisibility("msgset-time", "hidden");
}