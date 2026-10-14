---
workflow: product-launch-video
flow: automation
storyboard: no
message: "Put a real object in an aisle and FlowTwin sees it, replans the delivery, and shows the evidence for the decision."
destination: youtube
aspect: 1920x1080
language: en
audience: "Hackathon judges: technical and business reviewers"
length: 120s
angle: judge-pitch
narration: yes
---

## Intent

A two-minute demo video for the Physical AI hackathon jury. It follows the seven-slide pitch: the operational
problem and buyer, the product loop (see, map, decide, verify), what runs on the NVIDIA stack, the decisions
that make it trustworthy, the evidence, the business case and pilot, and the limits. It is a show-it demo:
the app's own captured screens are the featured assets, not an invented interface.

User's words: "create full video demo". Chosen in the intent form: angle "Judge pitch", length "About 2 minutes",
storyboard "No, build it", flow "Automation".

## Assets

- capture/app/*.png — screenshots of the running FlowTwin app at http://localhost:8000 (warehouse, cross-dock
  and factory floors; reroute; no-route hold; fleet; stock heatmap; rack inventory; accelerator panel).

## Customizations

- Feature the app's own captured screens as the video's assets (show-it-as-is intent).
- Brand: lime #BFD732 on black, white type, matching the app. No Globant logo or licensed typeface.

## Notes

- Honesty constraint, from the project plan: never present a number that was not measured. Jetson benchmark,
  TensorRT comparison and physical trials are PENDING, so the video must not state Jetson latency, FPS or
  accuracy figures. Allowed figures: the simulated fixed-route vs replanning totals (211.8 s vs 163.8 s over
  seven scenarios, warehouse) and the illustrative ROI table, both labelled as simulated or assumed.
- The vehicle is simulated; perception is real. Say so on screen.
- Destination, aspect and language come from saved defaults (YouTube, 1920x1080, English), not from a
  question this run.
- Audio decision (autonomous run): the configured ElevenLabs key lacks text-to-speech permission (HTTP 401
  missing_permissions) and library music needs a HeyGen sign-in, so narration uses the local Kokoro voice
  am_michael and the video has no music bed (`music: none`). Re-run Step 3.1 after signing in to change either.
