// ==========================================================================
// PROCESS & MEMORY HARD LOCK (EXTREME COMPACT)
// ==========================================================================
user_pref("dom.ipc.processCount", 1);               // Enforce single process
user_pref("browser.cache.memory.capacity", 65536);  // Hard cap memory cache at 64MB
user_pref("fission.bfcacheInParent", false);        // Disable bfcache (modern architecture)
user_pref("browser.sessionhistory.max_serialized_entries", 1); // Kill Back/Forward chain (modern replacement)
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.sessionstore.max_tabs_undo", 0);
user_pref("browser.sessionstore.max_windows_undo", 0);

// ==========================================================================
// JS ENGINE THINNING & AGGRESSIVE GC
// ==========================================================================
user_pref("javascript.options.ion", false);         // Disable heavy JIT compilation
user_pref("javascript.options.baselinejit", false);
user_pref("javascript.options.wasm_baselinejit", false);
user_pref("javascript.options.mem.gc_incremental_slice_ms", 10); // Force aggressive garbage collection

// ==========================================================================
// RENDERING & CPU MITIGATION
// ==========================================================================
user_pref("general.smoothScroll", false);            // Disable physics scroll animations
user_pref("general.smoothScroll.scrollbar", false);
user_pref("general.smoothScroll.mouseWheel", false);
user_pref("general.smoothScroll.keyboard", false);
user_pref("dom.animations-api.core.enabled", false);
user_pref("gfx.canvas.willReadFrequently.enable", true);
user_pref("image.animation_mode", "none");          // Stop GIF/WebP loop animations
user_pref("toolkit.cosmeticAnimations.enabled", false);
user_pref("reader.parse-on-load.enabled", false);
user_pref("browser.urlbar.maxRichResults", 3);
user_pref("layout.frame_rate", 60);                  // Lock maximum frame rate

// ==========================================================================
// NETWORK & PREFETCHING CUTOFF
// ==========================================================================
user_pref("network.http.max-connections", 300);
user_pref("network.prefetch-next", false);
user_pref("network.dns.disablePrefetch", true);
user_pref("network.http.speculative-parallel-limit", 0);
user_pref("network.dns.disableIPv6", true);

// ==========================================================================
// HARDWARE DECODING FORCE & CROSS-PLATFORM COMPATIBILITY
// ==========================================================================
user_pref("media.h264.enabled", true);               // Force H.264 decode
user_pref("media.wmf.h264.enabled", true);           // Force H.264 decode on Windows
user_pref("media.mp4.hevc.enabled", false);          // Disable HEVC decode
user_pref("media.av1.enabled", false);               // Disable heavy AV1 decode
user_pref("media.vp9.enabled", false);               // Disable VP9 decode
user_pref("media.mediasource.vp9.enabled", false);   // Disable VP9 MediaSource
user_pref("media.webm.enabled", false);              // Disable WebM container (VP8/VP9)
user_pref("media.mediasource.webm.enabled", false);  // Disable WebM MediaSource
user_pref("media.peerconnection.enabled", false);
user_pref("webgl.disabled", true);                   // Kill WebGL to save CPU/GPU overhead

// [Cross-Platform Hardware Acceleration]
user_pref("media.windows-media-foundation.enabled", true); // Native hardware decode for Windows
user_pref("media.ffmpeg.vaapi.enabled", true);             // Native hardware decode (VA-API) for Linux
user_pref("media.rdd-ffmpeg.enabled", true);               // Process isolation for Linux media engine

// ==========================================================================
// MOZILLA UI STRIPPING & PRIVACY
// ==========================================================================
user_pref("browser.privatebrowsing.vpnpromourl", "");
user_pref("extensions.getAddons.showPane", false);
user_pref("extensions.htmlaboutaddons.recommendations.enabled", false);
user_pref("browser.discovery.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.addons", false);
user_pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.features", false);
user_pref("browser.preferences.moreFromMozilla", false);
user_pref("browser.aboutConfig.showWarning", false);
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.profiles.enabled", true);
user_pref("permissions.default.shortcuts", 2);
user_pref("browser.backspace_action", 2);            // Disable backspace for back navigation
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true); // Set true ONLY if userChrome.css is used