(function () {
    const loader = document.getElementById("pageLoader");
    if (!loader) {
        return;
    }
    const LOADER_DELAY_MS = 2000;

    let isVisible = false;
    let isNavigating = false;

    function showLoader() {
        if (isVisible) {
            return;
        }
        isVisible = true;
        loader.classList.add("is-active");
        loader.setAttribute("aria-hidden", "false");
    }

    function hideLoader() {
        isVisible = false;
        loader.classList.remove("is-active");
        loader.setAttribute("aria-hidden", "true");
    }

    function isSamePageHashLink(anchor) {
        if (!anchor.hash) {
            return false;
        }
        const anchorUrl = new URL(anchor.href, window.location.href);
        return (
            anchorUrl.origin === window.location.origin &&
            anchorUrl.pathname === window.location.pathname &&
            anchorUrl.search === window.location.search
        );
    }

    document.addEventListener(
        "click",
        function (event) {
            const anchor = event.target.closest("a[href]");
            if (!anchor) {
                return;
            }

            const href = anchor.getAttribute("href");
            if (!href || href === "#" || href.startsWith("javascript:")) {
                return;
            }
            if (anchor.hasAttribute("download") || anchor.target === "_blank") {
                return;
            }
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                return;
            }
            if (isSamePageHashLink(anchor)) {
                return;
            }
            if (isNavigating) {
                event.preventDefault();
                return;
            }

            event.preventDefault();
            isNavigating = true;
            showLoader();
            window.setTimeout(function () {
                window.location.href = anchor.href;
            }, LOADER_DELAY_MS);
        },
        true
    );

    document.addEventListener(
        "submit",
        function (event) {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) {
                return;
            }
            if (form.target === "_blank") {
                return;
            }
            if (form.dataset.loaderSubmitted === "1") {
                return;
            }
            if (isNavigating) {
                event.preventDefault();
                return;
            }

            event.preventDefault();
            isNavigating = true;
            form.dataset.loaderSubmitted = "1";
            showLoader();
            window.setTimeout(function () {
                form.submit();
            }, LOADER_DELAY_MS);
        },
        true
    );

    window.addEventListener("pageshow", hideLoader);
})();
