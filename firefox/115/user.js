/******
*    name: arkenfox user.js (Migrated with personal overrides for ESR 115)
*    date: 27 August 2023
* version: 115
*     url: https://github.com/arkenfox/user.js
* license: MIT: https://github.com/arkenfox/user.js/blob/master/LICENSE.txt
******/

/* START: internal custom pref to test for syntax errors ***/
user_pref("_user.js.parrot", "START: Oh yes, the Norwegian Blue... what's wrong with it?");

/* 0000: disable about:config warning ***/
user_pref("browser.aboutConfig.showWarning", false);

/*** [SECTION 0100]: STARTUP ***/
user_pref("_user.js.parrot", "0100 syntax error: the parrot's dead!");
/* 0102: set startup page [SETUP-CHROME]
 * 0=blank, 1=home, 2=last visited page, 3=resume previous session ***/
user_pref("browser.startup.page", 1);
/* 0103: set HOME+NEWWINDOW page ***/
user_pref("browser.startup.homepage", "http://10.0.0.21");
/* 0104: set NEWTAB page ***/
user_pref("browser.newtabpage.enabled", false);
/* 0105: disable sponsored content on Firefox Home (Activity Stream) ***/
user_pref("browser.newtabpage.activity-stream.showSponsored", false); // [FF58+] Pocket > Sponsored Stories
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false); // [FF83+] Sponsored shortcuts
/* 0106: clear default topsites ***/
user_pref("browser.newtabpage.activity-stream.default.sites", "");

/*** [SECTION 0200]: GEOLOCATION / LANGUAGE / LOCALE ***/
user_pref("_user.js.parrot", "0200 syntax error: the parrot's definitely deceased!");
/* 0201: use Mozilla geolocation service instead of Google if permission is granted [FF74+] ***/
   // user_pref("geo.provider.network.url", "https://location.services.mozilla.com/v1/geolocate?key=%MOZILLA_API_KEY%");
   // user_pref("geo.provider.network.logging.enabled", true); // [HIDDEN PREF]
/* 0202: disable using the OS's geolocation service ***/
user_pref("geo.provider.ms-windows-location", false); // [WINDOWS]
user_pref("geo.provider.use_corelocation", false); // [MAC]
user_pref("geo.provider.use_gpsd", false); // [LINUX]
user_pref("geo.provider.use_geoclue", false); // [FF102+] [LINUX]
/* 0210: set preferred language for displaying pages ***/
   // user_pref("intl.accept_languages", "en-US, en");
/* 0211: use en-US locale regardless of the system or region locale ***/
   // user_pref("javascript.use_us_english_locale", true); // [HIDDEN PREF]

/*** [SECTION 0300]: QUIETER FOX ***/
user_pref("_user.js.parrot", "0300 syntax error: the parrot's not pinin' for the fjords!");
/** RECOMMENDATIONS ***/
/* 0320: disable recommendation pane in about:addons (uses Google Analytics) ***/
user_pref("extensions.getAddons.showPane", false); // [HIDDEN PREF]
/* 0321: disable recommendations in about:addons' Extensions and Themes panes [FF68+] ***/
user_pref("extensions.htmlaboutaddons.recommendations.enabled", false);
/* 0322: disable personalized Extension Recommendations in about:addons and AMO [FF65+] ***/
user_pref("browser.discovery.enabled", false);

/** TELEMETRY ***/
/* 0330: disable new data submission [FF41+] ***/
user_pref("datareporting.policy.dataSubmissionEnabled", false);
/* 0331: disable Health Reports ***/
user_pref("datareporting.healthreport.uploadEnabled", false);
/* 0332: disable telemetry ***/
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.enabled", false); // see [NOTE]
user_pref("toolkit.telemetry.server", "data:,");
user_pref("toolkit.telemetry.archive.enabled", false);
user_pref("toolkit.telemetry.newProfilePing.enabled", false); // [FF55+]
user_pref("toolkit.telemetry.shutdownPingSender.enabled", false); // [FF55+]
user_pref("toolkit.telemetry.updatePing.enabled", false); // [FF56+]
user_pref("toolkit.telemetry.bhrPing.enabled", false); // [FF57+] Background Hang Reporter
user_pref("toolkit.telemetry.firstShutdownPing.enabled", false); // [FF57+]
/* 0333: disable Telemetry Coverage ***/
user_pref("toolkit.telemetry.coverage.opt-out", true); // [HIDDEN PREF]
user_pref("toolkit.coverage.opt-out", true); // [FF64+] [HIDDEN PREF]
user_pref("toolkit.coverage.endpoint.base", "");
/* 0334: disable PingCentre telemetry (used in several System Add-ons) [FF57+] ***/
user_pref("browser.ping-centre.telemetry", false);
/* 0335: disable Firefox Home (Activity Stream) telemetry ***/
user_pref("browser.newtabpage.activity-stream.feeds.telemetry", false);
user_pref("browser.newtabpage.activity-stream.telemetry", false);

