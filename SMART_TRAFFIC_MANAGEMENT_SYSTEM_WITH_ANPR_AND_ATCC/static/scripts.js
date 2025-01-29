// Add animations to flash messages
document.addEventListener("DOMContentLoaded", () => {
    const flashMessages = document.querySelectorAll(".flashes li");

    flashMessages.forEach((msg) => {
        setTimeout(() => {
            msg.style.opacity = "0";
            msg.style.transform = "translateY(-10px)";
            setTimeout(() => msg.remove(), 500);
        }, 3000); // Auto-hide after 3 seconds
    });
});

// Add hover effect to the navigation
document.querySelectorAll("nav a").forEach((link) => {
    link.addEventListener("mouseenter", () => {
        link.style.transform = "scale(1.1)";
    });
    link.addEventListener("mouseleave", () => {
        link.style.transform = "scale(1)";
    });
});
