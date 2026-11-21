// Auto-close alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});

// Confirm delete actions
function confirmDelete(message = 'Are you sure?') {
    return confirm(message);
}

// Format date input
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toISOString().split('T')[0];
}

// Calculate days until due
function calculateDaysUntil(targetDate) {
    const today = new Date();
    const target = new Date(targetDate);
    const time = target - today;
    const days = Math.ceil(time / (1000 * 60 * 60 * 24));
    return days;
}

// Update maintenance status display
function updateMaintenanceStatus() {
    const nextDueElements = document.querySelectorAll('[data-next-due]');
    nextDueElements.forEach(element => {
        const nextDate = element.getAttribute('data-next-due');
        const daysUntil = calculateDaysUntil(nextDate);

        if (daysUntil < 0) {
            element.classList.add('overdue');
        } else if (daysUntil <= 7) {
            element.classList.add('due-soon');
        }
    });
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard!');
    });
}

// Validate form before submission
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    const inputs = form.querySelectorAll('input[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.style.borderColor = '#ef4444';
            isValid = false;
        } else {
            input.style.borderColor = '';
        }
    });

    return isValid;
}

// Print page function
function printPage() {
    window.print();
}

// Toggle sidebar (if needed for mobile)
function toggleMenu() {
    const menu = document.querySelector('.nav-menu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Ctrl+S or Cmd+S to submit form
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        const form = document.querySelector('form');
        if (form) form.submit();
    }

    // Escape to close modals/alerts
    if (event.key === 'Escape') {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.display = 'none';
        });
    }
});

// Export table to CSV
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;

    let csv = [];
    const rows = table.querySelectorAll('tr');

    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        let csvrow = [];
        cols.forEach(col => {
            csvrow.push('"' + col.innerText.replace(/"/g, '""') + '"');
        });
        csv.push(csvrow.join(','));
    });

    downloadCSV(csv.join('\n'), filename);
}

function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: "text/csv"});
    const downloadLink = document.createElement("a");
    downloadLink.href = URL.createObjectURL(csvFile);
    downloadLink.download = filename;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Initialize on page load
window.addEventListener('load', function() {
    updateMaintenanceStatus();
});
