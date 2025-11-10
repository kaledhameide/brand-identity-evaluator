# Brand Identity Evaluator – Streamlit MVP
# ---------------------------------------
# One-file prototype you can run on Replit or locally.
# - Collects brand inputs (positioning, segment, audience, colors, font, icon)
# - (Optional) Calls OpenAI to generate a score + feedback
# - Fallback: rule-based heuristic scorer using color/font psychology
#
# How to run locally:
# 1) pip install -r requirements.txt  (or individually: streamlit openai)
# 2) Set your OpenAI API key:  export OPENAI_API_KEY=sk-...  (or paste in the sidebar)
# 3) streamlit run app.py
#
# On Replit:
# - Create a new Python repl
# - Add this file as app.py
# - Add a secrets entry named OPENAI_API_KEY (or paste at runtime in the sidebar)
# - In the Shell:  pip install streamlit openai
# - Run:  streamlit run app.py --server.port=3000 --server.address=0.0.0.0

import os
import json
import re
from typing import List, Dict, Tuple

import streamlit as st

# --- Password Gate ---
import streamlit as st

st.title("🔒 Fashion Brand Identity Evaluator")

password = st.text_input("Enter access password:", type="password")

if password != "ARTX465":
    st.warning("Access restricted. Please enter the correct password to continue.")
    st.stop()  # Stops the app here until the correct password is entered


# Try to import OpenAI client, but app also works without it (heuristic mode)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

# -------------------------------
# Knowledge base (psychology maps)
# -------------------------------
COLOR_SEMANTICS: Dict[str, List[str]] = {
    "red": ["passionate", "powerful", "strong", "desire"],
    "orange": ["courageous", "confident", "energetic", "playful", "vibrant", "social"],
    "pink": ["sweet", "feminine", "loving", "playful", "gentle", "compassionate"],
    "yellow": ["joyful", "energetic", "bright", "warm"],
    "green": ["fresh", "wealthy", "growing", "organic", "balanced"],
    "blue": ["tranquil", "loyal", "calm", "healing", "trusting", "spiritual", "light"],
    "purple": ["royal", "noble", "majestic", "luxurious", "creative", "abundant"],
    "brown": ["earthy", "grounded", "conservative"],
    "white": ["innocent", "pure", "clean"],
    "black": ["sophisticated", "dramatic", "classic", "formal", "powerful", "elegant"],
    "gray": ["reliable", "secure", "solid", "modern", "futuristic", "sleek", "graceful"],
    "silver": ["reliable", "secure", "solid", "modern", "futuristic", "sleek", "graceful"],
    "gold": ["wise", "wealthy", "valued"],
}

FONT_SEMANTICS: Dict[str, List[str]] = {
    "serif": ["classic", "formal", "trustworthy", "heritage"],
    "slab-serif": ["bold", "confident", "youthful"],
    "sans-serif": ["modern", "clean", "straightforward", "minimal"],
    "script": ["elegant", "romantic", "feminine", "expressive"],
    "decorative": ["casual", "creative", "flexible"],
}

SEGMENT_NOTES: Dict[str, List[str]] = {
    "budget": ["low price", "basic", "non-trendy"],
    "moderate": ["affordable", "better quality"],
    "better": ["stylish", "affordable"],
    "contemporary": ["trendy", "youthful", "avant-garde", "fashion-forward"],
    "bridge": ["good value", "between better and premium"],
    "premium": ["accessible luxury", "designer RTW", "diffusion", "high-end"],
}

# Age/gender heuristics to bias scoring
# Younger audiences tolerate bolder palettes, display/script; older prefer legibility, contrast, restraint

def audience_bias(age: int, gender: str, font_key: str, colors: List[str]) -> float:
    bias = 0.0
    try:
        if age <= 28:
            if font_key in ("slab-serif", "sans-serif", "decorative"): bias += 2
            if any(c in ["red", "orange", "yellow"] for c in colors): bias += 1
        elif age >= 35:
            if font_key in ("serif", "sans-serif"): bias += 2
            if any(c in ["black", "gray", "blue"] for c in colors): bias += 1
    except Exception:
        pass
    # Very light touch on gender; avoid stereotypes—use readability/contrast instead
    return bias

# -------------------------------
# Heuristic Scoring (fallback)
# -------------------------------

def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z]+", (text or "").lower())


