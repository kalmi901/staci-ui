(() => {
    function initializeFrame(frame) {
        let observer;
        let pendingResize = 0;

        function resize() {
            pendingResize = 0;
            const content = frame.contentDocument;
            if (!content || !content.body) {
                return;
            }

            const footer = document.querySelector('footer');
            const footerHeight = footer ? footer.getBoundingClientRect().height : 0;
            const top = frame.getBoundingClientRect().top + window.scrollY;
            const minimumHeight = Math.max(0, window.innerHeight - top - footerHeight);
            const contentHeight = content.body.getBoundingClientRect().height;
            const height = Math.ceil(Math.max(minimumHeight, contentHeight));
            if (frame.style.height !== `${height}px`) {
                frame.style.height = `${height}px`;
            }
        }

        function scheduleResize() {
            if (!pendingResize) {
                pendingResize = window.requestAnimationFrame(resize);
            }
        }

        function observeContent() {
            if (observer) {
                observer.disconnect();
            }

            const content = frame.contentDocument;
            if (!content || !content.body) {
                return;
            }

            const style = content.createElement('style');
            style.textContent = `
                html, body { height: auto; min-height: 0; overflow: hidden; }
                body { margin: 0; }
                .app-shell, .sidebar { min-height: 0; }
            `;
            content.head.appendChild(style);
            observer = new ResizeObserver(scheduleResize);
            observer.observe(content.body);
            scheduleResize();
        }

        frame.addEventListener('load', observeContent);
        window.addEventListener('resize', scheduleResize);
        if (frame.contentDocument && frame.contentDocument.readyState === 'complete') {
            observeContent();
        }
    }

    function initialize() {
        document.querySelectorAll('.staci-tool-frame').forEach(initializeFrame);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, { once: true });
    } else {
        initialize();
    }
})();
