"""
client/tier2_engine.py — On-Device SLM Alert Generator
========================================================
Tier 2 processing path (Section 3.4, Point 2 and Section 3.6).

Implements the controlled AI generation approach:
    1. Build a structured, constrained prompt from decoded payload data
    2. Load a quantised Small Language Model (SLM) into memory
    3. Run inference with strict parameters (low temperature → deterministic)
    4. Pass output to validator.py before displaying
    5. Free model from RAM after generation (Section 3.4: "removes model from memory")

Supported models (in order of recommendation):
    1. Qwen/Qwen1.5-1.8B-Chat    — ~1.5 GB, best multilingual support
    2. google/gemma-2b-it         — ~2.5 GB, strong instruction following
    3. microsoft/phi-2            — ~1.7 GB, strong reasoning

To download a model before first use:
    python setup_model.py

If no model is downloaded, this engine returns a MOCK response clearly labeled
as simulated, with the exact structured prompt that would be sent to the model.
This allows a demonstration of the full prompt engineering without inference.
"""

from __future__ import annotations
import os
import gc
import json
from typing import List, Tuple

from client.tier1_engine import (
    find_nearest_landmark,
    build_route_description,
    _get_templates,
)
from codec.role import role_description

Coord = Tuple[float, float]

# ─────────────────────────────────────────────────────────────────────────────
# Model configuration
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_MODELS = [
    {
        "model_id": "Qwen/Qwen1.5-1.8B-Chat",
        "nickname": "Qwen-1.8B-Chat",
        "size_gb": 1.5,
        "recommended": True,
    },
    {
        "model_id": "google/gemma-2b-it",
        "nickname": "Gemma-2B-IT",
        "size_gb": 2.5,
        "recommended": False,
    },
    {
        "model_id": "microsoft/phi-2",
        "nickname": "Phi-2",
        "size_gb": 1.7,
        "recommended": False,
    },
]

# Path where downloaded model is cached
_MODEL_CACHE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "model", "slm_cache"
)

# Generation parameters (Section 3.6 — "controlled structure")
GENERATION_CONFIG = {
    "max_new_tokens":  300,
    "temperature":     0.15,   # near-deterministic
    "do_sample":       True,
    "top_p":           0.85,
    "repetition_penalty": 1.1,
}

# ─────────────────────────────────────────────────────────────────────────────
# Mock responses (used when real model is not downloaded)
# ─────────────────────────────────────────────────────────────────────────────

