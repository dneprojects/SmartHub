const switching_act = new Set([1, 2, 3, 9, 111, 112, 113, 114]);
const counter_act = new Set([6, 118, 119]);
const buzzer_act = new Set([10]);
const cover_act = new Set([17, 18])
const dimm_act = new Set([20, 22, 23, 24]);
const rgb_act = new Set([35]);
const ccmd_act = new Set([50]);
const mode_act = new Set([64]);
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
    document.getElementById("output-act").style.visibility = "hidden";
    document.getElementById("led-act").style.visibility = "hidden";
    document.getElementById("collcmd-act").style.visibility = "hidden";
    document.getElementById("flag-act").style.visibility = "hidden";
    document.getElementById("counter-act").style.visibility = "hidden";
    document.getElementById("countopt-act").style.visibility = "hidden";
    document.getElementById("outopt-act").style.visibility = "hidden";
    document.getElementById("rgb-select").style.visibility = "hidden";
    document.getElementById("rgb-opts").style.visibility = "hidden";
    document.getElementById("rgb-colorpicker").style.visibility = "hidden";
    document.getElementById("cover-act").style.visibility = "hidden";
    document.getElementById("covopt-act").style.visibility = "hidden";
    document.getElementById("dimmout-act").style.visibility = "hidden";
    document.getElementById("dimmopt-act").style.visibility = "hidden";
    document.getElementById("climopt-act").style.visibility = "hidden";
    document.getElementById("tsetopt-act").style.visibility = "hidden";
    document.getElementById("climoutput-act").style.visibility = "hidden";
    document.getElementById("tset-val").style.visibility = "hidden";
    document.getElementById("cnt-val").style.visibility = "hidden";
    document.getElementById("perc-val").style.visibility = "hidden";
    document.getElementById("timeinterv-val").style.visibility = "hidden";
    document.getElementById("timeunit-act").style.visibility = "hidden";
    document.getElementById("buzz-pars").style.visibility = "hidden";
    document.getElementById("buzz-pars2").style.visibility = "hidden";
    document.getElementById("modlite-pars").style.visibility = "hidden";
    document.getElementById("mode-low").style.visibility = "hidden";
    document.getElementById("mode-high").style.visibility = "hidden";
    if (selectn == "1") {
        document.getElementById("output-act").style.visibility = "visible";
        document.getElementById("outopt-act").style.visibility = "visible"; 
        setActTimeinterval();
    }
    if (selectn == "2") {
        document.getElementById("led-act").style.visibility = "visible";
        document.getElementById("outopt-act").style.visibility = "visible";
        setActTimeinterval();
    }
    if (selectn == "20") {
        document.getElementById("dimmout-act").style.visibility = "visible";
        document.getElementById("dimmopt-act").style.visibility = "visible";
        setActDPercval();
    }
    if (selectn == "17") {
        document.getElementById("cover-act").style.visibility = "visible";
        document.getElementById("covopt-act").style.visibility = "visible";
        document.getElementById("perc-val").style.visibility = "visible";
        disablePercval()
    }
    if (selectn == "35") {
        document.getElementById("rgb-select").style.visibility = "visible";
        document.getElementById("rgb-opts").style.visibility = "visible";
        setRGBPicker()
    }
    if (selectn == "220") {
        document.getElementById("climopt-act").style.visibility = "visible";
        setActClimate();
    }
    if (selectn == "50") {
        document.getElementById("collcmd-act").style.visibility = "visible";
    }
    if (selectn == "111") {
        document.getElementById("flag-act").style.visibility = "visible";
        document.getElementById("outopt-act").style.visibility = "visible"; 
        setActTimeinterval();
    }
    if (selectn == "6") {
        document.getElementById("counter-act").style.visibility = "visible";
        document.getElementById("countopt-act").style.visibility = "visible";
        setActCntval();
    }
    if (selectn == "10") {
        document.getElementById("buzz-pars").style.visibility = "visible";
        document.getElementById("buzz-pars2").style.visibility = "visible";
    }
    if (selectn == "64") {
        document.getElementById("mode-low").style.visibility = "visible";
        document.getElementById("mode-high").style.visibility = "visible";
    }
    if (selectn == "240") {
        document.getElementById("modlite-pars").style.visibility = "visible";
    }
}

