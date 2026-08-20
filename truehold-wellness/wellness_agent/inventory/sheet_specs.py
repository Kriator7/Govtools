"""Segmented science copy for TrueHold Wellness information sheets.

Facts are tied to the live vial sizes in catalog.json / protocol.py.
FDA status distinguishes the molecule (where a drug exists) from TrueHold's lyophilized research vial.
"""

from __future__ import annotations

from wellness_agent.inventory.protocol import PROTOCOLS

COMMON_FULFILLMENT = [
    "Prep and local delivery: Las Vegas residents only.",
    "Shipping: dry (lyophilized) vials only — we do not ship mixed liquid.",
    "Interest orders are confirmed by phone before payment.",
]

COMMON_TEAM = [
    "Share a phone number so the team can call.",
    "Confirm Las Vegas residency for prep and local delivery.",
    "Complete required documentation with the team.",
    "If anything on this sheet disagrees with your vial label or COA, stop and call before mixing.",
]

SHEETS: dict[str, dict] = {
    "tirzepatide": {
        "title": "Tirzepatide",
        "filename": "tirzepatide.pdf",
        "visual": "incretin",
        "what": (
            "Tirzepatide is a 39-amino-acid synthetic peptide with a C20 fatty-diacid chain "
            "that lets it bind albumin and last about five days. Molecular formula C225H348N48O68. "
            "Molecular weight 4,813.53 daltons — a large peptide hormone analog, not a small-molecule pill. "
            "TrueHold stocks a 20 mg lyophilized research vial."
        ),
        "works": (
            "It is a dual incretin agonist: it turns on both the GIP receptor and the GLP-1 receptor. "
            "In the body that means stronger glucose-dependent insulin release, less glucagon when glucose is high, "
            "slower stomach emptying, and quieter appetite signaling in the brain. That is why people notice "
            "less 'food noise' and smaller portions. It is injected under the skin once weekly because the fatty-acid "
            "tail keeps it in circulation."
        ),
        "animal": (
            "Rodent and primate incretin studies showed appetite reduction, improved insulin secretion, "
            "and weight loss versus GLP-1 alone. The rodent thyroid C-cell finding that produced the boxed warning "
            "on the approved pens was seen with this drug class in rats and mice; it has not been confirmed as a "
            "human cancer signal, but it is why people with a personal or family history of medullary thyroid carcinoma "
            "or MEN2 are told to stay away from GLP-1/GIP drugs."
        ),
        "human": (
            "Large Phase 3 programs (SURPASS for type 2 diabetes, SURMOUNT for obesity) enrolled thousands of adults. "
            "On the 15 mg approved pen, SURMOUNT-1 reported on the order of 15–22% mean body-weight reduction versus "
            "placebo depending on dose and diabetes status. The molecule is FDA-approved as Mounjaro (type 2 diabetes, 2022) "
            "and Zepbound (chronic weight management 2023; later sleep apnea)."
        ),
        "hopes": [
            "Less hunger and fewer cravings",
            "Lower weight and waist when food and protein are tracked",
            "Better glucose and insulin-response numbers in people who have that goal",
            "A once-weekly rhythm that is easier to keep than daily shots",
        ],
        "harm": (
            "Yes — people have been harmed, mostly from the gastrointestinal effect and from rare but serious class events. "
            "Very common: nausea, vomiting, diarrhea, constipation, reduced appetite, stomach pain. "
            "Serious and documented: acute pancreatitis (including rare fatal reports in post-marketing systems), "
            "gallbladder disease, kidney injury from dehydration after vomiting, delayed stomach emptying that can "
            "raise aspiration risk under anesthesia, and low blood sugar when stacked with insulin or sulfonylureas. "
            "Stop and get emergency care for severe persistent abdominal pain radiating to the back."
        ),
        "fda": (
            "FDA-APPROVED as the branded pens Mounjaro and Zepbound — not as this vial. "
            "TrueHold's 20 mg lyophilized research vial is not an FDA-approved drug product, not a pen, and not interchangeable "
            "with pharmacy Mounjaro/Zepbound. The milligram start on this sheet (2.5 mg weekly) matches the approved starting "
            "milligrams so the math is honest; it does not make this vial a licensed medicine."
        ),
        "sources": [
            "FDA Zepbound / Mounjaro prescribing information (Lilly): https://pi.lilly.com/us/zepbound-uspi.pdf",
            "PubChem tirzepatide: MW 4813.53 Da, 39 amino acids, C225H348N48O68",
            "TrueHold locked 20 mg vial protocol: 2 mL BAC, 25/50/75/100 units weekly",
        ],
    },
    "retatrutide": {
        "title": "Retatrutide",
        "filename": "retatrutide.pdf",
        "visual": "incretin",
        "what": (
            "Retatrutide (LY3437943) is a 39-amino-acid GIP-backbone peptide with a fatty-diacid albumin binder. "
            "Molecular weight about 4,731 daltons. It is a triple agonist: GLP-1 + GIP + glucagon receptors. "
            "TrueHold stocks a 20 mg lyophilized research vial — the same milligram size as our tirzepatide vial."
        ),
        "works": (
            "GLP-1 and GIP quiet appetite and improve insulin-response biology, as with tirzepatide. "
            "The extra glucagon-receptor arm is why researchers talk about higher energy expenditure and fat oxidation, "
            "not only eating less. Half-life is about six days, so it is a weekly subcutaneous shot. "
            "It is not AOD-9604 (a growth-hormone fragment) and not semaglutide."
        ),
        "animal": (
            "Preclinical incretin/glucagon co-agonist work showed greater weight loss than dual agonists in obese animals, "
            "with the glucagon arm raising energy expenditure. Class thyroid C-cell findings in rodents still apply to "
            "anything that strongly stimulates GLP-1 receptors."
        ),
        "human": (
            "Phase 2 obesity work (NEJM 2023) and Phase 3 TRIUMPH-1 topline (Lilly, 2026) reported very large mean weight "
            "loss at 9–12 mg weekly, with GI events similar to other incretins plus a dysesthesia (odd skin sensation) signal "
            "that was uncommon on older GLP-1 drugs. Lilly has described filing plans; as of this sheet it is not approved. "
            "Trials start at 2 mg weekly and step every 4 weeks — that is why our 20 mg vial starts at 20 units (2.0 mg)."
        ),
        "hopes": [
            "Strong appetite control",
            "Weight-loss magnitude in trials that exceeded earlier incretins at high dose",
            "Possible extra energy-expenditure from the glucagon receptor",
            "Weekly schedule",
        ],
        "harm": (
            "Trial participants have had substantial GI illness: nausea, vomiting, diarrhea, constipation — more often at 9–12 mg. "
            "Dysesthesia (tingling, burning, odd skin feeling) showed up in Phase 3 at higher rates than placebo. "
            "Expect the same rare serious class risks as tirzepatide (pancreatitis, gallbladder, dehydration, aspiration under anesthesia) "
            "because GLP-1 is still on. There is no long-term post-marketing safety database yet. This is not a beginner 'more is better' peptide."
        ),
        "fda": (
            "NOT FDA-APPROVED. Investigational Lilly molecule. No legal retail drug product. "
            "Any seller claiming to ship 'pharmaceutical retatrutide pens' is not selling an approved medicine. "
            "TrueHold's 20 mg vial is a research formula, not a licensed drug."
        ),
        "sources": [
            "Lilly TRIUMPH-1 Phase 3 obesity topline: https://investor.lilly.com/node/54321/pdf",
            "InvivoGen / public chemistry sheets: ~4731 Da, 39 amino-acid backbone",
            "Drugs.com retatrutide status: not FDA-approved",
        ],
    },
    "semax": {
        "title": "Semax",
        "filename": "semax.pdf",
        "visual": "size",
        "what": (
            "Semax is a 7-amino-acid neuropeptide: Met-Glu-His-Phe-Pro-Gly-Pro (MEHFPGP). "
            "Formula C37H51N9O10S. Molecular weight 813.93 daltons — small next to tirzepatide. "
            "It is a stabilized ACTH(4-10) analog with a Pro-Gly-Pro tail so enzymes do not chew it as fast. "
            "It does not tell the adrenal glands to make cortisol the way full ACTH does. "
            "TrueHold stocks a 10 mg lyophilized vial."
        ),
        "works": (
            "In the brain it is discussed for BDNF-related signaling, melanocortin receptors, and enkephalinase effects. "
            "People notice focus and stress tolerance, not appetite collapse. "
            "Russian medicine uses it as nasal drops so it can reach the brain along olfactory pathways. "
            "That is why this TrueHold sheet reconstitutes the 10 mg vial and then drips — it does not start you on an injection."
        ),
        "animal": (
            "Rodent work reports neuroprotection after ischemia, improved learning tasks, and BDNF changes. "
            "Those models are why it was developed for stroke and cognition in Russia."
        ),
        "human": (
            "Semax has been a registered medicine in Russia since the 1990s (0.1% cognitive drops; 1% hospital stroke drops) "
            "and is on the Russian vital-drugs list. Published English-language trials are smaller than Western Phase 3 programs. "
            "There are no FDA trials. Cognitive protocols commonly sit around 200–900 mcg/day nasally for 10–30 days."
        ),
        "hopes": [
            "Sharper focus and mental endurance",
            "Stress tolerance during heavy cognitive load",
            "Neuroprotective research interest after brain insult (that is a medical use in Russia, not a TrueHold claim)",
        ],
        "harm": (
            "Published Russian use mostly reports mild nasal irritation, occasional headache, and sleep disruption if taken late. "
            "Serious events are not a feature of the English-language literature, but Western long-term RCT safety does not exist. "
            "Do not treat this as a stroke medicine. Do not drive the 1% hospital dose at home. "
            "If you get a severe headache, nosebleed that will not stop, or mood crash, stop and call the team."
        ),
        "fda": (
            "NOT FDA-APPROVED in the United States. Approved as a nasal medicine in Russia/Ukraine. "
            "TrueHold's 10 mg lyophilized vial is a research formula, not a US drug."
        ),
        "sources": [
            "PubChem / Wikipedia Semax: C37H51N9O10S, 813.93 g/mol, sequence MEHFPGP",
            "Russian 0.1% cognitive range ~200–900 mcg/day mapped to 6 units (300 mcg) on this 10 mg / 2 mL vial",
        ],
    },
    "nad": {
        "title": "NAD+",
        "filename": "nad-plus.pdf",
        "visual": "mito",
        "what": (
            "NAD+ (nicotinamide adenine dinucleotide) is not a peptide. It is a coenzyme found in every living cell. "
            "Formula C21H26N7O14P2 (oxidized form). Molecular weight 663.4 daltons — smaller than Semax. "
            "TrueHold stocks a 1000 mg lyophilized vial in a larger ~5 mL bottle, not a 2 mL peptide vial."
        ),
        "works": (
            "NAD+ shuttles electrons in mitochondrial energy production (NAD+ ↔ NADH). "
            "It is also the fuel for sirtuins and PARP DNA-repair enzymes. When NAD+ is low, those systems run poorly. "
            "The body makes it from tryptophan and from vitamin B3 salvage (niacin, NR, NMN). "
            "An injectable vial is a direct NAD+ salt, not the same thing as an NR capsule."
        ),
        "animal": (
            "Raising NAD+ in mice (usually via precursors) has been tied to mitochondrial function, DNA repair, and metabolic resilience. "
            "That literature is about biochemistry, not a license for megadose injections."
        ),
        "human": (
            "Oral niacin is an old FDA-approved lipid drug with flushing and liver-risk at high modified-release doses — different molecule, different route. "
            "NR and NMN oral trials exist. Intravenous NAD+ is used in clinics with little gold-standard RCT evidence for 'anti-aging.' "
            "TrueHold's locked protocol is subcutaneous on this 1000 mg vial: 50 units (100 mg) twice weekly to start."
        ),
        "hopes": [
            "More stable daytime energy",
            "Recovery and training tolerance",
            "Focus",
            "Healthy-aging biochemistry (sirtuins / PARPs) — a research hope, not a proven human outcome from this vial",
        ],
        "harm": (
            "People feel unwell on high NAD+ pushes: flushing, chest tightness, nausea, cramping, anxiety during fast IV drips. "
            "Subcutaneous shots can sting. High-dose nicotinic acid (not identical to this salt) can injure the liver — another reason not to stack random B3 megadoses. "
            "There is no large safety trial of twice-weekly 100 mg subcutaneous NAD+ as an anti-aging drug. Stop for chest pain, severe shortness of breath, or yellowing skin."
        ),
        "fda": (
            "This injectable NAD+ vial is NOT an FDA-approved drug for energy, aging, or addiction. "
            "Niacin (nicotinic acid) tablets have FDA-approved lipid uses; that is not this product. "
            "Dietary NAD+ precursors are supplements, not this 1000 mg research vial."
        ),
        "sources": [
            "TrueHold locked 1000 mg protocol: 5 mL BAC, start 50 units twice weekly (100 mg per shot)",
            "NAD+ biochemistry: electron transport, sirtuins, PARPs (standard cell-biology references)",
        ],
    },
    "klow": {
        "title": "KLOW",
        "filename": "klow.pdf",
        "visual": "size",
        "what": (
            "KLOW is a four-peptide regenerative blend totaling 80 mg in TrueHold's vial. "
            "US research catalogs use this split: GHK-Cu 50 mg (copper tripeptide, ~404 Da) + BPC-157 10 mg "
            "(15 amino acids, gastric-juice fragment) + TB-500 10 mg (43 amino-acid thymosin-β4 fragment) + KPV 10 mg "
            "(Lys-Pro-Val, the C-terminal of α-MSH). Confirm that split on your COA before mixing."
        ),
        "works": (
            "The four pieces hit different repair stories at once: GHK-Cu on extracellular-matrix genes and copper-dependent enzymes; "
            "BPC-157 on nitric-oxide / growth-factor signaling in tissue models; TB-500 on actin and cell migration; "
            "KPV on NF-κB inflammatory signaling. That is why it is sold as one 80 mg vial instead of four bottles. "
            "It is not a GLP-1 drug and not a steroid."
        ),
        "animal": (
            "Each component has animal data (wound, tendon, gut, inflammation models). "
            "The four-peptide combination as KLOW does not have a published multi-center animal program of its own — you are stacking four literatures."
        ),
        "human": (
            "There is no Phase 3 trial of KLOW. GHK-Cu has topical cosmetic human use. BPC-157, TB-500, and KPV do not have FDA-approved human drugs. "
            "The 10-unit draw on this sheet is the handling math that puts each component into its usual research milligram/microgram window in one shot."
        ),
        "hopes": [
            "Tissue comfort and recovery from training",
            "Skin and connective-tissue notes",
            "A quieter inflammatory background (KPV / BPC themes)",
            "One daily draw instead of four separate peptides",
        ],
        "harm": (
            "This blend has not been safety-tested as a licensed combination. "
            "Injection-site redness is common. GHK-Cu can tinge the liquid blue-green. "
            "Copper load matters if you have Wilson disease. BPC-157 has been flagged in US compounding policy debates — quality and contamination risk on gray-market vials is real. "
            "People have reported dizziness or water-retention anecdotes on TB-500-type fragments; that is not a clean trial database. "
            "Stop for hives, breathing trouble, severe swelling, or yellowing skin."
        ),
        "fda": (
            "NOT FDA-APPROVED. None of the four peptides is an approved injectable drug in this blend. "
            "This is a research 80 mg vial, not a wound-healing medicine."
        ),
        "sources": [
            "Standard 80 mg KLOW catalog split: GHK-Cu 50 + BPC-157 10 + TB-500 10 + KPV 10",
            "2 mL BAC → 40 mg/mL; 10 units = 4 mg total (2.5 mg GHK-Cu + 0.5 mg × 3)",
        ],
    },
    "mots-c": {
        "title": "MOTS-c",
        "filename": "mots-c.pdf",
        "visual": "mito",
        "what": (
            "MOTS-c (mitochondrial open reading frame of the 12S rRNA type-c) is a 16-amino-acid peptide "
            "encoded in mitochondrial DNA, not nuclear DNA. Sequence MRWQEMGYIFYPRKLR. "
            "Molecular weight about 2,175 daltons. TrueHold stocks a 20 mg lyophilized vial."
        ),
        "works": (
            "Cells release MOTS-c as a mitochondrial signal. In muscle it is discussed as an AMPK-linked, exercise-mimetic message: "
            "more glucose uptake, more fatty-acid use, better insulin sensitivity in animal models. "
            "It is not a GLP-1 agonist and not NAD+."
        ),
        "animal": (
            "Lee and colleagues showed MOTS-c prevented diet-induced obesity and insulin resistance in mice at roughly 0.5 mg/kg. "
            "Exercise raises endogenous MOTS-c in human muscle; that is observational biology, not a dosing licence."
        ),
        "human": (
            "No completed Phase 3. A Phase 2a subcutaneous study in prediabetes (NCT07505745) is registered. "
            "FDA compounding reviews have treated MOTS-c as poorly characterized for 503A bulk lists. "
            "Research-handling writeups use about 5–10 mg three times weekly; this 20 mg vial starts at 2.5 mg (25 units) then 5 mg (50 units, a full 0.5 mL syringe)."
        ),
        "hopes": [
            "Steadier energy and training output",
            "Insulin-sensitivity and body-composition research themes",
            "An exercise-linked mitochondrial signal without being a stimulant",
        ],
        "harm": (
            "There is no mature human safety database. Theoretical risks: low blood sugar if you already use insulin or intense fasting, "
            "unknown immunogenicity, unknown long-term organ effects. Injection-site irritation is the practical near-term issue. "
            "Do not treat mouse obesity papers as proof it is safe for you."
        ),
        "fda": (
            "NOT FDA-APPROVED for any indication. Not a legal compounded drug on the FDA bulk list as of the 2026 peptide reviews. "
            "TrueHold's 20 mg vial is research material."
        ),
        "sources": [
            "Lee C. et al., mitochondrial MOTS-c metabolic papers; Front. Endocrinol. reviews (2023)",
            "ClinicalTrials.gov NCT07505745 (Phase 2a, subcutaneous)",
            "20 mg vial / 2 mL BAC: 25 units = 2.5 mg, 50 units = 5 mg",
        ],
    },
    "ss-31": {
        "title": "SS-31 (Elamipretide)",
        "filename": "ss-31.pdf",
        "visual": "mito",
        "what": (
            "SS-31 is a tiny mitochondria-targeted tetrapeptide (D-Arg-Dmt-Lys-Phe-NH2), also called elamipretide. "
            "The hydrochloride salt used in the approved drug has molecular weight 749.2. "
            "TrueHold stocks a 10 mg lyophilized research vial — one-quarter of a single 40 mg Forzinity pharmaceutical dose."
        ),
        "works": (
            "It concentrates on the inner mitochondrial membrane and binds cardiolipin, the lipid that folds the cristae "
            "and holds the electron-transport chain together. The hope is better ATP production and less oxidative leak. "
            "It is not an incretin and not NAD+."
        ),
        "animal": (
            "Many mitochondrial-disease and ischemia models show improved bioenergetics when SS-31 reaches mitochondria. "
            "That is a strong preclinical story and why Stealth BioTherapeutics took elamipretide into rare-disease trials."
        ),
        "human": (
            "On 19 September 2025 FDA granted accelerated approval to Forzinity (elamipretide) 40 mg subcutaneous daily "
            "to improve muscle strength in Barth syndrome (patients ≥30 kg), based on knee-extensor strength, with a confirmatory trial required. "
            "Common trial adverse events were injection-site reactions. "
            "TrueHold's 10 mg vial is not Forzinity and cannot deliver 40 mg/day."
        ),
        "hopes": [
            "Cellular energy and stamina notes",
            "Mitochondrial-efficiency research",
            "A daily cardiolipin-targeted shot at a research-vial milligram, not a Barth-syndrome prescription",
        ],
        "harm": (
            "Forzinity labeling: injection-site reactions are common; serious reactions have been reported. "
            "The branded syringe also contains benzyl alcohol (a neonate toxicity issue — not for babies). "
            "Using a 10 mg research vial is not a Barth-syndrome treatment. Do not chase 40 mg/day by buying four vials and guessing. "
            "Stop for severe injection-site necrosis, breathing trouble, or dark urine."
        ),
        "fda": (
            "The molecule elamipretide IS FDA-approved as Forzinity for Barth syndrome only (accelerated approval, 2025). "
            "TrueHold's 10 mg lyophilized SS-31 vial is NOT Forzinity, NOT approved, and NOT dosed at 40 mg. "
            "This sheet's 1–2 mg start is vial-honest research handling, not the Barth prescription."
        ),
        "sources": [
            "FDA Forzinity accelerated approval (19 Sep 2025): https://www.fda.gov/news-events/press-announcements/fda-grants-accelerated-approval-first-treatment-barth-syndrome",
            "DailyMed Forzinity: 40 mg SC daily; MW 749.2 (HCl salt)",
            "TrueHold 10 mg / 2 mL: 20 units = 1 mg, 40 units = 2 mg",
        ],
    },
    "ghk-cu": {
        "title": "GHK-Cu",
        "filename": "ghk-cu.pdf",
        "visual": "size",
        "what": (
            "GHK-Cu is glycyl-L-histidyl-L-lysine bound to copper(II). The peptide alone is 340 Da; the copper complex is about 404 daltons — "
            "one of the smallest things in this catalog. Isolated from human plasma by Pickart in 1973. "
            "Plasma levels fall with age (on the order of 200 ng/mL in young adults vs ~80 ng/mL later). "
            "TrueHold stocks a 100 mg lyophilized vial."
        ),
        "works": (
            "The copper-peptide complex is a signaling molecule for wound and matrix remodeling: collagen, elastin, glycosaminoglycans, "
            "and antioxidant enzymes in skin models. Topical cosmetic use is the well-studied route. "
            "Injectable use is a different, thinner evidence pile. The liquid may look faintly blue-green. That is copper, not contamination, "
            "if the COA matches."
        ),
        "animal": (
            "Wound and hair models in animals are the backbone of the regenerative story. "
            "Those papers do not equal a human injectable label."
        ),
        "human": (
            "Topical GHK-Cu (copper tripeptide-1) has cosmetic trials versus vitamin C / retinoic acid creams for appearance measures. "
            "There are no adequate Phase 3 trials of subcutaneous GHK-Cu. Community injectable handling is typically 1–2 mg daily, "
            "which is why this 100 mg / 2 mL vial is written so that 2 units = 1 mg and 4 units = 2 mg."
        ),
        "hopes": [
            "Skin quality and tissue-remodeling notes",
            "Hair and wound-appearance research (mostly topical data)",
            "A small daily draw from a large 100 mg vial",
        ],
        "harm": (
            "Topical use has a long cosmetic safety record. Injectable use does not. "
            "Risks: injection-site irritation, unknown chronic copper load, and a real problem if you have Wilson disease "
            "(cannot excrete copper). At 1–2 mg the elemental copper is small compared with food, but that is not a license for unmonitored years of shots. "
            "Stop for rash, breathing trouble, abdominal pain with yellowing, or a neurologist-level tremor/change that could be copper-related."
        ),
        "fda": (
            "NOT FDA-APPROVED as an injectable drug. Topical copper tripeptide-1 appears in cosmetics, which are not drugs. "
            "TrueHold's 100 mg vial is a research formula, not a skin medicine."
        ),
        "sources": [
            "Pickart GHK-Cu plasma peptide; cosmetic copper tripeptide-1 literature",
            "TrueHold 100 mg / 2 mL: 2 units = 1 mg, 4 units = 2 mg",
        ],
    },
}


def sheet_for(sku: str) -> dict:
    if sku not in SHEETS or sku not in PROTOCOLS:
        raise KeyError(sku)
    payload = dict(SHEETS[sku])
    payload["protocol"] = PROTOCOLS[sku]
    payload["fulfillment"] = COMMON_FULFILLMENT
    payload["team"] = COMMON_TEAM
    return payload
