# Disaster-Whisper: Asymmetric Emergency Communication & Alerting System

Disaster-Whisper is a publication-quality emergency communication framework designed to operate over congestion-prone or completely offline channels (e.g., SMS, Cell Broadcast, LoRa, BLE Mesh). The system optimizes and compresses complex multi-point evacuation routes and disaster metadata into compact sub-32-byte payloads, reconstructing rich, context-aware alerts on-device utilizing an Asymmetric Capability Model.

---

## 🏗️ System Architecture

The architecture is divided into two distinct operational phases:

### 1. Server-Side Pipeline (Centralized Broadcast Stations)
*   **Route Optimizer:** Takes a dense GPS track or set of street-level waypoints, validates bounds (India territory), and simplifies it using the Ramer-Douglas-Peucker (RDP) algorithm to a target (typically 5 points) evacuation corridor.
*   **Payload Encoder:** Compresses route coordinates, hazard classification, and targeted audience groups into a 4-part compact string layout:
    ```
    Payload = [Hazard_Code] [Role_Flag] [Polyline_Payload] [Checksum]
    ```
    *   **Hazard Code (1 Byte):** Maps disaster categories (`F` = Flood, `C` = Cyclone, `L` = Landslide, `W` = Wildfire, `E` = Earthquake, `T` = Tsunami, `H` = Heatwave).
    *   **Role Flag (1 Byte):** 4-bit bitmask mapped to ASCII hex representation ('0'-'F') identifying vulnerable target groups (Agricultural Workers, Elderly, Physically Challenged, Volunteer Responders).
    *   **Polyline Payload (16–29 Bytes):** Modified Google maps polyline algorithm scale-adjusted to 4-decimal precision (±11m grid resolution), delta-encoded, zigzag integer converted, and packed into Base64-URL characters.
    *   **Checksum (1 Byte):** Custom printable XOR checksum validating channel transmission integrity without network retransmission support.
*   **Payload Assembler:** Constructs the compact string and calculates the character budget to guarantee it fits within the 160-character SMS limit with fallback text.

### 2. Client-Side Pipeline (Edge Smartphones & Feature Phones)
*   **Asymmetric Tier Detector:** Identifies hardware specifications (specifically system RAM):
    *   **Tier 1 (< 4GB RAM):** Enforces Plaintext Fallback & Template-based slot filling. Completely offline and deterministic (zero-dependency).
    *   **Tier 2 (≥ 4GB RAM):** Activates on-device Small Language Model (SLM) synthesis.
*   **Pathway A Ingestion Bridge:** Ingests alerts via clipboard copy-detection bridge to circumvent restrictive OS sandboxes.
*   **Local SLM Synthesis Engine:** Runs low-temperature (near-deterministic) generation via cached lightweight models (e.g., `Qwen/Qwen1.5-1.8B-Chat` or `google/gemma-2b-it`) using structured prompts. Memory is instantly cleared (`gc` + cache flushing) after execution to ensure device stability.
*   **Output Validator:** A safety guard gating SLM output against an offline landmark registry database to reject hallucinated locations or directions before displaying them to the user. Triggers Tier 1 template fallback if validation fails.

---

## 📁 Repository Structure

```
Disaster-Whisper/
│
├── codec/                      # Compression & Decompression logic
│   ├── __init__.py
│   ├── hazard.py               # Hazard type definitions
│   ├── role.py                 # Role bitmask definitions
│   ├── polyline.py             # Delta, zigzag, & base64 coordinate compression
│   ├── checksum.py             # XOR checksum logic
│   └── payload.py              # E2E payload packer/unpacker
│
├── server/                     # Server-side components
│   ├── __init__.py
│   ├── route_optimizer.py      # Route validation & RDP simplification
│   └── alert_generator.py      # Audited payload compiler
│
├── client/                     # Client-side edge components
│   ├── __init__.py
│   ├── tier_detector.py        # RAM-based device profiling
│   ├── tier1_engine.py         # Slot-fill template alert renderer
│   ├── tier2_engine.py         # On-device SLM prompt & inference manager
│   ├── validator.py            # Local landmark validation gate
│   └── clipboard_bridge.py     # Clipboard bridge receiver (Pathway A)
│
├── data/                       # Offline JSON registries
│   ├── hazard_registry.json
│   ├── role_registry.json
│   ├── landmarks.json          # Indore locality & coordinates registry
│   ├── templates_en.json       # English alerting templates
│   └── templates_hi.json       # Hindi alerting templates
│
├── tests/                      # Unit & integration test suites
│   ├── test_codec.py
│   ├── test_server.py
│   └── test_client.py
│
├── templates/                  # Flask Web HTML Dashboard
│   └── index.html
│
├── static/                     # Assets for Leaflet & CSS/JS controllers
│   ├── css/style.css
│   └── js/app.js
│
├── app.py                      # Flask web demo app
├── demo.py                     # CLI end-to-end simulation script
├── setup_model.py              # Utility to download/cache SLMs locally
├── requirements.txt            # Package dependencies
└── LICENSE
```

---

## 🚀 Getting Started

### 1. Installation & Environment Setup
Create a Python virtual environment and install the required system libraries:
```bash
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate    # Linux/macOS

pip install -r requirements.txt
```

### 2. Run Automated Verification Tests
Disaster-Whisper features a complete test suite covering the entire pipeline. Execute using `pytest`:
```bash
python -m pytest tests/ -v
```

### 3. Run the CLI Simulation Demo
To verify the complete server-to-client pipeline from coordinate compression up to Tier 1 and Tier 2 prompt building, execute:
```bash
python demo.py
```

### 4. Setting up a Local Small Language Model (Optional - Tier 2 path)
If you wish to test real on-device AI synthesis instead of simulated mockups, download the recommended Qwen-1.8B-Chat model (~1.5GB):
```bash
python setup_model.py
```
*Note: If no local model is found, the system gracefully falls back to structured simulations with full logs.*

### 5. Launch the Interactive Dashboard Web App
Run the Flask server locally:
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 📊 Geodetic Compression Analysis

| Coordinate Precision | Spatial Grid Resolution | Polyline Length (5 points) | Available Suffix (160-Char Limit) | Spatial Error Impact |
| :--- | :--- | :--- | :--- | :--- |
| **5 Decimals** | ~1.1 meters | 29 Characters | 128 Characters | Overkill for evacuation; increases size. |
| **4 Decimals (Optimal)**| **~11.0 meters** | **24 Characters** | **133 Characters** | **Optimal balance; street-level resolution.** |
| **3 Decimals** | ~110.0 meters | 16 Characters | 141 Characters | Too inaccurate; causes street selection errors. |

---

## 🔒 Security & AI Hallucination Guardrails
To prevent LLM hallucination in stressful scenarios, Disaster-Whisper operates a strict three-tier verification process:
1.  **Template Grounding:** The prompt isolates the AI by specifying that only verified locations in the prompt's context may be generated.
2.  **Strict Low-Temperature:** Inference runs at `temp = 0.15` to ensure output stability.
3.  **Post-Inference Validation:** The validator parses the output text for any word resembling a landmark. If any locality keyword does not match Indore's offline `landmarks.json` registry, the alert is blocked from presentation and the Tier 1 template version is displayed.
