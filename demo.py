"""
Disaster-Whisper: CLI End-to-End Pipeline Demo
=============================================
This script demonstrates the complete server-to-client pipeline of the
Disaster-Whisper emergency communication system.

It runs:
  1. Server-side alert generation and route optimization.
  2. Compact 4-part payload compression and SMS budgeting.
  3. Client-side reception and clipboard extraction (Pathway A).
  4. Client-side RAM-based tier detection.
  5. On-device alert synthesis via template slot-filling (Tier 1)
     and structured prompt construction for SLM (Tier 2).
  6. On-device validation of the synthesized alert.
"""

import sys
import os
import json
import time

# Reconfigure stdout/stderr to use UTF-8 to prevent UnicodeEncodeError in Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure project modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codec.payload import encode_payload, decode_payload, payload_breakdown
from codec.role import build_role_flags, role_description
from server.alert_generator import generate_alert_with_audit
from client.tier_detector import get_system_info, TIER_2
from client.tier1_engine import render_tier1, build_route_description
from client.tier2_engine import render_tier2, is_model_available, build_slm_prompt
from client.validator import validate_alert_output
from client.clipboard_bridge import parse_sms_text

# ANSI color codes for premium terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BG_BLUE = "\033[44m"
BG_RED = "\033[41m"

def print_header(title):
    print("\n" + "=" * 80)
    print(f"{BOLD}{CYAN}{title.center(80)}{RESET}")
    print("=" * 80)

