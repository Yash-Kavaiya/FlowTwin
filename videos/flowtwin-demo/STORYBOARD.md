---
format: 1920x1080
duration: 105s
message: "Put a real object in an aisle and FlowTwin sees it, replans the delivery, and shows the evidence for the decision."
arc: PAS with a demo loop — hook → pain → promise → product → demo (reroute, hold) → trust rules → stack → operations → use cases → evidence → pilot → limits and close
audience: Hackathon judges, technical and business reviewers
mode: autonomous
music: none
---

## Video direction

- palette system: one register per frame, from frame.md. Dark register is the default: ground `ink-black`, text `cream`, accent `fire-orange` (the brand lime). The lime register (ground `fire-orange`, text `ink-black`) is used exactly twice, for the promise landing in Frame 2 and the close in Frame 12. Lime is the only colour; the reds, ambers and greys that appear are inside the captured app screens and are never recreated as frame chrome.
- type: display and headline roles in lowercase Heebo 800 as graphic primitive; `label` (IBM Plex Mono, uppercase, tracked) for kickers, numbers and the SIMULATED / OBSERVED tags; body in Heebo 400. Never by raw family or px.
- captured screens: the app screenshots are the product truth. Show them as flat plates with a 1px `border-dark` hairline, no device bezel, no shadow, no recreated UI. A plate may be cropped or pushed in on, never redrawn. Every plate that shows a simulated figure carries a mono SIMULATED tag.
- motion grammar + reveal model: long-tail `power3` settles, no overshoot. Every frame reveals each piece on its spoken cue and holds still once resolved; nothing enters before the voiceover reaches it. During a hold at most a low-amplitude jitter on one element; no breathing, no back-half pan or push.
- rhythm / held frames: Frames 5 and 10 are the held reads (the no-route state and the two numbers stay still once landed). Frames 1, 2 and 12 are type-led and fast. Frames 3, 4 and 8 carry the camera moves. Frames 6, 7, 9 and 11 are assemblies.
- caption band: the bottom 17% is reserved for captions; all content sits in the top 83%.
- negative list: no second accent colour, no gradients or glow blooms on type, no device mockups, no stock icons standing in for the app, no invented metrics, no Jetson latency or accuracy figures. No slideshow (front-load then freeze) and no screensaver (everything drifting independently).

## Frame 1 — Stalled

- scene: Three short pain lines land one at a time on a black field, the last one in lime
- voiceover: "A pallet in the wrong aisle. A delivery, stalled. And nobody knows, until someone picks up the radio."
- duration: 6.784s
- transition_in: cut
- status: animated
- src: compositions/frames/01-stalled.html
- type: hook
- persuasion: Pain validation
- beat: tension
- blueprint: kinetic-type-beats (Adapt)
- asset_candidates:

narrativeRole: open on the operational pain in the viewer's own words, before any product appears.
keyMessage: disruptions are found late and by radio.

Adapt: keep the in-place beat relay (each statement lands alone, hard cut between beats); three beats instead of a longer chain, and the last beat resolves on the radio line rather than a logo.
Scene 1 (0.0–2.0s): bare dark field; "a pallet in the wrong aisle." lands alone, display role, lowercase, left-aligned on the upper third — kinetic beat-slam (`kinetic-beat-slam`), one line at ~60% of frame width.
Scene 2 (2.0–3.7s): hard-cut word-swap (`discrete-text-sequence`) to "a delivery, stalled." in the same position; a 36x2 lime stub rule draws under it.
Scene 3 (3.7–6.8s): hard-cut to "nobody knows" in `cream`, then as the VO says "until someone picks up the radio" the second line "until the radio call." reveals per word in `fire-orange` beneath it; a mono kicker "THE PROBLEM" sits top-left from this window. Holds still to the cut.

## Frame 2 — The promise

- scene: The three verbs see, replan, prove build across the frame and resolve onto the FlowTwin wordmark
- voiceover: "FlowTwin sees it. Replans the delivery. And shows you the evidence."
- duration: 4.501s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/02-promise.html
- type: product_intro
- persuasion: Friction reduction
- beat: relief + clarity
- blueprint: kinetic-type-beats (Reproduce)
- asset_candidates:

narrativeRole: land the value claim by the second beat; everything after is evidence for it.
keyMessage: see it, replan it, prove it.

