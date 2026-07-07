#!/usr/bin/env python3
"""GitHub コントリビューションの半年分ヒートマップ SVG を生成する。

標準入力に GraphQL contributionCalendar のレスポンス JSON を受け取り、
標準出力へ SVG を書き出す。

使い方:
    gh api graphql -f query=... | python3 scripts/generate_activity.py > assets/activity.svg
    gh api graphql -f query=... | python3 scripts/generate_activity.py --theme dark > assets/activity-dark.svg
"""

import argparse
import json
import sys
from datetime import date

# デザイントークン (paper-summary 準拠)
THEMES = {
    "light": {
        "canvas": "#FAF9F5",
        "ink": "#141413",
        "muted": "#6C6A64",
        "muted_soft": "#8E8B82",
        "levels": ["#F0EBE1", "#F2D4C5", "#E3A88C", "#CC785C", "#A9583E"],
    },
    "dark": {
        "canvas": "#181715",
        "ink": "#FAF9F5",
        "muted": "#A09D96",
        "muted_soft": "#8E8B82",
        "levels": ["#26231F", "#4E3226", "#8A4F38", "#CC785C", "#E89B7B"],
    },
}

SERIF = "'Hiragino Mincho ProN', 'Yu Mincho', Georgia, serif"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', sans-serif"

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# レイアウト
CELL = 16
GAP = 4
PITCH = CELL + GAP
PAD = 28
LEFT = PAD + 34   # 曜日ラベル分
TOP = 76          # タイトル + 月ラベル分


def level(count: int) -> int:
    """コミット数を 5 段階の濃度に量子化する。"""
    if count == 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=["light", "dark"], default="light")
    args = parser.parse_args()
    theme = THEMES[args.theme]
    canvas, ink = theme["canvas"], theme["ink"]
    muted, muted_soft = theme["muted"], theme["muted_soft"]
    level_colors = theme["levels"]

    data = json.load(sys.stdin)
    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    n_weeks = len(weeks)
    grid_w = n_weeks * PITCH - GAP
    grid_h = 7 * PITCH - GAP
    width = LEFT + grid_w + PAD
    height = TOP + grid_h + PAD

    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Commit activity heatmap, last 6 months">',
        f'<rect width="{width}" height="{height}" rx="12" fill="{canvas}"/>',
        # タイトル (セリフ) と合計 (右寄せ)
        f'<text x="{PAD}" y="40" font-family="{SERIF}" font-size="20" '
        f'letter-spacing="0.3" fill="{ink}">Commit Activity</text>',
        f'<text x="{width - PAD}" y="40" text-anchor="end" font-family="{SANS}" '
        f'font-size="12" fill="{muted}">{total} contributions in the last 6 months</text>',
    ]

    # 月ラベル (月が変わる週の上に表示)
    prev_month = None
    for i, week in enumerate(weeks):
        first_day = date.fromisoformat(week["contributionDays"][0]["date"])
        if first_day.month != prev_month:
            if prev_month is not None or i == 0:
                x = LEFT + i * PITCH
                parts.append(
                    f'<text x="{x}" y="{TOP - 8}" font-family="{SANS}" '
                    f'font-size="11" fill="{muted_soft}">'
                    f'{MONTH_LABELS[first_day.month - 1]}</text>'
                )
            prev_month = first_day.month

    # 曜日ラベル (Mon / Wed / Fri)
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = TOP + row * PITCH + CELL - 4
        parts.append(
            f'<text x="{PAD}" y="{y}" font-family="{SANS}" '
            f'font-size="10" fill="{muted_soft}">{label}</text>'
        )

    # セル (週 × 曜日、日曜始まり)
    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            row = (d.weekday() + 1) % 7  # Sun=0 .. Sat=6
            x = LEFT + i * PITCH
            y = TOP + row * PITCH
            color = level_colors[level(day["contributionCount"])]
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="4" fill="{color}"><title>{day["date"]}: '
                f'{day["contributionCount"]}</title></rect>'
            )

    # 凡例 (右下)
    legend_y = height - PAD + 10
    legend_x = width - PAD - 5 * (CELL - 4 + 3) - 70
    parts.append(
        f'<text x="{legend_x - 8}" y="{legend_y + 9}" text-anchor="end" '
        f'font-family="{SANS}" font-size="10" fill="{muted_soft}">Less</text>'
    )
    for i, color in enumerate(level_colors):
        x = legend_x + i * (CELL - 4 + 3)
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="{CELL - 4}" height="{CELL - 4}" '
            f'rx="3" fill="{color}"/>'
        )
    parts.append(
        f'<text x="{legend_x + 5 * (CELL - 4 + 3) + 8}" y="{legend_y + 9}" '
        f'font-family="{SANS}" font-size="10" fill="{muted_soft}">More</text>'
    )

    parts.append("</svg>")
    sys.stdout.write("\n".join(parts) + "\n")


if __name__ == "__main__":
    main()