def score_alignment(positioning: str, segment: str, gender: str, age: int,
                    color_list: List[str], font_style: str, icon_style: str) -> Tuple[int, str, List[str]]:
    tokens = set(tokenize(positioning))

    # Map colors -> semantics
    color_hits = []
    for c in color_list:
        key = c.strip().lower()
        if key in COLOR_SEMANTICS:
            color_hits.extend(COLOR_SEMANTICS[key])
    color_hits_set = set(color_hits)

    # Map font -> semantics
    font_key = (font_style or "").strip().lower()
    font_meanings = set(FONT_SEMANTICS.get(font_key, []))

    # Segment
    seg_key = (segment or "").strip().lower()
    seg_tags = set(SEGMENT_NOTES.get(seg_key, []))

    # Base alignment: overlap of positioning tokens with visual semantics
    overlap_visual = len(tokens.intersection(set(tokenize(" ".join(list(color_hits_set) + list(font_meanings))))))

    # Segment nudges: premium ↔ black/gold/serif; contemporary ↔ bright/sans/decorative; budget ↔ simple/sans/basic
    segment_bonus = 0
    if seg_key == "premium":
        if any(c in ["black", "gold"] for c in color_list): segment_bonus += 2
        if font_key == "serif": segment_bonus += 1
    if seg_key == "contemporary":
        if any(c in ["red", "pink", "yellow", "orange"] for c in color_list): segment_bonus += 1
        if font_key in ("sans-serif", "decorative"): segment_bonus += 2
    if seg_key in ("budget", "moderate"):
        if font_key == "sans-serif": segment_bonus += 1

    # Audience bias
    try:
        age_i = int(age)
    except Exception:
        age_i = 30
    aud = audience_bias(age_i, (gender or "").lower(), font_key, [c.lower() for c in color_list])

    # Combine
    raw = 50 + 4 * overlap_visual + 3 * segment_bonus + aud
    score = max(0, min(100, int(round(raw))))

    # Explanation
    explain_bits = []
    if color_list:
        explain_bits.append(f"Colors {', '.join(color_list)} suggest: " + 
                            ", ".join(sorted(list(color_hits_set))[:6]) or "neutral cues")
    if font_meanings:
        explain_bits.append(f"Font ({font_style}) communicates: " + ", ".join(sorted(list(font_meanings))))
    if segment_bonus > 0:
        explain_bits.append(f"Segment fit: {segment} signals align with palette/type choices")
    if aud > 0:
        explain_bits.append("Audience resonance boosted by age/readability preferences")
    if not explain_bits:
        explain_bits.append("Limited inputs; using conservative baseline.")

    # Suggestions
    suggestions = []
    if seg_key == "premium" and not any(c in ["black", "gold"] for c in [c.lower() for c in color_list]):
        suggestions.append("Introduce black or gold accents to cue premium value.")
    if seg_key == "contemporary" and font_key == "serif":
        suggestions.append("Consider a modern sans-serif or slab to increase trend perception.")
    if age_i >= 35 and font_key in ("decorative", "script"):
        suggestions.append("Swap to a more legible face for older audiences (serif/sans with good contrast).")
    if not suggestions:
        suggestions.append("Tighten contrast and simplify shapes for stronger digital legibility.")
        suggestions.append("Ensure palette has sufficient WCAG contrast on light/dark backgrounds.")
        suggestions.append("Test recognition at small sizes (favicon/social avatars).")

    explanation = " ".join(explain_bits)
    return score, explanation, suggestions[:3]


# -------------------------------
# OpenAI call (optional)
# -------------------------------

def call_openai(positioning: str, segment: str, audience: str, colors: str, font: str, icon: str, api_key: str):
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI Python client not installed. Run: pip install openai")
    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a fashion branding and design-psychology expert. Using the following inputs, rate how well this logo expresses the brand positioning and fits the audience. Provide JSON with keys score, explanation, suggestions (3 items).

Color meanings: red=passion/power; orange=confidence/energy/playful; pink=feminine/compassion; yellow=optimism/energy; green=fresh/balanced/wealth; blue=trust/calm/loyal; purple=luxury/creative; brown=grounded; white=pure/clean; black=sophisticated/elegant/power; gray/silver=modern/reliable/sleek; gold=wealth/value.
Font meanings: serif=classic/formal/trust; slab-serif=bold/confident/youthful; sans-serif=modern/clean/straightforward; script=elegant/romantic; decorative=creative/flexible.
Segments: budget, moderate, better, contemporary (trendy/youthful), bridge (value between better & premium), premium (accessible luxury).