Scene 1 (0.0–1.0s): dark field; "sees it." slams in centred, display role (`kinetic-beat-slam`).
Scene 2 (1.0–2.3s): hard-cut swap (`discrete-text-sequence`) to "replans the delivery." same centre, same scale.
Scene 3 (2.3–3.3s): hard-cut swap to "shows the evidence."; the accent word "evidence" takes `fire-orange`.
Scene 4 (3.3–4.5s): scale-swap handoff — the line shrinks away as the register flips to lime ground and the wordmark "flowtwin" arrives centred in `ink-black`, display role, with the mono line "SEE IT / REPLAN IT / PROVE IT" beneath. Holds still.

## Frame 3 — The live twin

- scene: The app's warehouse view revealed from a tight detail on the racking out to the whole facility
- voiceover: "This is a live three-D twin of the floor. Racking, docks, conveyors. And a camera watching the aisles."
- duration: 7.019s
- transition_in: blur-crossfade
- status: animated
- src: compositions/frames/03-live-twin.html
- type: product_intro
- persuasion: Show-don't-tell proof
- beat: curiosity
- blueprint: zoom-out-workspace-reveal (Adapt)
- asset_candidates: assets/01-idle.png — warehouse use case idle, full 3D facility with racking, docks, conveyor and wall sign
- focal: assets/01-idle.png
- roles: 01-idle = background plate, full-bleed inside the top 83%

narrativeRole: first look at the real product surface, shown as it is.
keyMessage: the floor exists as a twin you can look at.

Adapt: keep the one continuous decelerating zoom-out that locks; the tight open is a crop of the real screenshot (the racking) instead of a graphic macro, and no micro-action plays in the close-up.
Scene 1 (0.0–1.8s): open TIGHT on the racking rows of the captured warehouse screen, the plate scaled so the cartons fill the frame; a mono kicker "LIVE 3D TWIN" top-left. Nothing else on screen.
Scene 2 (1.8–4.5s): as the VO says "racking, docks, conveyors", ONE decelerating zoom-out (`multi-phase-camera`, pull-back only) reveals the whole facility plate; three mono callout labels reveal on their words, each with a 1px leader line to its region (`dynamic-content-sequencing` + `svg-path-draw`): RACKING, DOCKS, CONVEYOR. The camera eases to a full stop and LOCKS.
Scene 3 (4.5–7.0s): frame locked; on "a camera watching the aisles" a lime outline draws around the Aisle A zone on the plate (`svg-path-draw`) with the label "OBSERVED ZONE". Holds still.

## Frame 4 — Block and reroute

- scene: The delivery runs through Aisle A, then the aisle turns red and the lime route swings to Aisle B
- voiceover: "Start a delivery. It takes aisle A. Now put a real object in that aisle. Three consistent observations, and the aisle is blocked. The route moves to aisle B."
- duration: 11.072s
- transition_in: crossfade
- status: animated
- src: compositions/frames/04-reroute.html
- type: feature_showcase
- persuasion: Show-don't-tell proof
- beat: tension + relief
- blueprint: device-surface-showcase (Adapt)
- asset_candidates: assets/02-route.png — delivery under way on the baseline route through Aisle A, zones CLEAR; assets/03-reroute.png — Aisle A BLOCKED in red, route through Aisle B, timeline shows the reason
- focal: assets/03-reroute.png
- roles: 02-route = supporting plate (the before state) · 03-reroute = focal plate (the after state)

narrativeRole: the core product moment, shown as a before and after on the same surface.
keyMessage: a physical obstruction changes the route, and the reason is recorded.

Adapt: keep the held surface whose screens change through a real flow; a flat hairline plate instead of a device mockup, and two states instead of a longer cycle.
Scene 1 (0.0–2.5s): the before plate (delivery on the baseline route) held as hero, ~78% of frame width, left-weighted asymmetric 70/30; on "start a delivery" a mono step tag "01 START" appears in the right column.
Scene 2 (2.5–4.3s): on "it takes aisle A" zoom-to-target (`coordinate-target-zoom`) eases onto the Aisle A region of the plate; step tag "02 ROUTE: AISLE A".
Scene 3 (4.3–7.4s): on "put a real object in that aisle" the plate swaps to the after state at matched framing (velocity-matched cut-the-curve, `cut-catalog.md`); three small lime ticks fill one by one beside the tag "03 THREE OBSERVATIONS" (`stat-bars-and-fills`) as the VO counts them, then the tag "BLOCKED" lands.
Scene 4 (7.4–11.1s): on "the route moves to aisle B" the camera eases back out to the whole plate (`multi-phase-camera`) so the new route through Aisle B reads; step tag "04 ROUTE: AISLE B" in lime. Locks and holds still.

## Frame 5 — Hold, do not guess