_MOCK_RESPONSES = {
    "F_en": (
        "FLOOD ALERT — Rajwada Palace Area, Indore: Residents in the Old City "
        "area must evacuate immediately. Water levels in the Khan River tributaries "
        "are rising rapidly. Proceed along the designated route: Rajwada Palace → "
        "LIG Square → Geeta Bhawan → Vijay Nagar Square → Scheme 54 Relief Centre. "
        "Scheme 54 Relief Centre has been activated with emergency supplies. "
        "Agricultural workers: secure livestock and move to higher ground. "
        "Elderly residents: contact 112 for assisted evacuation. "
        "Do NOT use flooded underpasses or low-lying roads. "
        "Stay tuned to All India Radio 101.9 FM for updates."
    ),
    "F_hi": (
        "बाढ़ चेतावनी — राजवाड़ा क्षेत्र, इंदौर: पुराने शहर के निवासी तुरंत निकलें। "
        "खान नदी की सहायक नदियों का जल स्तर तेज़ी से बढ़ रहा है। "
        "निर्धारित मार्ग: राजवाड़ा महल → एलआईजी चौक → गीता भवन → "
        "विजय नगर चौक → स्कीम 54 राहत केंद्र। "
        "स्कीम 54 राहत केंद्र में आपातकालीन आपूर्ति उपलब्ध है। "
        "किसान: पशुधन सुरक्षित करें और ऊंचे स्थान पर जाएं। "
        "वरिष्ठ नागरिक: सहायता के लिए 112 पर कॉल करें। "
        "बाढ़ के पानी और निचले रास्तों से बचें। "
        "अपडेट के लिए ऑल इंडिया रेडियो 101.9 FM सुनें।"
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Model availability check
# ─────────────────────────────────────────────────────────────────────────────

def is_model_available() -> dict:
    """
    Check whether a supported SLM is available locally for inference.

    Returns:
        dict with keys:
            available    — bool
            model_id     — model identifier if found, else None
            nickname     — friendly model name if found, else None
            transformers — bool: is transformers library importable?
            torch        — bool: is torch importable?
            reason       — human-readable explanation
    """
    # Check for transformers
    try:
        import transformers  # noqa
        has_transformers = True
    except ImportError:
        has_transformers = False

    # Check for torch
    try:
        import torch  # noqa
        has_torch = True
    except ImportError:
        has_torch = False

    if not has_transformers or not has_torch:
        missing = []
        if not has_transformers:
            missing.append("transformers")
        if not has_torch:
            missing.append("torch")
        return {
            "available":     False,
            "model_id":      None,
            "nickname":      None,
            "transformers":  has_transformers,
            "torch":         has_torch,
            "reason": f"Missing Python packages: {', '.join(missing)}. "
                      "Run: pip install transformers torch",
        }

    # Check if any model is cached
    if os.path.isdir(_MODEL_CACHE_DIR):
        for model_info in SUPPORTED_MODELS:
            model_dir = os.path.join(_MODEL_CACHE_DIR, model_info["model_id"].replace("/", "--"))
            if os.path.isdir(model_dir) and any(
                f.endswith(".safetensors") or f.endswith(".bin")
                for f in os.listdir(model_dir)
            ):
                return {
                    "available":    True,
                    "model_id":     model_info["model_id"],
                    "nickname":     model_info["nickname"],
                    "transformers": True,
                    "torch":        True,
                    "reason":       f"Model '{model_info['nickname']}' found in local cache.",
                }

    return {
        "available":    False,
        "model_id":     None,
        "nickname":     None,
        "transformers": has_transformers,
        "torch":        has_torch,
        "reason": "No model downloaded. Run: python setup_model.py",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder (Section 3.6, Point 2)
# ─────────────────────────────────────────────────────────────────────────────

def build_slm_prompt(
    hazard_code:    str,
    role_flags:     int,
    coordinates:    List[Coord],
    language:       str = "en",
) -> str:
    """
    Build the structured prompt as described in Section 3.6.

    The prompt uses fixed templates and fills verified data — the model is
    NOT allowed to invent locations or routes. Its only job is stylistic
    rendering of the pre-structured information.
    """
    templates = _get_templates(language)

    if hazard_code not in templates:
        hazard_code = "F"   # fallback

    prompt_template = templates[hazard_code].get("tier2_prompt", "")

    start_lm = find_nearest_landmark(coordinates[0],  prefer_safe_zone=False)
    end_lm   = find_nearest_landmark(coordinates[-1], prefer_safe_zone=True)

    name_key         = "name_hi" if language == "hi" else "name"
    area             = start_lm.get(name_key, start_lm["name"])
    destination      = end_lm.get(name_key, end_lm["name"])
    route_desc       = build_route_description(coordinates, language)
    target_audience  = role_description(role_flags, language)

    return prompt_template.format(
        area=area,
        destination=destination,
        route_description=route_desc,
        target_audience=target_audience,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Inference engine
# ─────────────────────────────────────────────────────────────────────────────

def _run_real_inference(prompt: str, model_id: str) -> str:
    """
    Load the SLM, run inference, then immediately unload from memory.
    Uses 4-bit quantization if bitsandbytes is available.
    """
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    use_4bit = False
    try:
        import importlib
        importlib.import_module("bitsandbytes")
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        use_4bit = True
    except ImportError:
        bnb_config = None

    model_dir = os.path.join(_MODEL_CACHE_DIR, model_id.replace("/", "--"))

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_dir,
            trust_remote_code=True,
        )

        load_kwargs = {
            "trust_remote_code": True,
            "device_map": "auto",
            "low_cpu_mem_usage": True,
        }
        if use_4bit:
            load_kwargs["quantization_config"] = bnb_config
        else:
            load_kwargs["torch_dtype"] = torch.float16 if torch.cuda.is_available() else torch.float32

        model = AutoModelForCausalLM.from_pretrained(model_dir, **load_kwargs)
        model.eval()

        # Build chat messages
        messages = [
            {"role": "system", "content": "You are a government emergency alert system. Generate accurate, concise disaster alerts using only provided information."},
            {"role": "user",   "content": prompt},
        ]

        # Use chat template if available
        try:
            input_ids = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
            ).to(model.device)
        except Exception:
            # Fallback: concatenate as plain text
            full_prompt = f"System: You are a government emergency alert system.\nUser: {prompt}\nAssistant:"
            input_ids = tokenizer.encode(full_prompt, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_new_tokens=GENERATION_CONFIG["max_new_tokens"],
                temperature=GENERATION_CONFIG["temperature"],
                do_sample=GENERATION_CONFIG["do_sample"],
                top_p=GENERATION_CONFIG["top_p"],
                repetition_penalty=GENERATION_CONFIG["repetition_penalty"],
                pad_token_id=tokenizer.eos_token_id,
            )

        # Decode only the new tokens
        new_tokens  = outputs[0][input_ids.shape[-1]:]
        result_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    finally:
        # ── Unload model from memory (Section 3.4) ───────────────────────────
        try:
            del model
            del tokenizer
        except NameError:
            pass
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    return result_text


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def render_tier2(
    hazard_code:  str,
    role_flags:   int,
    coordinates:  List[Coord],
    language:     str = "en",
    force_mock:   bool = False,
) -> dict:
    """
    Generate a Tier 2 (SLM-enhanced) emergency alert.

    If the model is not available, returns a clearly-labeled MOCK response
    along with the exact prompt that would have been sent to the model.

    Args:
        hazard_code:  Single character hazard code.
        role_flags:   4-bit audience bitmask.
        coordinates:  Decoded waypoints.
        language:     "en" or "hi".
        force_mock:   If True, skip real inference even if model is available.

    Returns:
        dict with keys:
            alert_text   — generated alert string
            prompt       — the structured prompt used
            model_used   — model nickname or "MOCK"
            is_mock      — bool: True if mock response
            language     — language used
            tier         — always 2
    """
    prompt = build_slm_prompt(hazard_code, role_flags, coordinates, language)

    model_status = is_model_available()

    if not force_mock and model_status["available"]:
        try:
            raw_text = _run_real_inference(prompt, model_status["model_id"])

            # Import validator lazily to avoid circular imports
            from client.validator import validate_alert_output
            validation = validate_alert_output(raw_text, hazard_code, coordinates, language)

            if validation["valid"]:
                return {
                    "alert_text": raw_text,
                    "prompt":     prompt,
                    "model_used": model_status["nickname"],
                    "is_mock":    False,
                    "language":   language,
                    "tier":       2,
                    "validation": validation,
                }
            else:
                # Validator rejected output — fall back to Tier 1 template
                from client.tier1_engine import render_tier1
                t1 = render_tier1(hazard_code, role_flags, coordinates, language)
                return {
                    "alert_text": t1["alert_text"],
                    "prompt":     prompt,
                    "model_used": model_status["nickname"] + " (fallback→template)",
                    "is_mock":    False,
                    "language":   language,
                    "tier":       2,
                    "validation": validation,
                    "fallback_reason": validation["issues"],
                }

        except Exception as e:
            # Real inference failed — fall back to mock
            force_mock = True
            fallback_error = str(e)
    else:
        fallback_error = None

    # ── Mock response path ────────────────────────────────────────────────────
    key = f"{hazard_code}_{language}"
    if key in _MOCK_RESPONSES:
        mock_text = _MOCK_RESPONSES[key]
    else:
        from client.tier1_engine import _get_templates, find_nearest_landmark
        
        t = _get_templates(language)
        hz_templates = t.get(hazard_code, t.get("F"))
        
        start_lm = find_nearest_landmark(coordinates[0], prefer_safe_zone=False)
        end_lm = find_nearest_landmark(coordinates[-1], prefer_safe_zone=True)
        
        # Use Devnagari script for all Devnagari languages to ensure native voice synthesis
        devnagari_langs = ["hi", "mr", "sa", "doi", "kok", "mai", "ne", "sd"]
        name_key = "name_hi" if language in devnagari_langs else "name"
        area = start_lm.get(name_key, start_lm["name"])
        destination = end_lm.get(name_key, end_lm["name"])

        
        route_nodes = []
        for coord in coordinates:
            lm = find_nearest_landmark(coord)
            label = lm.get(name_key, lm["name"])
            route_nodes.append(label)
        route_str = " → ".join(route_nodes)
        
        title_local = hz_templates.get("title", "ALERT")
        avoid_danger_local = hz_templates.get("avoid_danger", "Avoid danger zones.")
        farmers_local = hz_templates.get("farmers", "")
        seniors_local = hz_templates.get("seniors", "")
        accessible_local = hz_templates.get("accessible", "")
        volunteers_local = hz_templates.get("volunteers", "")
        call_local = hz_templates.get("call", "Call 112.")
        
        evac_instr = hz_templates.get("fallback", "").format(area=area, destination=destination)
        
        route_header_map = {
            "en": "Designated Evacuation Corridor",
            "hi": "निर्धारित निकासी मार्ग",
            "mr": "निर्धारित स्थलांतर मार्ग",
            "bn": "নির্ধারিত উচ্ছেদ রুট",
            "gu": "નિયુક્ત સ્થળાંતર માર્ગ",
            "ta": "நியமிக்கப்பட்ட வெளியேற்ற பாதை",
            "te": "నిర్దేశిత తరలింపు మార్గం",
            "ur": "مقررہ انخلا کا راستہ"
        }
        r_head = route_header_map.get(language, "Designated Evacuation Corridor")
        
        parts = [evac_instr]
        if route_str:
            parts.append(f"{r_head}: {route_str}.")
        
        if role_flags & 1:
            parts.append(farmers_local.format(destination=destination))
        if role_flags & 2:
            parts.append(seniors_local.format(destination=destination))
        if role_flags & 4:
            parts.append(accessible_local.format(destination=destination))
        if role_flags & 8:
            parts.append(volunteers_local.format(destination=destination))
            
        mock_text = " ".join(parts)



    return {
        "alert_text":       mock_text,
        "prompt":           prompt,
        "model_used":       "MOCK (Simulated Response)",
        "is_mock":          True,
        "mock_reason":      model_status["reason"] if not fallback_error else fallback_error,
        "model_status":     model_status,
        "language":         language,
        "tier":             2,
    }
