#!/usr/bin/env python3
"""Build docs/STAFF_TRAINING.pdf — landscape Sports Routing, with screenshots."""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor, white
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
IMG = ROOT / "docs" / "images" / "staff"
OUT = ROOT / "docs" / "STAFF_TRAINING.pdf"
ART = Path("/opt/cursor/artifacts")

NAVY = HexColor("#111827")
TEAL = HexColor("#0e7490")
MUTED = HexColor("#4b5563")
RULE = HexColor("#d1d5db")
ROW = HexColor("#f3f4f6")
GOLD = HexColor("#a16207")


def fit_image(path: Path, max_w: float, max_h: float) -> Image:
    with PILImage.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Image(str(path), width=w * scale, height=h * scale)


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, letter[1] - 28, letter[0], 28, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.65 * inch, letter[1] - 18, "Sports Routing  ·  staff training")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(letter[0] - 0.65 * inch, letter[1] - 18, "Greensboro  ·  ZIP 27403")
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0, letter[0], 22, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.65 * inch, 8, "Hold the iPad sideways  ·  Live commit stays off")
    canvas.drawRightString(letter[0] - 0.65 * inch, 8, f"Page {doc.page}")
    canvas.restoreState()


def cover_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, 2.05 * inch, letter[0], 8, fill=1, stroke=0)
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
            "h1staff",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=NAVY,
            spaceBefore=2,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2staff",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=TEAL,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "bodystaff",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13.5,
            textColor=NAVY,
            spaceAfter=8,
        ),
        "note": ParagraphStyle(
            "notestaff",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=GOLD,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "captionstaff",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=3,
            spaceAfter=8,
        ),
        "step": ParagraphStyle(
            "stepstaff",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=NAVY,
        ),
        "cell": ParagraphStyle(
            "cellstaff",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=NAVY,
        ),
        "cellHead": ParagraphStyle(
            "cellheadstaff",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=white,
        ),
    }


def P(styles, text: str):
    return Paragraph(text, styles["body"])


def bullets(styles, items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, styles["step"]), leftIndent=12) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=16,
        bulletFontName="Helvetica",
        bulletFontSize=10,
        spaceBefore=0,
        spaceAfter=8,
    )


def numbered(styles, items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, styles["step"]), leftIndent=14) for item in items],
        bulletType="1",
        start="1",
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=10,
        spaceBefore=0,
        spaceAfter=8,
    )