/** STUDIES ***/
/* 0340: disable Studies ***/
user_pref("app.shield.optoutstudies.enabled", false);
/* 0341: disable Normandy/Shield [FF60+] ***/
user_pref("app.normandy.enabled", false);
user_pref("app.normandy.api_url", "");

/** CRASH REPORTS ***/
/* 0350: disable Crash Reports ***/
user_pref("breakpad.reportURL", "");
user_pref("browser.tabs.crashReporting.sendReport", false); // [FF44+]
   // user_pref("browser.crashReports.unsubmittedCheck.enabled", false); // [FF51+] [DEFAULT: false]
/* 0351: enforce no submission of backlogged Crash Reports [FF58+] ***/
user_pref("browser.crashReports.unsubmittedCheck.autoSubmit2", false); // [DEFAULT: false]

/** OTHER ***/
/* 0360: disable Captive Portal detection ***/
user_pref("captivedetect.canonicalURL", "");
user_pref("network.captive-portal-service.enabled", false); // [FF52+]
/* 0361: disable Network Connectivity checks [FF65+] ***/
user_pref("network.connectivity-service.enabled", false);

/*** [SECTION 0400]: SAFE BROWSING (SB) ***/
user_pref("_user.js.parrot", "0400 syntax error: the parrot's passed on!");
/* 0401: disable SB (Safe Browsing) ***/
   // user_pref("browser.safebrowsing.malware.enabled", false);
   // user_pref("browser.safebrowsing.phishing.enabled", false);
/* 0402: disable SB checks for downloads (both local lookups + remote) ***/
   // user_pref("browser.safebrowsing.downloads.enabled", false);
/* 0403: disable SB checks for downloads (remote) ***/
user_pref("browser.safebrowsing.downloads.remote.enabled", false);
   // user_pref("browser.safebrowsing.downloads.remote.url", ""); // Defense-in-depth
/* 0404: disable SB checks for unwanted software ***/
   // user_pref("browser.safebrowsing.downloads.remote.block_potentially_unwanted", false);
   // user_pref("browser.safebrowsing.downloads.remote.block_uncommon", false);
/* 0405: disable "ignore this warning" on SB warnings [FF45+] ***/
   // user_pref("browser.safebrowsing.allowOverride", false);

/*** [SECTION 0600]: BLOCK IMPLICIT OUTBOUND ***/
user_pref("_user.js.parrot", "0600 syntax error: the parrot's no more!");
/* 0601: disable link prefetching ***/
user_pref("network.prefetch-next", false);
/* 0602: disable DNS prefetching ***/
user_pref("network.dns.disablePrefetch", true);
user_pref("network.dns.disablePrefetchFromHTTPS", true); // [DEFAULT: true]
/* 0603: disable predictor / prefetching ***/
user_pref("network.predictor.enabled", false);
user_pref("network.predictor.enable-prefetch", false); // [FF48+] [DEFAULT: false]
/* 0604: disable link-mouseover opening connection to linked server ***/
user_pref("network.http.speculative-parallel-limit", 0);
/* 0605: disable mousedown speculative connections on bookmarks and history [FF98+] ***/
user_pref("browser.places.speculativeConnect.enabled", false);
/* 0610: enforce no "Hyperlink Auditing" (click tracking) ***/
   // user_pref("browser.send_pings", false); // [DEFAULT: false]

/*** [SECTION 0700]: DNS / DoH / PROXY / SOCKS ***/
user_pref("_user.js.parrot", "0700 syntax error: the parrot's given up the ghost!");
/* 0702: set the proxy server to do any DNS lookups when using SOCKS ***/
user_pref("network.proxy.socks_remote_dns", true);
/* 0703: disable using UNC (Uniform Naming Convention) paths [FF61+] ***/
user_pref("network.file.disable_unc_paths", true); // [HIDDEN PREF]
/* 0704: disable GIO as a potential proxy bypass vector ***/
user_pref("network.gio.supported-protocols", ""); // [HIDDEN PREF]
/* 0705: disable proxy direct failover for system requests [FF91+] ***/
   // user_pref("network.proxy.failover_direct", false);
