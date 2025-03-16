$(document).ready(function() {
    $("#toggle-btn").click(function() {
        $("#sidebar").toggleClass("collapsed");
        $("#content").toggleClass("collapsed");
        if ($("#sidebar").hasClass("collapsed")) {
            $(this).text("▶"); // 접혔을 때
        } else {
            $(this).text("◀"); // 펼쳤을 때
        }
    });
});