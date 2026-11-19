"""Watch MedUni Wien KPJ availability using only the Python standard library."""

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

PAGE_URL = "https://kinder-jugendheilkunde.meduniwien.ac.at/studium-aus-und-weiterbildung/klinisch-praktisches-jahr-kpj/"
NTFY_URL = "https://ntfy.sh/kpj-restplatz-1ec30273"
REMINDER_SECONDS = 4 * 60 * 60


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1
        if not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def parse_count(html):
    parser = PageText()
    parser.feed(html)
    matches = re.findall(r"Aktuelle\s+Restplätze\s*:\s*(\S+)", "".join(parser.parts), re.IGNORECASE)
    if len(matches) != 1 or not re.fullmatch(r"[0-9]+", matches[0]):
        raise ValueError("Expected exactly one 'Aktuelle Restplätze: N' with a nonnegative integer")
    return int(matches[0])


def fetch_page():
    request = Request(PAGE_URL, headers={"User-Agent": "kpj-restplatz-watcher/1.0"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode(response.headers.get_content_charset() or "utf-8")


def notify(message, *, urgent=False):
    request = Request(NTFY_URL, data=message.encode("utf-8"), headers={
        "Title": "KPJ places available" if urgent else "KPJ watcher status",
        "Priority": "high" if urgent else "default",
        "Click": PAGE_URL,
    }, method="POST")
    with urlopen(request, timeout=30) as response:
        response.read()


def next_state(previous, count, error, now):
    if error:
        return {"error": error}, error != previous.get("error")
    alert = count > 0 and (
        previous.get("count") != count
        or now - previous.get("last_alert", 0) >= REMINDER_SECONDS
    )
    return {"count": count, "last_alert": now if alert else previous.get("last_alert", 0)}, alert


def main():
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument("--dry-run", action="store_true", help="Never send notifications or write state")
    args_parser.add_argument("--test-notification", action="store_true", help="Send only a test notification")
    args_parser.add_argument("--state", type=Path, default=Path("state.json"))
    args = args_parser.parse_args()
    if args.test_notification:
        if not args.dry_run:
            notify("Test notification from the KPJ Restplatz watcher.")
        print("Test notification " + ("skipped (dry-run)." if args.dry_run else "sent."))
        return

    previous = json.loads(args.state.read_text()) if args.state.exists() else {}
    count = None
    error = None
    try:
        page = fetch_page()
    except Exception as exc:
        error = "Page fetch failed"
        print(f"{error}: {exc}")
    else:
        try:
            count = parse_count(page)
        except ValueError as exc:
            error = "Could not parse availability"
            print(f"{error}: {exc}")
    state, alert = next_state(previous, count, error, int(time.time()))
    print(f"Parsed number: {count}" if error is None else f"Watcher error: {error}")
    print(f"Notification: {'needed' if alert else 'not needed'}" + (" (dry-run; not sent)" if args.dry_run else ""))
    if not args.dry_run:
        if alert:
            notify(error or f"Aktuelle Restplätze: {count}. Apply by email; see the KPJ page.", urgent=error is None)
        temporary = args.state.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(args.state)


if __name__ == "__main__":
    main()
