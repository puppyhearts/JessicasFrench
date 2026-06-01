"""
Patch script: replace generic "Proposition A/B/C/D" answer choices in the
Réussir le TCF catalog with real text extracted from the book's transcription
section (pages 211-260 of the OCR'd PDF).

Also fixes:
  - ABC TCF Compréhension orale Q1-Q4 (spoken choices extracted from transcripts)
  - TV5monde Q5-D, Q6-A, Q11-D trailing OCR artifacts

Run from the repo root:
    python scripts/patch-reussir-choices.py
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "content" / "generated" / "catalog.sqlite"

# ---------------------------------------------------------------------------
# Réussir TCF choices, verified against REUSSIR_ANSWERS answer key.
# Keys are question numbers (1-based) within each CEFR level.
# ---------------------------------------------------------------------------

REUSSIR_CHOICES: dict[str, dict[int, list[tuple[str, str]]]] = {
    "A1": {
        1:  [("A", "Quelle belle ville !"),
             ("B", "L'eau est froide ! Rentrons !"),
             ("C", "Chut, tu vas lui faire peur !"),     # correct
             ("D", "Il pleut depuis trois jours sur cette plage.")],
        2:  [("A", "Voilà votre carte d'embarquement, monsieur."),
             ("B", "Vous avez des bagages à enregistrer ?"),  # correct
             ("C", "Je vous donne la chambre numéro 2."),
             ("D", "C'est pour envoyer un colis ?")],
        3:  [("A", "Au secours !"),
             ("B", "Au lit !"),
             ("C", "À table !"),    # correct
             ("D", "Allo !")],
        4:  [("A", "Mais, éteins la lumière !"),
             ("B", "Mais, allume la télé !"),
             ("C", "Mais, ouvre la fenêtre !"),
             ("D", "Mais, allume la lumière !")],  # correct
        5:  [("A", "laver la voiture !"),
             ("B", "prendre une douche !"),   # correct
             ("C", "essuyer la table !"),
             ("D", "ranger la salle de bain !")],
        6:  [("A", "une baguette, s'il vous plaît !"),   # correct
             ("B", "deux kilos de tomates, s'il vous plaît !"),
             ("C", "trois côtelettes, s'il vous plaît !"),
             ("D", "un bouquet de roses, s'il vous plaît !")],
        7:  [("A", "J'ai faim."),
             ("B", "J'ai soif."),
             ("C", "J'ai sommeil."),  # correct
             ("D", "J'ai chaud.")],
        8:  [("A", "Joyeux anniversaire !"),   # correct
             ("B", "Joyeux Noël !"),
             ("C", "Bonne fête !"),
             ("D", "Bonne année !")],
        9:  [("A", "Michael saute dans la piscine."),   # correct
             ("B", "Michael sort de la piscine."),
             ("C", "Michael nage dans la piscine."),
             ("D", "Michael n'a pas envie de se baigner.")],
        10: [("A", "La randonnée en montagne est un sport pour toute la famille."),
             ("B", "L'escalade est un sport qui peut être pratiqué par tous."),  # correct
             ("C", "Cet enfant aime l'équitation."),
             ("D", "La natation se pratique aussi bien en salle qu'en plein air.")],
        11: [("A", "Avec plaisir."),
             ("B", "Bien, et toi ?"),   # correct
             ("C", "Jean-Marc et toi ?"),
             ("D", "À la bibliothèque.")],
        12: [("A", "Certainement, j'adore le café."),
             ("B", "Je vous en prie."),
             ("C", "Je n'ai plus faim, merci."),
             ("D", "Volontiers, merci.")],   # correct
        13: [("A", "Il neige."),    # correct
             ("B", "Il est huit heures."),
             ("C", "Il y a trois heures."),
             ("D", "Cet après-midi.")],
        14: [("A", "Dans le 3e arrondissement."),  # correct
             ("B", "De Nice."),
             ("C", "Pour Sophie."),
             ("D", "Depuis 3 ans.")],
        15: [("A", "Il n'y a pas de fleuriste dans le quartier."),
             ("B", "Le fleuriste ferme dans 3 minutes."),
             ("C", "Le fleuriste est tout près."),  # correct
             ("D", "Il y a un fleuriste mais il faut 30 minutes pour y aller.")],
        16: [("A", "Raccrocher et rappeler après."),
             ("B", "Choisir une des options proposées."),
             ("C", "Attendre qu'un conseiller soit disponible."),  # correct
             ("D", "Se présenter.")],
    },
    "A2": {
        1:  [("A", "Cette omelette me paraît excellente !"),
             ("B", "Tu veux encore un peu de café ?"),
             ("C", "Monsieur, ce café est délicieux mais je voudrais un verre d'eau s'il vous plaît."),
             ("D", "Attention Carole, tu as mis trop de sucre sur ces beignets.")],  # correct
        2:  [("A", "Il attend le train."),
             ("B", "Il a manqué son train."),   # correct
             ("C", "Il va prendre le train."),
             ("D", "Il descend du train.")],
        3:  [("A", "j'ai pris mon parapluie !"),
             ("B", "j'ai vu mon parapluie !"),
             ("C", "j'ai oublié mon parapluie !"),  # correct
             ("D", "j'ai lancé mon parapluie !")],
        4:  [("A", "La vraie salade niçoise se compose d'anchois et d'artichauts."),  # correct
             ("B", "La préparation d'un magret de canard exige une grande concentration."),
             ("C", "La soupe aux champignons est ma spécialité."),
             ("D", "Pour la tarte Tatin, il me faut des pommes et du sucre.")],
        5:  [("A", "Combien vous voulez ?"),
             ("B", "Ah, je n'ai pas de monnaie sur moi."),
             ("C", "Un peu plus loin, au bout de la rue."),  # correct
             ("D", "Non, non, mais il n'y a pas de mal.")],
        6:  [("A", "Non, aucun."),
             ("B", "Non, rien."),    # correct
             ("C", "Non, personne."),
             ("D", "Non, tout le monde.")],
        7:  [("A", "Entendu, il vous attend à 14 heures."),
             ("B", "Non, nous ne faisons aucun remboursement, monsieur."),
             ("C", "Veuillez patienter s'il vous plaît."),  # correct
             ("D", "Oui, il est disponible pour un tennis.")],
        8:  [("A", "Non, je n'achète pas de saucisse !"),
             ("B", "Evidemment, c'est mon meilleur ami."),  # correct
             ("C", "Sans doute, mais la réunion est reportée."),
             ("D", "Oui, je vais faire du feu si tu veux.")],
        9:  [("A", "Le 12 mai prochain."),
             ("B", "Le 22 juin 1976."),  # correct
             ("C", "En 1990."),
             ("D", "À Bordeaux.")],
        10: [("A", "D'accord, à plus tard."),
             ("B", "Dans peu de temps."),
             ("C", "Il y a quelques heures."),
             ("D", "Il est neuf heures.")],  # correct
        11: [("A", "Victor s'est perdu."),   # correct
             ("B", "Victor a vu sa maman à l'accueil."),
             ("C", "Victor a travaillé au magasin."),
             ("D", "Victor travaille à l'accueil du magasin.")],
        12: [("A", "des températures très froides."),
             ("B", "beaucoup de pluie."),
             ("C", "une forte chaleur."),   # correct
             ("D", "une tempête de neige.")],
        13: [("A", "l'arrivée d'un train."),   # correct
             ("B", "le départ d'un train."),
             ("C", "un changement de voie."),
             ("D", "le retard d'un train.")],
        14: [("A", "Maintenant."),
             ("B", "Le lendemain."),  # correct
             ("C", "Avant le petit-déjeuner."),
             ("D", "Dans la soirée.")],
        15: [("A", "Elle est encore fatiguée."),  # correct
             ("B", "Elle va beaucoup mieux."),
             ("C", "Elle est trop mal pour voyager."),
             ("D", "Elle se sent très en forme.")],
        16: [("A", "attendre la fin de l'incident."),
             ("B", "emprunter la ligne 1."),
             ("C", "prendre le bus."),   # correct
             ("D", "monter dans le métro.")],
    },
    "B1": {
        1:  [("A", "Taisez-vous, laissez-moi écouter la conférence !"),
             ("B", "Viens, on repart : il y a vraiment trop de monde ici !"),
             ("C", "Tout est prêt, il ne reste plus que le conférencier qui ne va pas tarder à arriver."),  # correct
             ("D", "Je voudrais une table pour trois personnes, s'il vous plaît. C'est pour dîner.")],
        2:  [("A", "C'est un château médiéval."),
             ("B", "C'est une chaumière normande."),  # correct
             ("C", "C'est un mas provençal."),
             ("D", "C'est un immeuble moderne.")],
        3:  [("A", "Mme Duval souhaite changer son abonnement Internet."),
             ("B", "Mme Duval souhaite changer d'ordinateur."),
             ("C", "Mme Duval souhaite résilier son abonnement Internet."),
             ("D", "Mme Duval souhaite faire rétablir sa connexion Internet.")],  # correct
        4:  [("A", "Son interlocuteur ne répond pas à sa demande."),
             ("B", "Elle a déjà rencontré le problème plusieurs fois."),   # correct
             ("C", "Elle a un rendez-vous en fin de matinée."),
             ("D", "Elle a appelé l'opérateur à plusieurs reprises pendant la matinée.")],
        5:  [("A", "Agnès emménagera dans son nouvel appartement après-demain."),
             ("B", "Agnès peut déjà fixer la date de son déménagement."),
             ("C", "Agnès espère trouver l'appartement de ses rêves."),
             ("D", "Agnès espère pouvoir bientôt emménager dans son nouvel appartement.")],  # correct
        6:  [("A", "Elle est désespérée."),
             ("B", "Elle est déçue."),
             ("C", "Elle est confiante."),  # correct
             ("D", "Elle a peur.")],
        7:  [("A", "On annonce la fin de l'épreuve."),
             ("B", "On donne les consignes de passation de l'épreuve."),  # correct
             ("C", "On invite les candidats à sortir de la salle."),
             ("D", "On encourage les candidats à utiliser un dictionnaire.")],
        8:  [("A", "Elle a eu un accident de voiture."),
             ("B", "Elle s'est blessée en faisant du ski."),  # correct
             ("C", "Elle s'est cassé le bras en jouant au tennis."),
             ("D", "Elle s'est fait mal au bras en faisant le ménage.")],
        9:  [("A", "Il est angoissé."),
             ("B", "Il est enthousiaste."),
             ("C", "Il est navré."),  # correct
             ("D", "Il est sceptique.")],
        10: [("A", "à des étudiants français désirant étudier la culture."),
             ("B", "à des étudiants internationaux qui viennent en France."),  # correct
             ("C", "à des spécialistes d'Internet."),
             ("D", "à des établissements universitaires.")],
        11: [("A", "s'inscrire à l'université."),
             ("B", "obtenir un justificatif de sa scolarité."),  # correct
             ("C", "payer ses droits d'inscription."),
             ("D", "poser sa candidature définitive.")],
        12: [("A", "Elle a une expérience trop grande pour le poste mais un CV adéquat."),
             ("B", "Elle a un CV qui ne correspond pas à l'emploi et trop peu d'expérience."),
             ("C", "Son CV et son expérience sont parfaits pour le poste mais sa motivation est faible."),
             ("D", "Son CV et son expérience ne correspondent pas vraiment au type de poste proposé.")],  # correct
        13: [("A", "Il propose un recrutement sur le poste initialement publié avec période d'essai."),
             ("B", "Il propose un recrutement sur un autre poste non publié sans période d'essai."),
             ("C", "Il propose un recrutement sur un autre poste publié avec période d'essai."),  # correct
             ("D", "Il ne propose aucun recrutement dans l'immédiat.")],
        14: [("A", "Un compte épargne et un compte chèque."),
             ("B", "Une carte bleue à débit différé."),
             ("C", "Une carte bleue à débit immédiat et un compte chèque."),  # correct
             ("D", "Un compte épargne à 3 % et une carte à débit immédiat.")],
        15: [("A", "À la banque."),
             ("B", "Au poste de police."),  # correct
             ("C", "Chez le garagiste."),
             ("D", "À la poste.")],
        16: [("A", "une caravane."),
             ("B", "une voiture."),  # correct
             ("C", "une moto."),
             ("D", "une tondeuse.")],
        17: [("A", "Il hésite parce qu'elle n'est plus toute neuve."),
             ("B", "Il hésite parce qu'elle a trop de kilomètres."),
             ("C", "Il semble complètement conquis."),
             ("D", "Il aimerait la voir avant tout.")],  # correct
        18: [("A", "Parce qu'elle va s'en acheter une neuve."),
             ("B", "Parce qu'elle a besoin d'argent."),
             ("C", "Parce qu'elle ne veut pas la réparer."),
             ("D", "Parce qu'elle n'en a plus l'utilité.")],  # correct
        19: [("A", "Ils vont à un anniversaire."),
             ("B", "Ils partent en vacances."),
             ("C", "Ils fêtent l'anniversaire de la femme."),
             ("D", "Ils fêtent leur anniversaire de mariage.")],  # correct
        20: [("A", "Elle est furieuse mais remercie son mari."),
             ("B", "Elle est ravie et remercie son mari."),
             ("C", "Elle est furieuse et réprimande son mari."),  # correct
             ("D", "Elle est ravie et réprimande son mari.")],
    },
    "B2": {
        1:  [("A", "La cliente est locataire et veut devenir propriétaire."),
             ("B", "La cliente est locataire et cherche un appartement à louer."),  # correct
             ("C", "La cliente souhaite acheter un appartement de 80 m² minimum."),
             ("D", "La cliente souhaite louer son appartement F5 sur l'île Saint-Louis.")],
        2:  [("A", "La cliente accepte l'offre de l'agent immobilier."),
             ("B", "La cliente refuse l'offre de l'agent immobilier."),
             ("C", "La cliente demande un temps de réflexion."),  # correct
             ("D", "La cliente est séduite par le prix de l'appartement.")],
        3:  [("A", "À un baptême."),
             ("B", "À un mariage."),    # correct
             ("C", "À un enterrement."),
             ("D", "À une fête d'anniversaire.")],
        4:  [("A", "Elle voulait prendre le volant."),
             ("B", "Ils ont oublié quelque chose à la maison."),
             ("C", "Ils sont en retard."),   # correct
             ("D", "Elle a oublié d'acheter des fleurs.")],
        5:  [("A", "Elle a donné sa démission."),
             ("B", "Elle a été licenciée pour raisons économiques."),
             ("C", "Elle a décidé de trouver un emploi à l'étranger."),
             ("D", "Elle a terminé son stage de deux ans.")],  # correct
        6:  [("A", "Elle a donné sa démission."),
             ("B", "Elle a été licenciée pour raisons économiques."),  # correct
             ("C", "Elle a décidé de trouver un emploi à l'étranger."),
             ("D", "Elle a terminé son stage de deux ans.")],
        7:  [("A", "Il va embaucher la candidate et la rappeler avant lundi."),
             ("B", "Il refuse de se prononcer mais rappellera la candidate avant lundi."),  # correct
             ("C", "Il rappellera deux candidats avant la fin de la semaine."),
             ("D", "Il demande à la candidate de le rappeler avant la fin de la semaine.")],
        8:  [("A", "La définition du rôle de chacun dans la nouvelle famille."),  # correct
             ("B", "Le manque d'amour dans les familles recomposées."),
             ("C", "Le taux de rupture plus élevé lors d'une deuxième union."),
             ("D", "L'absence de modèle pour les familles recomposées.")],
        9:  [("A", "un voyage à l'étranger."),
             ("B", "une expérience dans le bénévolat."),  # correct
             ("C", "un premier emploi de terrain."),
             ("D", "une mission dans les relations internationales.")],
        10: [("A", "acquérir une expérience et voyager."),  # correct
             ("B", "éviter de faire appel à l'ANPE."),
             ("C", "enseigner dans une association."),
             ("D", "accomplir une mission pour valider son diplôme.")],
        11: [("A", "un spectacle à la Cathédrale de Lyon."),
             ("B", "une promenade dans les rues de la vieille ville."),
             ("C", "un spectacle du moyen âge."),
             ("D", "des illuminations à travers la ville.")],  # correct
        12: [("A", "Cette célébration remonte aux frères Lumière."),
             ("B", "La ville a échappé à une épidémie à l'époque de l'Empire romain."),
             ("C", "Lyon a été protégé d'un fléau pendant la période médiévale."),  # correct
             ("D", "Certains quartiers s'illuminent le 8 décembre au soir.")],
        13: [("A", "Lutter contre une maladie par l'information et la prévention."),  # correct
             ("B", "Mener des campagnes de médicalisation dans 6 pays africains."),
             ("C", "Proposer des dépistages et vaccinations aux populations isolées."),
             ("D", "Faire un reportage sur les conditions sanitaires le long du fleuve Zambèze.")],
        14: [("A", "Il faut se méfier : les prétendus rabais sont parfois trompeurs."),
             ("B", "Il faut comparer les articles entre eux avant tout achat."),
             ("C", "Les soldes sont souvent appliqués sur des modèles différents."),
             ("D", "Les rabais sont presque toujours appliqués sur des articles démodés.")],  # correct
        15: [("A", "Fidéliser leur clientèle."),
             ("B", "Attirer de nouveaux clients."),
             ("C", "Augmenter leur chiffre d'affaires en bradant tout leur stock."),
             ("D", "Faire croire au consommateur qu'il fait une affaire.")],  # correct
        16: [("A", "parce qu'il a dû attendre longtemps avant de pouvoir s'inscrire."),
             ("B", "parce que le cours qu'il voulait suivre est complet."),  # correct
             ("C", "parce que tous les cours en macro-économie sont déjà complets."),
             ("D", "parce que cette année, il s'y est pris trop tard.")],
        17: [("A", "Il va s'inscrire au cours de Deschard."),  # correct
             ("B", "Il va s'inscrire au cours de Leblanc."),
             ("C", "Il va attendre de savoir s'il peut intégrer le cours de Leblanc."),
             ("D", "Il va finaliser son emploi du temps dans la journée.")],
        18: [("A", "De fortes pluies ont fait plusieurs morts."),
             ("B", "Un village a été inondé la nuit dernière."),  # correct
             ("C", "Les habitants sont restés chez eux à cause d'orages violents."),
             ("D", "Des arbres se sont abattus sur des maisons, obligeant les habitants à fuir.")],
        19: [("A", "Il ne veut parler à personne, ni à M. Martin, ni à M. Ishi."),
             ("B", "Il devait voir M. Martin mais en fait, il va téléphoner à M. Ishi."),  # correct
             ("C", "Il veut voir M. Martin pour lui parler de sa performance."),
             ("D", "Il va appeler son directeur commercial afin de récupérer un contrat.")],
        20: [("A", "Certaines plantes et espèces sont en danger à cause des changements climatiques."),
             ("B", "Ce parc est très bien situé pour étudier la diversité des plantes et des espèces."),  # correct
             ("C", "Ce parc subit des changements de température très importants."),
             ("D", "L'altitude réduit la biodiversité du parc.")],
    },
    "C1": {
        1:  [("A", "Le vocabulaire français a une origine variée."),   # correct
             ("B", "Le vocabulaire français provient du latin."),
             ("C", "Le vocabulaire français a une longue histoire."),
             ("D", "Le vocabulaire français a fait l'objet de nombreuses statistiques.")],
        2:  [("A", "une soirée concert de danses et musiques du monde."),
             ("B", "une soirée concert et une entrée au musée."),  # correct
             ("C", "une soirée concert pour le 20 juin 2008."),
             ("D", "une entrée au musée pour le 21 juin 2008.")],
        3:  [("A", "Permettre aux gens du quartier de se rencontrer."),  # correct
             ("B", "Manger et boire dans la rue."),
             ("C", "Utiliser les tables et les chaises de la mairie."),
             ("D", "Célébrer le printemps.")],
        4:  [("A", "Il est exorbitant."),
             ("B", "Il est modéré."),
             ("C", "Il est nul."),   # correct
             ("D", "Il est proportionné aux bénéfices reçus.")],
        5:  [("A", "Les boîtes de nuit ne sont plus adaptées aux lois antitabac."),
             ("B", "Le coin fumeur des boîtes de nuit permet de continuer à profiter de la musique."),
             ("C", "Le coin fumeur permet de se reposer avant de retourner danser."),
             ("D", "Le coin fumeur des boîtes de nuit est une cellule repoussante.")],  # correct
        6:  [("A", "Le déplacement d'un ministre et le décès de deux jeunes."),  # correct
             ("B", "Les interventions récurrentes des médias."),
             ("C", "Une centaine de quartiers s'est enflammée."),
             ("D", "L'intervention d'un ministre et les médias.")],
        7:  [("A", "le fait de boire en abondance."),
             ("B", "une chanson médiévale."),
             ("C", "une flûte ou un flageolet."),  # correct
             ("D", "une clématite ou un paquebot.")],
        8:  [("A", "vacarme."),
             ("B", "désordre."),
             ("C", "verve."),  # correct
             ("D", "charivari.")],
        9:  [("A", "parce que les touristes aiment son pain."),
             ("B", "parce qu'un magazine a fait un article sur sa boulangerie."),
             ("C", "parce qu'il a reçu un prix prestigieux."),  # correct
             ("D", "parce que son pain est vendu dans les grandes épiceries.")],
        10: [("A", "utiliser des noisettes pour la croûte."),
             ("B", "pétrir la pâte plusieurs fois."),
             ("C", "laisser la pâte fermenter longtemps."),  # correct
             ("D", "utiliser davantage de levure.")],
        11: [("A", "Il est devenu socialement discriminatoire."),  # correct
             ("B", "Il est devenu trop accessible et n'a donc plus de valeur."),
             ("C", "Il ne prépare plus aux Grandes Écoles."),
             ("D", "Il n'est pas adapté pour un avenir professionnel.")],
        12: [("A", "Contrairement à Milan et New York, les effets de l'interdiction de fumer dans les lieux publics sont peu mesurables."),
             ("B", "Il y a eu récemment un faible retentissement avec seulement 15% en moins d'accidents vasculaires cérébraux et d'infarctus."),
             ("C", "Les effets de l'interdiction de fumer dans les lieux publics n'ont été mesurables que pendant une période de courte durée."),
             ("D", "Les urgences des hôpitaux sont de bons évaluateurs des effets de l'interdiction de fumer dans les lieux publics.")],  # correct
        13: [("A", "deux fois par mois."),
             ("B", "tous les deux mois."),   # correct
             ("C", "tous les ans."),
             ("D", "deux fois par an.")],
        14: [("A", "le vol de brevets industriels et leurs effets."),
             ("B", "la copie frauduleuse de certains produits."),  # correct
             ("C", "la mauvaise qualité de certains produits."),
             ("D", "la définition ambiguë de « produit original ».")],
        15: [("A", "Il est nuancé et pense qu'il faut faire preuve de souplesse."),
             ("B", "Il est catégorique : c'est un phénomène condamnable."),  # correct
             ("C", "Il explique que ce phénomène est crucial pour l'industrie."),
             ("D", "Il n'a pas d'opinion et souhaite comprendre ce phénomène.")],
        16: [("A", "Les jeunes sont peu mobiles et dépendants car se loger est difficile."),  # correct
             ("B", "Les jeunes qui font des études longues ont besoin de se loger à bas prix."),
             ("C", "Le chômage important qui touche les jeunes diplômés ne leur permet pas de se loger."),
             ("D", "La crise du logement touche les classes les plus modestes.")],
    },
    "C2": {
        1:  [("A", "Elle est facile à identifier et à définir."),
             ("B", "Elle a été inventée avant d'être découverte."),  # correct
             ("C", "Elle a été identifiée depuis longtemps mais posait des problèmes de mesure."),
             ("D", "Depuis 1930 environ, ses propriétés de messager sont reconnues et utilisées.")],
        2:  [("A", "Les deux verbes possèdent la même étymologie."),
             ("B", "Les deux verbes sont complémentaires mais d'usages différents."),
             ("C", "Clore est déjà moins utilisé au Moyen Âge."),
             ("D", "Clore est déjà un verbe défectif au Moyen Âge.")],  # correct
        3:  [("A", "car les villes de Québec et La Rochelle organisent une traversée de l'Atlantique."),  # correct
             ("B", "car l'explorateur qui a fondé Québec vient de La Rochelle."),
             ("C", "car les 400 ans de Québec sont aussi les 400 ans de La Rochelle."),
             ("D", "car Samuel de Champlain est né à La Rochelle.")],
        4:  [("A", "La Francophonie cherche à exporter son modèle économique en Afrique."),
             ("B", "La Francophonie doit s'adapter aux nouvelles réalités de la mondialisation."),  # correct
             ("C", "La Francophonie est concurrencée par des pays asiatiques sur le plan culturel."),
             ("D", "La Francophonie renforce sa coopération avec l'Amérique Latine.")],
        5:  [("A", "Le mot s'est spécialisé dans l'art du costume."),
             ("B", "Le mot s'est spécialisé dans l'habillement masculin."),
             ("C", "Le mot s'est généralisé à tous les pantalons."),  # correct
             ("D", "Le mot est devenu un costume antillais.")],
        6:  [("A", "La tendance contemporaine est de ne pas prononcer les consonnes finales."),
             ("B", "La tendance contemporaine est de prononcer les consonnes finales."),
             ("C", "Le mot legs vient du verbe léguer."),
             ("D", "Il faut prononcer le -s de legs comme dans but, août.")],  # correct
        7:  [("A", "La plupart des méridionaux aimeraient perdre l'accent du midi."),
             ("B", "Une minorité tient absolument à perdre l'accent du midi."),  # correct
             ("C", "Une minorité de méridionaux parle encore avec l'accent du midi."),
             ("D", "À l'heure actuelle, aucun méridional n'est fier d'avoir l'accent du midi.")],
        8:  [("A", "Elle pense que la perte de l'accent a finalement des conséquences positives."),
             ("B", "Elle pense que la perte de l'accent est un fléau qui touche certaines couches sociales."),  # correct
             ("C", "Elle pense que les méridionaux ont tort de vouloir perdre leur accent."),
             ("D", "Elle pense que perdre son accent est une question de milieu social.")],
        9:  [("A", "car les villes de Québec et La Rochelle organisent une traversée de l'Atlantique."),
             ("B", "car le fondateur de Québec vient de la région de La Rochelle."),  # correct
             ("C", "car les 400 ans de Québec sont aussi les 400 ans de La Rochelle."),
             ("D", "car Samuel de Champlain est né à La Rochelle.")],
        10: [("A", "Ils sont trop stricts ou trop laxistes."),
             ("B", "Ils ne sont pas assez impliqués dans l'éducation des ados."),
             ("C", "Ils ne donnent pas assez de limites."),  # correct
             ("D", "Ils ne les aident pas à vivre dans le monde des adultes.")],
        11: [("A", "Elle s'adresse aux enfants uniquement."),
             ("B", "Elle montre des baleines vivantes et des squelettes."),
             ("C", "Elle ne se concentre que sur les baleines."),
             ("D", "Elle évoque les fléaux qui menacent les espèces.")],  # correct
        12: [("A", "Un fossile pourvu d'un embryon a été découvert."),  # correct
             ("B", "Le plus vieux fossile du monde a été découvert en Australie."),
             ("C", "Un site paléontologique exceptionnel vient d'être découvert."),
             ("D", "Un nouveau gisement offre la possibilité de récolter des fossiles en 3 dimensions.")],
        13: [("A", "Une course de 2 CV entre le Mali et la France."),
             ("B", "Les célébrations organisées par les passionnés de 2 CV."),  # correct
             ("C", "Une évaluation du nombre de 2 CV en Afrique de l'Ouest."),
             ("D", "L'anniversaire du premier grand défilé de 2 CV.")],
        14: [("A", "Transport Québec va multiplier les radars à partir de l'automne."),  # correct
             ("B", "À partir de l'automne, quelques régions seulement vont voir apparaître des radars."),
             ("C", "Trop d'excès de vitesse ont été constatés récemment."),
             ("D", "Les automobilistes demandent instamment l'installation de radars.")],
        15: [("A", "Ils seront arrêtés sur le champ."),
             ("B", "Une photo et une amende leur seront envoyées."),  # correct
             ("C", "Ils auront un mois pour contacter le Ministère de la Justice."),
             ("D", "Ils auront une suspension de permis de 30 jours.")],
        16: [("A", "Elles ont éliminé le radon des centres hospitaliers et lancé une campagne auprès du grand public."),
             ("B", "Elles ont financé des recherches sur les conséquences d'une exposition prolongée au radon."),
             ("C", "Elles ont créé un centre de recherche pour exposer les dangers du radon."),
             ("D", "Elles ont informé le public et fait baisser le taux de radon considéré comme acceptable.")],  # correct
    },
}

# ---------------------------------------------------------------------------
# ABC TCF Compréhension orale Q1-Q4 — choices extracted from audio transcripts.
# These are "choose which spoken option matches the image" questions.
# ---------------------------------------------------------------------------

ABC_CO_EXTRA_CHOICES: dict[int, list[tuple[str, str]]] = {
    1: [("A", "Asseyez-toi."),
        ("B", "Montre vite."),
        ("C", "Prends ce train."),
        ("D", "Reste debout.")],   # correct=A
    2: [("A", "Apporte-moi le menu rapidement s'il te plaît."),
        ("B", "Je vais prendre un kilo de tomates bien mûres."),
        ("C", "Ma femme va prendre une tarte aux fruits."),   # correct=C
        ("D", "Mon frère voudrait un gâteau au chocolat.")],
    3: [("A", "J'ai beaucoup d'amis."),
        ("B", "Je pars en voyage."),
        ("C", "Je suis informaticienne."),  # correct=C
        ("D", "Je viens du Sénégal.")],
    4: [("A", "Oui, j'aime la musique."),
        ("B", "Oui, j'écoute la radio."),
        ("C", "Oui, je joue du piano."),   # correct=C
        ("D", "Oui, je suis au concert.")],
}

# ---------------------------------------------------------------------------
# TV5monde OCR artifacts to strip from choice text
# ---------------------------------------------------------------------------

TV5_ARTIFACTS: dict[str, dict[str, str]] = {
    "tv5monde:entra-nement-1:q005": {"D": "Voir un concert."},
    "tv5monde:entra-nement-1:q006": {"A": "Il sera absent vendredi matin."},
    "tv5monde:entra-nement-1:q011": {"D": "Il se revendique artiste avant tout."},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def qid(collection: str, group: str, number: int) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", group.lower()).strip("-")
    return f"{collection}:{safe}:q{number:03d}"


def patch(conn: sqlite3.Connection) -> None:
    choices_updated = 0

    # == 1. Réussir TCF ==
    LEVEL_TO_GROUP = {
        "A1": "A1", "A2": "A2", "B1": "B1", "B2": "B2", "C1": "C1", "C2": "C2",
    }
    for level, questions in REUSSIR_CHOICES.items():
        group = LEVEL_TO_GROUP[level]
        for qnum, choices in questions.items():
            stable_id = qid("reussir-tcf", group, qnum)
            for label, text in choices:
                cur = conn.execute(
                    "UPDATE answer_choices SET text = ? WHERE question_id = ? AND label = ?",
                    (text, stable_id, label),
                )
                choices_updated += cur.rowcount
        print(f"  Réussir {level}: updated {sum(len(v) for v in questions.values())} choice rows")

    # == 2. ABC TCF CO Q1-Q4 ==
    CO_GROUP = "Compréhension orale"
    for qnum, choices in ABC_CO_EXTRA_CHOICES.items():
        stable_id = qid("abc-tcf", CO_GROUP, qnum)
        for label, text in choices:
            cur = conn.execute(
                "UPDATE answer_choices SET text = ? WHERE question_id = ? AND label = ?",
                (text, stable_id, label),
            )
            choices_updated += cur.rowcount
    print(f"  ABC TCF CO Q1-Q4: updated spoken choices")

    # == 3. TV5monde trailing OCR artifacts ==
    for stable_id, fixes in TV5_ARTIFACTS.items():
        for label, clean_text in fixes.items():
            cur = conn.execute(
                "UPDATE answer_choices SET text = ? WHERE question_id = ? AND label = ?",
                (clean_text, stable_id, label),
            )
            choices_updated += cur.rowcount
    print(f"  TV5monde artifacts: cleaned up")

    print(f"\nTotal choice rows updated: {choices_updated}")


def main() -> None:
    if not DB.exists():
        print(f"ERROR: catalog not found at {DB}")
        print("Run 'npm run build-catalog' first.")
        return
    conn = sqlite3.connect(DB)
    print("Patching question choices …")
    patch(conn)
    conn.commit()
    conn.close()
    print("Committed.")


if __name__ == "__main__":
    main()
