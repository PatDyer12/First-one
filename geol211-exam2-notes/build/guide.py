#!/usr/bin/env python3
"""Builds the GEOL 211 Exam 2 study guide (HTML -> PDF via render.js).

Every topic uses the same layout so it is easy to follow and to copy by hand:
  question  ->  ANSWER box (copy this)  ->  how it works (steps)  ->  diagram  ->  know these  ->  exam trap
"""
import base64
from pathlib import Path

import diagrams as D

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "geol211_exam2_study_guide.html"


# ------------------------------------------------------------------ building blocks
def topic(num, question, guide_text, answer, body, star=False):
    s = '<span class="star">★</span>' if star else ""
    lead = ""
    if body.startswith('<figure class="fig wide">'):   # keep a leading diagram with its question
        cut = body.index("</figure>") + len("</figure>")
        lead, body = body[:cut], body[cut:]
    return (f'<article class="topic" id="t{num}"><div class="keep">'
            f'<div class="t-head"><span class="num">{num}</span><div>'
            f'<div class="q">{question} {s}</div><div class="rg">Review guide: {guide_text}</div></div></div>'
            f'<div class="answer"><div class="lbl">ANSWER — copy this</div>{answer}</div>{lead}</div>'
            f'{body}</article>')


def steps(title, items):
    lis = "".join(f"<li>{i}</li>" for i in items)
    return f'<div class="blk"><h4>{title}</h4><ol>{lis}</ol></div>'


def facts(title, items):
    lis = "".join(f"<li>{i}</li>" for i in items)
    return f'<div class="blk"><h4>{title}</h4><ul>{lis}</ul></div>'


def fig(svg, caption, wide=False):
    cls = "fig wide" if wide else "fig"
    return f'<figure class="{cls}">{svg}<figcaption>{caption}</figcaption></figure>'


def side(left_html, figure_html):
    return f'<div class="two"><div class="two-l">{left_html}</div><div class="two-r">{figure_html}</div></div>'


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def tip(text_html):
    return f'<div class="tip"><b class="lbl">★ Exam trap:</b> {text_html}</div>'


R = lambda s: f'<span class="r">{s}</span>'   # red emphasis


# ------------------------------------------------------------------ front pages
FRONT = f"""
<header class="doc">
  <div class="doc-t">GEOL 211 · Exam 2 Study Guide</div>
  <div class="doc-s">Atmospheric Circulation + Ocean Circulation · built from the class slides + review guide</div>
  <div class="doc-i">Exam: Wed 9/30 · on paper · individual part (30 min) FIRST, then team part (20 min) ·
  questions also come from <b>class assignments</b>, so add them to your notes</div>
</header>

<div class="howto">
  <b>How to copy this into your notebook:</b>
  (1) Copy <b>The Big Picture</b> below first — it's the map of the whole unit.
  (2) For each topic, copy the <b>question</b>, the <b>ANSWER box</b>, the <b>numbered steps</b> and the <b>diagram</b>
  (that's what answers "explain why" questions). "Know these" + exam traps come next.
  (3) Fill in the page numbers in the contents table as you go — that's your index during the exam.
  Short on time? Do the {R('★')} topics first.
</div>

<h2 class="sec">The Big Picture — how everything connects</h2>
<p class="lead">This whole unit is <b>one chain of cause → effect</b>. Every topic is one link in it:</p>
<div class="chain">
  <div class="c-box"><b>1. The SUN heats Earth unevenly</b> — hot at the equator, cold at the poles <span class="tn">(topic 2)</span></div>
  <div class="c-arr">↓</div>
  <div class="c-box"><b>2. Heat changes air density</b> — warm/humid air is light and RISES (= LOW pressure, rain);
     cold/dry air is heavy and SINKS (= HIGH pressure, dry) <span class="tn">(topics 1–2)</span></div>
  <div class="c-arr">↓</div>
  <div class="c-box"><b>3. Air flows from HIGH to LOW = WIND</b> <span class="tn">(topic 2)</span></div>
  <div class="c-arr">↓</div>
  <div class="c-box"><b>4. Earth's spin bends the wind (CORIOLIS)</b> — right in the Northern Hemisphere, left in the Southern <span class="tn">(topic 4)</span></div>
  <div class="c-arr">↓</div>
  <div class="c-box"><b>5. Result: global wind belts</b> — trade winds, westerlies, polar easterlies (3 cells per hemisphere) <span class="tn">(topic 3)</span>
     <div class="c-side">• Land heats/cools faster than water → sea breezes + monsoons <span class="tn">(topic 5)</span><br>
     • Warm ocean + moist air + calm upper winds → HURRICANES, steered around highs <span class="tn">(topics 6–9)</span></div></div>
  <div class="c-arr">↓</div>
  <div class="c-box ocn-b"><b>6. Wind drags the ocean surface → SURFACE CURRENTS + GYRES</b> (bent by Coriolis again) <span class="tn">(topics 11–14)</span>
     <div class="c-side">• Wind pushes surface water away → deep water comes up = UPWELLING (nutrients → fish) <span class="tn">(topic 15)</span><br>
     • Trade winds weaken or strengthen → EL NIÑO / LA NIÑA <span class="tn">(topic 16)</span></div></div>
  <div class="c-arr">＋</div>
  <div class="c-box ocn-b"><b>7. Separately, DENSITY drives the deep ocean</b> — cold + salty water sinks near the poles →
     slow global CONVEYOR BELT that moves heat (~1000 yrs per loop) <span class="tn">(topics 10, 12, 17)</span></div>
</div>

<div class="rules">
  <div class="rules-t">3 rules that answer half the exam</div>
  <ol>
    <li><b>Warm or humid = light = rises = LOW = rain.</b> Cold or dry = heavy = sinks = HIGH = dry.</li>
    <li><b>Air and water move from HIGH → LOW</b> and get bent <b>RIGHT in the NH, LEFT in the SH</b> (Coriolis).</li>
    <li><b>Land heats up AND cools down faster than water.</b></li>
  </ol>
</div>
<p class="abbr"><b>Abbreviations:</b> NH / SH = Northern / Southern Hemisphere · H / L = high / low pressure ·
SST = sea-surface temperature · ITCZ = Intertropical Convergence Zone · ↑ = increases · ↓ = decreases</p>
"""

