#!/usr/bin/env python3
"""GEOL 211 Exam 2 — answers to each review-guide bullet, backed by the class slides."""
from pathlib import Path

import diagrams as D
from guide import CSS as BASE_CSS

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "geol211_exam2_review_answers.html"
R = lambda s: f'<span class="r">{s}</span>'


def q(num, guide, bullets, fig=None, cap=""):
    lis = "".join(b if b.startswith("<table") else f"<li>{b}</li>" for b in bullets)
    f = ""
    if fig:
        f = f'<figure>{fig}{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'
    return (f'<article class="qa"><div class="keep"><h3><span class="num">{num}</span>{guide}</h3>'
            f'<ul>{lis}</ul></div>{f}</article>')


def table(head, rows):
    th = "".join(f"<th>{h}</th>" for h in head)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


ATM = [
    q(1, "Explain how/why air density changes.", [
        "Air density is controlled by <b>temperature</b> and <b>moisture content</b>.",
        f"Warm air: molecules spread out → {R('less dense → rises')}. Cold air: molecules packed together → {R('denser → sinks')}.",
        f"Water vapor (H₂O) is lighter than the N₂ (78% of air) and O₂ (21%) it replaces → {R('humid air is LESS dense than dry air')}.",
        "Densest air on Earth = the <b>poles</b> (cold + dry).",
    ]),
    q(2, "Explain why regions of high/low density develop. Identify areas of high/low pressure. Describe the weather with each.", [
        "The Sun heats Earth <b>unevenly</b> (differential heating): the equator gets direct sunlight and is hot; the poles get spread-out sunlight and are cold.",
        f"Warm air rises → {R('LOW pressure')}: rising air cools, water vapor condenses → <b>clouds, rain, storms</b>.",
        f"Cold air sinks → {R('HIGH pressure')}: sinking air warms → <b>clear, dry</b> weather.",
        "Air flows from <b>high → low</b> pressure = wind.",
        f"Where: {R('LOW at 0° and 60°')} · {R('HIGH at 30° and 90°')}.",
    ]),
    q(3, "Draw the global atmospheric circulation pattern. Label high/low pressure, the ITCZ, and high/low precipitation.", [
        "3 cells per hemisphere: <b>Hadley</b> (0–30°), <b>Ferrel</b> (30–60°), <b>Polar</b> (60–90°).",
        f"{R('0° = LOW = ITCZ')} (trade winds meet, air rises) → <b>heavy rain</b>. 30° = HIGH → <b>dry, deserts</b>. 60° = LOW → <b>wet</b>. 90° = HIGH → <b>cold, dry</b>.",
        "Surface winds: <b>trade winds</b> (0–30°), <b>westerlies</b> (30–60°), <b>polar easterlies</b> (60–90°).",
    ], D.d_global(), "Loops = cells. Arrows = surface winds, from H toward L, bent right in the NH and left in the SH."),
    q(4, "Explain why the Coriolis Force exists and what the result is.", [
        "<b>Why:</b> Earth rotates. The equator travels farther each day (~40,000 km) than higher latitudes (~20,000 km at 60°), so it moves faster. "
        "A moving object keeps its original speed, so its path appears to curve.",
        f"<b>Result:</b> objects are deflected {R('to the RIGHT in the Northern Hemisphere and to the LEFT in the Southern Hemisphere')}.",
        "No Coriolis at the equator; it increases with latitude, speed and mass; it only matters for large motions (tens of km or more).",
        "It does <b>not</b> cause wind — it changes the wind's <b>direction</b>.",
    ]),
    q(5, "Explain the development of monsoons.", [
        f"Land heats up and cools down {R('faster than water')}.",
        f"<b>Summer:</b> land is hotter → air rises over land (LOW) → moist ocean air flows onto land → {R('heavy rain (wet season)')}.",
        "<b>Winter:</b> land is colder → air sinks over land (HIGH) → dry air flows from land to sea → <b>dry season</b>.",
        "Monsoons follow the ITCZ: June–July it's north over India (rain there); Dec–Jan it's south (rain in Darwin, Australia).",
    ]),
    q(6, "Explain the development of land/sea breeze.", [
        "Same cause as monsoons (land heats/cools faster than water), but on a <b>daily</b> cycle.",
        f"<b>Day:</b> land warmer → air rises over land → cool air flows from sea to land = {R('SEA BREEZE')}.",
        f"<b>Night:</b> land cooler → air sinks over land → air flows from land to sea = {R('LAND BREEZE')}.",
    ]),
    q(7, "List and describe the conditions necessary for a major hurricane to develop.", [
        f"{R('Warm water (&gt;27°C)')} — supplies the heat and moisture (fuel).",
        f"{R('Low-pressure system')} — air flows in and rises.",
        f"{R('Warm air with high water vapor')} — when vapor condenses it releases <b>latent heat</b>, which powers the storm.",
        f"{R('Low wind shear (&lt;20 knots)')} — keeps the storm upright; strong shear tears it apart.",
        f"{R('Strong Coriolis')} — makes it spin (cyclonic flow: counterclockwise in NH), so no hurricanes at the equator.",
    ]),
    q(8, "List and describe the risks associated with hurricanes.", [
        f"Hazards: <b>waves, wind, rain, flooding, landslides, {R('storm surge')}</b>. Rain flooding can reach far inland (Ivan → Asheville NC, 2004).",
        "<b>Storm surge</b> is caused by strong <b>onshore winds</b> pushing water onto the coast; worst at high tide (Sandy 2012).",
        "Surge is higher with: stronger <b>wind speed</b> · bigger <b>storm radius</b> · <b>forward speed</b> (fast = higher surge, slow = longer flooding) · "
        "<b>perpendicular</b> (head-on) approach · <b>wide, gently sloping continental shelf</b> · <b>coastline shape</b> that funnels water.",
    ]),
    q(9, "Predict the path of a hurricane based on the location of high/low pressure systems.", [
        f"Air flows from high to low, so hurricanes are {R('pushed around HIGH pressure')} (clockwise around a NH high) and {R('pulled toward LOW pressure')}.",
        "Atlantic: trade winds push it <b>west</b> → it curves <b>north</b> around the west side of the Bermuda High → westerlies push it <b>northeast</b>.",
        "High extends far west → storm keeps going west (Florida/Gulf). High farther east → storm turns north sooner (East Coast or out to sea).",
    ], D.d_track()),
    q(10, "Explain expected changes in hurricane activity due to climate change and trends observed over the last 100 years.", [
        f"<b>Expected:</b> warmer water = more fuel → {R('stronger, wetter storms')}; higher sea level → <b>higher storm surge</b>. Not necessarily more storms.",
        "<b>Last 100 years:</b> no clear trend in the <b>number</b> of hurricanes (older records missed storms), but a larger share of <b>strong</b> (Cat 3–5) storms, more rain, and more damage as coasts are built up.",
    ]),
]

