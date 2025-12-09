# Arvis Room Intelligence System — PRD

## 1. Overview

Arvis is a Raspberry Pi–powered ambient intelligence system for a single bedroom. The system integrates:

* Voice input (USB stick mic)
* Visual sensing (webcam)
* Presence sensing (PIR sensor)
* Lighting control (LED strips, WLED later)
* Corner-mounted satellite speakers for Arvis voice + FX
* Desk speakers (separate) for actual music via Spotify API

The goal is to create a seamless, magical, always-on room assistant that reacts to the user's presence, posture, sleep/wake transitions, and voice commands.

---

## 2. Core Objectives

1. Detect when the user enters or leaves the room.
2. Detect sleep vs awake vs out-of-bed states.
3. Provide ambient voice feedback through corner speakers.
4. Control room lighting (LED strips).
5. Support low-latency AI responses for voice interactions.
6. Maintain a clean, modular architecture.
7. **Build for extensibility** — the system should easily support future features (timers, briefings, soundscapes, integrations) without major refactoring.

---

## 3. System Architecture Summary

### Components

* **Raspberry Pi 5 (8GB)** – core compute
* **USB Webcam (Logitech C920)** – posture and activity detection
* **PIR Sensor (HC-SR501)** – simple presence/entry detection
* **Corner Speakers (Pyle PCB3WT)** – Arvis voice + ambient FX
* **Mini Amplifier (Pyle or Fosi)** – powers passive corner speakers
* **USB DAC** – Pi → amp audio
* **Desk Speakers** – connected to computer, not the Pi
* **WLED-compatible LED strips** – eventually

### Architecture Layers

1. **Inputs**

   * Voice (mic → STT)
   * PIR events
   * Camera events

2. **Processing**

   * Intent routing (central brain)
   * Event → Intent mapping
   * LLM via cloud or local fallback

3. **Outputs**

   * Light control
   * Corner speaker audio
   * Spotify API control
   * On-screen debugging logs

---

## 4. High-Level User Stories / Epics

### **Epic 1 — Presence & Room State**

**Goal**: Determine if the user is in the room, just entered, or left.

* As a user, when I enter my room, Arvis should detect me instantly.
* As a user, when I leave the room, Arvis should power down lights.
* As a user, I want Arvis to trigger a “Welcome Arman” scene on entry.

### **Epic 2 — Sleep & Wake Logic**

**Goal**: Smoothly automate sleep–wake cycles.

* As a user, when I lie down for >10 minutes, Arvis transitions to “sleep mode.”
* As a user, when I wake up, Arvis plays a subtle tone.
* As a user, I want alarms that stop only when I physically get out of bed.

### **Epic 3 — Voice Interaction**

**Goal**: Hands-free control, magical experience.

* As a user, I can say "Arvis…" and issue commands.
* As a user, Arvis should respond through corner speakers.
* As a user, Arvis should control lights, music, timers, scenes, etc.
* As a user, I can control smart plugs with voice commands ("turn on the lamp", "turn on the record player").

### **Epic 4 — Lighting Control**

**Goal**: Use LEDs for ambient automation + scenes.

* As a user, when I enter, lights should sweep on.
* As a user, when sleeping, lights should dim.
* As a user, I can set scenes ("focus," "night mode").

### **Epic 5 — Audio/FX System**

**Goal**: Create the magical atmosphere.

* As a user, I want ambient tones, chimes, and Arvis voice.
* As a user, I want corner-mounted speakers for immersive effects.
* As a user, I want music to stay separate (desk speakers).

### **Epic 6 — Spotify Control**

**Goal**: Arvis controls the user’s music through API.

* As a user, I want Arvis to start my playlist.
* As a user, I want Arvis to pause or skip music.
* As a user, I want focus mode to trigger a specific playlist.

---

## 5. Technical Breakdown

### 4.8 Corner Speaker Requirements

Arvis requires **small, lightweight passive satellite speakers** suitable for ceiling-corner mounting. Key constraints and requirements:

#### Required Characteristics

* **Passive speakers only** (no powered, no Bluetooth, no USB)
* **Lightweight** for safe corner mounting
* **Compact footprint** (cube or mini-satellite form factor)
* **Emphasis on mid/high clarity** (voice, chimes, ambient effects)
* **White preferred** (to blend with white walls), but black acceptable if painted
* **Compatible with a small 2-channel mini amplifier**
* **Can be wired with 18AWG speaker wire**

