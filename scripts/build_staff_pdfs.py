#!/usr/bin/env python3
"""Build the two bar handouts: quick start and full guide."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "scripts" / "build_staff_training_pdf.py"
ART = Path("/opt/cursor/artifacts")


def load_helpers():
    spec = importlib.util.spec_from_file_location("staffpdf", HELPERS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def doc_for(path: Path, title: str):
    return SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.48 * inch,
        title=title,
        author="AVAccess automator",
    )


def write(path: Path, story, helpers) -> None:
    document = doc_for(path, path.stem.replace("_", " "))

    def later(canvas, doc_):
        if doc_.page == 1:
            helpers.cover_page(canvas, doc_)
        else:
            helpers.header_footer(canvas, doc_)

    document.build(story, onFirstPage=later, onLaterPages=later)
    if ART.is_dir():
        (ART / path.name).write_bytes(path.read_bytes())


def cover(h, s, kicker, title, lines):
    story = [Spacer(1, 2.35 * inch), Paragraph(kicker, s["coverKicker"]), Paragraph(title, s["coverTitle"])]
    for line in lines:
        story.append(Paragraph(line, s["coverSub"]))
    story.append(PageBreak())
    return story


def quick_story(h):
    s = h.make_styles()
    story = cover(
        h,
        s,
        "QUICK START",
        "Sports Routing on the iPad",
        [
            "Hold the iPad sideways. Open Home Assistant and tap Sports Routing.",
            "Live commit stays off. Take only plans the change. The TVs do not move.",
            "Program names in the pictures are from one evening. They change. The buttons do not.",
        ],
    )
    story.append(Paragraph("The screen", s["h1"]))
    story.append(
        h.P(
            s,
            "Three columns, plus <b>Take</b> along the bottom. Left: a sport. Swipe down for <b>Guide</b>, <b>Now</b>, and <b>Sets</b>. "
            "Middle: the games or the channel list. Right: where it goes. Lists move when you drag. A scrollbar only flashes while your finger is moving.",
        )
    )
    story.append(Paragraph("One game on every TV", s["h2"]))
    story.append(
        h.numbered(
            s,
            [
                "Tap the sport, then a league if you need one. <b>All</b> shows every game in that sport.",
                "Tap the game. It turns blue.",
                "Tap <b>All 35 TVs</b>.",
                "Tap the blue <b>Take</b>. Read the summary. Tap <b>Dismiss</b>.",
            ],
        )
    )
    story.append(Paragraph("One game on a few TVs", s["h1"]))
    story.append(
        h.P(
            s,
            "Tap the game, then <b>Pick TVs</b>, then the TV numbers. Tap a number again to remove it. <b>Take</b> turns blue when the plan is ready.",
        )
    )
    story.append(h.photo(s, "02-pick-tvs.png", "Duke on TVs 1, 3, 5, and 7. Take is blue."))
    story.append(h.photo(s, "03-take.png", "The summary names the DirecTV box, the game, the TVs, and the channel. Nothing is sent to the wall.", 3.6 * inch))

    story.append(PageBreak())
    story.append(Paragraph("A named set of TVs", s["h1"]))
    story.append(
        h.P(
            s,
            "Use a set for a part of the room you send programs to again and again, such as Patio. "
            "Swipe the left column and tap <b>Sets</b>. Type a name, tap the TV numbers, and tap <b>Save</b>. "
            "The button then shows under Displays on Sports and Guide.",
        )
    )
    story.append(h.photo(s, "09-tv-sets.png", "Sets. Patio is TVs 8, 9, and 10.", 3.5 * inch))
    story.append(
        h.P(s, "Tap the game, tap <b>Patio</b>, tap <b>Take</b>. TVs that are not in Patio stay on whatever they were already showing.")
    )
    story.append(h.photo(s, "10-set-ready.png", "Duke ready for Patio. Take is blue.", 3.5 * inch))

    story.append(PageBreak())
    story.append(Paragraph("Guide", s["h1"]))
    story.append(
        h.P(
            s,
            "Swipe the left column and tap <b>Guide</b>. Search by channel name, by the program that is on, or by the channel number. "
            "Tap the row, then <b>All 35 TVs</b>, <b>Pick TVs</b>, or a set, then <b>Take</b>.",
        )
    )
    story.append(h.photo(s, "06-search-name.png", "HGTV finds channel 229.", 3.3 * inch))
    story.append(h.photo(s, "07-search-program.png", "NCIS finds CBS 2, because that is the program on right now.", 3.3 * inch))

    story.append(PageBreak())
    story.append(Paragraph("Several games at once", s["h1"]))
    story.append(
        h.P(
            s,
            "Tap <b>4 Programs</b> before the games, then tap up to four. You do not pick TV numbers. "
            "The first game goes on one set of TVs, the next game on the next set. <b>9 Programs</b> is the same idea, up to nine.",
        )
    )
    story.append(h.photo(s, "08-four-programs.png", "Two college games selected for 4 Programs. Take is blue."))
    story.append(Paragraph("When every DirecTV box is in use", s["h2"]))
    story.append(
        h.P(
            s,
            "A set or Pick TVs needs a free box. If there is not one, the line above Take says to choose a program to replace. "
            "Tap the program in the middle. Take turns into <b>Replace</b>. That program goes off. "
            "TVs that were on it and are not in your set turn off. The summary says so.",
        )
    )
    story.append(h.photo(s, "11-replace.png", "Every box is in use. Patio is still selected. Choose which program to replace.", 3.8 * inch))
    return story


def full_story(h):
    s = h.make_styles()
    story = cover(
        h,
        s,
        "FULL GUIDE",
        "Sports Routing on the iPad",
        [
            "Hold the iPad sideways. This is the screen staff use during a game.",
            "Live commit stays off until a manager turns it on. It cannot be turned on yet.",
            "Program names in the pictures are from one evening. They change. The buttons do not.",
        ],
    )
    story.append(Paragraph("1. How to open it", s["h1"]))
    story.append(
        h.numbered(
            s,
            [
                "Home Assistant Companion, or Safari, signed in to the bar's Home Assistant.",
                "Sidebar: <b>Sports Routing</b>.",
                "Turn the iPad sideways. Landscape is the layout in these pictures.",
            ],
        )
    )
    story.append(
        h.P(
            s,
            "<b>AVAccess Matrix</b> (favorites such as FOX Local) is a separate sidebar item and is not covered here.",
        )
    )
    story.append(Paragraph("2. How the screen is laid out", s["h2"]))
    story.append(h.photo(s, "01-sports.png", "Football. Games in the middle. Displays on the right. Take is gray until a plan is ready.", 3.8 * inch))
    story.append(PageBreak())
    story.append(Paragraph("What each part does", s["h1"]))
    story.append(
        h.bullets(
            s,
            [
                "<b>Bar</b> is the room name. The top right is <b>No route</b> until a plan is ready.",
                "<b>Live commit</b> would send the plan to the DirecTV boxes and the TVs. Leave it off. The yellow line says why.",
                "<b>Left rail.</b> DirecTV's sports, then <b>Guide</b>, <b>Now</b>, and <b>Sets</b>. Swipe. There is no permanent scrollbar.",
                "<b>Sources</b> (middle). League chips, then the games. On Guide, the channel list and search. On Now, every TV.",
                "<b>Displays</b> (right). <b>All 35 TVs</b>, <b>4 Programs</b>, <b>9 Programs</b>, <b>Pick TVs</b>, then any sets you saved. Only one is active.",
                "<b>Take</b> (bottom). Gray until a program and a destination are both chosen. The sentence above the button is the plan.",
            ],
        )
    )
    story.append(Paragraph("3. Sports", s["h2"]))
    story.append(
        h.P(
            s,
            "The game list comes from DirecTV for this bar (Greensboro, ZIP 27403, Bars and Restaurants). It is not filled from the TV guide.",
        )
    )
    story.append(
        h.bullets(
            s,
            [
                "College football, NFL (Sunday Ticket numbers are high, such as <b>9558</b>), and college basketball (Duke on <b>612</b> in the pictures).",
                "NBA, including out-of-market games on NBA League Pass (a number such as <b>1204</b>).",
                "The other sports on the left rail, when DirecTV has games that day.",
                "Locals that can carry a game: <b>2</b> CBS, <b>8</b> FOX, <b>12</b> NBC, <b>45</b> ABC.",
            ],
        )
    )
    story.append(
        h.P(
            s,
            "Under Sources, <b>All</b> shows every game in that sport. The other chips are the leagues. "
            "A card with no channel number is listed, but Take will not tune it. The list refreshes when the iPad opens the page, and about every 15 minutes.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("4. Guide", s["h1"]))
    story.append(
        h.P(s, "Guide is the DirecTV Greensboro lineup staff can put on a TV. These are left out:")
    )
    story.append(
        h.bullets(
            s,
            [
                "Music-only channels (Music Choice, Sirius). Music video networks such as MTV stay.",
                "Pay-per-view and Hot Choice.",
                "Promo barkers (Audience Network).",
                "On-demand menus.",
                "A second copy of a station that already has its real channel number.",
            ],
        )
    )
    story.append(
        h.P(
            s,
            "News, HBO, shopping, and the sports channels stay. <b>Now</b> and <b>Next</b> show on the main locals and sports channels "
            "(2, 8, 12, 45, 206, 209, 219, 245, 9554). If listings are more than six hours old, a banner says the channel list is all you have. Search by number or name still works.",
        )
    )
    story.append(h.photo(s, "05-guide.png", "Guide. CBS 2 is showing NCIS. Titles change through the day.", 3.5 * inch))
    story.append(PageBreak())
    story.append(h.photo(s, "06-search-name.png", "Search by name. HGTV is channel 229.", 3.4 * inch))
    story.append(h.photo(s, "07-search-program.png", "Search by the program on now. NCIS is on CBS 2.", 3.4 * inch))

    story.append(PageBreak())
    story.append(Paragraph("5. Where the picture goes", s["h1"]))
    story.append(
        h.P(
            s,
            "<b>All 35 TVs</b> puts one game or channel on every TV. The summary names <b>ENC-01</b>, the first DirecTV box.",
        )
    )
    story.append(
        h.P(
            s,
            "<b>4 Programs</b>. Tap this first, then up to four games or channels. First pick is ENC-01, second is ENC-02, and so on. The room is striped.",
        )
    )
    story.append(
        h.table(
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
        h.P(
            s,
            "If you only pick two games, the other two boxes are left alone, and those TVs stay as they were. "
            "<b>9 Programs</b> is the same rule for nine boxes. TV 1 gets the first game, TV 2 the second, TV 10 the first game again.",
        )
    )
    story.append(h.photo(s, "08-four-programs.png", "Two games ready for 4 Programs.", 3.3 * inch))

    story.append(PageBreak())
    story.append(Paragraph("6. Named sets of TVs", s["h1"]))
    story.append(
        h.P(
            s,
            "A set is a saved Pick TVs list with a name. It is not a split. Swipe to <b>Sets</b>, type a name, tap the TVs, and tap <b>Save</b>. "
            "You can save 8 sets. A TV can be in more than one set. The later Take wins on a shared TV. "
            "Deleting a set removes the button. It does not clear TVs that were already routed.",
        )
    )
    story.append(h.photo(s, "09-tv-sets.png", "Editing Patio. TVs 8, 9, and 10 are in the set.", 3.3 * inch))
    story.append(
        h.P(
            s,
            "On Sports or Guide, tap one program, tap the set, tap <b>Take</b>. "
            "The summary names one DirecTV box, the program, the TVs in the set, and the channel. Other TVs stay as they were.",
        )
    )
    story.append(h.photo(s, "10-set-ready.png", "Duke selected, Patio selected, Take blue.", 3.3 * inch))

    story.append(PageBreak())
    story.append(Paragraph("7. Take, and replacing a program", s["h1"]))
    story.append(
        h.P(
            s,
            "Take shows <b>DRY-RUN SUMMARY</b> and updates the on-screen status. With Live commit off, no box changes channel and no TV switches input. "
            "Read the summary, then tap <b>Dismiss</b>.",
        )
    )
    story.append(h.photo(s, "03-take.png", "Dry-run summary for Duke on four TVs.", 3.2 * inch))
    story.append(
        h.P(
            s,
            "All 35, 4 Programs, and 9 Programs already know which box to use. A set or Pick TVs needs a free box, ENC-01 through ENC-10. "
            "If every TV you picked is already on the same box, Take reuses that box. Any TV that was on it but is not in your set turns off, because one box can only show one channel.",
        )
    )
    story.append(
        h.P(
            s,
            "If the TVs are not already on one box, and every box is busy, Take stays gray. The line above it says <b>All DirecTV boxes are in use. Choose one to replace.</b> "
            "The middle column lists the programs that are on. Tap one. Take becomes <b>Replace</b>. Dismiss closes the list and leaves your game and set selected.",
        )
    )
    story.append(PageBreak())
    story.append(h.photo(s, "11-replace.png", "Replace sheet. Patio stays selected on the right. The 49ers are one of the programs you can replace.", 4.2 * inch))
    story.append(
        h.photo(
            s,
            "12-replace-done.png",
            "After Replace: ENC-03 is Duke on Patio. The 49ers go off, including TVs that were on that game and are not in Patio.",
            4.0 * inch,
        )
    )
    story.append(
        h.P(
            s,
            "Only the box you picked changes channel. The other programs stay. Until the yellow line is gone, treat every Take and Replace as a practice press.",
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("8. Now, and what to leave alone", s["h1"]))
    story.append(
        h.P(
            s,
            "<b>Now</b> lists TVs 1 through 35. A TV with a plan shows the program and the channel. A TV with nothing planned says <b>Off</b>.",
        )
    )
    story.append(h.photo(s, "04-now.png", "After a Take, the TVs you chose show the game. The others say Off.", 3.6 * inch))
    story.append(Paragraph("Leave these alone", s["h2"]))
    story.append(
        h.bullets(
            s,
            [
                "Do not turn on <b>Live commit</b>.",
                "Do not expect the wall to change while the yellow line is showing.",
                "Do not hunt the guide for music-radio channels, pay-per-view, or on-demand menus.",
                "Do not Take a game card that has no channel number.",
            ],
        )
    )
    story.append(Paragraph("If the screen looks wrong", s["h2"]))
    story.append(
        h.table(
            s,
            ["What you see", "What it means"],
            [
                ["<b>No games in this slate</b>", "Nothing in that sport for the loaded days. Try another sport, or Guide."],
                ["<b>Guide listings unavailable</b>", "Channels are still there. Program titles are stale. Search by name or number."],
                ["Search returns nothing", "Try the channel number, or clear the box. Titles change through the day."],
                ["Take stays gray", "You still need a program and a destination. A set or Pick TVs also needs at least one TV."],
                ["<b>Choose one to replace</b>", "All ten DirecTV boxes are in use. Tap the program that should go off, then Replace."],
                ["<b>8 sets is the limit</b>", "Delete a set you do not use. Deleting the button does not change what the TVs are showing."],
            ],
            [2.4 * inch, 4.8 * inch],
        )
    )
    return story


def main() -> None:
    helpers = load_helpers()
    quick = ROOT / "docs" / "STAFF_QUICK_START.pdf"
    full = ROOT / "docs" / "STAFF_FULL_GUIDE.pdf"
    write(quick, quick_story(helpers), helpers)
    write(full, full_story(helpers), helpers)
    print(quick, quick.stat().st_size)
    print(full, full.stat().st_size)


if __name__ == "__main__":
    main()
