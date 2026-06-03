import unittest
from unittest.mock import patch

from apps.api.app.audio import segment_listening_track
from apps.api.app.catalog_builder import extract_embedded_choices
from apps.api.app.parser import parse_answer_key, parse_questions_from_page, section_for
from apps.api.app.source_extractors import _choices


class ParserTests(unittest.TestCase):
    def test_sections_follow_tv5monde_ranges(self):
        self.assertEqual(section_for(15), "listening")
        self.assertEqual(section_for(16), "grammar")
        self.assertEqual(section_for(25), "grammar")
        self.assertEqual(section_for(26), "reading")

    def test_extracts_question_and_choices(self):
        page = """
        27. Lisez les documents. Choisissez la bonne réponse.
        Quelle réponse convient ?
        A La première réponse.
        B La deuxième réponse.
        C La troisième réponse.
        D La quatrième réponse.
        Entraînement au TCF
        """
        parsed = parse_questions_from_page(page, 12)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].number, 27)
        self.assertEqual(parsed[0].section, "reading")
        self.assertEqual([choice.label for choice in parsed[0].choices], ["A", "B", "C", "D"])

    def test_extracts_answers_from_series_one_grid(self):
        grid = """
        Corrigés
        Première partie    Compréhension orale
             A B C D    A B C D
        1    □ □  □ 6 □  □ □
        Deuxième partie    Maîtrise des structures de la langue
        1     □ □ □ 5 □ □ □ 
        Troisième partie   Compréhension écrite
        1    □  □ □ 6 □ □ □ 
        """
        self.assertEqual(parse_answer_key(grid), {1: "C", 6: "B", 16: "A", 20: "D", 26: "B", 31: "D"})

    def test_extracts_grammar_suffix_after_choices(self):
        page = """
        16. Choisissez la bonne réponse et cochez la bonne réponse.
        A Combien
        B Comment
        C Où
        D Quand
        … coûte ce livre ?
        """
        question = parse_questions_from_page(page, 8)[0]
        self.assertEqual(question.prompt, "… coûte ce livre ?")
        self.assertEqual(question.choices[-1].text, "Quand")

    def test_extracts_compact_grammar_choice(self):
        page = """
        17. Choisissez la bonne réponse et cochez la bonne réponse.
        Il prend le métro…
        Aà
        B après
        C pour
        D vers
        … aller travailler.
        """
        question = parse_questions_from_page(page, 8)[0]
        self.assertEqual(question.prompt, "Il prend le métro… aller travailler.")
        self.assertEqual([choice.label for choice in question.choices], ["A", "B", "C", "D"])
        self.assertEqual(question.choices[0].text, "à")

    def test_extracts_ocr_choices(self):
        block = """
        Réponse D.
        A. La première réponse.
        B. La deuxième réponse.
        C. La troisième réponse.
        D. La quatrième réponse.
        """
        self.assertEqual(
            _choices(block),
            [
                ("A", "La première réponse."),
                ("B", "La deuxième réponse."),
                ("C", "La troisième réponse."),
                ("D", "La quatrième réponse."),
            ],
        )

    def test_extracts_ocr_checkbox_choices(self):
        block = """
        [] A. La première réponse.
        LI B. La deuxième réponse.
        C1 C. La troisième réponse.
        L] D. La quatrième réponse.
        """
        self.assertEqual(
            _choices(block),
            [
                ("A", "La première réponse."),
                ("B", "La deuxième réponse."),
                ("C", "La troisième réponse."),
                ("D", "La quatrième réponse."),
            ],
        )

    def test_extracts_tcf_file_choices_embedded_in_transcript(self):
        transcript = "A. Allez y, entrez. B. Asseyez-vous, je vous en prie. C. Fermez la porte, s'il vous plaît. D. Merci pour ce café."
        self.assertEqual(
            extract_embedded_choices(transcript),
            [
                ("A", "Allez y, entrez"),
                ("B", "Asseyez-vous, je vous en prie"),
                ("C", "Fermez la porte, s'il vous plaît"),
                ("D", "Merci pour ce café"),
            ],
        )

    @patch("apps.api.app.audio._duration", return_value=180.0)
    @patch("apps.api.app.audio.detect_silences")
    def test_segments_track_using_long_pauses(self, detect_silences, _duration):
        detect_silences.return_value = [(float(index * 10), float(index * 10 + 9)) for index in range(1, 15)]
        segments = segment_listening_track("track.mp3")
        self.assertEqual(len(segments), 15)
        self.assertEqual(segments[0].start_seconds, 0.0)
        self.assertEqual(segments[-1].end_seconds, 180.0)


if __name__ == "__main__":
    unittest.main()
