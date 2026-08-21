"""Vial-specific mix and syringe math for TrueHold Wellness stock.

Every number is derived from: vial milligrams ÷ bacteriostatic water milliliters
on a U-100 insulin syringe (100 units = 1.00 mL; a 0.5 mL syringe holds 50 units).
`verify_protocols()` must pass before a sheet is written.
"""

from __future__ import annotations

from typing import Any

# U-100 insulin: 100 units == 1.00 mL. A 0.5 mL syringe is 50 units full.
UNITS_PER_ML = 100
HALF_ML_UNITS = 50


def mg_per_ml(vial_mg: float, bac_ml: float) -> float:
    if bac_ml <= 0:
        raise ValueError("bacteriostatic water volume must be positive")
    return vial_mg / bac_ml


def units_for_dose_mg(dose_mg: float, vial_mg: float, bac_ml: float) -> float:
    return dose_mg / mg_per_ml(vial_mg, bac_ml) * UNITS_PER_ML


def ml_for_units(units: float) -> float:
    return units / UNITS_PER_ML


def fits_half_ml(units: float) -> bool:
    return units <= HALF_ML_UNITS + 1e-9


def doses_from_vial(units: float, bac_ml: float) -> float:
    return bac_ml / ml_for_units(units)


def syringe_note(units: float) -> str:
    if fits_half_ml(units):
        if abs(units - HALF_ML_UNITS) < 1e-9:
            return "Fill the 0.5 mL (50-unit) U-100 syringe to the 50 mark."
        return f"On a 0.5 mL (50-unit) U-100 syringe, draw to the {int(units) if units == int(units) else units} mark."
    extra = units - HALF_ML_UNITS
    return (
        f"This draw is {units:.0f} units ({ml_for_units(units):.2f} mL) — more than a 0.5 mL syringe holds. "
        f"Use a 1 mL (100-unit) syringe, or two nearby 0.5 mL draws (50 + {extra:.0f})."
    )


def _step(when: str, units: float, freq: str, vial_mg: float, bac_ml: float) -> dict[str, Any]:
    dose_mg = mg_per_ml(vial_mg, bac_ml) * ml_for_units(units)
    return {
        "when": when,
        "units": units,
        "mg": round(dose_mg, 4),
        "ml": round(ml_for_units(units), 4),
        "freq": freq,
        "half_ml": fits_half_ml(units),
        "syringe": syringe_note(units),
    }


def _protocol(
    *,
    sku: str,
    vial_mg: float,
    bac_ml: float,
    vial_label: str,
    route: str,
    cadence: str,
    steps: list[tuple[str, float, str]],
    notes: list[str],
    source: str,
) -> dict[str, Any]:
    built = [_step(when, units, freq, vial_mg, bac_ml) for when, units, freq in steps]
    return {
        "sku": sku,
        "vial_mg": vial_mg,
        "bac_ml": bac_ml,
        "mg_per_ml": mg_per_ml(vial_mg, bac_ml),
        "mcg_per_unit": mg_per_ml(vial_mg, bac_ml) * 1000 / UNITS_PER_ML,
        "vial_label": vial_label,
        "route": route,
        "cadence": cadence,
        "steps": built,
        "notes": notes,
        "source": source,
        "start_units": built[0]["units"],
        "start_mg": built[0]["mg"],
        "start_ml": built[0]["ml"],
    }


