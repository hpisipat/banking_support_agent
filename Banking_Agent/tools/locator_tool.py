# tools/locator_tool.py
# Feature 5 — Branch / ATM Locator
# Uses LLM with chat_history to extract location naturally
# Uses ORS API for road distance, falls back to Haversine

import os
import sys
import json
import requests
from math import radians, sin, cos, sqrt, atan2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observability.logger import log_info, log_warning
from data.mock_branches   import (MOCK_BRANCHES, MOCK_ATMS,
                                   LOCALITY_COORDINATES)


# ── Haversine — fallback straight line distance ───────────────────────────────

def calculate_haversine(lat1, lon1, lat2, lon2):
    """Straight line distance — used as fallback"""
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a    = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c    = 2 * atan2(sqrt(a), sqrt(1-a))
    return round(R * c, 1)


# ── ORS Road Distance — with Haversine fallback ───────────────────────────────

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates road distance using OpenRouteService API.
    Falls back to Haversine if API key missing or API fails.
    Logs which method was used — visible in agent.log
    """
    SYSTEM_SESSION = "SYSTEM-LOCATOR"
    api_key        = os.getenv("ORS_API_KEY")

    # No API key — use Haversine
    if not api_key:
        log_info(SYSTEM_SESSION, "system",
                 "distance_method",
                 "haversine — ORS_API_KEY not configured")
        return calculate_haversine(lat1, lon1, lat2, lon2)

    # Try ORS API
    try:
        url     = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": api_key}
        params  = {
            "start": f"{lon1},{lat1}",   # ORS uses lon,lat order
            "end"  : f"{lon2},{lat2}"
        }

        response    = requests.get(url, headers=headers,
                                   params=params, timeout=5)
        data        = response.json()
        distance_m  = (data["features"][0]["properties"]
                           ["segments"][0]["distance"])
        distance_km = round(distance_m / 1000, 1)

        log_info(SYSTEM_SESSION, "system",
                 "distance_method",
                 f"ors_api — road_distance={distance_km}km")

        return distance_km

    except Exception as e:       # ✅ Fix — capture exception as e
        log_warning(SYSTEM_SESSION, "system",
                    "distance_fallback",
                    f"ors_failed={str(e)} — using haversine")

        return calculate_haversine(lat1, lon1, lat2, lon2)


# ── LLM extracts location from conversation ───────────────────────────────────

def extract_location_from_conversation(user_message, chat_history):
    """
    Uses LLM to extract RAW location name from conversation.
    Does NOT map to known areas — mapping happens separately.
    """
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    llm    = get_llm()
    prompt = f"""
    Extract location details from this banking support conversation.

    From the conversation, identify:
    1. area: The EXACT location/area name the customer mentioned
       (return exactly what they said — do not map or change it)
    2. type: "branch", "atm", or "both"
    3. wants_247: true if customer specifically wants 24/7 ATM

    Reply ONLY with valid JSON:
    {{"area": "exact_area_name_or_null", "type": "branch/atm/both", "wants_247": false}}
    """

    messages = [SystemMessage(content=prompt)]
    for msg in chat_history[-4:]:
        messages.append(msg)
    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        text     = response.content.strip()
        text     = text.replace("```json","").replace("```","").strip()
        data     = json.loads(text)
        return (
            data.get("area"),
            data.get("type", "both"),
            data.get("wants_247", False)
        )
    except Exception:
        return None, "both", False


# ── Main function ─────────────────────────────────────────────────────────────

def find_nearest(user_message, persona="existing_customer",
                 session_id="SYSTEM", chat_history=[]):
    """
    Finds nearest branch or ATM.
    LLM extracts location → exact match → ORS/Haversine distance.
    Unknown areas mapped to nearest known area via LLM.
    """

    log_info(session_id, persona, "locator_tool_called", user_message)

    # Step 1 — LLM extracts raw location
    area, search_type, wants_247 = extract_location_from_conversation(
        user_message, chat_history
    )

    # No location found — ask user
    if not area:
        log_warning(session_id, persona, "locator_area_unclear", user_message)
        return ("I can help find the nearest branch or ATM! "
                "Could you please share your area or locality "
                "in Hyderabad?\n\n"
                "       For example: Ameerpet, Kukatpally, "
                "Madhapur, Banjara Hills etc.")

    # Step 2 — Try exact match in mock data
    exact_branches = [b for b in MOCK_BRANCHES
                      if b["area"].lower() == area.lower()]
    exact_atms     = [a for a in MOCK_ATMS
                      if a["area"].lower() == area.lower()]

    if exact_branches or exact_atms:
        log_info(session_id, persona, "locator_exact_match",
                 f"area={area} type={search_type}")
        return format_results(area, exact_branches, exact_atms,
                              search_type, wants_247, exact_match=True)

    # Step 3 — Check LOCALITY_COORDINATES for known area
    ref_coords = LOCALITY_COORDINATES.get(area.lower())

    # Step 4 — Unknown area → LLM maps to nearest known area
    if not ref_coords:
        from core.llm_agent import get_llm
        from langchain_core.messages import HumanMessage

        llm   = get_llm()
        known = ", ".join(LOCALITY_COORDINATES.keys())

        map_prompt = f"""
        The customer is near "{area}" in Hyderabad.

        From this list of areas we have coordinates for:
        {known}

        Which area from the list is geographically closest to "{area}"?
        Reply with ONLY the area name from the list. Nothing else.
        """

        try:
            map_response = llm.invoke([HumanMessage(content=map_prompt)])
            mapped       = map_response.content.strip().lower()
            ref_coords   = LOCALITY_COORDINATES.get(mapped)

            if ref_coords:
                log_info(session_id, persona, "locator_area_mapped",
                         f"unknown={area} mapped_to={mapped}")

                ref_lat, ref_lon = ref_coords

                branches_with_dist = sorted([
                    {**b, "distance": calculate_distance(
                        ref_lat, ref_lon,
                        b["latitude"], b["longitude"]
                    )}
                    for b in MOCK_BRANCHES
                ], key=lambda x: x["distance"])

                atms_with_dist = sorted([
                    {**a, "distance": calculate_distance(
                        ref_lat, ref_lon,
                        a["latitude"], a["longitude"]
                    )}
                    for a in MOCK_ATMS
                ], key=lambda x: x["distance"])

                return format_results(
                    area,                    # original area (Bandlaguda)
                    branches_with_dist[:3],
                    atms_with_dist[:3],
                    search_type, wants_247,
                    exact_match = False,
                    mapped_to   = mapped     # mapped area (Gachibowli)
                )

            else:
                log_warning(session_id, persona,
                            "locator_area_unknown", area)
                return (f"I'm not familiar with '{area.title()}'. "
                        f"Could you share a nearby landmark or "
                        f"one of these areas?\n\n"
                        f"       Ameerpet, Kukatpally, Madhapur, "
                        f"Begumpet, Secunderabad, Banjara Hills")

        except Exception as e:
            log_warning(session_id, persona,
                        "locator_mapping_failed", str(e))
            return (f"I'm having trouble locating '{area.title()}'. "
                    f"Please share a nearby known area.")

    # Step 5 — Known area → calculate distances
    ref_lat, ref_lon = ref_coords

    branches_with_dist = sorted([
        {**b, "distance": calculate_distance(
            ref_lat, ref_lon,
            b["latitude"], b["longitude"]
        )}
        for b in MOCK_BRANCHES
    ], key=lambda x: x["distance"])

    atms_with_dist = sorted([
        {**a, "distance": calculate_distance(
            ref_lat, ref_lon,
            a["latitude"], a["longitude"]
        )}
        for a in MOCK_ATMS
    ], key=lambda x: x["distance"])

    log_info(session_id, persona, "locator_distance_calculated",
             f"area={area} type={search_type}")

    return format_results(area, branches_with_dist[:3],
                          atms_with_dist[:3], search_type,
                          wants_247, exact_match=False)


# ── Format results ────────────────────────────────────────────────────────────

def format_results(area, branches, atms, search_type,
                   wants_247=False, exact_match=True,
                   mapped_to=None):

    response   = ""
    area_title = area.title()

    # Distance reference = mapped area (where distances calculated from)
    dist_ref   = mapped_to.title() if mapped_to else area_title

    if not exact_match:
        if mapped_to:
            response += (f"📍 We don't have a branch or ATM directly "
                         f"in {area_title}.\n"
                         f"   Showing nearest locations "
                         f"(based on proximity to "
                         f"{mapped_to.title()}):\n\n")
        else:
            response += (f"📍 We don't have a branch or ATM directly "
                         f"in {area_title}. Here are the nearest:\n\n")

    if search_type in ["branch", "both"] and branches:
        response += f"🏦 Nearest Branch{'es' if len(branches)>1 else ''}:\n\n"
        for i, b in enumerate(branches[:3], 1):
            dist     = (f" ({b['distance']} km from {dist_ref})"
                        if not exact_match and "distance" in b else "")
            services = ", ".join(b.get("services", [])[:3])
            response += (f"   {i}. {b['name']}{dist}\n"
                         f"      Address  : {b['address']}\n"
                         f"      Phone    : {b['phone']}\n"
                         f"      Timings  : {b['timings']}\n"
                         f"      Closed   : {b['closed_on']}\n"
                         f"      Services : {services}\n\n")

    if search_type in ["atm", "both"] and atms:
        display_atms = atms
        if wants_247:
            display_atms = [a for a in atms if a["timings"] == "24/7"]
            if not display_atms:
                response += "⚠️  No 24/7 ATMs found. Showing all ATMs:\n\n"
                display_atms = atms

        response += f"🏧 Nearest ATM{'s' if len(display_atms)>1 else ''}:\n\n"
        for i, a in enumerate(display_atms[:3], 1):
            dist   = (f" ({a['distance']} km from {dist_ref})"
                      if not exact_match and "distance" in a else "")
            status = "✅ Operational" if a["operational"] else "🔴 Under Maintenance"
            response += (f"   {i}. {a['area']} ATM{dist}\n"
                         f"      Address  : {a['address']}\n"
                         f"      Timings  : {a['timings']}\n"
                         f"      Type     : {a['type']}\n"
                         f"      Status   : {status}\n\n")

    return response.strip() or (
        f"No branches or ATMs found near {area_title}. "
        f"Please call 1800-XXX-XXXX."
    )


# ── Zone Directory (banker only) ──────────────────────────────────────────────

def get_zone_directory(zone=None, session_id="SYSTEM"):
    log_info(session_id, "banker", "zone_directory_called", f"zone={zone}")

    zones = list(set(b["zone"] for b in MOCK_BRANCHES))

    if not zone:
        result = "📋 Branch Directory — All Zones:\n\n"
        for z in zones:
            zb      = [b for b in MOCK_BRANCHES if b["zone"] == z]
            result += f"   {z} ({len(zb)} branches):\n"
            for b in zb:
                result += (f"      • {b['name']} | "
                           f"{b['phone']} | Manager: {b['manager']}\n")
            result += "\n"
        return result

    zone_branches = [b for b in MOCK_BRANCHES
                     if zone.lower() in b["zone"].lower()]
    if not zone_branches:
        return (f"No branches in zone '{zone}'. "
                f"Available: {', '.join(zones)}")

    result  = f"📋 Branch Directory — {zone}:\n\n"
    result += f"{'Branch ID':<12} {'Name':<25} {'Phone':<15} {'Manager'}\n"
    result += "-" * 70 + "\n"
    for b in zone_branches:
        result += (f"{b['branch_id']:<12} {b['name']:<25} "
                   f"{b['phone']:<15} {b['manager']}\n")
    result += f"\nTotal branches: {len(zone_branches)}"
    return result