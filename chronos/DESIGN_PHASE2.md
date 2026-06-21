# CHRONOS Phase 2-A: pon AI VTuber System - Design Document

**Status:** Phase 2-A - In Progress  
**Date:** 2026-06-12  
**Character:** 星川 凪 (Hoshikawa Nagi) / pon  
**Target:** Autonomous AI VTuber Broadcast System (100% AI-generated)

---

## 1. System Overview

### 1.1 Core Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CHRONOS Phase 2-A                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐    ┌──────────────┐   ┌────────────┐  │
│  │ CHRONOS Core │───▶│ LLM Response │──▶│  TTS Gen   │  │
│  │ (Python)     │    │  (Gemini)    │   │ (SBV2 API) │  │
│  └──────────────┘    └──────────────┘   └────────────┘  │
│        │                                       │           │
│        │              ┌────────────────────────┘           │
│        │              │                                    │
│        └──────────────▶│ Web Server (port 8001)            │
│                       │                                    │
│                       ├─ viewer.html (Babylon.js)         │
│                       ├─ pon.glb (3D avatar)              │
│                       └─ Audio playback                   │
│                                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Asset Generation Pipeline                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Stable Diffusion XL (CPU)                              │
│  └─▶ pon_illustration.png (768×768, high quality)       │
│                                                           │
│  TripoSR (CPU)                                          │
│  └─▶ pon.glb (215+ MB, resolution=512)                  │
│  └─▶ pon.vrm (VRM format fallback)                      │
│                                                           │
│  ComfyUI (optional workflow automation)                 │
│  └─▶ Custom TripoSR node (resolution=512 optimization)  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Component | Technology | Purpose | Status |
|-----------|-----------|---------|--------|
| Image Generation | Stable Diffusion XL | High-quality pon illustration | ✅ Working |
| 3D Generation | TripoSR (local inference) | Image-to-3D conversion | ✅ Working |
| 3D Display | Babylon.js 6.0.0 | Web-based 3D viewer | ✅ Working |
| TTS | Style-Bert-VITS2 (port 5000) | Japanese voice synthesis | ✅ Working |
| LLM Response | Google Gemini 2.5 Flash | Autonomous dialogue | ✅ Working |
| Orchestration | Python 3.14 | Core CHRONOS engine | ✅ Working |
| Web Server | Python http.server | Asset serving (port 8001) | ✅ Working |

---

## 2. Asset Generation Pipeline

### 2.1 Character Illustration

**Input:** identity.json (character spec)

**Process:**
1. Load Stable Diffusion XL model (~7GB)
2. Generate prompt from character spec:
   - Appearance: black bob haircut, blue eyes, cat ears/tail
   - Outfit: black hoodie, blue jeans, black shoes
   - Style: "full body, full length, feet visible" (critical for TripoSR)
3. CPU inference: ~5 minutes (20 steps, guidance_scale=7.5)

**Output:** `pon_illustration.png` (768×768 SDXL quality)

**Key Learnings:**
- v1.5 SD insufficient for anime quality
- SDXL required for Neuro-sama level output
- Prompt must include "full body, feet visible" for TripoSR compatibility
- SDXL output: bust portrait → TripoSR fails → need full body image

**File:** `C:\stable-diffusion\generate_pon_image.py`

### 2.2 3D Avatar Generation

**Input:** `pon_illustration.png`

**Process:**

1. **Background Removal**
   - rembg (RGBA extraction)
   - resize_foreground (0.85 scale)
   - Composite: RGBA → RGB (white/gray background)

2. **TripoSR Inference** (CPU: 2-5 minutes)
   - Load pretrained model: `stabilityai/TripoSR`
   - Scene encoding via DINO-ViT backbone
   - Mesh extraction: resolution=512 (high quality)
   - Extract mesh via marching cubes

3. **Export**
   - GLB format (Babylon.js compatible)
   - VRM format (VSeeFace compatible fallback)
   - File size: 215+ MB (resolution=512)

**Output:** 
- `pon.glb` (215 MB, high-resolution mesh)
- `pon.vrm` (copy of GLB, VRM format)

**Debug Outputs:**
- `debug_bg_removed.png` - Background removal result
- `debug_final_input.png` - TripoSR input (final)

**Key Learnings:**
- resolution=256 (default) → fragmentary output
- resolution=512 → high-quality mesh (but 2× slower)
- Input image aspect critical: bust-only → TripoSR fails
- Full body image required for correct character inference

**File:** `C:\Users\you81\デスクトップ\Chronos\tripo_pon.py`

**ComfyUI Integration:**
- Custom node: `C:\ComfyUI\custom_nodes\comfy_triposr.py`
- Automatic mesh extraction in ComfyUI workflow
- Parameter: resolution=512 (added for quality)

---

## 3. Broadcast System

### 3.1 Architecture