CHEAT_ROWS = [
    ["Air density", "Warm or humid air = LESS dense → rises. Cold or dry air = MORE dense → sinks. Densest air = poles."],
    ["Low vs high pressure", "LOW = rising air → clouds, rain. HIGH = sinking air → clear, dry. Wind blows H → L."],
    ["Pressure belts", "0° LOW (ITCZ, wet) · 30° HIGH (dry, deserts) · 60° LOW (wet) · 90° HIGH (cold, dry)"],
    ["Cells + winds", "Hadley 0–30° (trade winds) · Ferrel 30–60° (westerlies) · Polar 60–90° (polar easterlies)"],
    ["Coriolis", "Bends RIGHT in NH, LEFT in SH · zero at equator, stronger toward poles · doesn't cause wind"],
    ["Breezes", "DAY = sea breeze (sea → land) · NIGHT = land breeze (land → sea)"],
    ["Monsoons", "SUMMER: ocean → land = WET · WINTER: land → ocean = DRY · follows the ITCZ"],
    ["Hurricane needs", "Water &gt;27°C · low pressure · warm, moist air · wind shear &lt;20 knots · Coriolis (not at equator)"],
    ["Hurricane fuel", "LATENT HEAT released when water vapor condenses · spins counterclockwise in NH"],
    ["Hurricane hazards", "Storm surge (worst) · wind · rain · flooding · waves · landslides"],
    ["Hurricane path", "Goes AROUND highs (clockwise in NH): west on trades → north → northeast on westerlies"],
    ["Climate change", "Not MORE hurricanes — STRONGER, WETTER, higher surge"],
    ["Surface vs deep currents", "Surface = WIND, ~10% of ocean, fast · Deep = DENSITY, ~90%, slow"],
    ["Thermocline", "Temp drops fast: 200 m (13°C) → 1000 m (4°C) · barrier to mixing"],
    ["Ekman transport", "Surface water 45° right of wind · NET transport 90° RIGHT of wind (NH), LEFT (SH)"],
    ["Gyres", "CLOCKWISE in NH, COUNTERCLOCKWISE in SH · warm current on WEST side, cold on EAST side"],
    ["West vs east boundary", "West (Gulf Stream) = fast, narrow, deep, warm · East (Canary) = slow, wide, shallow, cold"],
    ["Upwelling", "Cold, nutrient-rich water rises → plankton → fish · NH west coast + wind from the NORTH"],
    ["El Niño", "Trades WEAKEN → warm water moves east → no upwelling off Peru → FEWER Atlantic hurricanes"],
    ["La Niña", "Trades STRONGER → colder east Pacific → MORE Atlantic hurricanes"],
    ["Conveyor belt", "Sinks near Greenland + Antarctica · ~1000 yrs · moves heat · fresh meltwater SLOWS it"],
]

CONTENTS = [
    ("A", "1", "Air density — how + why it changes"), ("A", "2", "High + low pressure — why + weather"),
    ("A", "3", "Global atmospheric circulation ★"), ("A", "4", "Coriolis effect ★"),
    ("A", "5", "Sea/land breezes + monsoons"), ("A", "6", "What a hurricane needs ★"),
    ("A", "7", "Hurricane hazards + storm surge"), ("A", "8", "Predicting a hurricane's path ★"),
    ("A", "9", "Hurricanes + climate change"),
    ("B", "10", "Surface vs deep water ★"), ("B", "11", "Major ocean currents (gyres)"),
    ("B", "12", "What drives surface + deep currents ★"), ("B", "13", "West vs east boundary currents ★"),
    ("B", "14", "How currents affect weather"), ("B", "15", "Upwelling + downwelling ★"),
    ("B", "16", "El Niño + La Niña ★"), ("B", "17", "Deep water circulation + climate ★"),
]


def cheat_page():
    rows = "".join(f"<tr><td class='ck'>{a}</td><td>{b}</td></tr>" for a, b in CHEAT_ROWS)
    half = 9
    def col(items):
        return "".join(
            f"<tr><td class='cn'>{n}</td><td>{t.replace('★', R('★'))}</td><td class='cp'>p. ____</td></tr>"
            for _, n, t in items)
    return f"""
<section class="cheat">
<h2 class="sec">Quick Answers — fastest lookup during the exam</h2>
<table class="cheat-t"><thead><tr><th>If the question is about…</th><th>Remember…</th></tr></thead><tbody>{rows}</tbody></table>
<h2 class="sec small">Contents — write your notebook page numbers here</h2>
<div class="toc">
  <table><thead><tr><th colspan="3">PART A · ATMOSPHERE</th></tr></thead><tbody>{col(CONTENTS[:half])}</tbody></table>
  <table><thead><tr><th colspan="3">PART B · OCEAN</th></tr></thead><tbody>{col(CONTENTS[half:])}</tbody></table>
</div>
</section>"""