OCN = [
    q(11, "Describe the properties of surface and deep water.", [
        table(["", "Surface layer", "Deep layer"], [
            ["Temperature", "warm", "cold (~4°C)"],
            ["Density", "low", "high"],
            ["Moved by", "wind · 10% of ocean · fast", "density/gravity · 90% · slow"],
            ["Mixing", "mixed by wind", "not mixed by wind"],
            ["Nutrients", "low", "high"],
        ]),
        f"Between them is the {R('thermocline')}: temperature drops fast from ~13°C at 200 m to ~4°C at 1000 m, so the layers don't mix.",
        "Salinity ≈ 35 ppt; highest in the subtropics (23.5–35°, evaporation) and lowest near rivers and rainy areas.",
    ]),
    q(12, "Recognize the major oceanic currents.", [
        f"Currents form <b>gyres</b>: {R('clockwise in the NH, counterclockwise in the SH')}. The <b>west</b> side of each gyre is warm; the <b>east</b> side is cold.",
        table(["Gyre", "West side (warm)", "East side (cold)"], [
            ["N Atlantic", "Gulf Stream", "Canary"], ["S Atlantic", "Brazil", "Benguela"],
            ["N Pacific", "Kuroshio", "California"], ["S Pacific", "East Australian", "Peru"],
            ["Indian", "Agulhas", "West Australian"]]),
        "Also: Antarctic Circumpolar Current flows east around Antarctica.",
    ], D.d_world_gyres()),
    q(13, "Describe the forces causing surface and deep currents.", [
        "Ocean circulation is controlled by <b>wind, density, the position of the continents, and Coriolis</b>.",
        f"<b>Surface currents</b> = {R('driven by WIND')} (10% of ocean, fast). Coriolis turns them: <b>Ekman transport</b> moves water {R('90° to the right of the wind')} in the NH (left in SH).",
        f"<b>Deep currents</b> (thermohaline) = {R('driven by DENSITY')} (temperature + salinity) and gravity (90% of ocean, slow).",
        "Density is set at the surface: <b>temperature</b> (cooling by the air) and <b>salinity</b> (evaporation or sea-ice formation raise it; rain lowers it). Cold + salty water sinks.",
    ]),
    q(14, "Explain why the speed of surface currents varies (eastern/western boundary currents).", [
        f"Western boundary currents (Gulf Stream) are {R('fast, narrow, deep, warm')}. Eastern boundary currents (Canary) are <b>slow, wide, shallow, cold</b>.",
        f"<b>Why:</b> the {R('eastward rotation of Earth')} and {R('Coriolis increasing with distance from the equator')} compress the western boundary current, so its speed increases.",
    ]),
    q(15, "Explain how surface currents affect weather.", [
        "Currents <b>transport heat</b> from the equator toward the poles.",
        f"Warm currents warm the air → {R('milder, wetter climates')}. Ex: Gulf Stream keeps Europe warm — January avg: <b>Newfoundland 30/16°F vs Ireland 46/37°F</b> (same latitude).",
        "Cold currents cool the air → cooler, drier coasts.",
    ]),
    q(16, "Explain how deep and surface water mix (upwelling/downwelling). Implications for marine life and climate?", [
        f"{R('Upwelling')} = deep, cold, nutrient-rich water rises to the surface. {R('Downwelling')} = surface water sinks.",
        "<b>Coastal:</b> wind along the coast + Ekman transport pushes surface water <b>offshore</b> → deep water rises (upwelling); pushed <b>onshore</b> → water piles up and sinks (downwelling).",
        "<b>Equatorial</b> upwelling (water moves apart at the equator) and <b>Southern Ocean</b> upwelling (around Antarctica).",
        f"<b>Marine life:</b> upwelling brings {R('nutrients')} to the sunlit surface → phytoplankton → rich fisheries. Downwelling carries <b>oxygen</b> down to deep water.",
        "<b>Climate:</b> mixing moves heat and gases (O₂, CO₂) between the surface and deep ocean; upwelled cold water cools the coast.",
    ]),
    q(17, "Recognize and explain the causes/effects of El Niño/La Niña. How does this affect hurricane activity?", [
        "<b>Normal:</b> trade winds push warm water west → warm and rainy in Indonesia/Australia; upwelling of cold water off Peru.",
        f"<b>El Niño:</b> {R('trade winds weaken')} → warm water moves east → upwelling off Peru stops (fish decline); rain/floods in Peru, drought in Australia.",
        f"<b>La Niña:</b> {R('trade winds strengthen')} → even more warm water west, colder east Pacific, stronger upwelling.",
        f"<b>Hurricanes:</b> El Niño → {R('fewer Atlantic hurricanes')} (more wind shear), more Pacific. La Niña → {R('more Atlantic hurricanes')} (less shear), fewer Pacific.",
        "Anomaly = difference from the average (how SST maps show El Niño/La Niña).",
    ], D.d_enso(), "Dashed line = thermocline. Normal = tilted, El Niño = flat, La Niña = very tilted."),
    q(18, "Explain how deep water circulation affects climate.", [
        "Deep water forms near the poles where water is <b>cold and salty</b> (sea ice leaves salt behind) → dense → sinks: "
        "<b>North Atlantic Deep Water</b> (near Greenland) and <b>Antarctic Bottom Water</b>.",
        f"This drives the {R('conveyor belt')}: warm surface water flows to the North Atlantic, sinks, travels through the deep Atlantic, Indian and Pacific, rises, and returns.",
        f"It {R('transports heat')} toward the poles (keeps Europe mild) and stores gases (CO₂, O₂) in the deep ocean.",
        f"If it slows (fresh meltwater makes water less dense so it can't sink) → {R('abrupt cooling')}. Ex: <b>Younger Dryas</b> — Lake Agassiz meltwater → near-glacial cold; "
        "it ended with Greenland warming 10°C in a decade. The Atlantic overturning slowed in the 20th century.",
    ]),
]

