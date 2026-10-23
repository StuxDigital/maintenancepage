"""The icon set: favicon.ico, apple-touch-icon.png and site.webmanifest at the root, the same
icon tags in every page's <head>, and (with PHP) the dev server serving them correctly."""
import json
import os
import shutil
import socket
import struct
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from helpers import ROOT, head, html_pages

TAGS = [
    '<link rel="icon" href="/favicon.ico" sizes="48x48">',
    '<link rel="icon" type="image/png" sizes="512x512" href="/assets/icon-512.png">',
    '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
    '<link rel="manifest" href="/site.webmanifest">',
]


def png_info(data):
    """(width, height, colour type) from a PNG's header."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    width, height, _depth, colour = struct.unpack(">IIBB", data[16:26])
    return width, height, colour


def find_php():
    local = os.path.join(os.environ.get("LOCALAPPDATA", "/nonexistent"), "Programs", "PHP", "7.4", "php.exe")
    for c in [os.environ.get("PHP_BIN"), "php74", "php7.4", local, "php"]:
        if c and shutil.which(c):
            return shutil.which(c)
        if c and Path(c).is_file():
            return c
    return None


class IconFilesTest(unittest.TestCase):
    def test_favicon_ico_holds_16_32_and_48px_pngs(self):
        data = (ROOT / "favicon.ico").read_bytes()
        _reserved, kind, count = struct.unpack("<HHH", data[:6])
        self.assertEqual(1, kind)
        sizes = []
        for i in range(count):
            entry = data[6 + 16 * i:22 + 16 * i]
            offset = struct.unpack("<I", entry[12:16])[0]
            w, h, _ = png_info(data[offset:offset + 32])
            sizes.append((w, h))
        self.assertEqual([(16, 16), (32, 32), (48, 48)], sorted(sizes))

    def test_apple_touch_icon_is_180px_and_opaque(self):
        # iOS fills transparency with black, so no alpha channel (colour type 2 is plain RGB)
        self.assertEqual((180, 180, 2), png_info((ROOT / "apple-touch-icon.png").read_bytes()))

    def test_manifest(self):
        m = json.loads((ROOT / "site.webmanifest").read_text(encoding="utf-8"))
        for key in ("name", "short_name", "theme_color", "background_color"):
            self.assertTrue(m.get(key), key)
        self.assertEqual("/", m["start_url"])
        self.assertEqual("browser", m["display"])
        by_purpose = {}
        for icon in m["icons"]:
            w, h, colour = png_info((ROOT / icon["src"].lstrip("/")).read_bytes())
            self.assertEqual(icon["sizes"], "%dx%d" % (w, h), icon["src"])
            by_purpose.setdefault(icon.get("purpose", "any"), []).append(icon["sizes"])
            if icon.get("purpose") == "maskable":
                self.assertEqual(2, colour, "the maskable icon needs an opaque background")
        self.assertEqual(["192x192", "512x512"], sorted(by_purpose["any"]))
        self.assertEqual(["512x512"], by_purpose["maskable"])

    def test_every_page_lists_the_same_icons(self):
        pages = html_pages()
        self.assertIn("404.html", pages)
        for page in pages:
            h = head(page)
            for tag in TAGS:
                self.assertEqual(1, h.count(tag), "%s: %s" % (page, tag))
            self.assertEqual(3, h.count('rel="icon"') + h.count('rel="apple-touch-icon"'), page + ": no other icon links")


@unittest.skipUnless(find_php() and (ROOT / ".github" / "dev-router.php").is_file(), "PHP or the dev router isn't available")
class DevServerTest(unittest.TestCase):
    """Smoke test: the pages and icons through the dev server's router, as GitHub Pages serves them."""

    @classmethod
    def setUpClass(cls):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        env = dict(os.environ, DEV_MODE="0")
        cls.server = subprocess.Popen([find_php(), "-S", "127.0.0.1:%d" % cls.port, "-t", str(ROOT),
                                       str(ROOT / ".github" / "dev-router.php")], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), 0.2).close()
                return
            except OSError:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait()

    def fetch(self, path):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path), timeout=10) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type", ""), e.read()

    def test_pages(self):
        for path in ["/", "/changelog", "/legal", "/legal/privacy", "/legal/terms", "/legal/cookies",
                     "/legal/imprint", "/legal/disclaimer", "/legal/opt-out"] + (
                         ["/sitemap/", "/sitemap.xml"] if (ROOT / "sitemap.xml").is_file() else []):
            status, _type, _body = self.fetch(path)
            self.assertEqual(200, status, path)
        status, _type, body = self.fetch("/no-such-page")
        self.assertEqual(404, status)
        self.assertIn(b"/favicon.ico", body)

    def test_icons(self):
        for path, kind in [("/favicon.ico", "image/"), ("/apple-touch-icon.png", "image/png"),
                           ("/site.webmanifest", "application/manifest+json"),
                           ("/assets/icon-192.png", "image/png"), ("/assets/icon-512.png", "image/png"),
                           ("/assets/icon-maskable-512.png", "image/png")]:
            status, ctype, body = self.fetch(path)
            self.assertEqual(200, status, path)
            self.assertTrue(ctype.startswith(kind), "%s: %s" % (path, ctype))
            self.assertEqual((ROOT / path.lstrip("/")).read_bytes(), body, path)


if __name__ == "__main__":
    unittest.main()
