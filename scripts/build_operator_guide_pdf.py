#!/usr/bin/env python3
"""Build docs/AVACCESS_OPERATORS_GUIDE.pdf from live operator screenshots."""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "docs" / "images" / "operations"
OUT = ROOT / "docs" / "AVACCESS_OPERATORS_GUIDE.pdf"
ART = Path("/opt/cursor/artifacts")

NAVY = HexColor("#111827")
TEAL = HexColor("#0e7490")
MUTED = HexColor("#4b5563")
RULE = HexColor("#d1d5db")
ROW = HexColor("#f3f4f6")


def crop_panel(src: Path) -> Path:
    """Trim HA chrome around the bartender panel for print."""
    im = PILImage.open(src).convert("RGB")
    w, h = im.size
    px = im.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(0, h, 3):
        for x in range(0, w, 4):
            r, g, b = px[x, y]
            if r < 90 and g < 100 and b < 120:
                xs.append(x)
                ys.append(y)
    if not xs:
        return src
    pad = 12
    box = (
        max(0, min(xs) - pad),
        max(0, min(ys) - pad),
        min(w, max(xs) + pad),
        min(h, max(ys) + pad),
    )
    cropped = im.crop(box)
    dest = Path("/tmp") / f"{src.stem}-print.png"
    cropped.save(dest, "PNG")
    return dest


def fit_image(path: Path, max_w: float, max_h: float) -> Image:
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Image(str(path), width=w * scale, height=h * scale)


def caption(styles, text: str) -> Paragraph:
    return Paragraph(text, styles["caption"])


def heading(styles, text: str) -> Paragraph:
    return Paragraph(text, styles["h1"])


def body(styles, text: str) -> Paragraph:
    return Paragraph(text, styles["body"])


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, letter[1] - 28, letter[0], 28, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.7 * inch, letter[1] - 18, "AVAccess  ·  DirecTV operators guide")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(letter[0] - 0.7 * inch, letter[1] - 18, "ZIP 27403")
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0, letter[0], 22, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.7 * inch, 8, "No IR  ·  H25 SHEF + AVAccess matrix")
    canvas.drawRightString(letter[0] - 0.7 * inch, 8, f"Page {doc.page}")
    canvas.restoreState()


def cover_header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, 2.15 * inch, letter[0], 8, fill=1, stroke=0)
    canvas.restoreState()


