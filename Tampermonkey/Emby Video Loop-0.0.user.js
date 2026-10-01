// ==UserScript==
// @name         Emby Video Loop
// @match        http://10.0.0.21:8096/web/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // Observe DOM changes to capture dynamically rendered video elements
    const observer = new MutationObserver(() => {
        const video = document.querySelector('video');
        if (video && !video.loop) {
            video.loop = true;
            // Fallback: force replay if playback ends without looping
            video.onended = () => {
                video.currentTime = 0;
                video.play();
            };
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
})();