#### Acceptable Examples

* Pyle PCB3 series (BK version + repaint if needed)
* Herdio HIFI-100 (white)
* Small used home-theater satellites from Sony / LG / Samsung / Polk / Bose

#### Excluded Categories

* Powered computer speakers
* USB-powered speakers
* Bluetooth speakers
* Large bookshelf speakers (e.g., JBL 2500)
* Soundbars

#### Rationale

Arvis relies on these speakers for:

* AI voice output
* Welcome scenes
* Sleep/wake FX
* Ambient tones
* Light-linked FX

These effects require clarity and directional sound, not bass or volume. Smaller passive satellites provide the best cost-to-function ratio and clean mounting options.

### **5.1 PIR Logic**

* PIR triggers an entry event.
* If prior state was EMPTY → fires entry scene.
* If no PIR for X minutes → room declared EMPTY.

### **5.2 Camera Logic**

* Basic posture detection (lying/sitting/standing)
* Movement zones (bed zone vs floor zone)
* Sleep detection = lying + low motion for >10 min
* **Out-of-bed detection** = feet on floor (bed zone → floor zone transition)
  * Alarm stops ONLY when user physically leaves bed zone
  * Sitting up in bed does NOT stop alarm
  * Clear zone transition required for alarm dismissal
* **Sleep mode override**: User can say "Arvis, I'm still awake" to cancel automatic sleep mode transition
* **Time-of-day awareness**: ~8pm+ is sleep-likely window (soft context hint for detection confidence)

#### Multi-Person Handling

* **Design assumption**: System optimized for single-user operation
* **Sleep priority rule**: If anyone is detected sleeping in bed zone → room enters SLEEP mode
  * Lights dim regardless of other activity in room
  * "Respects the sleeper" — awake person can use voice commands but room stays dim
* **Quiet Hours mode**: For guests, say "Arvis, quiet mode" to disable automatic behaviors
* **Future enhancement**: Person counting and primary user tracking (not in MVP)

### **5.3 Audio Routing**

* Pi → USB DAC → Mini Amp → Corner speakers
* Desk speakers remain computer-only
* Pi never sends music; only voice + FX

### **5.4 Wake Word Detection**

Arvis uses **always-listening** wake word detection for hands-free activation from anywhere in the room.

