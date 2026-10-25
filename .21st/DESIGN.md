# Personal translator UI

Help Bilal select devices, choose Urdu/English, start translation and read/hear the result. Preserve existing audio behavior and keyboard-accessible controls.

Use a forest sidebar, warm gray workspace, white source panel and lightly tinted translation panel. Favor readable Urdu, compact forms, restrained borders, and a persistent control bar. Place transcripts side by side on laptops and stack them on narrow screens.

Start becomes Stop during a live session or voice preview. Preserve idle, connecting, live, muted, testing, missing devices/key, API quota error and disconnect states. Avoid marketing slogans, decorative animation and unsupported success indicators.

Key management is in Settings: an empty password input, no reveal control, and automatic clearing after a save attempt or leaving the view. Only the authenticated loopback API may save it; never return or prefill the saved key. Tests use temporary `.env` files and fake values.

Long instructions live in Guide. A short main-screen note says Zoom/Meet routing is pending. The project's existing design is the reference; 21st CLI search/review were unavailable because the CLI is not installed. Validate controls and layout in a real browser.