/* 0706: disable proxy bypass for system request failures [FF95+] ***/
   // user_pref("network.proxy.allow_bypass", false);
/* 0710: disable DNS-over-HTTPS (DoH) rollout [FF60+] ***/
user_pref("network.trr.mode", 5);

/*** [SECTION 0800]: LOCATION BAR / SEARCH BAR / SUGGESTIONS / HISTORY / FORMS ***/
user_pref("_user.js.parrot", "0800 syntax error: the parrot's ceased to be!");
/* 0802: disable location bar domain guessing ***/
user_pref("browser.fixup.alternate.enabled", false); // [DEFAULT: false FF104+]
/* 0804: disable live search suggestions ***/
user_pref("browser.search.suggest.enabled", false);
user_pref("browser.urlbar.suggest.searches", false);
/* 0805: disable location bar making speculative connections [FF56+] ***/
user_pref("browser.urlbar.speculativeConnect.enabled", false);
/* 0806: disable location bar leaking single words to a DNS provider **after searching** [FF78+] ***/
user_pref("browser.urlbar.dnsResolveSingleWordsAfterSearch", 0); // [DEFAULT: 0 FF104+]
/* 0807: disable location bar contextual suggestions [FF92+] ***/
user_pref("browser.urlbar.quicksuggest.enabled", false); // [FF92+]
user_pref("browser.urlbar.suggest.quicksuggest.nonsponsored", false); // [FF95+]
user_pref("browser.urlbar.suggest.quicksuggest.sponsored", false);
user_pref("browser.urlbar.addons.featureGate", false); // [FF115+]
user_pref("browser.urlbar.weather.featureGate", false); // [FF108+]
/* 0808: disable tab-to-search [FF85+] ***/
   // user_pref("browser.urlbar.suggest.engines", false);
/* 0810: disable search and form history ***/
user_pref("browser.formfill.enable", false);
/* 0820: disable coloring of visited links ***/
   // user_pref("layout.css.visited_links_enabled", false);
/* 0830: enable separate default search engine in Private Windows and its UI setting ***/
user_pref("browser.search.separatePrivateDefault", true); // [FF70+]
user_pref("browser.search.separatePrivateDefault.ui.enabled", true); // [FF71+]

/*** [SECTION 0900]: PASSWORDS ***/
user_pref("_user.js.parrot", "0900 syntax error: the parrot's expired!");
/* 0903: disable auto-filling username & password form fields ***/
user_pref("signon.autofillForms", false);
/* 0904: disable formless login capture for Password Manager [FF51+] ***/
user_pref("signon.formlessCapture.enabled", false);
/* 0905: limit (or disable) HTTP authentication credentials dialogs triggered by sub-resources [FF41+] ***/
user_pref("network.auth.subresource-http-auth-allow", 1);
/* 0906: enforce no automatic authentication on Microsoft sites [FF91+] [WINDOWS 10+] ***/
   // user_pref("network.http.windows-sso.enabled", false); // [DEFAULT: false]

/*** [SECTION 1000]: DISK AVOIDANCE ***/
user_pref("_user.js.parrot", "1000 syntax error: the parrot's gone to meet 'is maker!");
/* 1001: disable disk cache ***/
user_pref("browser.cache.disk.enable", false);
/* 1002: disable media cache from writing to disk in Private Browsing ***/
user_pref("browser.privatebrowsing.forceMediaMemoryCache", true); // [FF75+]
user_pref("media.memory_cache_max_size", 65536);
/* 1003: disable storing extra session data [SETUP-CHROME] ***/
user_pref("browser.sessionstore.privacy_level", 2);
/* 1005: disable automatic Firefox start and session restore after reboot [FF62+] [WINDOWS] ***/
user_pref("toolkit.winRegisterApplicationRestart", false);
/* 1006: disable favicons in shortcuts ***/
user_pref("browser.shell.shortcutFavicons", false);

/*** [SECTION 1200]: HTTPS (SSL/TLS / OCSP / CERTS / HPKP) ***/
user_pref("_user.js.parrot", "1200 syntax error: the parrot's a stiff!");
/** SSL (Secure Sockets Layer) / TLS (Transport Layer Security) ***/
/* 1201: require safe negotiation ***/
user_pref("security.ssl.require_safe_negotiation", true);
/* 1206: disable TLS1.3 0-RTT (round-trip time) [FF51+] ***/
user_pref("security.tls.enable_0rtt_data", false);

