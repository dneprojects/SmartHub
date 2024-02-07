function initCondElements(cnd_code) {
    if (cnd_code < 113) {
        cnd_code1 = cnd_code & 0xF8;
        cnd_code2 = cnd_code & 0x07;
        setElement("condition-select", cnd_code1);
        cond_sel.dispatchEvent(new Event("change"));
        setElement("condition_2", cnd_code2);
    }
    else if ((cnd_code >= 160) & (cnd_code < 184)) {
        setElement("condition-select", 160);
        cond_sel.dispatchEvent(new Event("change"));
        setElement("condition_time", cnd_code - 160);
    }
    else if ((cnd_code >= 192) & (cnd_code < 224)) {
        if (cnd_code < 208) {
            setElement("condition-select", 191);
            setElement("condition_flag", cnd_code - 191);
        }
        else {
            setElement("condition-select", 207);
            setElement("condition_flag", cnd_code - 207);
        }
        
    }
    else if ((cnd_code >= 224) & (cnd_code < 256)) {
        if (cnd_code < 240) {
            setElement("condition-select", 191);
            setElement("condition_flag", cnd_code - 191);
        }
        else {
            setElement("condition-select", 207);
            setElement("condition_flag", cnd_code - 207);
        }
    }
    cond_sel.dispatchEvent(new Event("change"));
}
    
function setConditionSels() {
    var idx = cond_sel.selectedIndex
    document.getElementById("condition_2").style.visibility = "hidden";
    document.getElementById("condition_time").style.visibility = "hidden";
    document.getElementById("condition_flag").style.visibility = "hidden";
    if ((idx == 2) || (idx == 3)) {
        document.getElementById("condition_flag").style.visibility = "visible";
    }
    if (idx == 4) {
        document.getElementById("condition_time").style.visibility = "visible";
    }
    if (idx > 4) {
        document.getElementById("condition_2").style.visibility = "visible";
    }
}