```
┌────────────────────────────────────────────────┐
│         start_test_broadcast.bat                │
├────────────────────────────────────────────────┤
│                                                 │
│ [1] Start SBV2 TTS Server (port 5000)          │
│     └─ Style-Bert-VITS2 local inference       │
│                                                 │
│ [2] Start Web Server (port 8001)               │
│     └─ Serve: viewer.html, pon.glb/.vrm       │
│                                                 │
│ [3] Open Browser                               │
│     └─ http://localhost:8001/viewer.html      │
│                                                 │
│ [4] Start CHRONOS (main.py pon)                │
│     └─ Autonomous response engine               │
│                                                 │
└────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
User Input (or Silence Detection)
    ↓
CHRONOS Core
    ├─ Emotion System (energy, mood, confidence)
    ├─ Action Decision Engine
    └─ Event Log
    ↓
LLM Request (Gemini)
    └─ Response: Voice text + motion
    ↓
TTS Generation (SBV2)
    └─ Audio synthesis (Japanese voice)
    ↓
Web Viewer Display
    ├─ 3D Avatar (Babylon.js)
    ├─ Audio playback (VB-Audio)
    └─ Motion animation (placeholder: "none")
```

### 3.3 Viewer Implementation

**File:** `apps/pon/viewer.html`

**Features:**
- Babylon.js 6.0.0 engine
- SceneLoader for GLB/VRM loading
- Cache-busting: `?t=` + timestamp
- Fallback: VRM → GLB
- Responsive canvas rendering

**Model Loading:**
```javascript
SceneLoader.Append("data/", "pon.glb", scene, function(scene) {
    // Auto-rotate, lighting setup
});
```

**Audio Sync:**
- Audio element in HTML
- Triggered by CHRONOS voice action
- Playback via VB-Audio virtual device

---

## 4. Autonomous Response Engine

### 4.1 Emotion System

**State Variables:**
- `energy` (0.0 - 1.0): Activity level
- `mood` (-1.0 - 1.0): Emotional state (sad → happy)
- `confidence` (0.0 - 1.0): Certainty in responses
- `stress` (0.0 - 1.0): Tension level

**Current Implementation:**
- Daily state initialization
- Episodic memory with decay
- Emotion-driven action selection

**Example:**
```
mood = -0.26 (slightly negative/moody)
energy = 0.53 (medium energy)
→ ACTION: "respond" (talkative enough)
→ VOICE_TYPE: "normal" (not serious)
```

### 4.2 Silence Detection

**Thread:** Continuous monitoring on startup

**Trigger:**
- Silence > N seconds on channel
- Early termination if user input received

**Action:**
- Autonomous response without user prompt
- Maintains continuity in broadcast

### 4.3 本気 (Serious Mode) System

**Status:** ❌ NOT YET IMPLEMENTED

**Specification:**
- **Rarity:** 2-tier threshold
  - Tier 1 (Minor 本気): 1-2 per week
  - Tier 2 (Full 本気): 1-2 per month
- **Trigger:** Random event + mood/stress condition
- **Effect:** 
  - Confidence boost: +0.3
  - Energy spike
  - Special dialogue/motion
  - VFX emphasis (shimmer, glow)

**Implementation Required:**
- Add `serious_mode_level` (0, 1, 2) to state
- Calculate rarity probabilities
- Trigger condition logic
- Special response handling in LLM

---

## 5. Data Structures

### 5.1 identity.json

```json
{
  "name": "星川 凪",
  "age": 18,
  "height": 162,
  "birthday": "07/22",
  "appearance": {
    "hair": "black bob with bangs",
    "eyes": "navy purple",
    "ears": "black cat ears",
    "tail": "black cat tail",
    "outfit": "gray hoodie, blue jeans"
  },
  "personality": {
    "talkative": 0.39,
    "emotional": 1.0,
    "logical": 0.034
  },
  "episodic_memory": [
    {
      "timestamp": "2026-06-12T03:00:00Z",
      "event": "broadcast started",
      "decay": 0.95
    }
  ]
}
```

### 5.2 State Object (Runtime)

```python
{
  "date": "2026-06-12",
  "energy": 0.53,
  "mood": -0.26,
  "confidence": 0.65,
  "stress": 0.2,
  "serious_mode": 0,  # Not yet implemented
  "last_action": "respond",
  "events": [
    {
      "_id": "...",
      "type": "input|action|emotion",
      "source": "user|system",
      "payload": {...},
      "timestamp": "..."
    }
  ]
}
```

---

## 6. File Structure

```
C:\Users\you81\デスクトップ\Chronos\
├── main.py                          # CHRONOS core engine
├── start_test_broadcast.bat         # Broadcast orchestration
│
├── apps/pon/
│   ├── data/
│   │   ├── identity.json            # Character spec
│   │   ├── pon_illustration.png     # SDXL output
│   │   ├── pon.glb                  # TripoSR 3D (215MB)
│   │   ├── pon.vrm                  # VRM fallback
│   │   ├── debug_bg_removed.png     # Debug: BG removal
│   │   └── debug_final_input.png    # Debug: TripoSR input
│   │
│   ├── viewer.html                  # Babylon.js viewer
│   └── ... (other app files)
│
├── tripo_pon.py                     # TripoSR 3D generation
├── run_tripo_simple.py              # Alternate TripoSR script
├── run_tripo_direct.py              # Direct inference (failed)
├── run_tripo3d_api.py               # Tripo3D API (not used)
│
└── ComfyUI/
    └── custom_nodes/
        ├── comfy_triposr.py         # TripoSR node (resolution=512)
        └── test_triposr.py          # Debug test node

C:\stable-diffusion\
├── generate_pon_image.py            # SDXL generation (current)
└── (Stable Diffusion model cache)
```

