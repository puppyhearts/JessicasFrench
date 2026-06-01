"""
Correction patch: fixes wrong answer choices identified by cross-referencing
the printed question pages against the transcription-derived choices from the
first patch.

Issues corrected:
  B2 Q5  — completely wrong question (director's concern, not candidate's departure)
  B2 Q8  — wrong choices for beau-parent question
  B2 Q14 — wrong choices for soldes/rabais conclusion question
  B2 Q15 — D was wrong ("Faire de la place" not "Faire croire")
  C1 Q9  — D was wrong (passion vs grandes épiceries)
  C2 Q1  — C used "mesure" not "conservation"; D missing "en astrophysique"
  C2 Q3  — completely wrong question (Québec choices on Francophonie question)
  C2 Q4  — D was wrong (Amérique Latine vs acteurs africains sub-sahariens)
  C2 Q8  — C and D were wrong
  C2 Q9  — A missing "chaque année"; D was wrong text

All choices verified against the printed question pages of the Réussir le TCF
OCR (.ocr-cache/reussir/images/).

Run from the repo root:
    python scripts/patch-choices-corrections.py
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "content" / "generated" / "catalog.sqlite"

CORRECTIONS: dict[str, list[tuple[str, str]]] = {
    # ── B2 Q5 ─ director's concern about the B2 candidate's profile ──────────
    # (previously had "Elle a donné sa démission" etc. — those are Q6's choices)
    "reussir-tcf:b2:q005": [
        ("A", "La candidate ne parle pas suffisamment bien anglais."),
        ("B", "La candidate n'a aucune expérience à l'étranger."),
        ("C", "La candidate n'a pas exactement les diplômes requis."),
        ("D", "La candidate manque de pratique professionnelle."),  # correct=D
    ],

    # ── B2 Q8 ─ main challenge of recomposed families ────────────────────────
    # (previously "La définition du rôle de chacun dans la nouvelle famille")
    "reussir-tcf:b2:q008": [
        ("A", "La définition du « beau-parent » n'est pas claire."),   # correct=A
        ("B", "Le beau-parent doit être en charge de la discipline."),
        ("C", "Le beau-parent doit s'adapter au partage des rôles."),
        ("D", "Le beau-parent doit prendre pour modèle les parents naturels."),
    ],

    # ── B2 Q14 ─ journalist's conclusion about sales (soldes) ────────────────
    # (previously had "Il faut comparer les articles" as B, which was wrong)
    "reussir-tcf:b2:q014": [
        ("A", "Les soldes sont généralement clairs et correspondent à de véritables rabais."),
        ("B", "Il faut se méfier : les soi-disant rabais sont parfois trompeurs."),  # correct=B
        ("C", "Les soldes ne sont valables que dans le domaine de l'électronique."),
        ("D", "Les clients ne trouveront des aubaines que durant les premiers jours."),
    ],

    # ── B2 Q15 ─ why companies offer sales ───────────────────────────────────
    # (D was "Faire croire au consommateur" — wrong)
    "reussir-tcf:b2:q015": [
        ("A", "Fidéliser leur clientèle."),
        ("B", "Attirer de nouveaux clients."),
        ("C", "Augmenter leur chiffre d'affaires en bradant tout leur stock."),
        ("D", "Faire de la place pour les nouveaux articles."),   # correct=D
    ],

    # ── C1 Q9 ─ why the baker became famous ──────────────────────────────────
    # (D was "vendu dans les grandes épiceries" — wrong)
    "reussir-tcf:c1:q009": [
        ("A", "parce que les touristes aiment son pain."),
        ("B", "parce qu'un magazine a fait un article sur sa boulangerie."),
        ("C", "parce qu'il a reçu un prix prestigieux."),  # correct=C
        ("D", "parce que faire du pain est sa passion."),
    ],

    # ── C2 Q1 ─ what characterises the neutrino ──────────────────────────────
    # (C had "mesure" not "conservation"; D missing "en astrophysique")
    "reussir-tcf:c2:q001": [
        ("A", "Elle est facile à identifier et à définir."),
        ("B", "Elle a été inventée avant d'être découverte."),   # correct=B
        ("C", "Elle a été identifiée depuis longtemps mais posait des problèmes de conservation."),
        ("D", "Depuis 1930 environ, ses propriétés de messager sont reconnues et utilisées en astrophysique."),
    ],

    # ── C2 Q3 ─ what the Francophonie entretiens reflect ─────────────────────
    # (previously had Québec/La Rochelle choices — completely wrong question)
    "reussir-tcf:c2:q003": [
        ("A", "une réflexion sur la francophonie dans un monde global."),  # correct=A
        ("B", "une réflexion sur la francophonie et l'indépendance."),
        ("C", "une réflexion sur la francophonie et son influence."),
        ("D", "une réflexion sur la francophonie post-coloniale."),
    ],

    # ── C2 Q4 ─ what the 3rd Francophonie era must navigate ──────────────────
    # (D was "La Francophonie renforce sa coopération avec l'Amérique Latine" — wrong)
    "reussir-tcf:c2:q004": [
        ("A", "des recommandations provenant des organisations internationales."),
        ("B", "le positionnement culturel et économique dans une phase concurrentielle."),  # correct=B
        ("C", "une concurrence exacerbée entre l'Amérique latine et l'Afrique."),
        ("D", "des solutions pour les nouveaux acteurs africains sub-sahariens."),
    ],

    # ── C2 Q8 ─ author's opinion on losing the southern accent ───────────────
    # (C and D were wrong)
    "reussir-tcf:c2:q008": [
        ("A", "Elle pense que la perte de l'accent a finalement des conséquences positives."),
        ("B", "Elle pense que la perte de l'accent est un fléau qui touche certaines personnes."),  # correct=B
        ("C", "Elle pense que l'accent a perdu son statut de vecteur culturel car il a moins d'importance."),
        ("D", "Elle pense qu'aujourd'hui les accents se perdent et c'est bien dommage."),
    ],

    # ── C2 Q9 ─ why La Rochelle celebrates Québec's 400th anniversary ────────
    # (A missing "chaque année"; D had wrong text)
    "reussir-tcf:c2:q009": [
        ("A", "car les villes de Québec et La Rochelle organisent une traversée de l'Atlantique chaque année."),
        ("B", "car le fondateur de Québec vient de la région de la Rochelle."),   # correct=B
        ("C", "car les 400 ans de Québec sont aussi les 400 ans de La Rochelle."),
        ("D", "car les Rochelais devenus Québécois aiment refaire la traversée."),
    ],
}


def patch(conn: sqlite3.Connection) -> None:
    total = 0
    for stable_id, choices in CORRECTIONS.items():
        for label, text in choices:
            cur = conn.execute(
                "UPDATE answer_choices SET text = ? WHERE question_id = ? AND label = ?",
                (text, stable_id, label),
            )
            total += cur.rowcount
        print(f"  {stable_id}: updated {len(choices)} choices")
    print(f"\nTotal rows updated: {total}")


def main() -> None:
    if not DB.exists():
        print(f"ERROR: catalog not found at {DB}")
        return
    conn = sqlite3.connect(DB)
    print("Applying choice corrections …")
    patch(conn)
    conn.commit()
    conn.close()
    print("Committed.")


if __name__ == "__main__":
    main()