/** OCSP (Online Certificate Status Protocol) ***/
/* 1211: enforce OCSP fetching to confirm current validity of certificates ***/
user_pref("security.OCSP.enabled", 1); // [DEFAULT: 1]
/* 1212: set OCSP fetch failures (non-stapled, see 1211) to hard-fail ***/
user_pref("security.OCSP.require", true);

/** CERTS / HPKP (HTTP Public Key Pinning) ***/
/* 1221: disable Windows 8.1's Microsoft Family Safety cert [FF50+] [WINDOWS] ***/
user_pref("security.family_safety.mode", 0);
/* 1223: enable strict PKP (Public Key Pinning) ***/
user_pref("security.cert_pinning.enforcement_level", 2);
/* 1224: enable CRLite [FF73+] ***/
user_pref("security.remote_settings.crlite_filters.enabled", true);
user_pref("security.pki.crlite_mode", 2);

/** MIXED CONTENT ***/
/* 1241: disable insecure passive content (such as images) on https pages ***/
   // user_pref("security.mixed_content.block_display_content", true); // Defense-in-depth (see 1244)
/* 1244: enable HTTPS-Only mode in all windows [FF76+] ***/
user_pref("dom.security.https_only_mode", false); // [FF76+]
   // user_pref("dom.security.https_only_mode_pbm", true); // [FF80+]
/* 1245: enable HTTPS-Only mode for local resources [FF77+] ***/
   // user_pref("dom.security.https_only_mode.upgrade_local", true);
/* 1246: disable HTTP background requests [FF82+] ***/
user_pref("dom.security.https_only_mode_send_http_background_request", false);

/** UI (User Interface) ***/
/* 1270: display warning on the padlock for "broken security" (if 1201 is false) ***/
user_pref("security.ssl.treat_unsafe_negotiation_as_broken", true);
/* 1272: display advanced information on Insecure Connection warning pages ***/
user_pref("browser.xul.error_pages.expert_bad_cert", true);

/*** [SECTION 1400]: FONTS ***/
user_pref("_user.js.parrot", "1400 syntax error: the parrot's bereft of life!");
/* 1402: limit font visibility (Windows, Mac, some Linux) [FF94+] ***/
   // user_pref("layout.css.font-visibility.private", 1);
   // user_pref("layout.css.font-visibility.standard", 1);
   // user_pref("layout.css.font-visibility.trackingprotection", 1);

/*** [SECTION 1600]: REFERERS ***/
user_pref("_user.js.parrot", "1600 syntax error: the parrot rests in peace!");
/* 1602: control the amount of cross-origin information to send [FF52+] ***/
user_pref("network.http.referer.XOriginTrimmingPolicy", 2);

/*** [SECTION 1700]: CONTAINERS ***/
user_pref("_user.js.parrot", "1700 syntax error: the parrot's bit the dust!");
/* 1701: enable Container Tabs and its UI setting [FF50+] ***/
user_pref("privacy.userContext.enabled", true);
user_pref("privacy.userContext.ui.enabled", true);
/* 1702: set behavior on "+ Tab" button to display container menu on left click [FF74+] ***/
   // user_pref("privacy.userContext.newTabContainerOnLeftClick.enabled", true);

/*** [SECTION 2000]: PLUGINS / MEDIA / WEBRTC ***/
user_pref("_user.js.parrot", "2000 syntax error: the parrot's snuffed it!");
/* 2002: force WebRTC inside the proxy [FF70+] ***/
user_pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);
/* 2003: force a single network interface for ICE candidates generation [FF42+] ***/
user_pref("media.peerconnection.ice.default_address_only", true);
/* 2004: force exclusion of private IPs from ICE candidates [FF51+] ***/
   // user_pref("media.peerconnection.ice.no_host", true);
/* 2020: disable GMP (Gecko Media Plugins) ***/
   // user_pref("media.gmp-provider.enabled", false);

/*** [SECTION 2400]: DOM (DOCUMENT OBJECT MODEL) ***/
user_pref("_user.js.parrot", "2400 syntax error: the parrot's kicked the bucket!");
/* 2402: prevent scripts from moving and resizing open windows ***/
user_pref("dom.disable_window_move_resize", true);

