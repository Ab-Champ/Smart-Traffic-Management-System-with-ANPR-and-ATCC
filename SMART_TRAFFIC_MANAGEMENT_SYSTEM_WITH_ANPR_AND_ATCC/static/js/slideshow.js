let slideIndex = 0;

function showSlides() {
    const slides = document.querySelectorAll('.slide');
    slides.forEach(slide => (slide.style.display = 'none'));

    slideIndex++;
    if (slideIndex > slides.length) {
        slideIndex = 1;
    }

    slides[slideIndex - 1].style.display = 'block';
    setTimeout(showSlides, 4000); // Change slide every 4 seconds
}

document.addEventListener('DOMContentLoaded', showSlides);
