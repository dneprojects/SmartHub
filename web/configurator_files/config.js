const form_upload = document.getElementById("file_upload");
const form_download = document.getElementById("file_download");
const resp_popup = document.getElementById("resp-popup");
const save_butt = document.getElementById("config_button_sv")
const protoc_butt = document.getElementById("showlogs_button")

if (document.getElementById("files_button")) {
    files_button.addEventListener("click", function () {
        file_popup.classList.add("show");
    });
}

if (protoc_butt) {
    protoc_butt.addEventListener("click", function () {
        msg_popup.classList.add("show");
    });
}

if (resp_popup) {
    resp_popup.classList.add("show");
}

close_resp_popup.addEventListener("click", function () {
    resp_popup.classList.remove("show");
});

close_file_popup.addEventListener("click", function () {
    file_popup.classList.remove("show");
});


form_upload.addEventListener("submit", function () {
    openMsgPopup();
});
window.addEventListener("click", function (event) {
    if (event.target == file_popup) {
        openMsgPopup();
    };
});
function openMsgPopup() {
    file_popup.classList.remove("show");
    msg_popup.classList.add("show");
};