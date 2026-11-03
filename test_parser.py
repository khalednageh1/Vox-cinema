"""Offline test: parser + notification formatting on HTML shaped like the VOX movie page."""
import os

os.environ["NTFY_TOPIC"] = "test"

import monitor  # noqa: E402

SAMPLE = """
<html><body>
<h1>Avengers: Doomsday</h1>
<ul class="dates">
  <li>Wed 16 Dec</li>
  <li><a href="/movies/avengers-doomsday?d=20261217#showtimes">Thu 17 Dec</a></li>
  <li><a href="/movies/avengers-doomsday?d=20261218#showtimes">Fri 18 Dec</a></li>
</ul>
<div id="showtimes">
  <h3>City Centre Alexandria</h3>
  <ol><li><strong>Standard</strong>
    <ol><li><a href="/booking/0032-169667">10:15am</a></li><li><a href="/booking/0032-169666">2:00pm</a></li></ol>
  </li></ol>
  <h3>City Centre Almaza</h3>
  <ol>
    <li><strong>GOLD</strong><ol><li>11:15am</li><li>3:00pm</li></ol></li>
    <li><strong>Standard</strong><ol><li>11:45am</li></ol></li>
  </ol>
  <h3>Mall of Egypt</h3>
  <ol><li><strong>GOLD</strong><ol><li>12:15pm</li></ol></li></ol>
</div>
<h2>Stay in touch</h2>
</body></html>
"""

title, links, sessions = monitor.parse_page(SAMPLE)
assert title == "Avengers: Doomsday", title
assert links == ["20261217", "20261218"], links
assert sessions == {
    ("City Centre Alexandria", "Standard", "10:15am"),
    ("City Centre Alexandria", "Standard", "2:00pm"),
    ("City Centre Almaza", "GOLD", "11:15am"),
    ("City Centre Almaza", "GOLD", "3:00pm"),
    ("City Centre Almaza", "Standard", "11:45am"),
    ("Mall of Egypt", "GOLD", "12:15pm"),
}, sessions

items = [
    {"slug": "x", "title": title, "date": "20261217", "cinema": c, "format": f, "time": t}
    for c, f, t in sorted(sessions)
]
text = monitor.format_new(items)
assert "City Centre Almaza (GOLD): 11:15am, 3:00pm" in text, text
print(text)
print("\nALL OK")

# ---- date window test: only 24-31 Dec tabs are fetched/kept ----
def fake_page(day_links, cinema_time):
    lis = "".join(f'<li><a href="/movies/x?d={d}#showtimes">{d}</a></li>' for d in day_links)
    return (f"<h1>X</h1><ul>{lis}</ul><div id='showtimes'><h3>Mall of Egypt</h3>"
            f"<strong>GOLD</strong><ol><li>{cinema_time}</li></ol></div>")

calls = []
def fake_fetch(url, retries=3):
    calls.append(url)
    if "?d=" in url:
        return fake_page([], "9:00pm")
    # default page = 23 Dec; tabs 24..31 Dec plus 1 Jan (out of window)
    return fake_page([f"202612{d}" for d in range(24, 32)] + ["20270101"], "1:00pm")

monitor.fetch = fake_fetch
monitor.time.sleep = lambda s: None
_, found = monitor.collect_movie("x")
dates = sorted({v["date"] for v in found.values()})
assert dates == [f"202612{d}" for d in range(24, 32)], dates
assert not any("20270101" in c for c in calls) and not any("20261223" in c for c in calls), calls
print("DATE WINDOW OK:", dates[0], "->", dates[-1])