def main():
    print(f"\n{BOLD}{GREEN}=== DISASTER-WHISPER EMERGENCY PIPELINE DEMO ==={RESET}")
    print("This simulation runs the complete asymmetric, offline-capable alerting framework.\n")

    # -------------------------------------------------------------------------
    # 1. SETUP SAMPLE DATA
    # -------------------------------------------------------------------------
    print(f"{BOLD}{WHITE}[Step 1] Initializing Input Parameters (Indore City Scenario){RESET}")
    hazard_type = "Flood"
    # Target audience: Agricultural workers (0x1) + Elderly (0x2) = 0x3
    role_flags = build_role_flags(agricultural=True, elderly=True)
    
    # 5-point evacuation route in Indore (referenced in Section 3.3)
    raw_coordinates = [
        (22.7181, 75.8574),   # Rajwada Palace
        (22.7325, 75.8763),   # LIG Square
        (22.7410, 75.9006),   # Geeta Bhawan
        (22.7527, 75.8944),   # Vijay Nagar Square
        (22.7284, 75.9112),   # Scheme 54 (Safe Zone/Relief Center)
    ]
    
    print(f"  - Hazard Type:     {BOLD}{RED}{hazard_type}{RESET} (F)")
    print(f"  - Role Flags:      {BOLD}{YELLOW}0x{role_flags:X}{RESET} ({role_description(role_flags)})")
    print(f"  - Route Waypoints: {len(raw_coordinates)} coordinates starting at Rajwada Palace")
    for idx, (lat, lng) in enumerate(raw_coordinates):
        print(f"      Pt {idx+1}: Lat {lat}, Lng {lng}")
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # 2. SERVER-SIDE COMPRESSION & ENCODING
    # -------------------------------------------------------------------------
    print_header("SERVER-SIDE PROCESS (ALERT ENCODING)")
    print(f"{BOLD}{WHITE}Optimizing route and encoding payload...{RESET}")
    
    # Add suffix text to simulate actual Cell Broadcast alert structure
    suffix_text = " Move to Scheme 54. Call 112."
    
    audit = generate_alert_with_audit(
        hazard=hazard_type,
        role_flags=role_flags,
        coordinates=raw_coordinates,
        precision=4,
        plain_text_suffix=suffix_text,
        auto_optimize=True
    )
    
    payload = audit["payload"]
    full_sms = audit["full_sms"]
    
    print(f"\n{BOLD}Payload Breakdown:{RESET}")
    print(f"  [H] Hazard Code:     '{audit['breakdown']['hazard_code']['char']}' (1 Byte) - {audit['breakdown']['hazard_code']['description']}")
    print(f"  [R] Role Flag:       '{audit['breakdown']['role_flag']['char']}' (1 Byte) - {audit['breakdown']['role_flag']['description']} ({audit['breakdown']['role_flag']['hex_value']})")
    print(f"  [P] Polyline String: '{audit['breakdown']['polyline']['str']}' ({audit['breakdown']['polyline']['bytes']} Bytes) - 4-decimal precision")
    print(f"  [C] Checksum:        '{audit['breakdown']['checksum']['char']}' (1 Byte) - XOR logic")
    
    print(f"\n{BOLD}Final Compact Payload:{RESET} {BG_BLUE}{WHITE} {payload} {RESET}")
    print(f"Payload Size: {BOLD}{GREEN}{len(payload)} characters / bytes{RESET}")
    
    print(f"\n{BOLD}Transmitted Message (Payload + Plaintext Fallback):{RESET}")
    print(f"  {CYAN}{full_sms}{RESET}")
    
    budget = audit["sms_budget"]
    print(f"\n{BOLD}SMS Budget Analysis (160-Character Limit):{RESET}")
    print(f"  - Payload Characters:   {budget['payload_chars']}")
    print(f"  - Plaintext Fallback:   {budget['suffix_chars']}")
    print(f"  - Total Transmitted:    {budget['total_chars']} / 160 characters")
    if budget["fits"]:
        print(f"  - Status:               {BOLD}{GREEN}FITS WITHIN ONE SMS BUDGET (Remaining: {budget['remaining']} chars){RESET}")
    else:
        print(f"  - Status:               {BOLD}{RED}EXCEEDS BUDGET!{RESET}")
    
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # 3. CLIENT-SIDE RECEPTION (INGESTION BRIDGE)
    # -------------------------------------------------------------------------
    print_header("CLIENT-SIDE PROCESS (INGESTION & DECODING)")
    print(f"{BOLD}{WHITE}Pathway A Ingestion Bridge: Simulating User Clipboard Capture...{RESET}")
    
    # We feed the full message into the parser
    extraction = parse_sms_text(full_sms)
    print(f"  - Ingested Text:       '{CYAN}{extraction['raw_text']}{RESET}'")
    print(f"  - Extracted Payload:   '{BOLD}{YELLOW}{extraction['payload']}{RESET}'")
    print(f"  - Extracted Plaintext: '{extraction['suffix']}'")
    
    print(f"\n{BOLD}{WHITE}Parsing Payload...{RESET}")
    decoded = decode_payload(extraction["payload"], precision=4)
    print(f"  - Checksum Integrity:  {'[SUCCESS] ' + GREEN if decoded['checksum_ok'] else '[CORRUPTED] ' + RED}{decoded['checksum_ok']}{RESET}")
    print(f"  - Hazard Type:         {decoded['hazard']['icon']} {decoded['hazard']['name']} (Severity: {decoded['hazard']['severity']})")
    print(f"  - Evacuation Target:   {role_description(decoded['role']['value'])}")
    
    recon_coords = decoded["coordinates"]
    print(f"  - Reconstructed Evacuation Route (Indore):")
    for idx, (lat, lng) in enumerate(recon_coords):
        print(f"      Way Point {idx+1}: Lat {lat}, Lng {lng}")
    
    route_desc_en = build_route_description(recon_coords, language="en")
    print(f"  - Reconstructed Landmarks: {BOLD}{MAGENTA}{route_desc_en}{RESET}")
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # 4. CLIENT-SIDE HARDWARE TIER DETECTION
    # -------------------------------------------------------------------------
    print_header("ASYMMETRIC HARDWARE TIER DETECTION")
    print(f"{BOLD}{WHITE}Detecting Device Specs...{RESET}")
    sys_info = get_system_info()
    print(f"  - Operating System:    {sys_info['os']}")
    print(f"  - Logical CPU Cores:   {sys_info['cpu_cores']}")
    print(f"  - Detected System RAM: {BOLD}{sys_info['ram_gb']:.2f} GB{RESET}")
    print(f"  - RAM Tier Threshold:  {sys_info['ram_threshold_gb']} GB")
    print(f"  - Target Category:     {BOLD}{YELLOW}{sys_info['tier_label']}{RESET}")
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # 5. ASYMMETRIC LOGIC EXECUTION
    # -------------------------------------------------------------------------
    print_header("ALERT SYNTHESIS VIA ASYMMETRIC PATHWAYS")
    
    # Pathway 1: Tier 1 Logic (Standard / Low-Memory Path)
    print(f"{BOLD}{UNDERLINE}Pathway I: Tier 1 - Lightweight Template Slot-Filling{RESET}")
    print(f"Rendering template alerts in English and Hindi (Zero-dependency, offline)...")
    
    t1_en = render_tier1(decoded["hazard"]["code"], decoded["role"]["value"], recon_coords, language="en")
    t1_hi = render_tier1(decoded["hazard"]["code"], decoded["role"]["value"], recon_coords, language="hi")
    
    print(f"\n  {BOLD}[English Output]{RESET}")
    print(f"  {GREEN}{t1_en['alert_text']}{RESET}")
    print(f"\n  {BOLD}[Hindi Output]{RESET}")
    print(f"  {GREEN}{t1_hi['alert_text']}{RESET}")
    print("-" * 80)
    time.sleep(1.0)

    # Pathway 2: Tier 2 Logic (Advanced / SLM Path)
    print(f"{BOLD}{UNDERLINE}Pathway II: Tier 2 - On-Device Small Language Model (SLM) Synthesis{RESET}")
    model_status = is_model_available()
    print(f"  - SLM Support: {model_status['reason']}")
    
    print(f"\n{BOLD}Step 2.1: Constructing Structured Instructions for SLM:{RESET}")
    slm_prompt = build_slm_prompt(decoded["hazard"]["code"], decoded["role"]["value"], recon_coords, language="en")
    print("=" * 80)
    print(f"{YELLOW}{slm_prompt}{RESET}")
    print("=" * 80)
    
    print(f"\n{BOLD}Step 2.2: Running On-Device Synthesis (Unloading after generation)...{RESET}")
    # Force mock for demo unless the user explicitly ran setup_model.py
    is_mock = not model_status["available"]
    
    t2_result = render_tier2(
        decoded["hazard"]["code"],
        decoded["role"]["value"],
        recon_coords,
        language="en",
        force_mock=is_mock
    )
    
    print(f"\n  {BOLD}[SLM Synthesized Output ({t2_result['model_used']})]{RESET}")
    print(f"  {CYAN}{t2_result['alert_text']}{RESET}")
    print("-" * 80)
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # 6. POST-SYNTHESIS VALIDATION
    # -------------------------------------------------------------------------
    print_header("CLIENT-SIDE INTEGRITY VALIDATION")
    print(f"{BOLD}{WHITE}Validating SLM output against offline database landmarks...{RESET}")
    
    val_result = validate_alert_output(
        t2_result["alert_text"],
        decoded["hazard"]["code"],
        recon_coords,
        language="en"
    )
    
    print(f"  - Validation Status: {'[PASSED] ' + GREEN if val_result['valid'] else '[REJECTED] ' + RED}{'VALID' if val_result['valid'] else 'INVALID'}{RESET}")
    
    if val_result["warnings"]:
        print(f"\n  {BOLD}{YELLOW}Warnings/Audits:{RESET}")
        for w in val_result["warnings"]:
            print(f"    ⚠️ {w}")
            
    if not val_result["valid"]:
        print(f"\n  {BOLD}{RED}Validation Failures:{RESET}")
        for error in val_result["issues"]:
            print(f"    ❌ {error}")
        print(f"\n{BOLD}{YELLOW}Fallback Triggered:{RESET} Falling back to Tier-1 template to prevent AI hallucination.")
        print(f"  {GREEN}{t1_en['alert_text']}{RESET}")
    else:
        print(f"\n{BOLD}{GREEN}Alert matches landmark registry. Output approved for display to user.{RESET}")
        
    print("\n" + "=" * 80)
    print(f"{BOLD}{GREEN}=== PIPELINE DEMO COMPLETED SUCCESSFULLY ==={RESET}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