/*** [SECTION 2600]: MISCELLANEOUS ***/
user_pref("_user.js.parrot", "2600 syntax error: the parrot's run down the curtain!");
/* 2601: prevent accessibility services from accessing your browser [RESTART] ***/
   // user_pref("accessibility.force_disabled", 1);
/* 2603: remove temp files opened with an external application ***/
user_pref("browser.download.start_downloads_in_tmp_dir", true); // [FF102+]
user_pref("browser.helperApps.deleteTempFileOnExit", true);
/* 2606: disable UITour backend so there is no chance that a remote page can use it ***/
user_pref("browser.uitour.enabled", false);
   // user_pref("browser.uitour.url", ""); // Defense-in-depth
/* 2608: reset remote debugging to disabled ***/
user_pref("devtools.debugger.remote-enabled", false); // [DEFAULT: false]
/* 2615: disable websites overriding Firefox's keyboard shortcuts [FF58+] ***/
user_pref("permissions.default.shortcuts", 2);
/* 2616: remove special permissions for certain mozilla domains [FF35+] ***/
user_pref("permissions.manager.defaultsUrl", "");
/* 2617: remove webchannel whitelist ***/
user_pref("webchannel.allowObject.urlWhitelist", "");
/* 2619: use Punycode in Internationalized Domain Names to eliminate possible spoofing ***/
user_pref("network.IDN_show_punycode", true);
/* 2620: enforce PDFJS, disable PDFJS scripting ***/
user_pref("pdfjs.disabled", false); // [DEFAULT: false]
user_pref("pdfjs.enableScripting", false); // [FF86+]
/* 2623: disable permissions delegation [FF73+] ***/
user_pref("permissions.delegation.enabled", false);
/* 2624: disable middle click on new tab button opening URLs or searches using clipboard [FF115+] ***/
user_pref("browser.tabs.searchclipboardfor.middleclick", false); // [DEFAULT: false NON-LINUX]

/** DOWNLOADS ***/
/* 2651: enable user interaction for security by always asking where to download ***/
user_pref("browser.download.useDownloadDir", true);
/* 2652: disable downloads panel opening on every download [FF96+] ***/
user_pref("browser.download.alwaysOpenPanel", false);
/* 2653: disable adding downloads to the system's "recent documents" list ***/
user_pref("browser.download.manager.addToRecentDocs", false);
/* 2654: enable user interaction for security by always asking how to handle new mimetypes [FF101+] ***/
user_pref("browser.download.always_ask_before_handling_new_types", false);

/** EXTENSIONS ***/
/* 2660: lock down allowed extension directories ***/
user_pref("extensions.enabledScopes", 5); // [HIDDEN PREF]
   // user_pref("extensions.autoDisableScopes", 15); // [DEFAULT: 15]
/* 2661: disable bypassing 3rd party extension install prompts [FF82+] ***/
user_pref("extensions.postDownloadThirdPartyPrompt", false);
/* 2662: disable webextension restrictions on certain mozilla domains (you also need 4503) [FF60+] ***/
   // user_pref("extensions.webextensions.restrictedDomains", "");

/*** [SECTION 2700]: ETP (ENHANCED TRACKING PROTECTION) ***/
user_pref("_user.js.parrot", "2700 syntax error: the parrot's joined the bleedin' choir invisible!");
/* 2701: enable ETP Strict Mode [FF86+] ***/
// user_pref("browser.contentblocking.category", "strict");
user_pref("browser.contentblocking.category", "standard");
/* 2702: disable ETP web compat features [FF93+] ***/
   // user_pref("privacy.antitracking.enableWebcompat", false);
/* 2710: enable state partitioning of service workers [FF96+] ***/
user_pref("privacy.partition.serviceWorkers", true); // [DEFAULT: true FF105+]
/* 2720: enable APS (Always Partitioning Storage) ***/
user_pref("privacy.partition.always_partition_third_party_non_cookie_storage", true); // [FF104+] [DEFAULT: true FF109+]
user_pref("privacy.partition.always_partition_third_party_non_cookie_storage.exempt_sessionstorage", false); // [FF105+] [DEFAULT: false FF109+]

/*** [SECTION 2800]: SHUTDOWN & SANITIZING ***/
user_pref("_user.js.parrot", "2800 syntax error: the parrot's bleedin' demised!");
/* 2810: enable Firefox to clear items on shutdown ***/
user_pref("privacy.sanitize.sanitizeOnShutdown", true);

