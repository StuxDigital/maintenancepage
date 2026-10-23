"""The Discord component embeds pre-built into each page's <head> by scripts/build-head-tags.py,
checked against Discord's rules: one Container at the root, link buttons using only allowed keys,
at most 40 components, and 3,000 bytes at most.
https://docs.discord.com/developers/link-previews/component-embeds"""
import json
import re
import unittest

from helpers import html_pages, load_script, read

build = load_script("build-head-tags")
OPEN = '<script id="discord:component-embed" type="application/json">'
TAG = re.compile(re.escape(OPEN) + r"(.*?)</script>", re.S)


def flatten(component):
    """Every component in the tree, the root included."""
    found = [component]
    for child in component.get("components", []) + ([component["accessory"]] if "accessory" in component else []):
        found += flatten(child)
    return found


def headline(payload):
    """The text of the first section, where every embed puts its title and description."""
    return payload["component"]["components"][0]["components"][0]["content"]


class DiscordEmbedTest(unittest.TestCase):
    def assert_valid_embed(self, tag, label):
        self.assertTrue(tag.startswith(OPEN) and tag.endswith("</script>"), label + ": embed left out or malformed")
        data = tag[len(OPEN):-len("</script>")]
        self.assertLessEqual(len(data.encode("utf-8")), 3000, label + ": over 3,000 bytes")
        self.assertNotIn("$1", data, label + ": a stray regex group")
        payload = json.loads(data)
        self.assertEqual(["component"], list(payload), label)
        self.assertEqual(17, payload["component"]["type"], label + ": the root is one Container")
        self.assertEqual(0x38BDF8, payload["component"]["accent_color"], label + ": the Stux.Digital brand colour")
        everything = flatten(payload["component"])
        self.assertLessEqual(len(everything), 40, label)
        for c in everything:
            self.assertIn(c["type"], [1, 2, 9, 10, 11, 12, 14, 17], label)
            if c["type"] == 17:
                self.assertIs(payload["component"], c, label + ": no nested Containers")
            if c["type"] == 2:
                self.assertEqual(5, c["style"], label + ": link buttons only")
                self.assertLessEqual(set(c), {"id", "type", "url", "style", "label", "emoji", "disabled"}, label)
                self.assertRegex(c["url"], r"^https?://", label)
        return payload

    def test_every_page_has_one_valid_embed(self):
        for src, path in build.PAGES:
            tags = TAG.findall(read(src))
            self.assertEqual(1, len(tags), src)
            payload = self.assert_valid_embed(OPEN + tags[0] + "</script>", src)
            if src != "index.html":
                self.assertIn("](%s%s)" % (build.BASE_URL, path), headline(payload), src + ": links to itself")

    def test_every_page_is_listed(self):
        self.assertEqual(sorted(html_pages()), sorted([src for src, _ in build.PAGES] + build.ERROR_PAGES))

    def test_error_pages_have_no_embed(self):
        for src in build.ERROR_PAGES:
            self.assertNotIn("discord:component-embed", read(src), src)

    def test_committed_pages_are_up_to_date(self):
        stale = [src for src, text in build.build().items() if read(src) != text]
        self.assertEqual([], stale, "run python scripts/build-head-tags.py")

    def test_home_embed_says_what_the_page_is(self):
        payload = self.assert_valid_embed(build.discord_home_embed("Back soon."), "home")
        self.assertIn("# [Under maintenance](%s/)" % build.BASE_URL, headline(payload))
        self.assertIn("**Back soon.**", headline(payload))

    def test_legal_embed_links_every_legal_page(self):
        payload = self.assert_valid_embed(
            build.discord_legal_embed("Boring Legal Stuff", "d", build.BASE_URL + "/legal"), "legal")
        text = json.dumps(payload)
        for _name, path in build.LEGAL_PAGES:
            self.assertIn(build.BASE_URL + path, text)

    def test_markdown_in_data_is_escaped(self):
        # One backslash before each special character, never a stray "$1"
        self.assertEqual(r"\*\*bold\*\* a\_b", build.discord_md("**bold** a_b"))
        self.assertEqual(r"\*\*bold\*\* \[x\](y) a\_b \~\~s\~\~ \`c\` \|\|p\|\| \\",
                         build.discord_md("**bold** [x](y) a_b ~~s~~ `c` ||p|| \\"))
        self.assertEqual("\\# heading\n\\- list\n\\> quote\nmid # - > stays",
                         build.discord_md("# heading\n- list\n> quote\nmid # - > stays"))
        self.assertNotIn("$1", build.discord_md("**bold** a_b"))

    def test_escaped_data_reaches_the_embed_intact(self):
        payload = self.assert_valid_embed(
            build.discord_page_embed("A_b *c*", "# not a heading", "https://example.com/x"), "escaped")
        self.assertIn("## [A\\_b \\*c\\*](https://example.com/x)\n\\# not a heading", headline(payload))
        self.assertNotIn("$1", headline(payload))

    def test_script_cant_be_closed_early(self):
        tag = build.discord_page_embed("</script><b>x", "d", "https://example.com/x")
        self.assertEqual(1, tag.count("</script>"), "only the tag's own closing")
        # JSON's <\/ decodes back to </, so Discord still shows the title as written
        self.assertIn("## [</script><b>x](", headline(json.loads(tag[len(OPEN):-len("</script>")])))

    def test_over_the_limit_falls_back_to_the_normal_preview(self):
        tag = build.discord_page_embed("T", "Long description. " * 300, "https://example.com/x")
        self.assertTrue(tag.startswith("<!-- discord:component-embed left out"), tag[:60])


if __name__ == "__main__":
    unittest.main()