CSS = BASE_CSS + """
body { font-size: 14px; }
.top { border-bottom: 3px solid #161616; padding-bottom: 4px; margin-bottom: 4px; }
.top .t { font-size: 24px; font-weight: 800; }
.top .s { font-size: 12.5px; color: #444; }
.part-h { margin-top: 10px; font-size: 18px; padding: 4px 10px; }
.part.atm { break-before: auto; }
.part.ocn { break-before: page; }
.qa ul > table { margin-left: -19px; width: calc(100% + 19px); }
.qa { margin: 10px 0 2px; }
.qa h3 { font-size: 15px; margin: 0 0 3px; display: flex; gap: 8px; align-items: flex-start; line-height: 1.25;
         border-bottom: 1.5px solid var(--acc); padding-bottom: 3px; }
.qa .num { min-width: 24px; height: 24px; font-size: 13px; border-radius: 5px; margin-top: 0; }
.qa ul { padding-left: 19px; }
.qa li { margin: 2px 0; }
.qa table { margin: 4px 0; font-size: 13px; }
figure { margin: 4px 0 0; }
figure svg { width: 560px; height: auto; }
figcaption { text-align: center; }
"""


def build():
    body = ('<div class="top"><div class="t">GEOL 211 · Exam 2 — Review Guide Answers</div>'
            '<div class="s">Every review-guide bullet, in order, answered from the class slides. '
            'Red = the key part of the answer. Also review your class assignments.</div></div>'
            '<section class="part atm"><div class="part-h">ATMOSPHERIC CIRCULATION</div>' + "".join(ATM) + "</section>"
            '<section class="part ocn"><div class="part-h">OCEAN CIRCULATION</div>' + "".join(OCN) + "</section>")
    OUT.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                   '<meta name="viewport" content="width=device-width, initial-scale=1">'
                   f'<title>GEOL 211 Exam 2 Review Answers</title><style>{CSS}</style></head><body>{body}</body></html>',
                   encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    build()
