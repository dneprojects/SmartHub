const form_upload = document.getElementById("file_upload");
const form_download = document.getElementById("file_download");
const form_rtr_update = document.getElementById("rtr_fw_upload");
const form_mod_update = document.getElementById("mod_fw_upload");

files_button.addEventListener("click", function () {
    file_popup.classList.add("show");
});
close_file_popup.addEventListener("click", function () {
    file_popup.classList.remove("show");
});
form_upload.addEventListener("submit", function () {
    openMsgPopup();
});
updates_button.addEventListener("click", function () {
    updates_popup.classList.add("show");
});
close_updates_popup.addEventListener("click", function () {
    updates_popup.classList.remove("show");
});
form_rtr_update.addEventListener("submit", function () {
    openMsgPopup();
});
form_mod_update.addEventListener("submit", function () {
    openMsgPopup();
});
window.addEventListener("click", function (event) {
    if (event.target == file_popup) {
    openMsgPopup();
    };
});
function openMsgPopup() {
    file_popup.classList.remove("show");
    updates_popup.classList.remove("show");
    msg_popup.classList.add("show");
};