function setMovLight(){
    var idx = mov_sel.selectedIndex
    document.getElementById("mov-light").style.visibility = "hidden";
    document.getElementById("mov-light-lbl").style.visibility = "hidden";
    if (idx <= 1) {
        document.getElementById("mov-light").style.visibility = "hidden";
        document.getElementById("mov-light-lbl").style.visibility = "hidden";
    }
    if (idx > 1) {
        document.getElementById("mov-light").style.visibility = "visible";
        document.getElementById("mov-light-lbl").style.visibility = "visible";
    }
}

function setActCntval() {
    var idx = cnt_actopt.selectedIndex
    document.getElementById("cnt-val").style.visibility = "hidden";
    if (idx == 3){
        document.getElementById("cnt-val").style.visibility = "visible";
    }
}
function setActDPercval() {
    var idx = dim_actopt.selectedIndex
    document.getElementById("perc-val").style.visibility = "hidden";
    if (idx == 1) {
        document.getElementById("perc-val").style.visibility = "visible";
    }
}
function setActTimeinterval() {
    var idx = out_actopt.selectedIndex
    document.getElementById("timeinterv-val").style.visibility = "hidden";
    document.getElementById("timeunit-act").style.visibility = "hidden";
    if (idx > 3) {
        document.getElementById("timeinterv-val").style.visibility = "visible";
        document.getElementById("timeunit-act").style.visibility = "visible";
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
    document.getElementById("timeinterv-act").style.visibility = "hidden";
    document.getElementById("timeunit-act").style.visibility = "hidden";
    if (idx == 1) {
        document.getElementById("timeinterv-val").style.visibility = "visible";
        document.getElementById("timeunit-act").style.visibility = "visible";
    }
}
function setActClimate() {
    var idx = clim_actopt.selectedIndex
    document.getElementById("tsetopt-act").style.visibility = "hidden";
    document.getElementById("climoutput-act").style.visibility = "hidden";
    document.getElementById("tset-val").style.visibility = "hidden";
    if ((idx == 1) || (idx == 2)) {
        document.getElementById("tsetopt-act").style.visibility = "visible";
        setActTsetval()
    }
    if ((idx == 3) || (idx == 4)) {
        document.getElementById("climoutput-act").style.visibility = "visible";
    }
}
function setActTsetval() {
    var idx = tset_actopt.selectedIndex
    document.getElementById("tset-val").style.visibility = "hidden";
    if ((idx == 1) || (idx == 2)) {
        document.getElementById("tset-val").style.visibility = "visible";
    }
}

function disablePercval() {
    var cvr_opt = cvr_actopt.value
    if (cvr_opt > 10)
        document.getElementById("perc-val").style.visibility = "hidden";
    else
        document.getElementById("perc-val").style.visibility = "visible";
}

function setSensorNums() {
    var idx = sens_sel.selectedIndex
    var selectn = sens_sel[idx].value
    document.getElementById("sens-lims-wind").style.visibility = "hidden";
    document.getElementById("sens-lims-lux").style.visibility = "hidden";
    document.getElementById("sens-lims-temp").style.visibility = "hidden";
    document.getElementById("sens-lims-perc").style.visibility = "hidden";
    document.getElementById("rain-select").style.visibility = "hidden";
    document.getElementById("sens-lims-ad").style.visibility = "hidden";
    if ((selectn == "218") || (selectn == "219")) {
        document.getElementById("sens-lims-ad").style.visibility = "visible";
    }
    if (selectn == "204") {
        document.getElementById("sens-lims-wind").style.visibility = "visible";
    }
    if ((selectn == "203") || (selectn == "216")) {
        document.getElementById("sens-lims-lux").style.visibility = "visible";
    } 
    if ((selectn == "201") || (selectn == "213")) {
        document.getElementById("sens-lims-temp").style.visibility = "visible";
    } 
    if ((selectn == "202") || (selectn == "215")) {
        document.getElementById("sens-lims-perc").style.visibility = "visible";
    } 
    if (selectn == "205") {
        document.getElementById("rain-select").style.visibility = "visible";
    }
    if (selectn == "217") {
        document.getElementById("sens-lims-perc").style.visibility = "visible";
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
        document.getElementById("rgb-colorpicker").style.visibility = "visible";
    else
        document.getElementById("rgb-colorpicker").style.visibility = "hidden";
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