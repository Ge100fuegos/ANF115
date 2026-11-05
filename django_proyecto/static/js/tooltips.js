var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-t="tooltip"]'));
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});