/** SANITIZE ON SHUTDOWN: IGNORES "ALLOW" SITE EXCEPTIONS ***/
/* 2811: set/enforce what items to clear on shutdown (if 2810 is true) [SETUP-CHROME] ***/
user_pref("privacy.clearOnShutdown.cache", true);     // [DEFAULT: true]
user_pref("privacy.clearOnShutdown.downloads", false); // Mapped from 140 clearOnShutdown_v2.downloads = false
user_pref("privacy.clearOnShutdown.formdata", true);  // [DEFAULT: true]
user_pref("privacy.clearOnShutdown.history", true);   // [DEFAULT: true]
user_pref("privacy.clearOnShutdown.sessions", true);  // [DEFAULT: true]
   // user_pref("privacy.clearOnShutdown.siteSettings", false); // [DEFAULT: false]
/* 2812: set Session Restore to clear on shutdown (if 2810 is true) [FF34+] ***/
   // user_pref("privacy.clearOnShutdown.openWindows", true);

/** SANITIZE ON SHUTDOWN: RESPECTS "ALLOW" SITE EXCEPTIONS FF103+ ***/
/* 2815: set "Cookies" and "Site Data" to clear on shutdown (if 2810 is true) [SETUP-CHROME] ***/
user_pref("privacy.clearOnShutdown.cookies", true); // Cookies
user_pref("privacy.clearOnShutdown.offlineApps", true); // Site Data

/** SANITIZE MANUAL: IGNORES "ALLOW" SITE EXCEPTIONS ***/
/* 2820: reset default items to clear with Ctrl-Shift-Del [SETUP-CHROME] ***/
user_pref("privacy.cpd.cache", true);    // [DEFAULT: true]
user_pref("privacy.cpd.formdata", true); // [DEFAULT: true]
user_pref("privacy.cpd.history", true);  // [DEFAULT: true]
user_pref("privacy.cpd.sessions", true); // [DEFAULT: true]
user_pref("privacy.cpd.offlineApps", false); // [DEFAULT: false]
user_pref("privacy.cpd.cookies", false);
   // user_pref("privacy.cpd.downloads", true); // not used, see note above
   // user_pref("privacy.cpd.openWindows", false); // Session Restore
   // user_pref("privacy.cpd.passwords", false);
   // user_pref("privacy.cpd.siteSettings", false);
/* 2822: reset default "Time range to clear" for "Clear Recent History" (2820) ***/
user_pref("privacy.sanitize.timeSpan", 0);

/*** [SECTION 4500]: RFP (RESIST FINGERPRINTING) ***/
user_pref("_user.js.parrot", "4500 syntax error: the parrot's popped 'is clogs");
/* 4501: enable privacy.resistFingerprinting ***/
   // user_pref("privacy.resistFingerprinting", true); // [FF41+]
   // user_pref("privacy.resistFingerprinting.pbmode", true); // [FF114+]
/* 4502: set new window size rounding max values [FF55+] ***/
user_pref("privacy.window.maxInnerWidth", 1600);
user_pref("privacy.window.maxInnerHeight", 900);
/* 4503: disable mozAddonManager Web API [FF57+] ***/
user_pref("privacy.resistFingerprinting.block_mozAddonManager", true); // [HIDDEN PREF FF57-108]
/* 4504: enable RFP letterboxing [FF67+] ***/
   // user_pref("privacy.resistFingerprinting.letterboxing", true); // [HIDDEN PREF]
   // user_pref("privacy.resistFingerprinting.letterboxing.dimensions", ""); // [HIDDEN PREF]
/* 4505: experimental RFP [FF91+] ***/
   // user_pref("privacy.resistFingerprinting.exemptedDomains", "*.example.invalid");
/* 4506: disable RFP spoof english prompt [FF59+] ***/
user_pref("privacy.spoof_english", 1);
   // user_pref("layout.css.font-visibility.resistFingerprinting", 1); // [DEFAULT: 1]
/* 4510: disable using system colors ***/
user_pref("browser.display.use_system_colors", false); // [DEFAULT: false NON-WINDOWS]
/* 4511: enforce non-native widget theme & disable using system accent colors ***/
user_pref("widget.non-native-theme.enabled", true); // [DEFAULT: true]
user_pref("widget.non-native-theme.use-theme-accent", false); // [DEFAULT: false WINDOWS]
/* 4512: enforce links targeting new windows to open in a new tab instead ***/
user_pref("browser.link.open_newwindow", 3); // [DEFAULT: 3]
/* 4513: set all open window methods to abide by "browser.link.open_newwindow" (4512) ***/
user_pref("browser.link.open_newwindow.restriction", 0);
/* 4520: disable WebGL (Web Graphics Library) ***/
   // user_pref("webgl.disabled", true);