# ------------------------------------------------------------------ PART A: ATMOSPHERE
def part_a():
    T = []
    T.append(topic(1, "How and why does air density change?", "Explain how/why air density changes.",
        f"<p>Air density depends on <b>temperature</b> and <b>moisture</b>. {R('Warm air and humid air are LESS dense, so they rise.')} "
        "Cold air and dry air are MORE dense, so they sink.</p>",
        side(steps("How it works", [
                "<b>Warm air:</b> molecules move fast and spread out → fewer molecules in the same space → less dense → <b>rises</b>.",
                "<b>Cold air:</b> molecules slow down and pack together → more molecules in the same space → denser → <b>sinks</b>.",
                f"<b>Humid air:</b> a water vapor molecule (H₂O, mass 18) is <b>lighter</b> than the N₂ (28) and O₂ (32) it replaces → "
                f"{R('humid air is LESS dense than dry air')}.",
             ]) + facts("Know these", [
                "Air moves 2 ways: <b>horizontally</b> (controlled by <b>pressure</b>, high → low) and <b>vertically</b> (controlled by <b>density</b>).",
                "Densest air on Earth: at the <b>poles</b> (cold + dry).",
                "Air = 78% N₂, 21% O₂, 0–4% water vapor.",
                "The <b>Sun</b> is the energy source for all wind and ocean circulation.",
             ]),
             fig(D.d_density(), "<b>How to read it:</b> same-size boxes. Fewer molecules = lighter = the air rises.")) +
        tip("\"Humid air is heavier\" is <b>false</b> — humid air is LIGHTER than dry air."), star=False))

    T.append(topic(2, "Why do high and low pressure form, and what weather do they bring?",
        "Explain why regions of high/low density develop. Identify high/low pressure. Describe the weather.",
        "<p>The Sun heats Earth <b>unevenly</b>. Where air is warmed it <b>rises</b>, leaving <b>LOW</b> pressure at the surface "
        f"({R('clouds + rain')}). Where air is cooled it <b>sinks</b> and piles up as <b>HIGH</b> pressure ({R('clear + dry')}). "
        "Air then flows from high to low = <b>wind</b>.</p>",
        side(steps("How it works", [
                "<b>Equator:</b> Sun is straight overhead → energy concentrated → hot. <b>Poles:</b> Sun is low → the same sunbeam spreads over more area → cold.",
                "So there's a heat <b>surplus</b> near the equator and a <b>deficit</b> near the poles → air + oceans carry heat toward the poles.",
                "<b>Rising</b> air expands and cools → water vapor condenses → <b>clouds, rain</b>.",
                "<b>Sinking</b> air compresses and warms → no condensation → <b>clear skies</b>.",
             ]),
             fig(D.d_pressure(), "<b>How to read it:</b> air rises at the L and sinks at the H; at the ground the wind blows from H to L.")) +
        table(["", "LOW pressure (L)", "HIGH pressure (H)"], [
            ["Air", "warm, humid, RISES", "cold, dry, SINKS"],
            ["Weather", "cloudy, rainy, stormy", "clear, dry, calm"],
            ["Surface winds", "flow IN toward it", "flow OUT away from it"],
            ["Spin (NH)", "counterclockwise", "clockwise"],
            ["Where", "0° (ITCZ) and 60°", "30° and 90° (poles)"],
        ], "cmp") +
        facts("Know these", ["Seasons shift where the Sun is most direct, so the belts shift north and south during the year."])))

    T.append(topic(3, "Draw the global atmospheric circulation pattern",
        "Draw the global circulation. Label high/low pressure, the ITCZ, and high/low precipitation.",
        "<p>Each hemisphere has <b>3 cells</b>: Hadley (0–30°), Ferrel (30–60°), Polar (60–90°). "
        f"Air {R('RISES at 0° and 60°')} (LOW → wet) and {R('SINKS at 30° and 90°')} (HIGH → dry). "
        "Surface winds blow from the highs to the lows and get bent by Coriolis → <b>trade winds, westerlies, polar easterlies</b>.</p>",
        fig(D.d_global(), "<b>How to read it:</b> the loops on the left are side views of the cells (air going up and down). "
            "The arrows on the globe are the surface winds. Every arrow starts at a H line and points toward a L line, bent right in the NH and left in the SH.", wide=True) +
        steps("How to draw it in 6 steps", [
            "Draw a circle. Add lines at 0°, 30°N, 60°N, 30°S, 60°S.",
            f"Write the pressure pattern going out from the equator: {R('L – H – L – H')} (0° L, 30° H, 60° L, 90° H), same in both hemispheres.",
            "Label rain: 0° = ITCZ, WET · 30° = DRY (deserts) · 60° = WET · 90° = DRY (cold desert).",
            "Draw surface winds from each H toward the next L: 30° → 0° (trades), 30° → 60° (westerlies), 90° → 60° (polar easterlies).",
            "Bend every arrow: <b>right in the NH, left in the SH</b>. That gives NE trades, SE trades, westerlies, polar easterlies.",
            "Draw the loops on the side and name them: Hadley (0–30°), Ferrel (30–60°), Polar (60–90°).",
        ]) +
        facts("Know these", [
            "<b>ITCZ</b> (Intertropical Convergence Zone, the \"doldrums\") = where NE + SE trades meet at the equator → rising air → heavy rain. It follows the Sun: farther <b>north in July</b>, <b>south in January</b>.",
            "<b>30° = horse latitudes / subtropical highs</b> → the world's deserts (Sahara, Arabian, Kalahari, Australian).",
            "<b>60° = subpolar lows</b> → rain, snow, storms. <b>90° = polar highs</b> → cold and dry.",
            "Winds are named for where they come <b>FROM</b> (NE trades blow from the northeast).",
            "A <b>non-rotating</b> Earth would have just 1 big cell per hemisphere. Rotation breaks it into 3.",
        ]), star=True))

    T.append(topic(4, "Why does the Coriolis effect exist, and what does it do?",
        "Explain why the Coriolis Force exists and what the result is.",
        "<p>Earth spins west → east, and places near the equator move <b>faster</b> than places near the poles. "
        "Anything moving north or south keeps its old eastward speed, so it drifts off course. "
        f"{R('Result: moving objects bend RIGHT in the NH and LEFT in the SH.')}</p>",
        side(steps("How it works", [
                "Every point on Earth makes one full turn per day.",
                "The equator has the longest trip (~40,000 km/day) so it's fastest. 60° goes ~20,000 km/day. The poles barely move.",
                "Air moving from the equator toward the North Pole is still moving east faster than the ground under it → it gets ahead → curves to the <b>right</b>.",
             ]) + facts("Know these", [
                "It's an <b>apparent</b> deflection — we see it because we're standing on a spinning planet.",
                f"{R('Zero at the equator')}, gets stronger toward the poles.",
                "Stronger for faster, heavier objects. Only matters for big motions (tens of km or more).",
                "It does <b>NOT cause</b> wind — it only changes the wind's <b>direction</b>.",
             ]),
             fig(D.d_coriolis(w=300, n=7), "<b>How to read it:</b> dashed = path with no spin. Both objects head north: the NH one bends right, the SH one bends left.")) +
        facts("What it causes", [
            "Bends the global winds into trade winds, westerlies and polar easterlies (topic 3).",
            "Makes ocean gyres turn and causes Ekman transport (topics 11–12).",
            "Makes storms spin: in the NH, air flowing into a LOW veers right → <b>counterclockwise</b>. That's why hurricanes can't form right at the equator.",
        ]) + tip("\"Coriolis causes wind\" is <b>false</b>. Pressure differences cause wind; Coriolis just bends it."), star=True))

    T.append(topic(5, "Explain sea/land breezes and monsoons", "Explain the development of monsoons + land/sea breeze.",
        f"<p>Both happen because {R('LAND heats up and cools down FASTER than WATER')} (water has a high heat capacity). "
        "Air rises over whichever surface is <b>warmer</b> (LOW) and sinks over the <b>cooler</b> one (HIGH), so the wind blows "
        "from the cool surface toward the warm one. <b>Breezes</b> flip every <b>day</b>; <b>monsoons</b> flip every <b>season</b>.</p>",
        fig(D.d_breeze_monsoon(), "<b>How to read it:</b> left = land is warmer (daytime or summer) → wind blows from the water onto the land. "
            "Right = land is cooler (night or winter) → the whole loop reverses.", wide=True) +
        table(["When", "Warmer surface (L)", "Surface wind blows", "Result"], [
            ["DAY", "land", "sea → land (onshore)", "<b>SEA breeze</b>"],
            ["NIGHT", "sea", "land → sea (offshore)", "<b>LAND breeze</b>"],
            ["SUMMER", "land", "ocean → land (moist air rises, cools)", f"<b>{R('WET monsoon')}</b> — heavy rain"],
            ["WINTER", "ocean", "land → ocean (dry air)", "<b>DRY season</b>"],
        ], "cmp") +
        facts("Know these", [
            "A breeze is named for where it comes <b>FROM</b> (sea breeze comes from the sea).",
            "Monsoon = a <b>seasonal reversal of winds</b>. The biggest is India / South Asia.",
            "Monsoons follow the <b>ITCZ</b>: June–July it moves north over India → rain there (Kozhikode). "
            "December–January it moves south → rain at Darwin, Australia.",
        ])))

    T.append(topic(6, "What conditions does a major hurricane need?", "List and describe the conditions necessary for a major hurricane.",
        "<p>Class list — memorize all 5: " + R("(1) warm water &gt;27°C, (2) a low-pressure system, (3) warm air with lots of water vapor, "
        "(4) low wind shear (&lt;20 knots), (5) strong enough Coriolis") + " (so not at the equator).</p>",
        table(["Condition", "Why it matters"], [
            ["1. Warm water &gt;27°C", "supplies heat + moisture = the fuel"],
            ["2. Low-pressure system", "the starting point: air flows in and rises"],
            ["3. Warm air, high water vapor", "more vapor = more latent heat released when it condenses"],
            ["4. Low wind shear (&lt;20 knots)", "winds at all heights similar → storm stays upright. High shear <b>tilts</b> it and tears it apart"],
            ["5. Strong Coriolis", "makes it spin → no hurricanes right at the equator"],
        ], "cmp") +
        steps("The engine = LATENT HEAT", [
            "Warm ocean water evaporates (evaporation <b>absorbs</b> heat).",
            "Moist air spirals in toward the low and rises in the eyewall.",
            "The water vapor condenses into clouds → <b>releases</b> that heat into the storm.",
            "The air warms and rises faster → pressure drops more → winds speed up → the cycle repeats.",
        ]) +
        facts("Know these", [
            "Air rushes toward the low and veers right → spins <b>counterclockwise in the NH</b> (clockwise in the SH).",
            "Structure: calm <b>eye</b> (~13–16 km wide) · <b>eyewall</b> = strongest winds (can top 250 km/h) · rain bands spiral out.",
            "Form over warm tropical water (none in the S Atlantic). Die over land or cold water (no fuel) or in high shear.",
            "Hurricane (Atlantic) = typhoon (W Pacific) = tropical cyclone — same storm.",
        ]), star=True))

    T.append(topic(7, "What are the risks (hazards) of hurricanes?", "List and describe the risks associated with hurricanes.",
        f"<p>Six hazards: <b>waves, wind, rain, flooding, landslides, storm surge</b>. {R('Storm surge')} — ocean water pushed up "
        "onto the land — is usually the most destructive.</p>",
        steps("Storm surge explained", [
            f"Mostly caused by strong <b>onshore winds</b> pushing water toward land ({R('wind-driven')}).",
            "The storm's low pressure lifts the sea only a little (about <b>5%</b> of the surge).",
            "As the water reaches shallow water near the coast it <b>piles up</b>.",
            "Worst if it arrives at <b>high tide</b> (Hurricane Sandy 2012, Atlantic City tide gauge).",
        ]) +
        table(["Factor", "Surge is HIGHER when…"], [
            ["Wind speed", "winds are stronger"],
            ["Size (radius) of storm", "the storm is bigger"],
            ["Forward speed", "fast storm → higher surge on the open coast · slow storm → floods longer and farther inland"],
            ["Angle of approach", "it hits the coast <b>head-on (perpendicular)</b> instead of sliding along it (parallel)"],
            ["Continental shelf", "the shelf is <b>wide and gently sloping</b> (shallow water)"],
            ["Shape of coastline", "bays and inlets <b>funnel</b> the water in"],
        ], "cmp") +
        facts("Know these", ["Rain flooding can hit far inland — e.g., Hurricane Ivan flooded Asheville, NC (2004)."])))

    T.append(topic(8, "Predict a hurricane's path from the highs and lows", "Predict the path of a hurricane based on high/low pressure.",
        f"<p>Hurricanes are <b>steered by the winds around pressure systems</b>. They can't push through a HIGH, so they "
        f"{R('travel around its edge — clockwise around a high in the NH')} — and they get pulled toward LOWS.</p>",
        fig(D.d_track(), "<b>How to read it:</b> the storm (red) rides the clockwise flow around the Bermuda High: west, then north, then northeast.", wide=True) +
        steps("Typical Atlantic path", [
            "Forms off Africa → the <b>trade winds</b> push it <b>WEST</b>.",
            "Reaches the west edge of the <b>Bermuda High</b> → turns <b>NORTH</b>.",
            "Meets the <b>westerlies</b> (~30°N) → curves <b>NORTHEAST</b>, out to sea.",
        ]) +
        facts("Rules for predicting", [
            "High is strong / stretches far west → storm keeps going west → Florida / Gulf of Mexico.",
            "High is weak or shifted east → storm turns north early → out to sea or up the East Coast.",
            "A low (trough) over the eastern US pulls the storm north toward the coast.",
        ]) + tip("On a map question: find the H, sketch clockwise arrows around it, then slide the storm along the H's edge toward the nearest L."), star=True))

    T.append(topic(9, "How will hurricanes change as the climate warms?",
        "Explain expected changes in hurricane activity due to climate change + trends over the last 100 years.",
        f"<p>Expect {R('not MORE hurricanes, but STRONGER and WETTER ones')}, with higher storm surge.</p>",
        '<div class="cols2">' +
        facts("Expected (future)", [
            "Warmer ocean = more fuel → <b>stronger</b> storms (more Cat 4–5) that intensify faster.",
            "Warmer air holds more water vapor → <b>more rain</b> + flooding.",
            "Sea-level rise → <b>higher storm surge</b>, more coast flooded.",
            "Total number of storms: about the same or fewer.",
        ]) +
        facts("Observed (last ~100 years)", [
            "Total number: <b>no clear long-term trend</b> (old records missed storms at sea — no satellites before the 1960s).",
            "The <b>share of major storms</b> (Cat 3–5) and their rainfall has gone up.",
            "Damage ($) has gone up a lot — mostly because more people and buildings are on the coast.",
        ]) + "</div>"))
    return "".join(T)