def make_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "coverKicker": ParagraphStyle(
            "coverKicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=TEAL,
            tracking=1,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "coverTitle": ParagraphStyle(
            "coverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=white,
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "coverSub": ParagraphStyle(
            "coverSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=16,
            textColor=HexColor("#e5e7eb"),
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "h1op",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=NAVY,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2op",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=TEAL,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "bodyop",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "captionop",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=12,
        ),
        "cell": ParagraphStyle(
            "cellop",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.2,
            textColor=NAVY,
        ),
        "cellHead": ParagraphStyle(
            "cellhead",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.2,
            textColor=white,
        ),
    }


def table(styles, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> Table:
    data = [[Paragraph(h, styles["cellHead"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, styles["cell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), ROW))
    t.setStyle(TableStyle(style_cmds))
    return t


def photo_block(styles, path: Path, cap: str, max_h: float = 6.6 * inch) -> list:
    img = fit_image(path, 7.1 * inch, max_h)
    return [img, caption(styles, cap)]


def build() -> Path:
    styles = make_styles()
    story: list = []

    # Cover (dark page drawn by onFirstPage)
    story.append(Spacer(1, 2.4 * inch))
    story.append(Paragraph("GAME DAY PLAYBOOK", styles["coverKicker"]))
    story.append(Paragraph("AVAccess operators guide", styles["coverTitle"]))
    story.append(
        Paragraph(
            "10 DirecTV H25 boxes  ·  35 TVs  ·  iPad in Home Assistant Companion",
            styles["coverSub"],
        )
    )
    story.append(
        Paragraph(
            "Tune over IP (SHEF). Route with the AVAccess matrix. There is no IR remote and no Xumo.",
            styles["coverSub"],
        )
    )
    story.append(Paragraph("Greensboro ZIP 27403  ·  local affiliates first on blackouts", styles["coverSub"]))
    story.append(PageBreak())

    story.append(heading(styles, "1. Open the iPad"))
    story.append(
        body(
            styles,
            "Open <b>Home Assistant Companion</b> (or Safari) and sign in. The sidebar has two operator surfaces. Use both.",
        )
    )
    story.append(
        table(
            styles,
            ["Sidebar", "When to use it"],
            [
                [
                    "Sports Routing",
                    "Bartender iPad. Pick a game or DirecTV channel, then send it to ALL / 4-way / 9-way or to specific TVs.",
                ],
                [
                    "AVAccess Matrix",
                    "One-tap favorites (FOX Local, NFL Afternoon, All Sunday) plus presets, program letters, and route-to-TVs.",
                ],
            ],
            [1.7 * inch, 5.4 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.extend(
        photo_block(
            styles,
            IMG / "01-control-overview.png",
            "AVAccess Matrix Control tab. Sidebar also shows Sports Routing. Now Playing is DirecTV (staging stub text until site HA is live).",
            5.4 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "2. Sports Routing — pick a game"))
    story.append(
        body(
            styles,
            "This is the bartender panel. Sport chips across the top: NFL, CFB, NBA, NHL, MLB, WNBA, Guide, TVs. "
            "Leave <b>Live commit</b> off unless you mean to change the wall. Dry-run Send only updates occupancy on the iPad.",
        )
    )
    nfl = crop_panel(IMG / "08-sports-routing-nfl.png")
    story.extend(
        photo_block(
            styles,
            nfl,
            "Sports Routing · NFL. Tap a game card, then choose ALL / 4 programs / 9 programs or Pick TVs.",
            6.8 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "3. Sports Routing — DirecTV guide"))
    story.append(
        body(
            styles,
            "Tap <b>Guide</b> for the DirecTV lineup in ZIP 27403. Search by number, name, or title. "
            "If listings are stale you still get the channel list (as below). On site HA with a fresh EPG, Now/Next titles fill in.",
        )
    )
    guide = crop_panel(IMG / "09-sports-routing-guide.png")
    story.extend(
        photo_block(
            styles,
            guide,
            "Guide heading is DirecTV · ZIP 27403. Channel numbers are DirecTV majors, not Spectrum/Xumo.",
            6.8 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "4. Sports Routing — send to the wall"))
    story.append(
        body(
            styles,
            "After you pick a game: <b>ALL</b> = every TV on ENC-01 / H25-01. <b>4 Prog</b> = striped across ENC-01…04. "
            "<b>9 Prog</b> = striped across ENC-01…09. Then tap <b>Dry-run Send</b>. Turn Live commit on only on the site HA when inventory hostnames are real.",
        )
    )
    dest = crop_panel(IMG / "10-sports-routing-destination.png")
    story.extend(
        photo_block(
            styles,
            dest,
            "Chiefs @ Bills → ALL (all 35 TVs). Dry-run Send is the default. Live Send tunes the H25 over SHEF, then UDP-reconnects the TVs.",
            6.6 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "5. Matrix — iPad Control tab"))
    story.append(
        body(
            styles,
            "Use this for one-tap favorites. Stars at the top: <b>FOX Local</b>, <b>NFL Afternoon Games</b>, <b>All NFL Sunday Games</b>. "
            "Program A is H25-01 / ENC-01. Channel buttons retune that box. Now Playing shows each H25.",
        )
    )
    story.extend(
        photo_block(
            styles,
            IMG / "02-control-ipad.png",
            "iPad portrait Control tab — favorites, presets, programs, channels, DirecTV Now Playing.",
            6.8 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "6. Matrix — route one program to specific TVs"))
    story.append(
        body(
            styles,
            "Scroll to <b>Destination</b> and <b>Route Actions</b>. Put receiver IDs in Target TVs (example <b>RX-01,RX-02</b>), "
            "tap the program letter, then <b>Route Program -&gt; TVs</b>. That does not retune the H25 — it only points those TVs at the encoder. Tune first if the box is on the wrong channel.",
        )
    )
    story.extend(
        photo_block(
            styles,
            IMG / "03-control-ipad-route.png",
            "iPad Control scrolled to Destination + Route Program -> TVs. Target TVs is RX-01,RX-02.",
            6.8 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "7. Matrix — sport tabs"))
    story.append(
        body(
            styles,
            "Same routing cards, shorter channel lists. Use NFL for Sunday Ticket slots A1–A4 and S1–S9. "
            "College Football and Basketball keep local + cable sports nets.",
        )
    )
    story.extend(photo_block(styles, IMG / "04-nfl.png", "NFL tab — locals plus afternoon and Sunday slots.", 5.3 * inch))

    story.append(PageBreak())
    story.extend(
        photo_block(styles, IMG / "05-college-football.png", "College Football tab — locals + ESPN / ESPN2 / FS1.", 3.15 * inch)
    )
    story.append(Spacer(1, 6))
    story.extend(
        photo_block(styles, IMG / "06-basketball.png", "Basketball tab — ESPN / ESPN2 / TNT / local ABC.", 3.15 * inch)
    )

    story.append(PageBreak())
    story.append(heading(styles, "8. Proof the tap ran"))
    story.append(
        body(
            styles,
            "Home Assistant <b>Activity</b> lists each script. Look for <b>Ran</b> on Favorite FOX Local, route-to-TVs, and presets. "
            "On the bar, also look at the wall: TVs follow the preset, and the H25 OSD / Now Playing matches the channel.",
        )
    )
    story.extend(
        photo_block(
            styles,
            IMG / "07-activity-logbook.png",
            "Activity after FOX Local, Route Program -> TVs, and Preset 2. Each script shows Ran (and On/Off).",
            5.8 * inch,
        )
    )

    story.append(PageBreak())
    story.append(heading(styles, "9. Game-day cheat sheet"))
    story.append(
        table(
            styles,
            ["You want", "Tap"],
            [
                ["All TVs on local FOX (WGHP)", "Matrix Control → <b>FOX Local</b><br/>or Sports Routing → that FOX game → ALL → Send"],
                [
                    "Afternoon NFL package (four games)",
                    "Matrix → <b>NFL Afternoon Games</b><br/>or Sports Routing Preset 2 / 4 Prog with four games",
                ],
                ["Every Sunday game (nine-way)", "Matrix → <b>All NFL Sunday Games</b>"],
                [
                    "One overflow TV onto Program C",
                    "Target TVs = that RX (example RX-22) → Program C → Route Program -&gt; TVs",
                ],
                [
                    "Wrong channel on one box",
                    "Tap that Program letter → tap the correct channel. Other TVs on that program follow (same H25).",
                ],
            ],
            [2.3 * inch, 4.8 * inch],
        )
    )
    story.append(Paragraph("What the words mean", styles["h2"]))
    story.append(
        table(
            styles,
            ["Word", "Meaning"],
            [
                ["Program A…I", "One DirecTV H25. A = ENC-01 / H25-01 … I = ENC-09 / H25-09. ENC-10 is spare."],
                ["Preset 1 / 2 / 3", "Which TVs watch which program (the AVAccess matrix). Layout only — does not change channel by itself."],
                ["Channel / Guide number", "DirecTV major. FOX local is WGHP. Sunday Ticket is 705+ unless blackout prefers local."],
                ["Dry-run Send", "Plan only. Does not talk to H25s or the switch."],
                ["Live Send", "SHEF /tv/tune on that H25, then UDP msg_b_reconnect to the TVs. Keep Live commit off until you mean it."],
            ],
            [1.7 * inch, 5.4 * inch],
        )
    )

    story.append(Paragraph("If something looks wrong", styles["h2"]))
    story.append(
        table(
            styles,
            ["Symptom", "Try"],
            [
                ["TVs did not split", "Tap the preset again. Activity should show the preset script Ran."],
                ["Right layout, wrong game", "Tap the Program letter, then the channel (or the matching favorite)."],
                ["One TV on the wrong program", "Route that RX to the program you want."],
                ["Now Playing says STAGING", "You are on the cloud UI stub. Site HA shows live H25 titles after External Access is on."],
                ["Sunday slot is Ticket instead of local", "Re-run weekly sync. ZIP 27403 prefers WGHP/WFMY/WXII/WXLV over 705–713 when both carry the game."],
            ],
            [2.3 * inch, 4.8 * inch],
        )
    )

    story.append(Paragraph("Staging vs the bar", styles["h2"]))
    story.append(
        table(
            styles,
            ["", "These photos (staging)", "Site / production HA"],
            [
                ["Buttons and tabs", "Same", "Same"],
                [
                    "Channel / preset / route",
                    "Scripts run; shell is echo STAGING",
                    "HTTP SHEF to each H25 + UDP to the AVAccess switch",
                ],
                ["Now Playing", "Dummy sensor text", "Official DirecTV media_player titles"],
                ["IR / Xumo", "Not used", "Not used"],
            ],
            [1.5 * inch, 2.8 * inch, 2.8 * inch],
        )
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.45 * inch,
        title="AVAccess operators guide",
        author="AVAccess automator",
    )

    def later(canvas, doc_):
        if doc_.page == 1:
            cover_header_footer(canvas, doc_)
        else:
            header_footer(canvas, doc_)

    doc.build(story, onFirstPage=later, onLaterPages=later)
    if ART.is_dir():
        dest = ART / OUT.name
        dest.write_bytes(OUT.read_bytes())
    return OUT


if __name__ == "__main__":
    path = build()
    print(path, path.stat().st_size)
