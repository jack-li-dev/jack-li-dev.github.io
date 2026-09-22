import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "AGENTS.md"


class PublicationReentryContractTests(unittest.TestCase):
    """Keep fresh-session English publication gates aligned with the Router owner."""

    def test_english_release_projection_keeps_mastery_humanizer_red_team_order(self):
        """Fresh sessions must recover the current publication sequence from durable repo rules."""
        text = AGENTS.read_text(encoding="utf-8")

        required = [
            "fortress-publish-router Pre-Publish Human Mastery Refresh",
            "humanizer (one default review/edit pass; NO-OP allowed)",
            "semantic diff against pre-edit copy and Canonical Knowledge",
            "load-bearing claim revalidation",
            "GPT-6 Final Red Team",
            "Human final approval",
            "assistant memory as publication-readiness evidence",
        ]
        for needle in required:
            self.assertIn(needle, text)

        start = text.index("English release copy:")
        mastery = text.index("fortress-publish-router Pre-Publish Human Mastery Refresh", start)
        humanizer = text.index("humanizer (one default review/edit pass; NO-OP allowed)", start)
        semantic = text.index("semantic diff against pre-edit copy and Canonical Knowledge", start)
        red_team = text.index("GPT-6 Final Red Team", start)
        human_final = text.index("Human final approval", start)

        self.assertLess(mastery, humanizer)
        self.assertLess(humanizer, semantic)
        self.assertLess(semantic, red_team)
        self.assertLess(red_team, human_final)

    def test_english_release_projection_does_not_restore_stop_slop_default_chain(self):
        """Stop-Slop stays exceptional instead of becoming a mandatory second rewrite pass."""
        text = AGENTS.read_text(encoding="utf-8")
        english = text.split("English release copy:", 1)[1].split(
            "Simplified Chinese release copy:", 1
        )[0]

        self.assertNotIn("stop-slop\n-> humanizer", english)
        self.assertIn("Never automatically chain them after Humanizer", english)


if __name__ == "__main__":
    unittest.main()