- scene: Both aisles red, the vehicle amber at the wait point, a callout reading no feasible route
- voiceover: "Block both aisles, and it does not guess. It holds at the wait point, and says there is no feasible route."
- duration: 6.784s
- transition_in: crossfade
- status: animated
- src: compositions/frames/05-hold.html
- type: feature_showcase
- persuasion: Risk reversal
- beat: control
- blueprint: device-surface-showcase (Adapt)
- asset_candidates: assets/04-hold.png — both aisles BLOCKED, vehicle paused at Wait West, right column reads Paused: no feasible route
- focal: assets/04-hold.png
- roles: 04-hold = focal plate

narrativeRole: show the failure behaviour, which is what makes the reroute trustworthy.
keyMessage: when there is no route it stops and says so.

Adapt: keep the held hero surface; a static hold instead of cycling screens, because this is a held read.
Scene 1 (0.0–2.3s): the hold plate enters already at rest, ~70% of frame width, right-weighted; left column empty except a mono kicker "NO ROUTE". On "block both aisles" two lime outlines draw around the two red aisles (`svg-path-draw`).
Scene 2 (2.3–4.2s): on "it does not guess" the headline "it does not guess." reveals per word in the left column, h2 role (`dynamic-content-sequencing`).
Scene 3 (4.2–6.8s): on "holds at the wait point" a leader line draws from a mono callout "HOLDS AT WAIT POINT" to the amber vehicle on the plate; on "no feasible route" the quoted status line "paused: no feasible route" lands under the headline in mono. Everything then holds completely still.

## Frame 6 — Rules it will not break

- scene: Three rule cards assemble in a row, each with a mono number and one sentence
- voiceover: "Three rules it will not break. A missed detection never clears an aisle. A covered camera turns every zone unknown. And every decision keeps the frame that caused it."
- duration: 11.328s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/06-rules.html
- type: benefit_highlight
- persuasion: Rule of three
- beat: trust
- blueprint: grid-card-assemble (Adapt)
- asset_candidates:

narrativeRole: turn the demo into principles a reviewer can check.
keyMessage: conservative by rule, with evidence kept.

Adapt: keep the staggered self-assembly into a row that holds; three top-border stat-cards instead of a larger grid, each revealed on its spoken rule rather than as one cascade.
Scene 1 (0.0–2.3s): dark field; headline "three rules it will not break." enters upper-left, h2 role, per-word (`dynamic-content-sequencing`). The row below is empty.
Scene 2 (2.3–4.9s): on "a missed detection never clears an aisle" card 01 assembles into the left third (top-border-only card, mono "01", one sentence) — spring-pop entrance on a smooth settle (`spring-pop-entrance`).
Scene 3 (4.9–7.7s): on "a covered camera turns every zone unknown" card 02 assembles into the middle third; the word "unknown" set in mono.
Scene 4 (7.7–11.3s): on "every decision keeps the frame that caused it" card 03 assembles into the right third; its top border is lime, the others hairline. Triptych holds still.

## Frame 7 — The NVIDIA stack

- scene: A vertical stack of layers builds from camera to twin, with the Jetson layer in lime
- voiceover: "Perception is built for NVIDIA Jetson Thor. A detector on CUDA. A TensorRT export. And a panel that reports only what the device measured."
- duration: 10.368s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/07-stack.html
- type: feature_showcase
- persuasion: Authority by association
- beat: confidence
- blueprint: grid-card-assemble (Adapt)
- asset_candidates:

narrativeRole: answer the Jetson criterion without claiming a number that was not measured.
keyMessage: built for the Jetson, and honest about measurement.

Adapt: keep the accumulating vertical list that holds; five stack layers build bottom-up on their spoken cues, one layer accented.
Scene 1 (0.0–2.6s): dark field, asymmetric 60/40; on the right a vertical stack outline is empty; on "built for NVIDIA Jetson Thor" the layer "JETSON THOR" fills in `fire-orange` at the centre of the stack and the headline "built for jetson thor." reveals on the left, h2 role (`dynamic-content-sequencing`).
Scene 2 (2.6–4.7s): on "a detector on CUDA" the layer "DETECTOR · PYTORCH ON CUDA" assembles above it (`spring-pop-entrance`, smooth).
Scene 3 (4.7–6.8s): on "a TensorRT export" the layer "TENSORRT FP16 EXPORT" assembles; a mono tag "EXPORT PATH" beside it.
Scene 4 (6.8–10.4s): on "reports only what the device measured" the top layer "ACCELERATOR PANEL · MEASURED VALUES ONLY" assembles and the bottom layer "BROWSER CAMERA" completes the stack; a mono footnote under the headline reads "NO JETSON FIGURES ARE SHOWN IN THIS VIDEO". Holds still.

