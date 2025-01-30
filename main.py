from os import lstat

import requests

from bs4 import BeautifulSoup
from typing import Any, Generator
from datetime import datetime, timedelta, date
from collections import defaultdict


def get_click_tt_html() -> str:
    payload = {
        "searchType": "0",
        "searchTimeRange": "4",
        "searchTimeRangeFrom": "",
        "searchTimeRangeTo": "",
        "selectedTeamId": "WONoSelectionString",
        "club": "33194",
        "searchMeetings": "Suchen",
    }
    r = requests.post('https://www.click-tt.ch/cgi-bin/WebObjects/nuLigaTTCH.woa/wa/clubMeetings',
                      data=payload)
    return r.text


def parse_click_tt(html_text: str) -> list[dict[str, str]]:
    entries = []

    soup = BeautifulSoup(html_text, 'html.parser')

    cols = [
        "day",
        "date",
        "time",
        "location",
        "round",
        "league",
        "home team",
        "-",
        "guest team",
    ]

    last_day = None
    last_date = None
    for r in soup.find("table", class_="result-set").find_all("tr"):
        values = []

        for i in r.find_all("td"):
            values.append(i.get_text().strip().strip('\n'))
        values_dict = dict(zip(cols, values))
        values_dict.pop('-', None)

        # maybe populate empty dates
        if values_dict["day"]:
            last_day = values_dict["day"]
        elif last_day:
            values_dict["day"] = last_day

        if values_dict["date"]:
            last_date = values_dict["date"]
        elif last_date:
            values_dict["date"] = last_date

        entries.append(values_dict)
    return entries


def filter_home_matches(matches: list[dict[str, str]]) -> list[dict[str, str]]:
    return [m for m in matches if "home team" in m and "urdorf" in m["home team"].lower()]


def add_o40(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for m in matches:
        m["O40"] = "O40" in m["league"]
    return matches


def parse_date(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for m in matches:
        m["date parsed"] = datetime.strptime(m["date"], "%d.%m.%Y").date()
    return matches


def group_matches_by_date(matches: list[dict[str, Any]]) -> dict[date, list[dict[str, Any]]]:
    dates = defaultdict(list)
    for m in matches:
        dates[m["date parsed"]].append(m)
    return dates


def generate_all_training_dates(start_date: date = date.today(), days: int = 40) -> Generator[date]:
    return (j for j in (start_date + timedelta(days=i) for i in range(days)) if j.weekday() in {0, 2, 4})


def german_day_name_short(day: int):
    return {
        0: "Mo",
        2: "Mi",
        4: "Fr",
    }.get(day, "")


def generate_match_html(matches: list[dict[str, Any]]) -> str:
    html = ""
    for m in matches:
        if m["O40"]:
            html += "O40 "
        html += f"{m['home team']} vs {m['guest team']}<br />"
    return html


def generate_training_html(matches: list[dict[str, Any]], d: date) -> str:
    html = ""
    if len(matches) < 2:
        public = ""
        if d.weekday() == 0:
            public += " - <strong>Tischtennis für Alle!</strong>"
        html += f"Training{public}"
    else:
        html += "<strong>Kein Training!</strong>"
    html += "<br />"
    html += generate_match_html(matches)
    return html


def generate_date_html(d: date, matches: dict[date, list[dict[str, Any]]]):
    return f"""<td>{german_day_name_short(d.weekday())}</td>
    <td>{d.strftime("%d.%m.%Y")}</td>
    <td>{generate_training_html(matches.get(d, []), d)}</td>"""


def generate_homepage_html(grouped_matches: dict[date, list[dict[str, Any]]], training_dates: list[date]) -> str:
    html = ""
    for i in training_dates:
        html += f"""<tr>
    {generate_date_html(i, grouped_matches)}
</tr>
"""
    return html


def main():
    click_tt_html = get_click_tt_html()
    matches = parse_click_tt(click_tt_html)
    home_matches = parse_date(add_o40(filter_home_matches(matches)))
    grouped_matches = group_matches_by_date(home_matches)
    print(generate_homepage_html(grouped_matches, generate_all_training_dates()))


if __name__ == '__main__':
    main()