# ------------------------------------------------------------------ PART B: OCEAN
def part_b():
    T = []
    T.append('<p class="part-intro"><b>Why ocean currents matter:</b> they regulate <b>climate</b> (move and store heat, store gases) and '
             'control <b>marine productivity</b> (supply nutrients and oxygen). Ocean circulation is controlled by '
             '<b>wind, density, the position of the continents, and Coriolis</b>.</p>')

    T.append(topic(10, "Surface water vs deep water", "Describe the properties of surface and deep water.",
        "<p>The ocean is <b>layered by density</b>. A warm, light, wind-mixed <b>surface layer</b> sits on top of a cold, dense, dark "
        f"<b>deep layer</b>. In between is the {R('THERMOCLINE')}, where temperature drops fast (≈13°C at 200 m → ≈4°C at 1000 m). "
        "It acts like a barrier, so the two layers barely mix.</p>",
        side(table(["", "SURFACE layer", "DEEP layer"], [
                ["Temperature", "warm (varies)", "cold (≈4°C or less)"],
                ["Density", "low", "high"],
                ["Light", "sunlit → photosynthesis", "dark"],
                ["Nutrients", f"{R('LOW')} (plankton use them up)", f"{R('HIGH')} (from decaying material)"],
                ["Oxygen", "high (air + photosynthesis)", "lower"],
                ["Mixing", "mixed by wind + waves", "not mixed by wind"],
                ["Moved by", "wind · ~10% of ocean · fast", "density · ~90% · slow"],
             ], "cmp"),
             fig(D.d_thermo(), "<b>How to read it:</b> red line = temperature going down. It stays warm in the mixed layer, drops fast in the thermocline, then stays cold.")) +
        facts("Salinity (saltiness)", [
            "Measured in parts per thousand (ppt, ‰) — average seawater ≈ <b>35 ppt</b> (34.7).",
            "Salt comes from erosion of the continents + hydrothermal vents.",
            "<b>Highest</b> in the subtropics (23.5–35°): evaporation &gt; rain under the dry 30° highs. The Atlantic is the saltiest ocean.",
            "<b>Lowest</b> at the equator (lots of rain) and near big rivers (Amazon, Ganges).",
        ]), star=True))

    T.append(topic(11, "Recognize the major ocean currents", "Recognize the major oceanic currents.",
        f"<p>Surface currents form giant loops called <b>GYRES</b> — {R('clockwise in the NH, counterclockwise in the SH')}. "
        f"Every gyre has a {R('WARM current on its WEST side')} (flowing toward the pole) and a <b>COLD current on its EAST side</b> "
        "(flowing toward the equator).</p>",
        fig(D.d_world_gyres(), "<b>How to read it:</b> simplified world map (Pacific on the left, like the class map). "
            "Red = warm west-side current, black = cold east-side current. Arrows show the spin direction.", wide=True) +
        table(["Gyre", "WEST side — warm", "EAST side — cold"], [
            ["North Atlantic", "Gulf Stream", "Canary"],
            ["South Atlantic", "Brazil", "Benguela"],
            ["North Pacific", "Kuroshio", "California"],
            ["South Pacific", "East Australian", "Peru (Humboldt)"],
            ["Indian", "Agulhas", "West Australian"],
        ], "cmp") +
        facts("Also know", [
            "<b>North Atlantic Current</b> carries Gulf Stream water to Europe. <b>North Pacific Current</b> crosses the top of the N Pacific gyre.",
            "<b>North + South Equatorial Currents</b> flow west (pushed by the trades). The <b>Equatorial Countercurrent</b> flows east between them.",
            "<b>Antarctic Circumpolar Current</b> (West Wind Drift) flows east all the way around Antarctica — the biggest current.",
            "Cold currents coming down from the north: <b>Labrador</b> (off Canada), <b>Oyashio</b> (off Japan).",
            "Gulf Stream: first seen 1513 (Ponce de León), charted by Ben Franklin (1770s); flows ~300× more water than the Amazon.",
        ])))

    T.append(topic(12, "What forces drive surface currents and deep currents?", "Describe the forces causing surface and deep currents.",
        f"<p><b>Surface currents</b> are driven by {R('WIND')}, then turned by Coriolis and blocked by continents. "
        f"<b>Deep currents</b> are driven by {R('DENSITY')} differences — cold, salty water is heavy, so gravity pulls it down "
        "(called <b>thermohaline</b> circulation: thermo = temperature, haline = salt).</p>",
        table(["", "SURFACE currents", "DEEP currents (thermohaline)"], [
            ["Driven by", "wind", "density (temperature + salt) → gravity"],
            ["Share of ocean", "~10%", "~90%"],
            ["Speed", "fast", "slow"],
            ["Where", "above the thermocline", "below the thermocline"],
        ], "cmp") +
        side(steps("How wind moves water: Ekman transport", [
                "Wind drags the top layer of water.",
                f"Coriolis turns it: surface water moves {R('45° to the right')} of the wind (NH).",
                "Each layer drags the one below it, a bit slower and turned a bit more → the <b>Ekman spiral</b>.",
                f"The <b>net</b> movement of all that water = {R('90° to the RIGHT of the wind')} in the NH (90° LEFT in the SH). "
                "This is <b>Ekman transport</b>.",
             ]),
             fig(D.d_ekman(w=230, n=6), "<b>How to read it:</b> wind blows north; the water ends up moving east (90° right).")) +
        facts("How density is set (deep currents)", [
            "Density is \"fixed\" at the <b>surface</b> — then the water sinks and keeps that density.",
            "<b>Colder = denser</b> (water is cooled by contact with the cold air).",
            "<b>Saltier = denser.</b> Salt goes UP with evaporation and <b>sea-ice formation</b> (freezing leaves the salt behind). "
            "Salt goes DOWN with rain, rivers and melting ice.",
            "The coldest, saltiest water forms near the <b>poles</b> → that's where deep water sinks.",
        ]) + tip("Ekman transport is <b>90°</b>, not 45°. 45° is only the very top layer."), star=True))

    T.append(topic(13, "Why are western boundary currents fast and eastern ones slow?",
        "Explain why the speed of surface currents varies (eastern/western boundary currents).",
        f"<p>Currents on the <b>west side</b> of an ocean (Gulf Stream) are {R('fast, narrow, deep and warm')}. "
        "Currents on the <b>east side</b> (Canary) are slow, wide, shallow and cold. This is <b>western intensification</b>, caused by "
        f"{R('Earth rotating eastward')} and {R('Coriolis getting stronger away from the equator')}. Together they squeeze the "
        "gyre's flow against the west side, so the same water has to move faster through a narrow path.</p>",
        fig(D.d_gyre(), "<b>How to read it:</b> one NH gyre (North Atlantic). The \"hill\" of water in the middle is shoved west, "
            "so the Gulf Stream is squeezed into a thin, fast current, while the Canary Current spreads out wide and slow.", wide=True) +
        table(["", "WESTERN boundary", "EASTERN boundary"], [
            ["Speed", f"{R('FAST')}", "slow"],
            ["Width", "narrow", "wide"],
            ["Depth", "deep", "shallow"],
            ["Temperature", "warm (comes from the equator)", "cold (comes from high latitudes)"],
            ["Flow", "Gulf Stream ~55 Sv", "Canary ~16 Sv"],
            ["Examples", "Gulf Stream, Kuroshio", "Canary, California"],
        ], "cmp") +
        facts("Know these", ["Sv = Sverdrup = 1 million m³ of water per second.",
                             "Think of a river: where it's narrow the water runs fast; where it's wide it runs slow."]), star=True))

    T.append(topic(14, "How do surface currents affect weather?", "Explain how surface currents affect weather.",
        f"<p>Currents move <b>heat</b> from the equator toward the poles. {R('Warm currents')} warm the air and add moisture → "
        f"warm, humid, rainy coasts. {R('Cold currents')} cool the air and add little moisture → cool, foggy, dry coasts (even deserts).</p>",
        table(["", "WARM current", "COLD current"], [
            ["Where", "west side of a gyre → <b>east</b> coasts of continents", "east side of a gyre → <b>west</b> coasts"],
            ["Effect on air", "warm + humid, lots of evaporation", "cool, little evaporation, fog"],
            ["Weather", "rain; fuels storms + hurricanes", "dry — coastal deserts"],
            ["Examples", "Gulf Stream → humid US East Coast", "California Current → cool, foggy California; Peru + Benguela → Atacama + Namib deserts"],
        ], "cmp") +
        facts("Class example", [
            "The Gulf Stream + North Atlantic Current keep Western Europe mild. January average high/low: "
            f"<b>Newfoundland 30/16°F vs Ireland 46/37°F</b> — about the same latitude!",
            "Water's high heat capacity → coastal climates are milder than inland ones.",
        ])))

    T.append(topic(15, "How do deep and surface water mix? (upwelling + downwelling)",
        "Explain upwelling/downwelling. What does it mean for marine life and climate?",
        f"<p>{R('UPWELLING')} = cold, nutrient-rich deep water rises to the surface. {R('DOWNWELLING')} = surface water piles up and sinks. "
        "Both are mostly caused by <b>wind + Ekman transport</b> moving surface water <b>away</b> from an area (upwelling) or "
        "<b>toward</b> it (downwelling).</p>",
        fig(D.d_upwelling(), "<b>How to read it:</b> left = map view of a NH west coast (like California). Wind blows south along the coast; "
            "Ekman transport moves water 90° right = offshore. Right = side view: deep water rises to replace it.", wide=True) +
        table(["Where", "What happens", "Why"], [
            ["NH west coast, wind from the <b>north</b> (California)", "<b>UPWELLING</b>", "Ekman moves water offshore → deep water rises to replace it"],
            ["NH west coast, wind from the <b>south</b>", "<b>DOWNWELLING</b>", "Ekman moves water onshore → it piles up at the coast and sinks"],
            ["Equator", "<b>UPWELLING</b>", "Coriolis turns water right (north of equator) and left (south) → water spreads apart"],
            ["Around Antarctica", "<b>UPWELLING</b>", "winds push surface water apart"],
            ["Center of a gyre", "<b>DOWNWELLING</b>", "water converges and piles up"],
        ], "cmp") +
        '<div class="cols2">' +
        facts("Why it matters: marine life ★", [
            "Upwelling brings nutrients up into the sunlight → phytoplankton bloom → zooplankton → <b>fish</b>.",
            "Best fisheries: California, Peru, Canary, Benguela — all <b>eastern boundary currents</b>.",
            "Downwelling carries <b>oxygen</b> down to deep-sea life, but leaves the surface nutrient-poor → low productivity.",
        ]) +
        facts("Why it matters: climate", [
            "Upwelled cold water cools the coast → cool, foggy weather.",
            "Mixing moves heat and gases (O₂, CO₂) between the surface and the deep ocean.",
        ]) + "</div>", star=True))

    T.append(topic(16, "El Niño and La Niña — causes, effects, hurricanes",
        "Recognize and explain the causes/effects of El Niño/La Niña. How does this affect hurricane activity?",
        f"<p>It's all about the <b>trade winds</b> over the equatorial Pacific. <b>Normal:</b> trades push warm water west. "
        f"{R('El Niño: trades WEAKEN')} → warm water slides back east. {R('La Niña: trades get STRONGER')} → even more warm water piles up in the west.</p>",
        fig(D.d_enso(), "<b>How to read it:</b> each panel is a slice across the equatorial Pacific (Australia left, Peru right). "
            "The dashed line is the thermocline. Watch it tilt: normal = tilted, El Niño = flat, La Niña = very tilted.", wide=True) +
        table(["", "NORMAL", "EL NIÑO", "LA NIÑA"], [
            ["Trade winds", "blow east → west", f"{R('weak')} (or reverse)", f"{R('stronger')}"],
            ["Warm water", "piled up in the WEST", "spreads EAST toward Peru", "even more in the WEST"],
            ["Peru / E Pacific", "cold upwelling, great fishing, dry", "NO upwelling → fish die; heavy rain + floods", "strong upwelling, colder; very dry"],
            ["Indonesia / Australia", "rain", "DROUGHT", "heavy rain + floods"],
            ["US winter", "—", "north warmer, south wetter", "north colder, south drier"],
            [f"{R('Atlantic hurricanes')}", "—", f"{R('FEWER')}", f"{R('MORE')}"],
            ["E Pacific hurricanes", "—", "more", "fewer"],
        ], "cmp enso") +
        facts("Know these", [
            "<b>Why fewer Atlantic hurricanes in El Niño:</b> stronger vertical wind shear + trade winds and a more stable atmosphere. "
            "<b>La Niña</b> is the opposite: weaker shear + trades, less stable → more hurricanes.",
            "<b>ENSO</b> = El Niño–Southern Oscillation. The Southern Oscillation = the air-pressure seesaw between the west and east Pacific.",
            "<b>Anomaly</b> = difference from the average (e.g., an SST anomaly map shows where water is warmer or colder than normal).",
        ]), star=True))

    T.append(topic(17, "How does deep water circulation affect climate?", "Explain how deep water circulation affects climate.",
        f"<p>Near the poles, surface water becomes {R('cold and salty')} (sea ice leaves salt behind), so it gets dense and <b>sinks</b>. "
        "That sinking drives the global <b>conveyor belt</b>: warm water flows toward the poles at the surface, sinks, and returns as "
        f"cold deep water that slowly rises in the Indian and Pacific Oceans. {R('One loop takes ~1000 years.')} "
        "It carries <b>heat</b> toward the poles and carries <b>O₂ and CO₂</b> into the deep ocean.</p>",
        fig(D.d_conveyor(), "<b>How to read it:</b> red = warm, shallow return flow; black = cold, salty, deep flow. "
            "Water sinks at Greenland (NADW) and Antarctica (AABW) and rises in the Indian + Pacific.", wide=True) +
        steps("The conveyor path", [
            "Warm surface water flows north in the Atlantic (Gulf Stream) and gives off heat to the air → keeps Europe mild.",
            "Near Greenland it's now cold + salty → dense → <b>sinks</b> = NADW (North Atlantic Deep Water).",
            "It flows south along the Atlantic bottom and joins <b>AABW</b> (Antarctic Bottom Water — the densest water, formed in the Weddell Sea).",
            "It travels around Antarctica into the Indian and Pacific Oceans.",
            "It slowly warms and <b>rises</b>, then returns at the surface to the Atlantic.",
        ]) +
        facts("If the conveyor slows ★", [
            "Melting ice + more rain → <b>fresher</b> (less salty) water → less dense → can't sink → conveyor slows → less heat carried north → the North Atlantic and Europe <b>cool</b>.",
            "It happened before: the <b>Younger Dryas</b> (~12,900–11,500 years ago). Meltwater from glacial <b>Lake Agassiz</b> poured out → "
            "the NH went back to near-glacial cold. It ended fast: Greenland warmed <b>10°C in about a decade</b>.",
            "Today: the Atlantic overturning (AMOC) slowed in the 20th century → a \"cold blob\" south of Greenland cooled while the rest of Earth warmed.",
            "Pacific deep water: weakly layered, sluggish, very uniform below 2000 m.",
        ]), star=True))
    return "".join(T)