/*** [SECTION 5000]: OPTIONAL OPSEC ***/
user_pref("_user.js.parrot", "5000 syntax error: the parrot's taken 'is last bow");
/* 5001: start Firefox in PB (Private Browsing) mode ***/
   // user_pref("browser.privatebrowsing.autostart", true);
/* 5002: disable memory cache ***/
   // user_pref("browser.cache.memory.enable", false);
   // user_pref("browser.cache.memory.capacity", 0);
/* 5003: disable saving passwords ***/
   // user_pref("signon.rememberSignons", false);
/* 5004: disable permissions manager from writing to disk [FF41+] [RESTART] ***/
   // user_pref("permissions.memory_only", true); // [HIDDEN PREF]
/* 5005: disable intermediate certificate caching [FF41+] [RESTART] ***/
   // user_pref("security.nocertdb", true);
/* 5006: disable favicons in history and bookmarks ***/
   // user_pref("browser.chrome.site_icons", false);
/* 5007: exclude "Undo Closed Tabs" in Session Restore ***/
   // user_pref("browser.sessionstore.max_tabs_undo", 0);
/* 5008: disable resuming session from crash ***/
   // user_pref("browser.sessionstore.resume_from_crash", false);
/* 5009: disable "open with" in download dialog [FF50+] ***/
   // user_pref("browser.download.forbid_open_with", true);
/* 5010: disable location bar suggestion types ***/
   // user_pref("browser.urlbar.suggest.history", false);
   // user_pref("browser.urlbar.suggest.bookmark", false);
   // user_pref("browser.urlbar.suggest.openpage", false);
   // user_pref("browser.urlbar.suggest.topsites", false); // [FF78+]
/* 5011: disable location bar dropdown ***/
   // user_pref("browser.urlbar.maxRichResults", 0);
/* 5012: disable location bar autofill ***/
   // user_pref("browser.urlbar.autoFill", false);
/* 5013: disable browsing and download history ***/
   // user_pref("places.history.enabled", false);
/* 5014: disable Windows jumplist [WINDOWS] ***/
   // user_pref("browser.taskbar.lists.enabled", false);
   // user_pref("browser.taskbar.lists.frequent.enabled", false);
   // user_pref("browser.taskbar.lists.recent.enabled", false);
   // user_pref("browser.taskbar.lists.tasks.enabled", false);
/* 5015: disable Windows taskbar preview [WINDOWS] ***/
   // user_pref("browser.taskbar.previews.enable", false); // [DEFAULT: false]
/* 5016: discourage downloading to desktop ***/
   // user_pref("browser.download.folderList", 2);
/* 5017: disable Form Autofill ***/
   // user_pref("extensions.formautofill.addresses.enabled", false); // [FF55+]
   // user_pref("extensions.formautofill.creditCards.enabled", false); // [FF56+]
/* 5018: limit events that can cause a pop-up ***/
   // user_pref("dom.popup_allowed_events", "click dblclick mousedown pointerdown");
/* 5019: disable page thumbnail collection ***/
   // user_pref("browser.pagethumbnails.capturing_disabled", true); // [HIDDEN PREF]
/* 5020: disable Windows native notifications and use app notications instead [FF111+] [WINDOWS] ***/
   // user_pref("alerts.useSystemBackend.windows.notificationserver.enabled", false);
/* 5021: disable location bar using search ***/
   // user_pref("keyword.enabled", false);

/*** [SECTION 5500]: OPTIONAL HARDENING ***/
user_pref("_user.js.parrot", "5500 syntax error: this is an ex-parrot!");
/* 5501: disable MathML (Mathematical Markup Language) [FF51+] ***/
   // user_pref("mathml.disabled", true); // 1173199
/* 5502: disable in-content SVG (Scalable Vector Graphics) [FF53+] ***/
   // user_pref("svg.disabled", true); // 1216893
/* 5503: disable graphite ***/
   // user_pref("gfx.font_rendering.graphite.enabled", false);
/* 5504: disable asm.js [FF22+] ***/
   // user_pref("javascript.options.asmjs", false);
/* 5505: disable Ion and baseline JIT to harden against JS exploits ***/
   // user_pref("javascript.options.ion", false);
   // user_pref("javascript.options.baselinejit", false);
   // user_pref("javascript.options.jit_trustedprincipals", true); // [FF75+] [HIDDEN PREF]
