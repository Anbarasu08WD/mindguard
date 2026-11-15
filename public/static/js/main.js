// MINDGUARD Main Client-side Script
document.addEventListener("DOMContentLoaded", function () {
    // Initialize Lucide icons if available
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // Password visibility toggle
    const toggleBtns = document.querySelectorAll(".toggle-password-btn");
    toggleBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (input) {
                if (input.type === "password") {
                    input.type = "text";
                    this.innerHTML = '<i data-lucide="eye-off"></i>';
                } else {
                    input.type = "password";
                    this.innerHTML = '<i data-lucide="eye"></i>';
                }
                if (window.lucide) {
                    window.lucide.createIcons();
                }
            }
        });
    });

    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("appSidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener("click", function (event) {
            if (!sidebar.contains(event.target) && !sidebarToggle.contains(event.target)) {
                sidebar.classList.remove("open");
            }
        });
    }
});