# TrueHold stock only. Tirzepatide and NAD+ keep the locked starting protocols.
PROTOCOLS: dict[str, dict[str, Any]] = {
    "tirzepatide": _protocol(
        sku="tirzepatide",
        vial_mg=20,
        bac_ml=2.0,
        vial_label="20 mg powder in a standard ~3 mL glass vial",
        route="Subcutaneous (belly or back of upper arm)",
        cadence="Once weekly. Stay on each level at least 4 weeks before going up.",
        steps=[
            ("Weeks 1–4 (start here)", 25, "Once per week"),
            ("Weeks 5–8 (if tolerated)", 50, "Once per week"),
            ("Weeks 9–12 (optional)", 75, "Once per week"),
            ("Week 13+ (optional)", 100, "Once per week"),
        ],
        notes=[
            "Use 2 mL bacteriostatic water only — this vial cannot hold more. Do not pour into another container.",
            "25 units = 2.5 mg, which is the same milligram start used on FDA-approved tirzepatide pens. This sheet is for TrueHold's 20 mg research vial, not Mounjaro or Zepbound.",
            "At 25 units/week one mixed vial lasts about 8 weekly doses.",
        ],
        source="TrueHold Standard Starting Protocol locked to the 20 mg vial (2 mL BAC, 25/50/75/100 units weekly).",
    ),
    "retatrutide": _protocol(
        sku="retatrutide",
        vial_mg=20,
        bac_ml=2.0,
        vial_label="20 mg powder in a standard ~3 mL glass vial",
        route="Subcutaneous (belly or back of upper arm)",
        cadence="Once weekly. Stay on each level at least 4 weeks before going up.",
        steps=[
            ("Weeks 1–4 (start here)", 20, "Once per week"),
            ("Weeks 5–8 (if tolerated)", 40, "Once per week"),
            ("Weeks 9–12 (optional)", 60, "Once per week"),
            ("Week 13+ (optional, trial-range)", 90, "Once per week"),
        ],
        notes=[
            "Use 2 mL bacteriostatic water only — this vial cannot hold more.",
            "20 units = 2.0 mg once weekly, matching the TRIUMPH Phase 3 start (2 mg, then step up every 4 weeks).",
            "Lilly trial maintenance doses go to 9–12 mg. 12 mg would be 120 units (two syringes) and is not a TrueHold start.",
            "At 20 units/week one mixed vial lasts 10 weekly doses.",
        ],
        source="Same 20 mg / 2 mL mix as TrueHold tirzepatide. Milligram steps follow published TRIUMPH start (2 mg weekly), not an invented scale.",
    ),
    "nad": _protocol(
        sku="nad",
        vial_mg=1000,
        bac_ml=5.0,
        vial_label="1000 mg powder in a larger ~5 mL glass vial",
        route="Subcutaneous (belly or upper arm)",
        cadence="Twice per week (about every 3–4 days). Not a daily shot.",
        steps=[
            ("Weeks 1–2 (start here)", 50, "Twice per week"),
            ("Weeks 3+ (if tolerated)", 75, "Twice per week"),
            ("Optional advance", 100, "Twice per week"),
            ("Optional advance", 125, "Twice per week"),
        ],
        notes=[
            "Draw 5 mL of BAC — this is the most this vial can hold. Mix and store in this vial only.",
            "50 units = 0.50 mL = 100 mg. That fill is exactly one full 0.5 mL syringe.",
            "125 units = two syringes in one session: 100 + 25 (two nearby sites).",
            "At 50 units twice per week one mixed vial lasts about 5 weeks.",
        ],
        source="TrueHold Standard Starting Protocol locked to the 1000 mg NAD+ vial (5 mL BAC, 50-unit start twice weekly).",
    ),
    "semax": _protocol(
        sku="semax",
        vial_mg=10,
        bac_ml=2.0,
        vial_label="10 mg powder in a standard ~3 mL glass vial",
        route="Intranasal drops (clinical Semax is a nasal medicine in Russia). Draw, then drip — do not inject this starting protocol.",
        cadence="Once or twice daily for 10–14 days, then take a break of at least 7 days.",
        steps=[
            ("Days 1–10 (start here)", 6, "Once in the morning"),
            ("If tolerated, still in the 10-day block", 6, "Morning and early afternoon (not late evening)"),
            ("Optional upper end of the cognitive range", 12, "Once in the morning"),
        ],
        notes=[
            "10 mg in 2 mL → 5 mg/mL. 1 unit = 50 mcg. 6 units = 300 mcg, inside the Russian 0.1% cognitive range (about 200–900 mcg/day).",
            "Drip half the draw into each nostril while seated. Do not inject Semax on this sheet — published human use is nasal.",
            "At 6 units once daily, one mixed vial lasts about 33 days; TrueHold still cycles 10–14 days on, then a break.",
        ],
        source="Russian 0.1% Semax cognitive range mapped onto TrueHold's 10 mg vial with 2 mL BAC so unit marks are round.",
    ),
    "mots-c": _protocol(
        sku="mots-c",
        vial_mg=20,
        bac_ml=2.0,
        vial_label="20 mg powder in a standard ~3 mL glass vial",
        route="Subcutaneous (belly or upper arm)",
        cadence="Three days per week (for example Mon/Wed/Fri) for 4–8 weeks, then a 2–4 week break.",
        steps=[
            ("Weeks 1–2 (start here)", 25, "Three days per week"),
            ("Weeks 3–8 (if tolerated)", 50, "Three days per week"),
        ],
        notes=[
            "20 mg in 2 mL → 10 mg/mL. 25 units = 2.5 mg; 50 units = 5.0 mg (a full 0.5 mL syringe).",
            "5–10 mg three times weekly is the range scaled from published mouse work (Lee et al. ~0.5 mg/kg) and used in research-handling writeups. There is no FDA-approved human dose.",
            "At 25 units three times weekly one mixed vial lasts a little over 2 weeks.",
        ],
        source="20 mg TrueHold vial / 2 mL BAC. Starting 2.5 mg and step to 5 mg stay inside the commonly cited 5–10 mg research window without emptying the vial in two shots.",
    ),
    "ss-31": _protocol(
        sku="ss-31",
        vial_mg=10,
        bac_ml=2.0,
        vial_label="10 mg powder in a standard ~3 mL glass vial",
        route="Subcutaneous (belly or upper arm)",
        cadence="Daily for 5 days, then 2 days off, for 4 weeks, then a break. Not the Barth-syndrome pharmaceutical dose.",
        steps=[
            ("Weeks 1–2 (start here)", 20, "Once daily, 5 days on / 2 days off"),
            ("Weeks 3–4 (if tolerated)", 40, "Once daily, 5 days on / 2 days off"),
        ],
        notes=[
            "10 mg in 2 mL → 5 mg/mL. 20 units = 1.0 mg; 40 units = 2.0 mg. Both fit a 0.5 mL syringe.",
            "FDA-approved Forzinity (elamipretide) is 40 mg subcutaneous daily for Barth syndrome in patients ≥30 kg. That is a different product. This 10 mg research vial cannot supply a 40 mg daily pharmaceutical dose.",
            "At 20 units five days per week one mixed vial lasts 2 weeks.",
        ],
        source="TrueHold 10 mg vial / 2 mL BAC. Conservative research-vial start (1–2 mg), explicitly not Forzinity 40 mg.",
    ),
    "ghk-cu": _protocol(
        sku="ghk-cu",
        vial_mg=100,
        bac_ml=2.0,
        vial_label="100 mg powder in a standard ~3 mL glass vial",
        route="Subcutaneous (belly, love-handle, or upper arm). Solution may look faintly blue-green from copper — that is expected.",
        cadence="Once daily, 5 days on / 2 days off, for 8–12 weeks, then a break.",
        steps=[
            ("Weeks 1–4 (start here)", 2, "Once daily, 5 days on / 2 days off"),
            ("Weeks 5–12 (if tolerated)", 4, "Once daily, 5 days on / 2 days off"),
        ],
        notes=[
            "100 mg in 2 mL → 50 mg/mL. 1 unit = 0.50 mg. 2 units = 1.0 mg; 4 units = 2.0 mg — the commonly cited injectable research window.",
            "Use a 0.5 mL U-100 syringe with 1-unit marks. Draw slowly to the 2 (then 4) mark. Do not confuse this with a 50-unit fill.",
            "At 2 units five days per week one mixed vial lasts about 20 weeks; still cycle off after 8–12 weeks.",
            "Do not use if you have Wilson disease or another copper-handling disorder.",
        ],
        source="TrueHold 100 mg vial / 2 mL BAC so 2 units = 1 mg, matching the 1–2 mg daily research-handling range.",
    ),
    "klow": _protocol(
        sku="klow",
        vial_mg=80,
        bac_ml=2.0,
        vial_label="80 mg KLOW blend powder in a standard ~3 mL glass vial",
        route="Subcutaneous (belly or love-handle). Faint blue-green tint from GHK-Cu is expected.",
        cadence="Once daily, 5 days on / 2 days off, for 8–12 weeks, then a 4-week break.",
        steps=[
            ("Weeks 1–4 (start here)", 10, "Once daily, 5 days on / 2 days off"),
            ("Weeks 5–12 (if tolerated)", 10, "Once daily, 5 days on / 2 days off (same draw; do not double)"),
        ],
        notes=[
            "80 mg in 2 mL → 40 mg/mL total blend. 10 units = 0.10 mL = 4.0 mg total.",
            "Standard 80 mg KLOW split used in US research catalogs: GHK-Cu 50 mg + BPC-157 10 mg + TB-500 10 mg + KPV 10 mg. A 10-unit draw then delivers about 2.5 mg GHK-Cu and 0.50 mg of each of the other three — each piece sits in its usual research window at once.",
            "If your vial's COA lists a different milligram split, stop and call the team before mixing.",
            "At 10 units five days per week one mixed vial lasts 4 weeks.",
        ],
        source="80 mg TrueHold vial / 2 mL BAC. 10 units = 4 mg total blend, the documented 80 mg KLOW handling draw.",
    ),
}


