"""技術スタックのアイコンSVG（assets/skills.svg / skills-dark.svg）を生成する。

assets/icons/ 配下のアイコンを、カテゴリラベル付きのグリッドに配置した
単一のSVGへインライン展開する。外部リクエストを発生させないため、
アイコンはすべて自前ホストしたものを埋め込む。
"""

import re
import xml.sax.saxutils as saxutils
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "icons"

# アイコン定義: キー -> (ライト用ファイル, ダーク用ファイル, 描画スタイル)
#   tile  : 角丸の下地を内蔵した完成タイル（skillicons）。そのまま使う
#   round : 全面塗りの矩形（AWS公式）。外側で角丸に切り抜いて見た目を揃える
#   glyph : 下地のない単色グリフ（simple-icons）。下地タイルを付けて揃える
SKILL = ICONS / "skillicons"
AWS = ICONS / "aws"
SIMPLE = ICONS / "simpleicons"
ICON_SOURCES = {
    "python": (SKILL / "Python-Light.svg", SKILL / "Python-Dark.svg", "tile"),
    "typescript": (SKILL / "TypeScript.svg", SKILL / "TypeScript.svg", "tile"),
    "react": (SKILL / "React-Light.svg", SKILL / "React-Dark.svg", "tile"),
    "vue": (SKILL / "VueJS-Light.svg", SKILL / "VueJS-Dark.svg", "tile"),
    "vite": (SKILL / "Vite-Light.svg", SKILL / "Vite-Dark.svg", "tile"),
    "fastapi": (SKILL / "FastAPI.svg", SKILL / "FastAPI.svg", "tile"),
    "docker": (SKILL / "Docker.svg", SKILL / "Docker.svg", "tile"),
    "gha": (SKILL / "GithubActions-Light.svg", SKILL / "GithubActions-Dark.svg", "tile"),
    "lambda": (AWS / "AWSLambda.svg", AWS / "AWSLambda.svg", "round"),
    "apigateway": (AWS / "AmazonAPIGateway.svg", AWS / "AmazonAPIGateway.svg", "round"),
    "agentcore": (AWS / "AmazonBedrockAgentCore.svg", AWS / "AmazonBedrockAgentCore.svg", "round"),
    "dynamodb": (AWS / "AmazonDynamoDB.svg", AWS / "AmazonDynamoDB.svg", "round"),
    "s3": (AWS / "AmazonSimpleStorageService.svg", AWS / "AmazonSimpleStorageService.svg", "round"),
    "cloudfront": (AWS / "AmazonCloudFront.svg", AWS / "AmazonCloudFront.svg", "round"),
    "codepipeline": (AWS / "AWSCodePipeline.svg", AWS / "AWSCodePipeline.svg", "round"),
    "langchain": (SIMPLE / "langchain.svg", SIMPLE / "langchain.svg", "glyph"),
    "langgraph": (SIMPLE / "langgraph.svg", SIMPLE / "langgraph.svg", "glyph"),
}

# glyph スタイルの下地と glyph 色。skillicons の Light/Dark と同じ下地色を使う。
# ブランド色 #7FC8FF は淡く、ライトの下地では沈むため、ライトのみ濃度を上げる。
GLYPH_TILE = {"light": "#F4F2ED", "dark": "#242938"}
GLYPH_FILL = {"light": "#1C6EA4", "dark": "#7FC8FF"}
GLYPH_SCALE = 0.52  # タイルに対するグリフの占有率。skillicons の余白感に合わせる

# 各行のアイコン数を揃えると左右の端が縦に揃い、グリッドとして読める
ROWS = [
    [
        ("Language", ["python", "typescript"]),
        ("Frontend", ["react", "vue", "vite"]),
        ("Backend", ["fastapi", "lambda", "apigateway"]),
    ],
    [
        ("AI / LLM", ["agentcore", "langchain", "langgraph"]),
        ("Data & Storage", ["dynamodb", "s3"]),
        ("Infra / CI", ["docker", "cloudfront", "codepipeline", "gha"]),
    ],
]

ICON = 44  # アイコンの一辺
ICON_GAP = 8  # 同一カテゴリ内のアイコン間隔
GROUP_GAP = 32  # カテゴリ間の間隔。アイコン間隔より広げて群として見せる
ROW_GAP = 22
LABEL_SIZE = 11
LABEL_BASELINE = 8  # 行上端からラベルのベースラインまで
LABEL_TO_ICON = 6  # ラベル下端からアイコン上端まで
CORNER = ICON * 60 / 256  # skillicons の角丸比率に合わせる

FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
LABEL_FILL = {"light": "#57606a", "dark": "#8b949e"}  # GitHubの二次テキスト色

SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.S)
VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')
TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
ID_RE = re.compile(r'\bid="([^"]+)"')


def load_icon(path: Path, key: str) -> tuple[str, str]:
    """アイコンSVGを viewBox と中身に分解し、id を key で名前空間化して返す。

    1つのSVGに複数アイコンを埋め込むと、グラデーション等の id が衝突して
    別のアイコンの定義を参照してしまうため、事前に一意化する。
    """
    raw = path.read_text(encoding="utf-8")
    open_tag = SVG_OPEN_RE.search(raw)
    viewbox = VIEWBOX_RE.search(open_tag.group(0)).group(1)
    body = raw[open_tag.end() : raw.rindex("</svg>")]
    body = TITLE_RE.sub("", body)

    for old in set(ID_RE.findall(body)):
        new = f"{key}-{old}"
        body = body.replace(f'id="{old}"', f'id="{new}"')
        body = body.replace(f"url(#{old})", f"url(#{new})")
        body = body.replace(f'href="#{old}"', f'href="#{new}"')
    return viewbox, body


def group_width(keys: list[str]) -> int:
    return len(keys) * ICON + (len(keys) - 1) * ICON_GAP


def build(theme: str) -> str:
    row_height = LABEL_BASELINE + LABEL_TO_ICON + ICON

    # 列の開始位置を行間で揃える。行ごとにアイコン数が違っても縦の区切りが
    # 一致し、カテゴリの並びがグリッドとして読める。
    column_widths = [
        max(group_width(row[col][1]) for row in ROWS) for col in range(len(ROWS[0]))
    ]
    column_x = [
        sum(column_widths[:col]) + GROUP_GAP * col for col in range(len(column_widths))
    ]

    width = column_x[-1] + column_widths[-1]
    height = len(ROWS) * row_height + ROW_GAP * (len(ROWS) - 1)

    clips: list[str] = []
    parts: list[str] = []

    for row_index, row in enumerate(ROWS):
        row_top = row_index * (row_height + ROW_GAP)
        icon_top = row_top + LABEL_BASELINE + LABEL_TO_ICON
        for col, (label, keys) in enumerate(row):
            x = column_x[col]
            parts.append(
                f'<text x="{x}" y="{row_top + LABEL_BASELINE}" font-family="{FONT}" '
                f'font-size="{LABEL_SIZE}" font-weight="600" letter-spacing="0.4" '
                f'fill="{LABEL_FILL[theme]}">{saxutils.escape(label)}</text>'
            )
            for key in keys:
                light, dark, style = ICON_SOURCES[key]
                viewbox, body = load_icon(light if theme == "light" else dark, f"{key}-{theme}")

                if style == "glyph":
                    # グリフを中央に縮小配置し、下地の角丸タイルを自前で敷く
                    side = float(viewbox.split()[2])
                    scale = ICON * GLYPH_SCALE / side
                    offset = (ICON - side * scale) / 2
                    parts.append(
                        f'<rect x="{x}" y="{icon_top}" width="{ICON}" height="{ICON}" '
                        f'rx="{CORNER:.2f}" fill="{GLYPH_TILE[theme]}"/>'
                        f'<g transform="translate({x + offset:.2f} {icon_top + offset:.2f}) '
                        f'scale({scale:.4f})" fill="{GLYPH_FILL[theme]}">{body}</g>'
                    )
                    x += ICON + ICON_GAP
                    continue

                icon = (
                    f'<svg x="{x}" y="{icon_top}" width="{ICON}" height="{ICON}" '
                    f'viewBox="{viewbox}" overflow="hidden">{body}</svg>'
                )
                if style == "round":
                    clip_id = f"clip-{key}-{theme}"
                    clips.append(
                        f'<clipPath id="{clip_id}"><rect x="{x}" y="{icon_top}" '
                        f'width="{ICON}" height="{ICON}" rx="{CORNER:.2f}"/></clipPath>'
                    )
                    icon = f'<g clip-path="url(#{clip_id})">{icon}</g>'
                parts.append(icon)
                x += ICON + ICON_GAP

    defs = f"<defs>{''.join(clips)}</defs>" if clips else ""
    body = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" '
        f'version="1.1">{defs}{body}</svg>\n'
    )


def main() -> None:
    for theme, filename in (("light", "skills.svg"), ("dark", "skills-dark.svg")):
        path = ROOT / "assets" / filename
        path.write_text(build(theme), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