/* 5506: disable WebAssembly [FF52+] ***/
   // user_pref("javascript.options.wasm", false);
/* 5507: disable rendering of SVG OpenType fonts ***/
   // user_pref("gfx.font_rendering.opentype_svg.enabled", false);
/* 5508: disable all DRM content (EME: Encryption Media Extension) ***/
user_pref("media.eme.enabled", false);
user_pref("browser.eme.ui.enabled", false);
/* 5509: disable IPv6 if using a VPN ***/
user_pref("network.dns.disableIPv6", true);
/* 5510: control when to send a cross-origin referer ***/
   // user_pref("network.http.referer.XOriginPolicy", 2);

/*** [SECTION 6000]: DON'T TOUCH ***/
user_pref("_user.js.parrot", "6000 syntax error: the parrot's 'istory!");
/* 6001: enforce Firefox blocklist ***/
user_pref("extensions.blocklist.enabled", true); // [DEFAULT: true]
/* 6002: enforce no referer spoofing ***/
user_pref("network.http.referer.spoofSource", false); // [DEFAULT: false]
/* 6004: enforce a security delay on some confirmation dialogs such as install, open/save ***/
user_pref("security.dialog_enable_delay", 1000); // [DEFAULT: 1000]
/* 6008: enforce no First Party Isolation [FF51+] ***/
user_pref("privacy.firstparty.isolate", false); // [DEFAULT: false]
/* 6009: enforce SmartBlock shims [FF81+] ***/
user_pref("extensions.webcompat.enable_shims", true); // [DEFAULT: true]
/* 6010: enforce no TLS 1.0/1.1 downgrades ***/
user_pref("security.tls.version.enable-deprecated", false); // [DEFAULT: false]
/* 6011: enforce disabling of Web Compatibility Reporter [FF56+] ***/
user_pref("extensions.webcompat-reporter.enabled", false); // [DEFAULT: false]
/* 6012: enforce Quarantined Domains [FF115+] ***/
user_pref("extensions.quarantinedDomains.enabled", true); // [DEFAULT: true]

/*** [SECTION 7000]: DON'T BOTHER ***/
user_pref("_user.js.parrot", "7000 syntax error: the parrot's pushing up daisies!");
/* 7020: disable WebRTC (Web Real-Time Communication) ***/
user_pref("media.peerconnection.enabled", false);

/*** [SECTION 8000]: DON'T BOTHER: FINGERPRINTING ***/
user_pref("_user.js.parrot", "8000 syntax error: the parrot's crossed the Jordan");

/*** [SECTION 9000]: NON-PROJECT RELATED ***/
user_pref("_user.js.parrot", "9000 syntax error: the parrot's cashed in 'is chips!");
/* 9001: disable welcome notices ***/
user_pref("browser.startup.homepage_override.mstone", "ignore");
/* 9002: disable General>Browsing>Recommend extensions/features as you browse [FF67+] ***/
user_pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.addons", false);
user_pref("browser.newtabpage.activity-stream.asrouter.userprefs.cfr.features", false);
/* 9003: disable What's New toolbar icon [FF69+] ***/
user_pref("browser.messaging-system.whatsNewPanel.enabled", false);
/* 9004: disable search terms [FF110+] ***/
user_pref("browser.urlbar.showSearchTerms.enabled", false);

/*** [SECTION 9999]: CUSTOM MEDIA & H.264 HARDWARE DECODING OVERRIDES ***/
user_pref("_user.js.parrot", "9999 syntax error: the parrot's shuffled off 'is mortal coil!");

// Enable hardware video decoding
user_pref("media.hardware-video-decoding.enabled", true);
user_pref("media.hardware-video-decoding.force-enabled", true);

// Force H.264 only: disable AV1, VP8, VP9, WebM, and HEVC
user_pref("media.av1.enabled", false); // Disable AV1
user_pref("media.mediasource.vp9.enabled", false); // Disable VP9
user_pref("media.mediasource.webm.enabled", false); // Disable WebM (VP8/VP9)
user_pref("media.webm.enabled", false); // Disable WebM container
user_pref("media.wmf.vp9.enabled", false); // Disable Windows Media Foundation VP9 decoder
user_pref("media.wmf.hevc.enabled", false); // Disable H.265 (Windows)

/* END: internal custom pref to test for syntax errors ***/
user_pref("_user.js.parrot", "SUCCESS: No no he's not dead, he's, he's restin'!");