# ------------------------------------------------------------------ page + CSS
FONT = base64.b64encode((HERE / "fonts" / "SourceSans3.ttf").read_bytes()).decode()

CSS = """
@font-face { font-family: 'SS3'; src: url(data:font/ttf;base64,%FONT%) format('truetype'); font-weight: 200 900; }
@page { size: 8.5in 11in; margin: 0.5in 0.6in 0.62in 0.6in; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'SS3', 'Liberation Sans', Arial, 'DejaVu Sans', sans-serif; font-size: 14.2px; line-height: 1.36;
       color: #161616; margin: 0 auto; max-width: 7.3in; background: #fff; }
b { font-weight: 700; }
.r { color: #c8102e; font-weight: 700; }
.star { color: #c8102e; }
/* front */
.doc { border-bottom: 3px solid #161616; padding-bottom: 6px; margin-bottom: 8px; }
.doc-t { font-size: 27px; font-weight: 800; letter-spacing: -.2px; }
.doc-s { font-size: 14px; color: #444; }
.doc-i { font-size: 13px; margin-top: 4px; }
.howto { background: #fff6e0; border: 1.5px solid #e2b64a; border-radius: 7px; padding: 7px 10px; font-size: 13.4px; margin: 8px 0 10px; }
h2.sec { font-size: 19px; margin: 10px 0 4px; border-bottom: 2px solid #161616; padding-bottom: 2px; break-after: avoid; }
h2.sec.small { font-size: 16px; margin-top: 12px; }
.lead { margin: 4px 0 6px; }
.chain { margin: 0 0 8px; }
.c-box { border: 2px solid #1d4e89; background: #eef4fb; border-radius: 7px; padding: 5px 10px; break-inside: avoid; }
.c-box.ocn-b { border-color: #0b6e69; background: #e8f5f3; }
.c-side { font-size: 13.2px; margin-top: 2px; padding-left: 6px; color: #222; }
.c-arr { text-align: center; font-size: 17px; line-height: 1.05; color: #555; font-weight: 700; }
.tn { color: #666; font-size: 12.3px; white-space: nowrap; }
.rules { border: 2px solid #c8102e; border-radius: 7px; padding: 6px 10px 5px; break-inside: avoid; }
.rules-t { font-weight: 800; color: #c8102e; font-size: 15px; }
.rules ol { margin: 2px 0 0; padding-left: 20px; }
.abbr { font-size: 12.3px; color: #333; margin: 7px 0 0; }
/* cheat page */
.cheat { break-before: page; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 4px; break-inside: avoid; font-size: 13.4px; line-height: 1.28; }
th, td { border: 1px solid #b9b9b9; padding: 3px 6px; vertical-align: top; text-align: left; }
th { background: #efefef; font-weight: 700; }
.cheat-t td.ck { font-weight: 700; width: 27%; white-space: nowrap; }
.cheat-t { font-size: 13.2px; }
.toc { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.toc table { font-size: 13px; margin: 2px 0; }
.toc td.cn { width: 26px; font-weight: 700; text-align: center; }
.toc td.cp { width: 68px; color: #777; white-space: nowrap; }
/* parts */
.part { break-before: page; }
.atm { --acc: #1d4e89; --tint: #eaf1fa; }
.ocn { --acc: #0b6e69; --tint: #e5f3f1; }
.part-h { background: var(--acc); color: #fff; padding: 6px 12px; font-size: 21px; font-weight: 800; border-radius: 7px; letter-spacing: .3px; }
.part-h span { font-weight: 400; font-size: 15px; opacity: .92; }
.part-intro { margin: 7px 0 2px; }
.topic { margin: 16px 0 6px; }
.keep { break-inside: avoid; }
.t-head { display: flex; gap: 9px; align-items: flex-start; border-bottom: 2px solid var(--acc); padding-bottom: 3px; }
.num { background: var(--acc); color: #fff; font-weight: 800; border-radius: 6px; min-width: 30px; height: 30px;
       display: flex; align-items: center; justify-content: center; font-size: 17px; flex: none; margin-top: 1px; }
.q { font-size: 17.5px; font-weight: 800; line-height: 1.2; }
.rg { font-size: 12px; color: #5a5a5a; font-style: italic; }
.answer { background: var(--tint); border-left: 5px solid var(--acc); border-radius: 0 6px 6px 0; padding: 5px 10px 6px; margin: 7px 0 4px; }
.answer .lbl { font-size: 11px; font-weight: 800; letter-spacing: .09em; color: var(--acc); }
.answer p { margin: 1px 0 0; font-size: 14.6px; }
h4 { font-size: 12.6px; text-transform: uppercase; letter-spacing: .07em; color: var(--acc); margin: 8px 0 2px; break-after: avoid; }
.blk { break-inside: avoid; }
ol, ul { margin: 0; padding-left: 21px; }
li { margin: 1.5px 0; }
.two { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: start; }
.two-r { padding-top: 6px; }
.cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
figure { margin: 6px 0 2px; break-inside: avoid; }
figure svg { display: block; margin: 0 auto; }
figure.wide { margin-top: 8px; }
figcaption { font-size: 12.2px; color: #3c3c3c; margin-top: 3px; line-height: 1.3; }
.two-r figcaption { max-width: 330px; }
table.cmp th:first-child { width: auto; }
table.enso td:first-child, table.enso th:first-child { width: 21%; }
.tip { border: 1.5px solid #c8102e; border-radius: 6px; padding: 4px 9px; margin: 8px 0 2px; break-inside: avoid; font-size: 13.8px; }
.tip .lbl { color: #c8102e; }
.dia text { font-family: 'SS3', 'Liberation Sans', Arial, sans-serif; }
@media screen { body { padding: 20px 0 40px; } }
""".replace("%FONT%", FONT)


def build():
    body = (FRONT + cheat_page() +
            '<section class="part atm"><div class="part-h">PART A · THE ATMOSPHERE <span>(topics 1–9)</span></div>' + part_a() + "</section>" +
            '<section class="part ocn"><div class="part-h">PART B · OCEAN CIRCULATION <span>(topics 10–17)</span></div>' + part_b() + "</section>")
    doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>GEOL 211 Exam 2 Study Guide</title><style>{CSS}</style></head><body>{body}</body></html>')
    OUT.write_text(doc, encoding="utf-8")
    print("wrote", OUT, f"{len(doc)//1024} KB")


if __name__ == "__main__":
    build()