* **Local wake word engine** runs continuously on Pi (low CPU footprint)
* Wake word: **"Arvis"**
* On detection → start recording → stream to cloud STT
* Recommended engines (architect's choice):
  * Porcupine (Picovoice) — free tier, custom wake words
  * OpenWakeWord — open source, decent accuracy
  * Vosk — heavier, but fully local STT option

**Rationale**: Always-listening requires local detection to avoid streaming audio 24/7 to the cloud. Only post-wake-word audio is sent to STT.

### **5.5 LLM + STT**

* Cloud STT (OpenAI Whisper API)
* Cloud LLM (GPT-based)
* Intent JSON returned
* Actions executed by intent handler

---

## 6. Hardware Placement

### **Camera**

* Mounted in the ceiling corner above desk/guitar wall, angled down.

### **PIR Sensor**

* Mounted chest-high on desk wall, angled into doorway + room center.

### **Corner Speakers**

* Speaker A: same corner as camera
* Speaker B: opposite diagonal corner above futon

### **Amp + Pi**

* On desk under loft

### **Cable Routing**

* Use adhesive white raceway up corners and across ceiling edges.

---

## 7. Implementation Phases

> **Priority Principle**: Voice commands are the highest priority — the core magic of Arvis. Presence detection (entry/exit) and vision (sleep/wake) are built on top as enhancements. The system should be valuable with voice alone.

### Phase 1 — Core Voice Loop ⭐ HIGHEST PRIORITY

**Goal**: Arvis responds to voice commands. This is the foundation.

* Pi + mic input with always-listening wake word detection
* Local wake word engine (Porcupine/OpenWakeWord)
* Cloud STT (Whisper API)
* LLM intent handler
* Basic corner speaker audio output (TTS responses)
* Simple LED control (manual voice commands: "lights on/off")
* Scene commands: "Arvis, focus mode" / "Arvis, night mode"

**Success**: You can talk to Arvis and it responds. Lights obey voice commands.

### Phase 2 — Presence System (Entry/Exit)

**Goal**: Room knows when you arrive and leave.

* Add PIR sensor
* Implement entry detection → Welcome scene (golden shimmer + "Welcome back, Arman")
* Implement exit detection → Exit scene (fade out + "Goodbye")
* Room state management (OCCUPIED/EMPTY)

**Success**: Walk in, lights sweep on. Leave, lights fade off.

### Phase 3 — Vision System (Sleep/Wake)

**Goal**: Room knows when you're sleeping and wakes you up.

* Integrate C920 webcam
* Add sleep detection (lying + low motion >10 min → sleep mode)
* Add out-of-bed detection (feet on floor = alarm off)
* Alarm sequence: "Arman, wake up now" (repeated until feet on floor)
* Voice override: "Arvis, I'm still awake"

**Success**: Fall asleep, lights dim automatically. Alarm won't stop until you're up.

### Phase 4 — Scenes & Polish

**Goal**: Refine the experience, expand capabilities.

**Core polish:**
* Expand LED animation library
* Refine voice response timing and personality
* Edge case handling

**Feature additions:**
* Time-aware greetings ("Good morning/evening, Arman")
* Contextual wake-up ("It's 7 AM. It's Tuesday.")
* Date awareness ("Happy Friday, Arman." / "Happy birthday.")
* Quick status ("Arvis, status" → "Lights on. Night mode. 11:43 PM.")
* Timer support ("Arvis, set a timer for 10 minutes")
* Smart plug control ("Arvis, turn on the lamp" / "turn on the record player" / "turn off the lamp")
* Quiet hours mode (no voice responses, lights only — for guests)
* Gradual wake light (LED sunrise 10–15 min before alarm)

**Stretch goals (if time permits):**
* Morning briefing (weather, calendar on wake)
* Focus timer with Pomodoro-style breaks
* Sleep quality log (motion tracking → restful/restless)
* Ambient soundscapes ("Arvis, play rain sounds" — local audio)

### Phase 5 — Spotify Control (Future/Optional)

**Goal**: Music integration via API.

* Add Spotify Web API integration
* Trigger playlists from scenes
* Voice commands for play/pause/skip

**Note**: Deprioritized. Core value is voice + presence + vision. Spotify is a nice-to-have.

---

## 8. Arvis Persona & Voice

### Personality Profile

Arvis speaks with a **minimal, efficient, calm** voice — inspired by the Lex Fridman interview style.

| Attribute | Value |
|-----------|-------|
| **Tone** | Calm, measured, no fluff |
| **Sentence length** | Short, direct statements |
| **Warmth** | Present but restrained |
| **Filler words** | None — no "certainly," "of course," "I'd be happy to" |

### Voice Examples

**Do:**
* "Welcome back, Arman."
* "Lights on."
* "Sleep mode disabled."
* "Alarm set for 7 AM."
* "Understood."

**Don't:**
* "Hey there! I've gone ahead and turned the lights on for you!"
* "Certainly, sir. Right away."
* "I'd be happy to help you with that!"
* "Sure thing! Let me get that started."

### TTS Requirements

* Natural-sounding male voice (not robotic)
* Slight pauses between sentences
* Consistent pacing — never rushed
* Cloud TTS recommended (ElevenLabs, OpenAI TTS, or similar)

### Error & Fallback Responses

Arvis should handle errors gracefully with minimal, calm responses:

| Situation | Response |
|-----------|----------|
| Didn't understand | "I didn't catch that." |
| Network unavailable | "I'm offline." |
| Command not supported | "I can't do that." |
| Action failed | "Something went wrong." |
| Retrying | (Silent retry, no announcement unless repeated failure) |

**Behavior notes:**
* Never apologize excessively ("I'm so sorry, I couldn't...")
* Never explain technical details to user
* Retry silently once before announcing failure
* If offline for extended period, announce once: "I'm back online."

---

## 9. Scene Definitions

### Welcome Scene (Entry)

Triggered when: PIR detects motion AND prior room state was EMPTY.

| Element | Specification |
|---------|---------------|
| **Lights** | "Golden Shimmer" animation — honey-gold sweep across LED strip |
| **Animation** | Wave/chase pattern with brightness variation, like light reflecting off a gold chain |
| **Colors** | Primary `#FFD700` (gold), accents `#FFC107` (amber), `#FFECB3` (soft cream) |
| **Duration** | 2–3 seconds animation, then settle to warm ambient |
| **End state** | Honey-gold, ~70% brightness |
| **Voice** | "Welcome back, Arman." |
| **Sound FX** | None |

### Sleep Scene

Triggered when: Vision detects lying + low motion for >10 minutes.

| Element | Specification |
|---------|---------------|
| **Lights** | Fade to off over 30 seconds |
| **Voice** | None (silent transition) |
| **Room state** | Set to SLEEP |

### Wake Scene

Triggered when: Alarm fires OR user exits bed zone after SLEEP state.

| Element | Specification |
|---------|---------------|
| **Lights** | Gentle warm fade-in (sunrise colors) |
| **Voice** | Optional soft tone or "Good morning, Arman." |

### Focus Scene

Triggered when: Voice command "Arvis, focus mode."

| Element | Specification |
|---------|---------------|
| **Lights** | Cool white, 100% brightness |
| **Voice** | "Focus mode." |

### Night Mode Scene

Triggered when: Voice command "Arvis, night mode."

| Element | Specification |
|---------|---------------|
| **Lights** | Warm amber, ~30% brightness (low, easy on eyes) |
| **Voice** | "Night mode." |
| **Purpose** | Winding down, phone browsing, pre-sleep relaxation |

### Exit Scene

Triggered when: PIR timeout (no motion for X minutes) AND room state was OCCUPIED.

| Element | Specification |
|---------|---------------|
| **Lights** | Fade out over 3–5 seconds |
| **Voice** | "Goodbye." |
| **Room state** | Set to EMPTY |

### Alarm Sequence

Triggered when: Scheduled alarm time reached.

| Element | Specification |
|---------|---------------|
| **Voice** | "Arman, wake up now." — repeated every 10–15 seconds |
| **Lights** | Gentle sunrise fade-in (warm → bright) |
| **Stop condition** | Feet on floor detected (bed zone → floor zone) |
| **Escalation** | Optional: increase volume slightly each cycle |
| **Final** | Once stopped: "Good morning, Arman." |

---

## 10. Risks & Considerations

* Camera false positives in low light
* PIR blind spots
* Latency of cloud LLM for voice commands
* Wiring aesthetics
* Speaker mounting stability
* Wake word false positives (TV, conversations)
* Sleep detection false positives (lying down to read/relax)

---

## 11. Success Criteria

* Wake word "Arvis" activates consistently from anywhere in the room
* System reliably detects entry/exit via PIR
* Arvis voice responses play cleanly through corner speakers
* Sleep/wake transitions correctly detected via vision
* "Feet on floor" alarm dismissal works reliably
* Lights follow scene logic without manual input
* Voice commands consistently work with <2.5s round-trip
* Golden shimmer welcome animation feels magical
* Voice override ("Arvis, I'm still awake") cancels sleep mode

---

## 12. Future Enhancements

### Planned for Phase 4+

* Morning briefing (weather, calendar integration)
* Focus timer with Pomodoro breaks
* Sleep quality logging
* Ambient soundscapes (rain, white noise — local audio)

### Long-term Possibilities

* mmWave sensor for micro-presence detection
* Multi-room extensions
* Local LLM fallback (llama.cpp)
* Spotify API integration
* Smart desk height control (standing desk automation)
* Calendar/weather API integrations
* RFID or NFC triggers

---

## 13. Hardware Bill of Materials (BOM)

### Required Core Hardware

* **Compute**

  * Raspberry Pi 5 (8GB RAM)
  * USB-C power supply with sufficient amperage
* **Audio Input**

  * USB stick microphone (plugged into Pi or macOS during dev)
* **Audio Output**

  * 2× Passive corner speakers (small satellite/cube form factor)
  * 1× Mini 2-channel amplifier (e.g., Pyle or Fosi)
  * 1× USB DAC (e.g., UGREEN/Syba-style USB sound card)
  * 18AWG speaker wire (approx. 50 ft)
* **Vision**

  * Logitech C920 (or comparable USB webcam)
* **Presence Sensors**

  * 1× PIR sensor module (e.g., HC-SR501)
  * Optional future: 1× mmWave human presence sensor
* **Lighting**

  * **WS2812B LED Strip** — [LOAMLIN WS2812B 16.4ft/5m 300LED 60LED/m IP30](https://www.amazon.com/dp/B09573HX4X) (~$14)
    * Individually addressable, 5V DC, white PCB
    * 60 LEDs/m density for smooth animations
  * **5V 10A Power Supply** — Required for LED strip (not included with strip)
    * Search: "5V 10A switching power supply" (~$12-15)
  * Optional: WLED-compatible controller for LEDs (future enhancement)
* **Smart Plugs**

  * **TP-Link Kasa Smart Plug KP125M** — Matter Compatible, Energy Monitoring (2-pack ~$23)
    * Local network control via python-kasa library
    * Energy monitoring for power usage tracking
    * Matter compatible for future ecosystem integration
    * **Primary use cases:**
      * Lamp/light control (turn on/off room lighting)
      * Record player control (turn on/off turntable)
    * Can also control fans, heaters, or other appliances
* **Mounting & Cable Management**

  * Wall/ceiling speaker brackets
  * USB webcam mount or bracket
  * PIR sensor bracket or adhesive mount
  * Adhesive white cable raceways for walls/ceiling edges

### Nice-to-Have / Expansion

* Secondary microcontroller(s) for local LED/WLED control
* NFC/RFID reader
* Additional cameras (multi-view)
* Hardware buttons/knobs for local override (manual light/music control)

---

## 14. Software Architecture & Modules

### Language & Runtime

* **Primary language**: Python
* **Runtime targets**:

  * macOS (development and early prototyping)
  * Raspberry Pi OS on Pi 5 (deployment)

### High-Level Processes

1. **Wake Word Detector**

   * Always-listening local engine (Porcupine/OpenWakeWord)
   * Detects "Arvis" wake word
   * Triggers Voice Agent to start recording

2. **Voice Agent**

   * Handles mic capture → STT → LLM → intent
   * Runs as a loop or background task
   * Streams post-wake-word audio to cloud STT

3. **Presence Agent**

   * Listens to PIR events via GPIO
   * Maintains room state (OCCUPIED/EMPTY)

4. **Vision Agent**

   * Captures frames from C920
   * Estimates posture (lying/sitting/standing) and zone (bed/floor)
   * Emits events (e.g., SLEEPING, BED_EXIT)
   * Detects "feet on floor" for alarm dismissal

5. **Intent Router**

   * Central module that consumes intents from voice/presence/vision
   * Resolves conflicts and prioritizes actions
   * **Voice commands override automatic state transitions**

6. **Action Executor**

   * Implements side effects: lights, audio FX, TTS responses
   * LED animations (golden shimmer, fades, etc.)

### Suggested Module Layout

* `arvis.py` — main orchestrator / entrypoint
* `wake_word.py` — local wake word detection (Porcupine/OpenWakeWord)
* `audio_io.py` — record/playback utilities
* `stt_backend.py` — cloud STT integration (Whisper API)
* `tts_backend.py` — cloud TTS integration (voice responses)
* `llm_backend.py` — cloud LLM integration (intent extraction)
* `intent_router.py` — merges events → intents → actions (with priority rules)
* `actions.py` — concrete actions (lights, TTS, alarms)
* `led_controller.py` — LED animations (golden shimmer, fades, scenes)
* `smart_plug_controller.py` — Kasa smart plug control via python-kasa
* `presence_agent.py` — PIR handling + room state
* `vision_agent.py` — camera frame processing + posture/zone detection
* `config.py` — paths, thresholds, API keys, room layout zones

---

## 15. Events & Intents Schema

### Event Types (produced by sensors/agents)

* `presence.motion_detected` — PIR fired
* `presence.room_empty_timeout` — no PIR motion for X minutes
* `vision.posture_update` — payload: {posture: lying|sitting|standing, zone: bed|floor|desk}
* `vision.sleep_state` — payload: {state: sleeping|awake}
* `vision.bed_exit` — user transitioned from bed zone to floor zone (feet on floor)
* `voice.wake_word` — "Arvis" detected, begin recording
* `voice.command` — payload: {text: "..."}
* `scheduler.alarm_trigger` — alarm time reached

### Intent Types (consumed by actions)

* `lights.set_state` — {state: on|off}
* `lights.set_scene` — {scene: focus|night|sleep|wake|entry|exit}
* `lights.animate` — {animation: "golden_shimmer", duration: 2.5}
* `device.on` — {device: "record_player" | "lamp" | "fan" | ...}
* `device.off` — {device: "record_player" | "lamp" | "fan" | ...}
* `device.status` — {device: "record_player" | ...}
* `audio.say` — {text: "Welcome back, Arman", voice_id: optional}
* `alarm.start` — {profile: "morning_default"}
* `alarm.stop` — {}
* `room.set_state` — {state: OCCUPIED|EMPTY|SLEEP|WAKE}
* `room.cancel_sleep_transition` — user said "Arvis, I'm still awake"

### Intent Priority Rules

**Voice commands ALWAYS override automatic state transitions:**

1. If room is in SLEEP mode and user issues a voice command → execute command, do NOT ignore
2. If sleep transition is pending and user says "Arvis, I'm still awake" → cancel transition, stay OCCUPIED
3. Voice intents take precedence over vision-derived intents
4. Alarm dismissal requires physical action (bed exit), NOT voice command

**Scene conflict resolution:**

* Entry at any hour → always play welcome scene (even at 1am)
* User sets scene manually → override any automatic scene

### Design Notes

* Keep intents **small, JSON-serializable**, and **backend-agnostic** (no direct API calls inside intents).
* The `intent_router` decides when to emit which intent based on current state and new events.
* Voice override phrases are flexible — LLM interprets intent, not exact phrase match.

### Extensibility Principle

**The system must be architected to easily add new capabilities without major refactoring.**

Future features to anticipate:
* New intent types (timers, briefings, soundscapes)
* New event sources (calendar API, weather API)
* New output types (local audio playback beyond TTS)
* New scenes and LED animations
* New voice commands and conversational patterns

**Architectural implications:**
* Intent system should be plugin-friendly (easy to add new intent handlers)
* Action executor should support modular action types
* Config should allow easy addition of new scenes
* LLM prompt should be structured to recognize new command categories
* Audio system should support both TTS and local file playback

---

## 16. Non-Functional Requirements

### Latency

* Voice round-trip (speak → response): target < 2.5 seconds under typical network conditions.
* PIR entry response (motion → lights on): target < 500 ms.
* Vision-driven alarms (out-of-bed detection): target < 1 second.

### Availability & Reliability

* System should recover gracefully from:

  * network loss (cloud LLM/STT unavailable)
  * camera disconnect
  * PIR sensor glitches
* On startup, Arvis should default to a safe state (lights controllable, no stuck alarms).

### Privacy

* No camera frames stored by default; only derived state (posture/zone).
* No raw microphone audio stored; only transcripts (optional) for debugging.
* Clear config flags for enabling/disabling logging of events/intents.

### Safety

* LED power and wiring sized correctly for current draw.
* Speaker mounts rated for weight with margin.
* All raceways and cables routed to avoid tripping and heat sources.

---

## 17. Developer Setup & Workflow

### Environments

* **Stage 1**: macOS-only dev

  * Run `arvis.py` with local mic, no LEDs, no PIR, no camera.
  * Use print/logs instead of real actions.
* **Stage 2**: Pi hardware integration

  * Move code to Pi.
  * Wire PIR, speakers, test LEDs.

### Core Dev Tasks

* Implement `audio_io.py`, `stt_backend.py`, `llm_backend.py` first (voice prototype).
* Implement `actions.py` with stubbed behavior then real hardware integrations.
* Add `presence_agent.py` for PIR-based entry/exit.
* Add `vision_agent.py` once C920 is mounted and running.

### Testing Strategy

* Unit test intent routing with simulated events.
* Integration test PIR → entry scene, vision → alarm stop, voice → lights.
* Use a debug CLI mode to inject fake events and verify resulting intents/actions.

---

## 18. Open Questions / TBD

### Resolved

* ✅ Wake word strategy → always-listening with local detection (architect chooses engine)
* ✅ Alarm dismissal trigger → feet on floor (bed zone → floor zone)
* ✅ Sleep mode override → voice command "Arvis, I'm still awake"
* ✅ Arvis personality → minimal, efficient, Lex Fridman style
* ✅ Welcome scene → golden shimmer LED animation + "Welcome back, Arman"
* ✅ Spotify priority → deprioritized to Phase 5

### Still Open

* Final choice of corner speakers (model may vary but must satisfy requirements)
* Exact LED controller path (direct GPIO, WLED over Wi-Fi, or both)
* Choice of TTS engine (ElevenLabs, OpenAI TTS, or other)
* Long-term LLM strategy (cloud-only vs hybrid with local models)
* Whether to add a small wall panel or physical button for manual overrides

### Future Considerations

* mmWave sensor for micro-presence detection
* Multi-room extensions
* Local LLM fallback (llama.cpp)
* RFID or NFC triggers
* Gesture detection via camera
* Dynamic spatialized audio (multi-speaker)