Inputs:
- Positioning: {positioning}
- Segment: {segment}
- Audience: {audience}
- Colors: {colors}
- Font: {font}
- Icon: {icon}

Output JSON only.
"""

    msg = [{"role": "user", "content": prompt.strip()}]
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msg,
        temperature=0.4,
    )
    content = resp.choices[0].message.content

    # Try to parse JSON block
    try:
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            return json.loads(m.group(0))
        return json.loads(content)
    except Exception:
        # Fallback: wrap plain text
        return {
            "score": None,
            "explanation": content,
            "suggestions": []
        }


# -------------------------------
# UI
# -------------------------------

st.set_page_config(page_title="Brand Identity Evaluator (by KKH)", page_icon="👗", layout="centered")
st.title("👗 Brand Identity Evaluator – by KKH")
st.caption("Upload your brand details, then get a score + rationale. Works with or without OpenAI.")

with st.sidebar:
    st.header("Settings")
    api_key = os.getenv("OPENAI_API_KEY", "")
    use_key = st.toggle("Use OpenAI (optional)", value=bool(api_key))
    if use_key and not api_key:
        api_key = st.text_input("OpenAI API Key", type="password")
    st.markdown("---")
    st.markdown("**Tips**\n- If you skip the API key, the app uses a built-in heuristic.\n- Provide colors as names (e.g., black, gold, blue).")

st.subheader("Brand Inputs")
col1, col2 = st.columns(2)
with col1:
    positioning = st.text_area("Brand positioning line", placeholder="e.g., Modern luxury streetwear for creative professionals")
    segment = st.selectbox("Market segment", ["Premium", "Bridge", "Contemporary", "Better", "Moderate", "Budget"], index=0)
    gender = st.selectbox("Primary customer gender", ["Unisex", "Female", "Male"], index=0)
with col2:
    age = st.number_input("Primary customer age (typical)", min_value=15, max_value=80, value=32)
    colors_text = st.text_input("Dominant logo colors (comma-separated)", placeholder="black, gold")
    font_style = st.selectbox("Font style used in logo", ["Serif", "Slab-serif", "Sans-serif", "Script", "Decorative"], index=0)
icon_style = st.text_input("Icon/shape style (optional)", placeholder="monogram, abstract geometric, emblem, wordmark only…")
logo = st.file_uploader("(Optional) Upload logo image (not required for MVP)", type=["png", "jpg", "jpeg", "webp"])

if st.button("Analyze Logo", type="primary"):
    color_list = [c.strip() for c in (colors_text or "").split(",") if c.strip()]

    if use_key and api_key:
        try:
            ai = call_openai(
                positioning=positioning,
                segment=segment,
                audience=f"{gender}, age {age}",
                colors=", ".join(color_list) or "(not specified)",
                font=font_style,
                icon=icon_style or "(not specified)",
                api_key=api_key,
            )
            score = ai.get("score")
            explanation = ai.get("explanation", "")
            suggestions = ai.get("suggestions", [])

            if score is None:
                # If the model didn't return a numeric score, compute heuristic
                hscore, hexpl, hsug = score_alignment(positioning, segment, gender, age, color_list, font_style, icon_style)
                score = hscore
                explanation = explanation or hexpl
                suggestions = suggestions or hsug
        except Exception as e:
            st.warning(f"OpenAI failed ({e}); falling back to heuristic.")
            score, explanation, suggestions = score_alignment(positioning, segment, gender, age, color_list, font_style, icon_style)
    else:
        score, explanation, suggestions = score_alignment(positioning, segment, gender, age, color_list, font_style, icon_style)

    st.markdown("---")
    st.subheader("Results")
    st.metric("Effectiveness Score", f"{int(score)} / 100")
    st.write(explanation)
    st.markdown("**Suggestions**")
    for s in suggestions:
        st.write("- ", s)

    # Downloadable report
    report = {
        "positioning": positioning,
        "segment": segment,
        "gender": gender,
        "age": age,
        "colors": color_list,
        "font_style": font_style,
        "icon_style": icon_style,
        "score": int(score),
        "explanation": explanation,
        "suggestions": suggestions,
    }
    st.download_button("Download JSON report", data=json.dumps(report, indent=2), file_name="brand_identity_evaluation.json", mime="application/json")

# -------------------------------
# Minimal requirements (for convenience):
# streamlit
# openai  # optional; remove if not using API
# -------------------------------