def table(styles, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> Table:
    data = [[Paragraph(h, styles["cellHead"]) for h in headers]]
    for row in rows:
        data.append([Paragraph(c, styles["cell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), ROW))
    t.setStyle(TableStyle(cmds))
    return t


def photo(styles, name: str, cap: str, max_h: float = 4.55 * inch) -> KeepTogether:
    img = fit_image(IMG / name, 7.2 * inch, max_h)
    return KeepTogether([img, Paragraph(cap, styles["caption"])])


def build() -> Path:
    s = make_styles()
    story: list = []

    story.append(Spacer(1, 2.35 * inch))
    story.append(Paragraph("STAFF TRAINING", s["coverKicker"]))
    story.append(Paragraph("Sports Routing on the iPad", s["coverTitle"]))
    story.append(
        Paragraph(
            "Part 1  ·  Quick start&nbsp;&nbsp;&nbsp;Part 2  ·  Full guide",
            s["coverSub"],
        )
    )
    story.append(
        Paragraph(
            "Hold the iPad sideways. Open Home Assistant and tap Sports Routing.",
            s["coverSub"],
        )
    )
    story.append(
        Paragraph(
            "Live commit stays off. Take only plans the change. The TVs do not move until a manager turns Live commit on.",
            s["coverSub"],
        )
    )
    story.append(Paragraph("Program names in the pictures are from one evening. They change. The buttons do not.", s["coverSub"]))
    story.append(PageBreak())

    # --- Part 1 ---
    story.append(Paragraph("Part 1. Quick start", s["h1"]))
    story.append(
        P(
            s,
            "The yellow line says <b>Live commit is off until the room inventory is set up.</b> "
            "Leave it. Pressing <b>Take</b> shows a summary and nothing on the wall changes.",
        )
    )
    story.append(
        P(
            s,
            "The screen is three columns, plus <b>Take</b> along the bottom. Lists move when you drag them. "
            "A scrollbar only flashes while your finger is moving. You will not see a gray bar.",
        )
    )
    story.append(
        table(
            s,
            ["Column", "What you use it for"],
            [
                ["Left", "A sport (Football, Basketball, and the rest). Swipe down for <b>Guide</b> and <b>Now</b>."],
                ["Middle", "The games, or the channel list."],
                ["Right", "Where it goes: every TV, a split, or TVs you pick."],
            ],
            [1.3 * inch, 5.9 * inch],
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("One game on every TV", s["h2"]))
    story.append(
        numbered(
            s,
            [
                "Tap the sport on the left.",
                "Tap a league if you need one (<b>NFL</b>, <b>NCAA Basketball (M)</b>, and so on). <b>All</b> shows every game in that sport.",
                "Tap the game. It turns blue.",
                "On the right, tap <b>All 35 TVs</b>.",
                "Tap the blue <b>Take</b>.",
                "Read the summary, then tap <b>Dismiss</b>.",
            ],
        )
    )
    story.append(
        P(
            s,
            "<b>Take</b> stays gray until you have both a program and a place to put it. "
            "When it turns blue, the line above it is the plan in one sentence.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("One game on a few TVs", s["h1"]))
    story.append(
        P(
            s,
            "Basketball, then <b>NCAA Basketball (M)</b>, then the game. Tap <b>Pick TVs</b> and tap the TV numbers. "
            "Tap a number again to remove it. <b>Clear TVs</b> removes all of them.",
        )
    )
    story.append(
        photo(
            s,
            "02-pick-tvs.png",
            "Tennessee at Duke is selected. TVs 1, 3, 5, and 7 are picked. Take is blue.",
        )
    )
    story.append(
        P(
            s,
            "The top right reads <b>Ready · Tennessee @ Duke · Tune 612 → TVs 1, 3, 5, 7</b>. "
            "<b>612</b> is the DirecTV channel. Tap <b>Take</b>.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Read the summary, then dismiss it", s["h1"]))
    story.append(
        P(
            s,
            "The summary names the DirecTV box, the game, the TVs, and the channel. "
            "<b>Dismiss</b> closes it. Nothing was sent to the wall. The game card then shows a badge such as <b>4 TVs</b>, "
            "and those TV buttons show the channel.",
        )
    )
    story.append(
        photo(
            s,
            "03-take.png",
            "Dry-run summary: ENC-01, Tennessee at Duke, TVs 1, 3, 5, and 7, Tune 612.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("What is on each TV", s["h1"]))
    story.append(
        P(
            s,
            "Swipe the left column to the bottom and tap <b>Now</b>. Every TV is listed. "
            "After the Take above, 1, 3, 5, and 7 show the game and channel <b>612</b>. The others say <b>Off</b>.",
        )
    )
    story.append(
        photo(
            s,
            "04-now.png",
            "Now: TVs 1, 3, and 5 on Duke. TVs 2 and 4 are off. TV 7 is the same as 1, 3, and 5.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Find a channel that is not a game", s["h1"]))
    story.append(
        P(
            s,
            "Swipe the left column and tap <b>Guide</b>. The list is DirecTV for Greensboro (ZIP 27403). "
            "The box says <b>Search by channel, name, or title</b>.",
        )
    )
    story.append(
        photo(
            s,
            "05-guide.png",
            "Guide open. CBS 2 is showing NCIS. FOX 8 and NBC 12 are under it. Titles change through the day.",
        )
    )
    story.append(
        P(
            s,
            "Search works three ways: channel name, what is on right now, or the channel number (for example <b>206</b> for ESPN). "
            "Tap the row, then <b>All 35 TVs</b> or <b>Pick TVs</b>, then <b>Take</b>.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Search by channel name", s["h1"]))
    story.append(P(s, "Type the name. <b>HGTV</b> leaves channel <b>229</b>."))
    story.append(photo(s, "06-search-name.png", "Search HGTV. One row: 229 HGTV USA - Eastern Feed."))

    story.append(PageBreak())
    story.append(Paragraph("Search by the program that is on", s["h1"]))
    story.append(
        P(
            s,
            "Type the show. <b>NCIS</b> finds CBS <b>2</b>, because that is the program on right now. "
            "Tomorrow the same word can find a different channel.",
        )
    )
    story.append(photo(s, "07-search-program.png", "Search NCIS. CBS 2, Now: NCIS."))

    story.append(PageBreak())
    story.append(Paragraph("Several games at once", s["h1"]))
    story.append(
        P(
            s,
            "Tap <b>4 Programs</b> before you tap the games. Then tap up to four games. Each one turns blue. "
            "You do not pick TV numbers. The first game goes on one set of TVs, the next game on the next set. "
            "TVs that do not get a game stay on whatever they were already showing.",
        )
    )
    story.append(
        photo(
            s,
            "08-four-programs.png",
            "4 Programs is on. Two college games are selected. The line reads 2 programs, then 4 Programs. Take is blue.",
        )
    )
    story.append(
        P(
            s,
            "<b>9 Programs</b> is the same idea, with up to nine games. "
            "A game that has no channel number can still be in the list. <b>Take</b> will not tune it.",
        )
    )

    # --- Part 2 ---
    story.append(PageBreak())
    story.append(Paragraph("Part 2. Full guide", s["h1"]))
    story.append(Paragraph("How to open it", s["h2"]))
    story.append(
        numbered(
            s,
            [
                "Home Assistant Companion, or Safari, signed in to the bar's Home Assistant.",
                "Sidebar: <b>Sports Routing</b>.",
                "Turn the iPad sideways. In portrait the columns stack and the buttons get small. Landscape is the layout in these pictures.",
            ],
        )
    )
    story.append(
        P(
            s,
            "Sports Routing is the screen staff use during a game. "
            "<b>AVAccess Matrix</b> (favorites such as FOX Local) is a separate sidebar item and is not covered here.",
        )
    )
    story.append(Paragraph("How the screen is laid out", s["h2"]))
    story.append(photo(s, "01-sports.png", "Football open. Games in the middle. Displays on the right. Take is gray until a plan is ready.", 3.7 * inch))

    story.append(PageBreak())
    story.append(Paragraph("What each part of the screen does", s["h1"]))
    story.append(
        bullets(
            s,
            [
                "<b>Bar</b> is the room name. The top right is <b>No route</b> until a plan is ready, then a one-line description of what Take will do.",
                "<b>Live commit</b> is the switch that would send the plan to the DirecTV boxes and the TVs. It is off, and the yellow line says why. Leave it off.",
                "<b>Left rail.</b> DirecTV's own sports: Football, Basketball, Baseball, Hockey, Soccer, Rugby, Racing, Combat, Golf, Tennis, Cricket, Volleyball, Rodeo, Raquet Ball. <b>Guide</b> and <b>Now</b> are under that list. Swipe the rail.",
                "<b>Sources</b> (middle). League chips, then the games. On Guide, this column is the channel list and the search box. On Now, it is the TV-by-TV list.",
                "<b>Displays</b> (right). <b>All 35 TVs</b>, <b>4 Programs</b>, <b>9 Programs</b>, or <b>Pick TVs</b>. Only one of these is active. Choosing a preset clears a TV pick, and choosing Pick TVs leaves the preset.",
                "<b>Take</b> (bottom). Gray until a program and a destination are both chosen. Blue means the plan is ready. The sentence above the button is the same plan.",
            ],
        )
    )

    story.append(Paragraph("Sports", s["h2"]))
    story.append(
        P(
            s,
            "The game list comes from DirecTV's sports page for this bar (Greensboro, ZIP 27403, Bars and Restaurants). "
            "It is not filled from the TV guide.",
        )
    )
    story.append(
        bullets(
            s,
            [
                "College football on ESPNU, ESPN2, and the other sports channels.",
                "NFL, including Sunday Ticket. Those numbers are high, such as <b>9558</b>.",
                "College basketball, men's and women's, including games on ACC Network (Duke on <b>612</b> in the pictures).",
                "NBA, including out-of-market games on NBA League Pass (a number such as <b>1204</b>).",
                "The other sports on the left rail, when DirecTV has games that day.",
            ],
        )
    )
    story.append(
        P(
            s,
            "Locals stay in the guide and can carry a game: <b>2</b> CBS (WFMY), <b>8</b> FOX (WGHP), "
            "<b>12</b> NBC (WXII), <b>45</b> ABC (WXLV).",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Sports, continued", s["h1"]))
    story.append(
        P(
            s,
            "Under <b>Sources</b>, <b>All</b> shows every game in the sport you tapped. The other chips are the leagues inside that sport "
            "(NFL, NCAA Football, NBA, NCAA Basketball (M), and so on). A sport with one league has no extra chips.",
        )
    )
    story.append(
        P(
            s,
            "Each card shows the two teams, the league, the channel number and name, and the start time. "
            "Tap a card to select it. Tap it again to clear it when you are in <b>4 Programs</b> or <b>9 Programs</b>. "
            "For a single game, tap a different card to switch.",
        )
    )
    story.append(
        P(
            s,
            "If a card has no channel number, it is listed so you can see the game, but Take will not tune it. "
            "The list refreshes when the iPad opens the page, and about every 15 minutes after that.",
        )
    )

    story.append(Paragraph("Guide", s["h2"]))
    story.append(
        P(
            s,
            "Guide is the DirecTV Greensboro lineup. It is the full lineup staff can put on a TV, with these left out:",
        )
    )
    story.append(
        bullets(
            s,
            [
                "Music-only channels (Music Choice, Sirius, and similar). Music video networks such as MTV stay.",
                "Pay-per-view and Hot Choice.",
                "Promo barkers (Audience Network).",
                "On-demand menus.",
                "A second copy of a station that already has its real channel number (usually a 9000-series number).",
            ],
        )
    )
    story.append(P(s, "News, HBO, shopping, and the sports channels stay."))
    story.append(
        P(
            s,
            "<b>Now</b> and <b>Next</b> (the title under the channel name) are filled for the main locals and sports channels: "
            "2, 8, 12, 45, 206 ESPN, 209 ESPN2, 219 FS1, 245 TNT, and 9554. Other channels show the number and name only.",
        )
    )
    story.append(
        P(
            s,
            "If the program list is missing or more than six hours old, a banner says "
            "<b>Guide listings unavailable - channel list only</b>. You can still search by number or name and still Take a channel. "
            "You just will not see what is on.",
        )
    )
    story.append(
        P(
            s,
            "Search matches the channel number, the channel name, the category, and the Now or Next title. "
            "Clear the box to get the full list back. The titles in the pictures (NCIS on CBS 2, Best Medicine on FOX 8) "
            "are whatever was on that evening.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Where the picture goes", s["h1"]))
    story.append(
        P(
            s,
            "<b>All 35 TVs</b> (Preset 1). One game or one channel, on every TV. The summary names <b>ENC-01</b>. "
            "That is the first DirecTV box. The tune line is Tune plus the channel number.",
        )
    )
    story.append(
        P(
            s,
            "<b>4 Programs</b> (Preset 2). Tap this first, then tap up to four games or channels. "
            "The order you tap is the order of the boxes: first pick is ENC-01, second is ENC-02, and so on. "
            "The room is striped, not blocked into four corners.",
        )
    )
    story.append(
        table(
            s,
            ["Pick", "DirecTV box", "TVs"],
            [
                ["1st", "ENC-01", "1, 5, 9, 13, 17, 21, 25, 29, 33"],
                ["2nd", "ENC-02", "2, 6, 10, 14, 18, 22, 26, 30, 34"],
                ["3rd", "ENC-03", "3, 7, 11, 15, 19, 23, 27, 31, 35"],
                ["4th", "ENC-04", "4, 8, 12, 16, 20, 24, 28, 32"],
            ],
            [1.1 * inch, 1.6 * inch, 4.5 * inch],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        P(
            s,
            "If you only pick two games, ENC-03 and ENC-04 are left alone, and the TVs in those two rows stay as they were. "
            "Extra taps past four are ignored. The line above Take tells you how many you have picked "
            "(<b>2 programs → 4 Programs</b>).",
        )
    )
    story.append(
        P(
            s,
            "<b>9 Programs</b> (Preset 3). Same rule, up to nine games, nine boxes (ENC-01 through ENC-09). "
            "TVs are striped by nine: TV 1 with the first game, TV 2 with the second, TV 10 with the first game again.",
        )
    )
    story.append(
        P(
            s,
            "<b>Pick TVs.</b> Choose the exact set. Tap numbers, tap again to remove, or <b>Clear TVs</b>. "
            "This uses the lowest free DirecTV box from ENC-01 through ENC-10. ENC-10 is the spare. "
            "If every box is already in use, Take stays blocked and the panel says <b>No free encoders</b>.",
        )
    )
    story.append(
        P(
            s,
            "You plan either a preset or a TV pick, not both. The header and the line above Take are the check before you press the button.",
        )
    )

    story.append(Paragraph("Take, and what the summary means", s["h2"]))
    story.append(
        P(
            s,
            "Take builds the plan, shows <b>DRY-RUN SUMMARY</b>, and updates the on-screen status. "
            "With Live commit off, that is all it does. No box changes channel. No TV switches input.",
        )
    )
    story.append(
        P(
            s,
            "Read the summary before you dismiss it. One line per box, for example: "
            "<b>ENC-01 · Tennessee @ Duke · TVs 1, 3, 5, 7 · Tune 612</b>.",
        )
    )
    story.append(
        P(
            s,
            "<b>Dismiss</b> closes the summary. The game card gets a badge with the TV count. Open <b>Now</b> for the full room list. "
            "When a manager later turns Live commit on, the same Take sends the channel change and then switches the TVs. "
            "Until the yellow line is gone, treat every Take as a practice press.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Now, and what to leave alone", s["h1"]))
    story.append(
        P(
            s,
            "<b>Now</b> is the room status, not a channel you can tune. It lists TVs 1 through 35. "
            "A TV with a plan shows the program name and the channel. A TV with nothing planned says <b>Off</b> and <b>No program</b>. "
            "The count at the top is how many of the 35 are on.",
        )
    )
    story.append(
        P(
            s,
            "While <b>Pick TVs</b> is open, the number buttons on the right also show the channel under the TV number "
            "(the pictures show <b>612 ACC</b> on 1, 3, 5, and 7).",
        )
    )
    story.append(Paragraph("What to leave alone", s["h2"]))
    story.append(
        bullets(
            s,
            [
                "Do not turn on <b>Live commit</b>. It will not turn on until the room inventory is set up, and the yellow line is the reminder.",
                "Do not expect the TVs on the wall to change after Take while that line is showing.",
                "Do not hunt the guide for music-radio channels, pay-per-view, or the on-demand menus. They are left out on purpose.",
                "Do not Take a game card that has no channel number.",
            ],
        )
    )
    story.append(Paragraph("If the screen looks wrong", s["h2"]))
    story.append(
        table(
            s,
            ["What you see", "What it means"],
            [
                ["<b>No games in this slate</b>", "DirecTV has nothing in that sport for the days that were loaded. Try another sport, or Guide."],
                [
                    "<b>Guide listings unavailable - channel list only</b>",
                    "The channel list is fine. Program titles are stale. Search by name or number still works.",
                ],
                ["Search returns nothing", "Try the channel number, or clear the box. Titles change. Yesterday's show will not match."],
                [
                    "Take stays gray",
                    "You still need a game or channel, and a destination (All 35, 4 Programs or 9 Programs with at least one pick, or at least one TV).",
                ],
                ["<b>No free encoders</b>", "All ten DirecTV boxes are already assigned. Clear a plan or use a preset instead of Pick TVs."],
            ],
            [2.5 * inch, 4.7 * inch],
        )
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.48 * inch,
        title="Sports Routing staff training",
        author="AVAccess automator",
    )

    def later(canvas, doc_):
        if doc_.page == 1:
            cover_page(canvas, doc_)
        else:
            header_footer(canvas, doc_)

    doc.build(story, onFirstPage=later, onLaterPages=later)
    if ART.is_dir():
        (ART / OUT.name).write_bytes(OUT.read_bytes())
    return OUT


if __name__ == "__main__":
    path = build()
    print(path, path.stat().st_size)
