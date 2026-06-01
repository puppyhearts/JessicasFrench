"""
Patch script: replace generic "Proposition A/B/C/D" answer choices in the
ABC TCF catalog with the real text extracted from the textbook OCR pages.

Sources:
  CO  Q5-Q40  : .ocr-cache/abc-main/images/page-022 through page-029
  TB  Q1-Q30  : .ocr-cache/abc-main/images/page-103 through page-109
  Image questions (choices are 4 photos): store the page PNG so the UI can
  show the images; choices remain as Proposition A/B/C/D (no text equivalent).

Run from the repo root:
    python scripts/patch-abc-choices.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "content" / "generated" / "catalog.sqlite"
OCR = ROOT / ".ocr-cache" / "abc-main" / "images"

# ---------------------------------------------------------------------------
# Verified text choices extracted from book OCR pages (page images cross-checked
# against the answer key to confirm each option's label).
# Keys are (collection_slug, group_label_safe, question_number).
# ---------------------------------------------------------------------------

CO_GROUP = "Compréhension orale"
TB_GROUP = "Test blanc"

CO_CHOICES: dict[int, list[tuple[str, str]]] = {
    # ── Niveau A2 ────────────────────────────────────────────────────────────
    5:  [("A", "Pour annuler un rendez-vous."),
         ("B", "Pour changer un rendez-vous."),
         ("C", "Pour confirmer un rendez-vous."),  # ← correct (Q5=C)
         ("D", "Pour prendre un rendez-vous.")],
    # Q6 : spoken choices in the audio
    7:  [("A", "Son collègue."),
         ("B", "Son médecin."),
         ("C", "Son pharmacien."),
         ("D", "Son responsable.")],       # ← correct (Q7=D)
    # Q8 : image choices (4 weather/sky photos) — page image stored separately
    9:  [("A", "L'adresse."),
         ("B", "La situation."),
         ("C", "Le prix."),                # ← correct (Q9=C)
         ("D", "Les services.")],
    10: [("A", "Des conseils pour les études universitaires."),
         ("B", "Des emplois d'été pour les étudiants."),
         ("C", "Des emplois pour les jeunes toute l'année."),
         ("D", "Des stages professionnels à l'étranger.")],  # ← Q10=B

    # ── Niveau B1 ────────────────────────────────────────────────────────────
    11: [("A", "Avec sa cousine."),
         ("B", "Avec ses enfants."),     # ← correct (Q11=B)
         ("C", "Avec Patrick."),
         ("D", "Avec Thomas.")],
    12: [("A", "Il va faire sa valise."),
         ("B", "Il va travailler."),     # ← correct (Q12=B)
         ("C", "Il va visiter l'Égypte."),
         ("D", "Il va voir sa cousine.")],
    # Q13 : image choices (4 transport photos) — page image stored separately
    14: [("A", "Elle a laissé son argent dans la boutique."),  # ← correct (Q14=A)
         ("B", "Elle est partie trop tard de chez elle."),
         ("C", "Elle n'a pas fait attention à l'heure."),
         ("D", "Elle s'est trompée de lieu de rendez-vous.")],
    15: [("A", "Elle veut acheter un nouveau téléphone."),
         ("B", "Il manque un accessoire dans la boîte."),
         ("C", "La qualité des écouteurs est mauvaise."),
         ("D", "Son appareil a un défaut technique.")],       # ← Q15=D
    16: [("A", "Arrêter les séances d'entraînement."),
         ("B", "Faire moins de séances d'entraînement."),    # ← correct (Q16=B)
         ("C", "Faire plus de séances d'entraînement."),
         ("D", "S'entraîner doucement de la même manière.")],
    # Q17 : watermarked in OCR, choices unreadable — left as Proposition A/B/C/D
    18: [("A", "Parce que les écoles et les entreprises rendent la pratique sportive obligatoire."),
         ("B", "Parce que les Suédois gagnent beaucoup de compétitions sportives internationales."),
         ("C", "Parce que les Suédois ont droit à beaucoup de vacances pour pratiquer le sport."),
         ("D", "Parce que les Suédois pratiquent le sport dans leur quotidien, à l'école et au travail.")],  # ← Q18=D

    # ── Niveau B2 ────────────────────────────────────────────────────────────
    19: [("A", "Aucune université canadienne ne proposait de programme en immersion."),
         ("B", "Étudier dans deux langues, en anglais et en français, n'était pas possible."),
         ("C", "Sa motivation pour étudier et pour apprendre l'anglais n'était pas assez forte."),
         ("D", "Son niveau d'anglais et ses résultats scolaires français étaient insuffisants.")],  # ← Q19=D
    20: [("A", "Des conseils pratiques sur les animaux de compagnie."),  # ← Q20=A
         ("B", "Des idées de sorties pour découvrir les animaux."),
         ("C", "Des recettes de cuisine originales pour les animaux."),
         ("D", "Des fiches techniques pour mieux reconnaître les animaux.")],
    21: [("A", "Au restaurant pour un dîner."),
         ("B", "Chez eux avec leurs amis."),
         ("C", "Dans un casino pour jouer."),
         ("D", "En ville pour aller danser.")],              # ← Q21=D
    22: [("A", "Il crée des liens entre les personnes qui ont les mêmes intérêts."),
         ("B", "Il garde en mémoire le nom de sites visités par les internautes."),
         ("C", "Il reconnaît automatiquement l'utilisateur qui se connecte."),
         ("D", "Il se fonde sur les renseignements fournis par les utilisateurs.")],  # ← Q22=D
    23: [("A", "Les grands groupes occupent trop de place sur les sites d'avis."),
         ("B", "La plupart des avis publiés sur Internet sont malintentionnés."),
         ("C", "Les règles de contrôle sur les sites d'avis sont trop contraignantes."),
         ("D", "Les sites d'avis sont souvent manipulés par les entreprises.")],      # ← Q23=D
    24: [("A", "Ils les utilisent très peu."),
         ("B", "Ils leur font plutôt confiance."),           # ← correct (Q24=B)
         ("C", "Ils ne les trouvent pas pratiques."),
         ("D", "Ils s'en méfient beaucoup.")],
    25: [("A", "Encadrer la pratique des médecines non conventionnelles."),  # ← Q25=A
         ("B", "Présenter les alternatives avec les médecines traditionnelles."),
         ("C", "Promouvoir les médecines non conventionnelles auprès du public."),
         ("D", "Rassurer les médecins à l'égard des médecines non conventionnelles.")],
    26: [("A", "Des candidats avec une longue expérience et des compétences variées."),
         ("B", "Des gens avec de l'expérience prêts à travailler immédiatement."),   # ← Q26=B
         ("C", "Des jeunes diplômés dont la formation sera complétée en interne."),
         ("D", "Des personnes ambitieuses et diplômées en quête d'évolution.")],
    27: [("A", "Utiliser uniquement les réseaux sociaux."),
         ("B", "Répondre seulement aux annonces en ligne."),
         ("C", "Favoriser d'abord les filières qui embauchent."),
         ("D", "Faire appel à tous les moyens possibles.")],  # ← Q27=D
    28: [("A", "Le cinéma européen a bien fonctionné cette année."),  # ← Q28=A
         ("B", "Le festival de Cannes favorise le cinéma européen."),
         ("C", "Les films commerciaux ne trouvent plus leur public."),
         ("D", "Les films européens ne se portent pas très bien.")],

    # ── Niveau C1 ────────────────────────────────────────────────────────────
    29: [("A", "La décision du groupe d'experts."),
         ("B", "Le nombre de passagers insatisfaits."),
         ("C", "La non-intervention du Conseil régional."),  # ← correct (Q29=C)
         ("D", "L'état d'entretien des lignes concernées.")],
    30: [("A", "Dresser une cartographie précise de l'attractivité médicale des nations européennes."),
         ("B", "Faire un état des lieux complet des médecines non conventionnelles à l'échelle mondiale."),  # ← Q30=B
         ("C", "Inciter les états membres à faire du droit à l'accès aux soins une priorité."),
         ("D", "Informer les citoyens européens sur la nocivité de certaines médecines parallèles.")],
    31: [("A", "De compenser l'altération des capacités auditives des patients."),  # ← Q31=A
         ("B", "D'empêcher la perte progressive de l'ouïe."),
         ("C", "De doter les personnes atteintes d'une prothèse auditive adaptée."),
         ("D", "De guérir les personnes atteintes d'une surdité.")],
    32: [("A", "Il a agressé un contrôleur de billet de train de la SNCF."),
         ("B", "Il a conduit des trains de la SNCF sans en avoir l'autorisation."),
         ("C", "Il passait ses journées à voler les passagers des trains."),
         ("D", "Il voyageait souvent déguisé en employé de la SNCF.")],  # ← Q32=D
    33: [("A", "motivation."),
         ("B", "organisation."),   # ← correct (Q33=B)
         ("C", "réflexion."),
         ("D", "transgression.")],
    34: [("A", "effraye les consommateurs."),
         ("B", "rebute les consommateurs."),
         ("C", "stimule les consommateurs."),  # ← correct (Q34=C)
         ("D", "trompe les consommateurs.")],

    # ── Niveau C2 ────────────────────────────────────────────────────────────
    35: [("A", "Comme un bouleversement profond des stratégies de ventes."),  # ← Q35=A
         ("B", "Comme un essor notable des techniques commerciales créatives."),
         ("C", "Comme une amplification marquée des déséquilibres financiers."),
         ("D", "Comme une évolution naturelle de l'économie de marché.")],
    36: [("A", "Elles correspondent parfaitement au modèle classique du roman historique."),
         ("B", "Elles intègrent divers genres littéraires afin de les rendre plus réalistes."),  # ← Q36=B
         ("C", "Elles retracent, de façon chronologique, les grandes étapes d'une époque."),
         ("D", "Elles sont similaires à celles de Walter Scott qui reflètent l'âme d'une époque.")],
    37: [("A", "Les pouvoirs publics ne respectent pas le cahier des charges imposé par la Ville de Bruxelles."),
         ("B", "Les pouvoirs publics souhaitent avoir le monopole du marché des enlèvements de véhicules."),
         ("C", "Les sociétés de dépannage appliquent des prix élevés et ne respectent pas certaines règles."),  # ← Q37=C
         ("D", "La Ville de Bruxelles veut modifier la procédure d'attribution du marché de l'enlèvement des véhicules.")],
    38: [("A", "Un combat difficile à mener."),
         ("B", "Un décalage avec son rêve."),        # ← correct (Q38=B)
         ("C", "Un doute sans finalité réelle."),
         ("D", "Une vocation acquise naturelle.")],
    39: [("A", "L'Europe doit être plus exigeante en matière de taxes douanières vis-à-vis du Japon."),
         ("B", "L'Europe doit encore prouver au Japon que cet accord sera économiquement favorable."),
         ("C", "Le Japon doit accepter d'accélérer les partenariats avec les entreprises européennes."),
         ("D", "Le Japon doit ajuster ses contraintes administratives douanières sur celles de l'Europe.")],  # ← Q39=D
    40: [("A", "L'amertume."),
         ("B", "L'humour."),   # ← correct (Q40=B)
         ("C", "L'ironie."),
         ("D", "La nostalgie.")],
}

TB_CHOICES: dict[int, list[tuple[str, str]]] = {
    # ── Niveau A1 ────────────────────────────────────────────────────────────
    1:  [("A", "J'ai 25 ans."),
         ("B", "J'étudie l'économie."),
         ("C", "J'habite à Bordeaux."),
         ("D", "Je m'appelle Thomas.")],   # ← TB Q1=D
    2:  [("A", "Il est à la plage."),
         ("B", "Il est grand."),
         ("C", "Il mange beaucoup."),
         ("D", "Il va bien.")],            # ← TB Q2=D
    # Q3, Q4 : image choices — page image stored separately
    5:  [("A", "Parce qu'il a un autre rendez-vous."),  # ← TB Q5=A
         ("B", "Parce qu'il fait beaucoup trop chaud."),
         ("C", "Parce que John ne l'accompagne pas."),
         ("D", "Parce que le temps n'est pas beau.")],

    # ── Niveau A2 ────────────────────────────────────────────────────────────
    6:  [("A", "Il aime assez bien."),
         ("B", "Il l'aime beaucoup."),
         ("C", "Il n'aime pas beaucoup."),
         ("D", "Il n'aime pas du tout.")],   # ← TB Q6=D
    7:  [("A", "d'autobus."),   # ← TB Q7=A
         ("B", "d'avion."),
         ("C", "de bateau."),
         ("D", "de train.")],
    # Q8 : unclear / possibly image — left as Proposition A/B/C/D
    9:  [("A", "Un appartement à Marseille."),
         ("B", "Un appartement à Paris."),
         ("C", "Un nouveau travail à Marseille."),
         ("D", "Un nouveau travail à Paris.")],  # ← TB Q9=D
    # Q10 : choices cut off at bottom of page — left as Proposition A/B/C/D

    # ── Niveau B1 ────────────────────────────────────────────────────────────
    11: [("A", "Aux adolescents."),   # ← TB Q11=A
         ("B", "Aux adultes."),
         ("C", "Aux enfants."),
         ("D", "Aux familles.")],
    12: [("A", "Une émission de jeux-concours."),
         ("B", "Une émission musicale."),   # ← TB Q12=B
         ("C", "Une émission sur la danse."),
         ("D", "Une émission sur les voyages.")],
    13: [("A", "Les étudiants."),   # ← TB Q13=A
         ("B", "Les élèves."),
         ("C", "Les touristes."),
         ("D", "Les travailleurs.")],
    14: [("A", "Il est conseillé d'utiliser les nouvelles technologies."),  # ← TB Q14=A
         ("B", "Il est nécessaire d'utiliser les nouvelles méthodes."),
         ("C", "Il faut utiliser les moyens traditionnels."),
         ("D", "Il faut utiliser de la même manière toutes les méthodes.")],
    15: [("A", "Ceux qui ont réservé."),
         ("B", "Les amoureux du confort."),
         ("C", "Les spectateurs riches."),
         ("D", "Tous les spectateurs.")],   # ← TB Q15=D

    # ── Niveau B2 ────────────────────────────────────────────────────────────
    16: [("A", "La lune cachera complètement le soleil."),
         ("B", "La lune et la terre seront peu éloignées."),  # ← TB Q16=B
         ("C", "On verra la lune très proche du soleil."),
         ("D", "Un satellite s'approchera de la lune.")],
    17: [("A", "C'est un produit essentiel pour la santé."),
         ("B", "Ces qualités nutritionnelles ont diminué."),
         ("C", "Il faut le consommer avec modération."),
         ("D", "Sa saveur a tendance à se standardiser.")],  # ← TB Q17=D
    18: [("A", "L'empreinte écologique des bouquets."),   # ← TB Q18=A
         ("B", "L'origine géographique des espèces de fleurs."),
         ("C", "La disparition de nombreuses variétés de fleurs."),
         ("D", "Les nouvelles méthodes de culture.")],
    # Q19 : choice D unreadable in OCR — left as Proposition A/B/C/D
    20: [("A", "Il attire des milliers de touristes chaque année."),
         ("B", "Il est un des sommets les plus hauts du monde."),
         ("C", "Il est une source d'inspiration pour les artistes."),  # ← TB Q20=C
         ("D", "Son sommet est entouré de merveilles naturelles.")],

    # ── Niveau C1 ────────────────────────────────────────────────────────────
    21: [("A", "Une panne technique a empêché un grand nombre de personnes de s'inscrire sur ce réseau."),
         ("B", "Une panne informatique a supprimé les données personnelles d'un grand nombre d'utilisateurs."),
         ("C", "Un problème informatique a provoqué la publication de données personnelles d'utilisateurs."),  # ← TB Q21=C
         ("D", "Un problème technique a regroupé et mélangé les données personnelles de millions d'utilisateurs.")],
    22: [("A", "Une conférence pour mieux connaître la loi."),
         ("B", "Une leçon de droit en ligne pour les étudiants."),
         ("C", "Une méthode pour se préparer à un examen."),   # ← TB Q22=C
         ("D", "Une réflexion sur le devoir moral des citoyens.")],
    # Q23 : very garbled OCR — left as Proposition A/B/C/D
    24: [("A", "Ils constituent un apport innovant pour la cuisine traditionnelle française."),
         ("B", "Ils font partie du folklore gastronomique de certaines régions du monde."),
         ("C", "Ils ont des qualités nutritionnelles supérieures aux aliments industriels."),
         ("D", "Ils représentent une véritable alternative alimentaire pour les hommes.")],  # ← TB Q24=D
    25: [("A", "L'engouement des Français pour ce produit est unique en Europe."),
         ("B", "Les enjeux sanitaires et commerciaux sont très importants."),  # ← TB Q25=B
         ("C", "Les laboratoires pharmaceutiques souhaitent en interdire la vente."),
         ("D", "Son utilisation est déjà encadrée par la loi dans certains pays européens.")],
    26: [("A", "Les autorités aéroportuaires canadiennes ne sont pas responsables de cet incident."),  # ← TB Q26=A
         ("B", "Les autorités canadiennes et Air France se partagent la responsabilité."),
         ("C", "La compagnie Air France n'est absolument pas responsable de cet incident."),
         ("D", "Les conditions météorologiques sont la principale cause de cet accident.")],
    27: [("A", "Le comportement discutable des climatologues."),  # ← TB Q27=A
         ("B", "Le désintérêt des autorités pour les événements climatiques."),
         ("C", "Le manque de moyens dont disposent les chercheurs."),
         ("D", "Les piètres critères de recrutement des météorologues.")],
    28: [("A", "L'accès trop facile au tourisme culturel."),
         ("B", "La marchandisation du tourisme culturel."),  # ← TB Q28=B
         ("C", "Le mauvais goût culturel des touristes."),
         ("D", "La valorisation du patrimoine culturel.")],

    # ── Niveau C2 ────────────────────────────────────────────────────────────
    29: [("A", "Les dépressifs ont tous une activité cérébrale plus active."),
         ("B", "La dépression serait liée à une forte activité cérébrale."),  # ← TB Q29=B
         ("C", "L'inactivité cérébrale accélère le processus de la dépression."),
         ("D", "Les personnes inactives sont plus enclines à la dépression nerveuse.")],
    30: [("A", "C'est un gage que l'homme est capable de discernement."),
         ("B", "C'est un sentiment pernicieux qui altère l'esprit critique."),  # ← TB Q30=B
         ("C", "C'est une colère saine provoquée par une action injuste."),
         ("D", "C'est une révolte intérieure qui fait avancer les hommes.")],
}

# ---------------------------------------------------------------------------
# Image-based questions: store the book page PNG so the UI shows the visual
# options. The Proposition A/B/C/D placeholder choices are kept as-is.
# ---------------------------------------------------------------------------
CO_IMAGE_ASSETS: dict[int, str] = {
    1:  str(OCR / "page-020.png"),  # scene shown while 4 spoken propositions are heard
    2:  str(OCR / "page-021.png"),
    3:  str(OCR / "page-021.png"),
    4:  str(OCR / "page-021.png"),
    8:  str(OCR / "page-022.png"),  # 4 weather image choices shown
    13: str(OCR / "page-023.png"),  # 4 transport image choices
}

TB_IMAGE_ASSETS: dict[int, str] = {
    3: str(OCR / "page-103.png"),   # image choices in TCF blanc
    4: str(OCR / "page-103.png"),
}


def qid(collection: str, group: str, number: int) -> str:
    import re
    safe_group = re.sub(r"[^a-z0-9]+", "-", group.lower()).strip("-")
    return f"{collection}:{safe_group}:q{number:03d}"


def patch(connection: sqlite3.Connection) -> None:
    updated_choices = 0
    updated_assets = 0

    # Clear mappings from older exports before applying the reviewed set.
    for num in (6, 9, 10):
        connection.execute(
            "DELETE FROM question_assets WHERE question_id = ?",
            (qid("abc-tcf", CO_GROUP, num),),
        )

    # ── Update CO text choices ──────────────────────────────────────────────
    for num, choices in CO_CHOICES.items():
        quid = qid("abc-tcf", CO_GROUP, num)
        for label, text in choices:
            cursor = connection.execute(
                "UPDATE answer_choices SET text = ? WHERE question_id = ? AND label = ?",
                (text, quid, label),
            )
            updated_choices += cursor.rowcount
        print(f"  CO Q{num:02d}: updated choices")

    # ── Update Test blanc text choices ─────────────────────────────────────
    for num, choices in TB_CHOICES.items():
        quid = qid("abc-tcf", TB_GROUP, num)
        for label, text in choices:
            cursor = connection.execute(
                "UPDATE answer_choices SET text = ? WHERE question_id = ? AND label = ?",
                (text, quid, label),
            )
            updated_choices += cursor.rowcount
        print(f"  TB Q{num:02d}: updated choices")

    # ── Store page images for image-based CO questions ──────────────────────
    for num, img_path in CO_IMAGE_ASSETS.items():
        if not Path(img_path).exists():
            print(f"  WARNING: image not found for CO Q{num}: {img_path}")
            continue
        quid = qid("abc-tcf", CO_GROUP, num)
        connection.execute(
            "INSERT OR REPLACE INTO question_assets(question_id, image_path) VALUES (?, ?)",
            (quid, img_path),
        )
        updated_assets += 1
        print(f"  CO Q{num:02d}: stored page image")

    # ── Store page images for image-based TB questions ──────────────────────
    for num, img_path in TB_IMAGE_ASSETS.items():
        if not Path(img_path).exists():
            print(f"  WARNING: image not found for TB Q{num}: {img_path}")
            continue
        quid = qid("abc-tcf", TB_GROUP, num)
        connection.execute(
            "INSERT OR REPLACE INTO question_assets(question_id, image_path) VALUES (?, ?)",
            (quid, img_path),
        )
        updated_assets += 1
        print(f"  TB Q{num:02d}: stored page image")

    print(f"\nDone: {updated_choices} choice rows updated, {updated_assets} image assets stored.")


def main() -> None:
    if not DB.exists():
        print(f"ERROR: catalog not found at {DB}")
        print("Run 'python -m apps.api.app.catalog_builder' first.")
        return
    connection = sqlite3.connect(DB)
    print("Patching ABC TCF answer choices …")
    patch(connection)
    connection.commit()
    connection.close()
    print("Committed.")


if __name__ == "__main__":
    main()