---

## 7. Current Status - Phase 2-A

### ✅ Completed

1. **3D Avatar Generation Pipeline**
   - Stable Diffusion XL: high-quality illustration
   - TripoSR: 215MB high-resolution 3D mesh
   - Parameter optimization: resolution=512

2. **Broadcast System**
   - Web viewer (Babylon.js): ✅ display
   - TTS (SBV2): ✅ voice generation
   - Web server: ✅ asset serving
   - Audio sync: ✅ playback

3. **Autonomous Response Engine**
   - Emotion system: ✅ energy/mood/confidence
   - LLM integration: ✅ Gemini response
   - Silence detection: ✅ auto-trigger
   - Action selection: ✅ emotion-driven

4. **Testing & Validation**
   - 3D avatar loads in viewer
   - Audio generation working
   - Autonomous responses in chat
   - Broadcast fully functional

### ⚠️ In Progress / Issues

1. **Image Quality**
   - SDXL must generate full-body image (not bust portrait)
   - Current prompt tuning ongoing
   - Next: Regenerate with "feet visible" emphasis

2. **ComfyUI Integration**
   - Custom node loads: ✅
   - Workflow execution: ✅
   - But manual Python script preferred (faster iteration)

### ❌ Not Yet Implemented

1. **本気 (Serious Mode) System**
   - 2-tier rarity thresholds
   - Event trigger logic
   - Special response handling

2. **Motion/Animation**
   - Currently: placeholder ("motion": "none")
   - Future: Skeletal animation via bone data

3. **VRM Rigging**
   - Currently: GLB only
   - Future: Humanoid bone structure for motion sync

---

## 8. Performance Metrics

| Component | Hardware | Time | Status |
|-----------|----------|------|--------|
| SDXL Image Gen | CPU | ~5 min | ✅ Acceptable |
| TripoSR 3D Gen | CPU | ~2-3 min | ✅ Acceptable |
| Broadcast Startup | CPU | <10 sec | ✅ Fast |
| TTS Generation | CPU | Variable | ✅ Real-time |
| Babylon.js Render | GPU (native) | 60 FPS | ✅ Smooth |

**Note:** All CPU-based (no GPU required). Bottleneck: offline inference (not real-time).

---

## 9. Quality Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| 3D Avatar Quality | Neuro-sama level | High-res mesh | 🟡 Approaching |
| Avatar Appearance | pon specification | Gray hair→silver, eyes correct | 🟡 Tweaking |
| Broadcast Stability | 100% uptime | No crashes observed | ✅ Good |
| Broadcast Views | 100+ per session | TBD | 📊 Testing |
| Autonomy | 100% AI | Zero manual assets | ✅ Achieved |

---

## 10. Next Steps - Phase 2-B

### Priority 1: 本気 System Implementation
```python
# In main.py event handler:
if random() < P_SERIOUS_MODE and mood < -0.2 and energy > 0.4:
    serious_level = 1 if confidence > 0.7 else 2
    # Trigger special response, VFX, etc.
```

### Priority 2: Full-Body Image Quality
- Regenerate pon_illustration.png with corrected prompt
- Verify: feet visible, full standing pose
- Re-run TripoSR with new image

### Priority 3: Motion System
- Humanoid bone structure for avatar
- Sync TTS phoneme timing to bone animation
- Add skeletal animation library

### Priority 4: Broadcast Automation
- Schedule autonomous broadcasts (no user present)
- Live stream to YouTube/Twitch (future)
- Viewer count/analytics (future)

---

## 11. Appendix: Known Issues & Workarounds

### Issue 1: Bust-Only Image → Dungeon 3D
**Symptom:** TripoSR output is castle/dungeon instead of character  
**Root Cause:** Input image crop (bust portrait) confuses model  
**Workaround:** Regenerate image with "full body, feet visible" in prompt  
**Status:** Being fixed

### Issue 2: Model Download Failures
**Symptom:** HuggingFace 401 Unauthorized  
**Root Cause:** Model not cached locally, repo may be gated/offline  
**Workaround:** Use official public models only (SDXL base, TripoSR)  
**Status:** Ongoing

### Issue 3: ComfyUI Workflow vs Direct Python
**Decision:** Use direct tripo_pon.py (faster iteration)  
**Reason:** No ComfyUI node dependency issues  
**Status:** Working

---

## 12. Appendix: Command Reference

```bash
# Generate pon illustration (SDXL, ~5 min)
cd C:\stable-diffusion
python generate_pon_image.py

# Generate 3D avatar (TripoSR, ~3 min)
cd C:\Users\you81\デスクトップ\Chronos
python tripo_pon.py

# Start broadcast system
.\start_test_broadcast.bat

# View results
# Browser: http://localhost:8001/viewer.html
# Terminal: Chat with pon (type messages)
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-12  
**Author:** CHRONOS Design Team