## Frame 8 — Around the loop

- scene: The fleet and stock heatmap view, then a push onto the rack inventory card
- voiceover: "Around that loop: a fleet that obeys the same zones. Live numbers, counted from the session. And stock on every rack, down to the slot."
- duration: 9.323s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/08-operations.html
- type: feature_showcase
- persuasion: Value stacking
- beat: power
- blueprint: camera-journey (Adapt)
- asset_candidates: assets/05-fleet-heatmap.png — fleet of three vehicles, stock heatmap tinting racks, KPI strip with deliveries; assets/06-inventory.png — rack R2 selected with slot-level inventory card, 328 of 480 units
- focal: assets/06-inventory.png
- roles: 05-fleet-heatmap = supporting plate (first leg) · 06-inventory = focal plate (landing)

narrativeRole: widen from one decision to the operating picture.
keyMessage: fleet, KPIs and inventory sit on the same twin.

Adapt: keep the multi-leg motivated journey (dive in, travel, landing push); the legs travel across two real plates and there is no click, the voiceover motivates each leg.
Scene 1 (0.0–2.6s): the fleet and heatmap plate held wide, ~84% of frame width; on "a fleet that obeys the same zones" zoom-to-target (`coordinate-target-zoom`) dives onto the vehicles in the aisles; mono tag "FLEET · SIMULATED".
Scene 2 (2.6–5.4s): on "live numbers, counted from the session" the camera travels up and left to the KPI strip at the top of the plate (`viewport-change`) and locks; mono tag "KPIS · FROM THE SESSION".
Scene 3 (5.4–9.3s): on "stock on every rack" the plate swaps to the inventory plate at matched framing (cut-the-curve, `cut-catalog.md`) and the camera pushes onto the rack inventory card; on "down to the slot" a lime outline draws around one table row (`svg-path-draw`); mono tag "STOCK · SIMULATED". Locks and holds still.

## Frame 9 — Three floors

- scene: Three use-case views side by side, each labelled, entering in sequence
- voiceover: "The same loop, on three floors. A warehouse aisle. A cross-dock lane. A factory corridor."
- duration: 5.995s
- transition_in: crossfade
- status: animated
- src: compositions/frames/09-three-floors.html
- type: benefit_highlight
- persuasion: Rule of three
- beat: aspiration
- blueprint: grid-card-assemble (Adapt)
- asset_candidates: assets/03-reroute.png — warehouse, Aisle A blocked, route through Aisle B; assets/07-crossdock.png — cross-dock, direct lane blocked, route through the bypass lane; assets/08-factory.png — factory, main corridor blocked, route through the north corridor
- focal: assets/03-reroute.png
- roles: 03-reroute = panel 1 · 07-crossdock = panel 2 · 08-factory = panel 3, equal weight

narrativeRole: show the product is a pattern, not a single map.
keyMessage: one loop, three operations.

Adapt: keep the staggered assembly into a held array; three image panels in a triptych, each entering on its spoken floor, each cropped to the 3D scene region of its plate.
Scene 1 (0.0–1.7s): dark field; headline "the same loop, on three floors." centred on the upper third, h3 role, per-word (`dynamic-content-sequencing`). Three empty hairline panel slots below.
Scene 2 (1.7–3.1s): on "a warehouse aisle" panel 1 fills from the warehouse plate (`spring-pop-entrance`, smooth) with the mono caption "WAREHOUSE · AISLE".
Scene 3 (3.1–4.4s): on "a cross-dock lane" panel 2 fills from the cross-dock plate, caption "CROSS-DOCK · LANE".
Scene 4 (4.4–6.0s): on "a factory corridor" panel 3 fills from the factory plate, caption "FACTORY · CORRIDOR"; a single lime rule draws under all three (`svg-path-draw`). Holds still.

## Frame 10 — The evidence

- scene: Two numbers count up side by side, 211.8 fixed and 163.8 replanning, under a simulated label
- voiceover: "Across seven fixed scenarios, replanning finished in one hundred sixty-four simulated seconds, against two hundred twelve for a fixed route. In one scenario waiting wins. So we show it."
- duration: 12.736s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/10-evidence.html
- type: social_proof
- persuasion: Statistical proof
- beat: trust
- blueprint: dataviz-countup (Adapt)
- asset_candidates: assets/09-evidence-panels.png — warehouse with the Fixed route vs replanning table open, totals 211.8 and 163.8
- focal: assets/09-evidence-panels.png
- roles: 09-evidence-panels = supporting plate, small, cropped to the comparison table, lower right at 40% opacity

