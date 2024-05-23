const form_upload = document.getElementById("file_upload");
const form_download = document.getElementById("file_download");
if (document.getElementById("files_button")) {
    files_button.addEventListener("click", function () {
        file_popup.classList.add("show");
    });
}

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