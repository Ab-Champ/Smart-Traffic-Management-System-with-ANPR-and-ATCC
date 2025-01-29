// Dynamically load and display live CCTV feeds
function loadCCTVFeeds(ips) {
    const container = document.getElementById('cctv-container');
    container.innerHTML = ''; // Clear any previous content

    ips.forEach((ip, index) => {
        const feed = document.createElement('div');
        feed.classList.add('cctv-feed');
        feed.innerHTML = `
            <h3>Camera ${index + 1}</h3>
            <img src="http://${ip}/video" alt="Live feed from ${ip}" width="100%" />
        `;
        container.appendChild(feed);
    });
}

// Mock IPs for now
const mockIPs = ["192.168.1.101", "192.168.1.102", "192.168.1.103", "192.168.1.104"];
document.addEventListener('DOMContentLoaded', () => {
    loadCCTVFeeds(mockIPs);
});