narrativeRole: give the one comparison that is actually measured, with its caveat.
keyMessage: 163.8 against 211.8, simulated, including a case where waiting wins.

Adapt: keep the count-up numbers as the hero and the landing on one hero metric; two numbers side by side instead of a chart tour, and no push-through, because this is a held read.
Scene 1 (0.0–2.9s): dark field; mono kicker "SEVEN FIXED SCENARIOS · SIMULATED SECONDS" top-left. On "replanning finished in one hundred sixty-four" the right-hand number counts up to 163.8 in `fire-orange`, stat-value role scaled up (`counting-dynamic-scale`), label "REPLANNING" beneath in mono.
Scene 2 (2.9–6.9s): on "against two hundred twelve for a fixed route" the left-hand number counts up to 211.8 in `cream`, label "FIXED ROUTE"; two horizontal bars fill beneath the numbers in proportion (`stat-bars-and-fills`), the replanning bar lime and shorter.
Scene 3 (6.9–9.8s): on "in one scenario waiting wins" a third small line reveals under the bars: "3-SECOND BLOCK: FIXED ROUTE 18.25 · REPLANNING 21.25" in mono, with the cropped table plate fading up small in the lower right as its source.
Scene 4 (9.8–12.7s): on "so we show it" the line "so we show it." lands in h3 role beside the small line. Everything holds completely still.

## Frame 11 — The pilot

- scene: The buyer line, then a four-step week-by-week pilot rail fills left to right
- voiceover: "The buyer is an operations manager. The first step is a four-week advisory pilot on one aisle. Baseline. Shadow mode. Measured recommendations. Review."
- duration: 11.115s
- transition_in: push-slide LEFT
- status: animated
- src: compositions/frames/11-pilot.html
- type: benefit_highlight
- persuasion: Future pacing
- beat: confidence
- blueprint: grid-card-assemble (Adapt)
- asset_candidates:

narrativeRole: the business criterion, as a concrete next step rather than a market claim.
keyMessage: one buyer, one aisle, four weeks.

Adapt: keep the items assembling into a held row; a four-step rail filled left to right on the spoken steps, preceded by the buyer line.
Scene 1 (0.0–2.4s): dark field; mono kicker "THE BUYER"; headline "an operations manager." upper-left, h2 role, per-word (`dynamic-content-sequencing`).
Scene 2 (2.4–5.6s): on "a four-week advisory pilot on one aisle" the line "four weeks. one aisle. advisory." reveals beneath in lead role, and an empty four-segment rail draws across the middle of the frame (`svg-path-draw`).
Scene 3 (5.6–11.1s): on each spoken step one rail segment fills lime and its card assembles above it (`stat-bars-and-fills` + `spring-pop-entrance`, smooth): "WEEK 1 · BASELINE", "WEEK 2 · SHADOW MODE", "WEEK 3 · MEASURED RECOMMENDATIONS", "WEEK 4 · REVIEW". Holds still on the full rail.

## Frame 12 — Limits and close

- scene: Three plain limit lines, then the wordmark and the three verbs on a lime field
- voiceover: "One camera. Three prop classes. A simulated vehicle, and it says so on screen. FlowTwin. See it. Replan it. Prove it."
- duration: 8.213s
- transition_in: zoom-through
- status: animated
- src: compositions/frames/12-close.html
- type: cta
- persuasion: Risk reversal
- beat: inevitability
- blueprint: kinetic-type-beats (Reproduce)
- asset_candidates:

narrativeRole: state the limits before the judges ask, then close on the promise.
keyMessage: honest limits, then see it, replan it, prove it.

Scene 1 (0.0–3.4s): dark field; three limit lines land one at a time on their spoken cues, stacked left, h3 role, each prefixed by a lime mono "/": "one camera." then "three prop classes." then "a simulated vehicle, labelled on screen.". Mono kicker "LIMITS".
Scene 2 (3.4–4.8s): on "FlowTwin" a scale-swap handoff (`scale-swap-transition`) clears the list as the register flips to lime ground and the wordmark "flowtwin" arrives centred in `ink-black`, display role.
Scene 3 (4.8–8.2s): on "see it. replan it. prove it." the three verbs slam in beneath the wordmark one per beat (`kinetic-beat-slam`), mono, tracked. The final frame holds still to the end; no exit animation beyond a short fade on the last half second.