def verify_protocols(protocols: dict[str, dict[str, Any]] | None = None) -> None:
    """Raise if reconstitution and syringe numbers disagree."""
    catalog = protocols or PROTOCOLS
    expected_vials = {
        "tirzepatide": 20,
        "retatrutide": 20,
        "semax": 10,
        "nad": 1000,
        "klow": 80,
        "mots-c": 20,
        "ss-31": 10,
        "ghk-cu": 100,
    }
    for sku, spec in catalog.items():
        vial_mg = float(spec["vial_mg"])
        bac_ml = float(spec["bac_ml"])
        if sku in expected_vials and vial_mg != expected_vials[sku]:
            raise AssertionError(f"{sku}: vial_mg {vial_mg} does not match stock {expected_vials[sku]} mg")
        conc = mg_per_ml(vial_mg, bac_ml)
        if abs(conc - spec["mg_per_ml"]) > 1e-9:
            raise AssertionError(f"{sku}: stored mg/mL {spec['mg_per_ml']} != {conc}")
        if bac_ml > 5.01:
            raise AssertionError(f"{sku}: BAC volume {bac_ml} mL exceeds the largest TrueHold vial (NAD+ 5 mL)")
        if sku != "nad" and bac_ml > 2.01:
            raise AssertionError(f"{sku}: standard peptide vials hold 2 mL BAC, not {bac_ml}")
        start = spec["steps"][0]
        if not start["half_ml"]:
            raise AssertionError(f"{sku}: starting draw {start['units']} units does not fit a 0.5 mL syringe")
        for step in spec["steps"]:
            recomputed = units_for_dose_mg(step["mg"], vial_mg, bac_ml)
            if abs(recomputed - step["units"]) > 0.05:
                raise AssertionError(
                    f"{sku}: {step['when']} {step['mg']} mg → {recomputed} units, sheet says {step['units']}"
                )
            if abs(step["ml"] - ml_for_units(step["units"])) > 1e-9:
                raise AssertionError(f"{sku}: mL mismatch on {step['when']}")
            if step["half_ml"] != fits_half_ml(step["units"]):
                raise AssertionError(f"{sku}: 0.5 mL flag wrong on {step['when']}")
        # Locked TrueHold numbers that must never drift.
        if sku == "tirzepatide":
            units = [s["units"] for s in spec["steps"]]
            if units != [25, 50, 75, 100] or spec["bac_ml"] != 2.0:
                raise AssertionError("tirzepatide locked protocol drifted")
            if abs(spec["steps"][0]["mg"] - 2.5) > 1e-9:
                raise AssertionError("tirzepatide start must be 2.5 mg (25 units in 2 mL / 20 mg)")
        if sku == "nad":
            if spec["bac_ml"] != 5.0 or spec["steps"][0]["units"] != 50:
                raise AssertionError("NAD+ locked protocol drifted")
            if abs(spec["steps"][0]["mg"] - 100) > 1e-9:
                raise AssertionError("NAD+ 50 units in 5 mL / 1000 mg must be 100 mg")


verify_protocols()
