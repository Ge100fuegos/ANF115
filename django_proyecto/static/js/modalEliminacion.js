document.addEventListener("DOMContentLoaded", function() {
    var deleteButtons = document.querySelectorAll('.delete-btn');
    var confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
    var confirmDeleteButton = document.getElementById('confirmDeleteButton');
    var currentHref = '';

    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            currentHref = button.getAttribute('href');
            confirmDeleteModal.show();
        });
    });

    confirmDeleteButton.addEventListener('click', function() {
        window.location.href = currentHref;
    });
});