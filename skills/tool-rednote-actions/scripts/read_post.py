# /// script
# requires-python = ">=3.11"
# dependencies = ["curl-cffi>=0.13"]
# ///
"""Retrieve one shared RedNote post and its images through anonymous HTTP."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


POST_HOSTS = {"xiaohongshu.com", "www.xiaohongshu.com", "rednote.com", "www.rednote.com"}
SHARE_HOSTS = POST_HOSTS | {"xhslink.com", "xhslink.cn"}
URL_PATTERN = re.compile(r"https?://[^\s\"<>，。；！？、【】《》]+")
STATE_PREFIX = re.compile(r"^\s*window\.__INITIAL_STATE__\s*=\s*")
STATE_TOKENS = re.compile(r'"(?:\\.|[^"\\])*"|\bundefined\b|new Map\(\[\]\)')
NOTE_ID = re.compile(r"^[0-9a-f]{24}$")


class ReadError(Exception):
    """The shared post could not be retrieved completely."""


class StateScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script and STATE_PREFIX.match(data):
            self.scripts.append(data)


def shared_url(text):
    for match in URL_PATTERN.finditer(text):
        url = match.group().rstrip(".,;!?)）]")
        parts = urlsplit(url)
        if parts.hostname in SHARE_HOSTS and not parts.username and not parts.password:
            return url
    raise ReadError("No supported RedNote share URL found.")


def post_id(url):
    parts = urlsplit(url)
    note_id = parts.path.rstrip("/").rsplit("/", 1)[-1]
    if parts.hostname not in POST_HOSTS or not NOTE_ID.fullmatch(note_id):
        raise ReadError("HTTP did not reach a post page (it may require login or a fresh link).")
    return note_id


def parse_note(html, note_id):
    parser = StateScripts()
    parser.feed(html)
    for script in reversed(parser.scripts):
        payload = STATE_PREFIX.sub("", script, count=1)
        payload = STATE_TOKENS.sub(
            lambda match: {"undefined": "null", "new Map([])": "[]"}.get(
                match.group(), match.group()
            ),
            payload,
        )
        try:
            state, _ = json.JSONDecoder().raw_decode(payload)
            note = state.get("note", {}).get("noteDetailMap", {}).get(note_id, {}).get("note")
            if not note:
                note = state.get("noteData", {}).get("data", {}).get("noteData")
            if not isinstance(note, dict) or note.get("noteId") != note_id:
                continue
            if not isinstance(note.get("desc"), str) or not isinstance(note.get("user"), dict):
                continue
            if not isinstance(note.get("imageList"), list):
                continue
            return note
        except (ValueError, AttributeError, TypeError):
            continue
    raise ReadError("Requested post content is absent or its embedded state cannot be parsed.")


def image_url(image):
    url = image.get("urlDefault") or image.get("url")
    if not url:
        url = next((entry.get("url") for entry in image.get("infoList", []) if entry.get("url")), None)
    if not isinstance(url, str):
        raise ReadError("Image has no download URL.")
    if url.startswith("//"):
        url = "https:" + url
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ReadError("Image URL is not HTTP.")
    return url


def image_extension(content, content_type):
    if not content_type.lower().startswith("image/"):
        raise ReadError("Image request returned non-image content.")
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    raise ReadError("Image bytes are not a supported PNG, JPEG, or WebP file.")


def request_response(session, url, **kwargs):
    try:
        response = session.get(url, **kwargs)
        response.raise_for_status()
        return response
    except Exception as error:
        # Convert failures only at the external HTTP client boundary.
        raise ReadError(f"HTTP request failed: {error}") from error


def download_images(session, images, output, referer):
    results = []
    for index, image in enumerate(images, 1):
        entry = {"index": index}
        try:
            url = image_url(image)
            entry["url"] = url
            response = request_response(session, url, headers={"Referer": referer})
            extension = image_extension(response.content, response.headers.get("Content-Type", ""))
            path = output / f"image-{index:02d}.{extension}"
            path.write_bytes(response.content)
            entry["path"] = str(path)
        except (ReadError, OSError, ValueError, TypeError, AttributeError) as error:
            entry["error"] = str(error)
        results.append(entry)
    return results


def read_post(session, url, output):
    response = request_response(session, url)
    note_id = post_id(response.url)
    note = parse_note(response.text, note_id)
    output.mkdir(parents=True, exist_ok=False)
    images = download_images(session, note["imageList"], output, response.url)
    result = {
        "status": "partial" if any("error" in image for image in images) else "complete",
        "source_url": url,
        "resolved_url": response.url,
        "note_id": note_id,
        "title": note.get("title", ""),
        "body": note["desc"],
        "author": note["user"].get("nickname") or note["user"].get("nickName", ""),
        "type": note.get("type", ""),
        "image_count": len(images),
        "downloaded_count": sum("path" in image for image in images),
        "images": images,
    }
    (output / "note.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("link", help="Complete post link or pasted share text")
    parser.add_argument("--output", required=True, type=Path, help="New directory for the post and images")
    args = parser.parse_args()
    try:
        url = shared_url(args.link)
        from curl_cffi.requests import Session
        with Session(impersonate="chrome", timeout=30, max_redirects=8) as session:
            result = read_post(session, url, args.output.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "complete" else 2
    except (ReadError, OSError, ValueError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
