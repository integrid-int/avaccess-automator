# Sports Routing — staff training

Printable handouts, with the pictures:

- **[STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf)** — the short version staff can keep at the bar. _(PDF pending rebuild; use this page, STAFF_TRAINING.md, for the current UI.)_
- **[STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf)** — every button, including named TV sets and replacing a program when every DirecTV box is in use. _(PDF pending rebuild; use this page, STAFF_TRAINING.md, for the current UI.)_

This page is the same training in text. If this page and a PDF disagree, this page is current. The older combined file, STAFF_TRAINING.pdf, does not include Sets or Replace. Until the two PDFs above are rebuilt, train from this page.

Hold the iPad **sideways**. Open the Home Assistant app, sign in, and tap **Sports Routing** in the sidebar.

**Look at the banner at the top first.** Next to **Bar** it says one of two things:

- **PRACTICE – TVs will not change** (gray). Take only plans the change and shows a summary. Nothing on the wall moves.
- **LIVE – TVs WILL change** (red, with a red stripe across the top). Take tunes the DirecTV boxes and switches the TVs for real.

Right now the banner says **PRACTICE**. The yellow line under the **Live commit: OFF** button says *Live commit is off until the room inventory is set up.* That button cannot be turned on yet. When a manager turns it on, every iPad in the bar turns red at the same time.

**AVAccess Matrix** (the other sidebar item, with FOX Local and the presets) has no PRACTICE mode. Every tap there changes the wall. If you are practicing, stay on Sports Routing.

The lists move when you drag them. On the iPad a scrollbar appears only while your finger is moving, then it disappears. You will not see a permanent gray bar.

The program names in these pictures are from one evening. They change through the day. The buttons do not. The pictures were taken before the banner was added and before Guide, Now, and Sets moved to the top of the left column.

---

## 1. Quick start

The screen is three columns, plus **Take** along the bottom.

| Column | What you use it for |
|---|---|
| Left | **Guide**, **Now**, and **Sets** at the top. Under them, a sport (Football, Basketball, and the rest). |
| Middle | The games, or the channel list |
| Right | Where it goes: every TV, a split, or TVs you pick |

**Take** stays gray until you have both a program and a place to put it. When it turns blue, the line above it is the plan in one sentence.

### One game on every TV

1. Tap the sport on the left.
2. Tap a league if you need one (**NFL**, **NCAA Basketball (M)**, and so on). **All** shows every game in that sport.
3. Tap the game. It turns blue.
4. On the right, tap **All 35 TVs**.
5. Tap the blue **Take**.
6. Read the summary, then tap **Dismiss**.

### One game on a few TVs

Basketball, then **NCAA Basketball (M)**, then the game. Tap **Pick TVs** and tap the TV numbers. Tap a number again to remove it. **Clear TVs** removes all of them.

![Tennessee at Duke selected, TVs 1, 3, 5, and 7 picked, Take in blue](images/staff/02-pick-tvs.png)

The top right reads **Ready · Tennessee @ Duke · Tune 612 → TVs 1, 3, 5, 7**. **612** is the DirecTV channel. Tap **Take**.

![Practice summary for Duke on TVs 1, 3, 5, and 7](images/staff/03-take.png)

The summary is headed **PRACTICE summary**. It names the DirecTV box, the game, the TVs, and the channel. **Dismiss** closes it. Nothing was sent to the wall. The game card then shows a badge such as **4 TVs**, and those TV buttons show the channel.

### What is on each TV

Tap **Now** at the top of the left column.

![Now playing: TVs 1, 3, and 5 on Duke, 2 and 4 unassigned](images/staff/04-now.png)

Every TV is listed. After the Take above, 1, 3, 5, and 7 show the game and channel **612**. The others say **Unassigned** and **Still showing last box until reassigned**. Unassigned does not mean the TV is off. The picture shows the older word *Off*; the screen now says Unassigned.

### Find a channel that is not a game

Tap **Guide** at the top of the left column. The list is DirecTV for Greensboro (ZIP 27403). The box says **Search by channel, name, or title**.

![Guide open on the Greensboro lineup, CBS 2 showing NCIS](images/staff/05-guide.png)

Search works three ways:

- **Channel name.** `HGTV` leaves channel **229**.

  ![Search HGTV shows channel 229](images/staff/06-search-name.png)

- **What is on right now.** `NCIS` finds CBS **2**, because that is the current program.

  ![Search NCIS finds CBS 2](images/staff/07-search-program.png)

- **Channel number.** `206` finds ESPN.

Tap the row, then **All 35 TVs** or **Pick TVs**, then **Take**.

### Several games at once

Tap **4 Programs** *before* you tap the games. Then tap up to four games. Each one you tap turns blue. You do not pick TV numbers. The first game goes on one set of TVs, the next game on the next set. TVs that do not get a game stay on whatever they were already showing.

![4 Programs with two college games selected and Take in blue](images/staff/08-four-programs.png)

The line above Take reads **2 programs → 4 Programs**. **9 Programs** is the same idea, with up to nine games.

A game that has no channel number can still be in the list, but you cannot Take it. If you select it, Take stays gray and a red line above it says **Cannot Take: … has no DirecTV channel**. Pick a game with a channel number, or find the channel in Guide.

### A named set of TVs

Tap **Sets** at the top of the left column. Type a name such as Patio (24 characters at most), tap the TV numbers, then **Save**. You need at least one TV. Eight sets is the limit. The same name cannot be saved twice. A TV can be in more than one set.

![Sets editor with Patio and TVs 8, 9, and 10 selected](images/staff/09-tv-sets.png)

The name shows under Displays on Sports and on Guide, under All 35 TVs, 4 Programs, 9 Programs, and Pick TVs. Tap the game, tap **Patio**, tap **Take**. Only the TVs in the set change. **Delete** removes the button. It does not clear TVs that were already routed.

![Duke selected, Patio highlighted, Take ready](images/staff/10-set-ready.png)

### When every DirecTV box is in use

**All 35 TVs**, **4 Programs**, and **9 Programs** do not get stuck. They reuse their own boxes. **Pick TVs** and a named set need a free box (ENC-01 through ENC-10).

If a free DirecTV box exists, Take uses that free box. The other TVs stay on their current program. Take only reuses a shared box when none are free, or when you tap **Replace**.

Reusing a shared box always asks first. The button changes to **Confirm** and the summary says, for example, **6 TVs will keep showing the retuned program until reassigned. Tap Confirm to continue.** Those leftover TVs were on that box but are not in your set. They do not turn off. They follow the box to the new channel. Tap **Confirm** only if that is all right. Otherwise **Dismiss** and choose different TVs.

If the TVs are not already one box and no box is free, Take stays gray. The header says **All DirecTV boxes are in use**. The middle column becomes **Choose a program** and lists what is on, with the channel and the TVs. Tap the one to retune. Take becomes **Replace**, then **Confirm** if any TVs are left over.

![Choose a program: the 49ers row is selected, Patio stays on the right, Replace is ready](images/staff/11-replace.png)

The summary names the box, the new program, the set’s TVs, the channel, and a **still on retuned box** line for the leftover TVs.

![Practice summary: Duke on Patio, 49ers still on retuned box for TVs 1 through 6](images/staff/12-replace-done.png)

Dismiss on the banner leaves the game and the set selected. Only the box you chose changes. Other programs stay.

---

## 2. Full guide

### How to open it

1. Home Assistant Companion, or Safari, signed in to the bar’s Home Assistant.
2. Sidebar: **Sports Routing**.
3. Turn the iPad sideways. In portrait the columns stack and the buttons get small. Landscape is the layout in these pictures.

Sports Routing is the screen staff use during a game. **AVAccess Matrix** (favorites such as FOX Local) is a separate sidebar item and is not covered here. Matrix is always live: it has no PRACTICE banner and no Live commit button.

### How the screen is laid out

![Football open, college games in the middle, displays on the right, Take gray](images/staff/01-sports.png)

- **Bar** is the room name. Next to it is the banner: **PRACTICE – TVs will not change** or **LIVE – TVs WILL change**. The top right is **No route** until a plan is ready, then a one-line description of what Take will do.
- **Live commit: OFF / ON** is the switch that would send the plan to the DirecTV boxes and the TVs. It is off, and the yellow line says why. Leave it off. It is one switch for the whole bar: if a manager turns it on, every iPad shows **LIVE**.
- **Clear room state** (next to Live commit) wipes both of this iPad’s Now lists: the PRACTICE one and the LIVE one. Use it when Now is wrong, or when a manager asks before going Live. It does not change any TV and does not delete your named sets.
- **Left rail.** **Guide**, **Now**, and **Sets** are pinned at the top. Under them, DirecTV’s own sports, in this order: Football, Basketball, Baseball, Hockey, Soccer, Rugby, Racing, Combat, Golf, Tennis, Cricket, Volleyball, Rodeo, Raquet Ball. The sports list scrolls on its own. There is no permanent scrollbar.
- **Sources** (middle). League chips, then the games. On Guide, this column is the channel list and the search box. On Now, it is the TV-by-TV list.
- **Displays** (right). **All 35 TVs**, **4 Programs**, **9 Programs**, **Pick TVs**, or a named set such as **Patio**. Only one of these is active. Choosing a preset clears a set. Choosing a set clears the preset. Pick TVs is the one-off number grid.
- **Take** (bottom). Gray and disabled until a program and a destination are both chosen. Blue means the plan is ready. The sentence above the button is the same plan. The button can also read **Replace**, **Confirm**, or **Sending…**.

### Sports

The game list comes from DirecTV’s sports page for this bar (Greensboro, ZIP 27403, Bars and Restaurants). It is not filled from the TV guide.

What you will see:

- College football on ESPNU, ESPN2, and the other sports channels.
- NFL, including Sunday Ticket channels. Those numbers are high, such as **9558**.
- College basketball, men’s and women’s, including games on ACC Network (Duke on **612** in the pictures).
- NBA, including out-of-market games on NBA League Pass (a number such as **1204**).
- The other sports on the left rail, when DirecTV has games that day.

Locals stay in the guide and can carry a game: **2** CBS (WFMY), **8** FOX (WGHP), **12** NBC (WXII), **45** ABC (WXLV).

Under **Sources**, **All** shows every game in the sport you tapped. The other chips are the leagues inside that sport (NFL, NCAA Football, NBA, NCAA Basketball (M), and so on). A sport with one league has no extra chips.

Each card shows the two teams, the league, the channel number and name, and the start time. Teams without a logo show their initials. Tap a card to select it. Tap it again to clear it when you are in **4 Programs** or **9 Programs**. For a single game, tap a different card to switch.

If a card has no channel number, it is listed so you can see the game, but Take stays gray and the line above it says **Cannot Take: … has no DirecTV channel**.

If the sports list could not load, a banner says **Sports listings unavailable — showing demo games. Live Take is blocked.** Those are not real games. Use Guide instead. If the list is more than a day old, a banner says **Sports listings are stale**.

The list refreshes when the iPad opens the page, and about every 15 minutes after that.

### Guide

Guide is the DirecTV Greensboro lineup from TV Passport. It is the full lineup staff can actually put on a TV, with these left out:

- Music-only channels (Music Choice, Sirius, and similar). Music *video* networks such as MTV stay.
- Pay-per-view and Hot Choice.
- Promo barkers (Audience Network).
- On-demand menus.
- A second copy of a station that already has its real channel number (the extra copy is usually a 9000-series number).

News, HBO, shopping, and the sports channels stay.

**Now** and **Next** (the program title under the channel name) are filled for the main locals and sports channels: 2, 8, 12, 45, 206 ESPN, 209 ESPN2, 219 FS1, 245 TNT, and 9554. The other channels show the number and name only.

If the program list is missing or more than six hours old, a banner says **Guide listings unavailable — channel list only**. You can still search by number or name and still Take a channel. You just will not see what is on.

Search matches the channel number, the channel name, the category, and the Now or Next title. It waits a moment while you type so the cursor is not stolen. Clear the box to get the full list back.

The titles in the pictures (`NCIS` on CBS 2, `Best Medicine` on FOX 8, `NBA Basketball` on NBC 12) are whatever was on that evening. Tomorrow the same search can find a different channel.

### Where the picture goes

**All 35 TVs** (Preset 1). One game or one channel, on every TV. The summary names **ENC-01**. That is the first DirecTV box. The tune line is `Tune` plus the channel number.

**4 Programs** (Preset 2). Tap this first, then tap up to four games or channels. The order you tap is the order of the boxes: first pick is ENC-01, second is ENC-02, and so on. The room is striped, not blocked into four corners:

| Pick | DirecTV box | TVs |
|---|---|---|
| 1st | ENC-01 | 1, 5, 9, 13, 17, 21, 25, 29, 33 |
| 2nd | ENC-02 | 2, 6, 10, 14, 18, 22, 26, 30, 34 |
| 3rd | ENC-03 | 3, 7, 11, 15, 19, 23, 27, 31, 35 |
| 4th | ENC-04 | 4, 8, 12, 16, 20, 24, 28, 32 |

If you only pick two games, ENC-03 and ENC-04 are left alone, and the TVs in those two rows stay on whatever they were already showing. Extra taps past four are ignored. The line above Take tells you how many you have picked (`2 programs → 4 Programs`).

**9 Programs** (Preset 3). Same rule, up to nine games, nine boxes (ENC-01 through ENC-09). TVs are striped by nine: TV 1 with the first game, TV 2 with the second, TV 10 with the first game again.

AVAccess Matrix’s Preset 2 and Preset 3 split the room into blocks of neighboring TVs, not stripes. Do not expect the two screens to put the same game on the same TVs.

**Pick TVs.** Choose the exact screens for this one plan. Tap numbers, tap again to remove, or **Clear TVs**. This uses the lowest free DirecTV box from ENC-01 through ENC-10. ENC-10 is the spare.

**Named sets.** **Sets** at the top of the left rail saves a name and a list of TVs (Patio is 8, 9, and 10 in the pictures). Save needs a name and at least one TV. Eight sets is the limit. Duplicate names are refused. The button then appears under Displays on Sports and Guide. Tap one program, tap the set, tap Take. A TV can belong to more than one set; the later Take wins on a shared TV. Delete removes the button only. It does not clear a route that already happened. The iPad keeps the list. When Home Assistant is connected, the same save writes `custom_tv_sets.json` so a replacement iPad can load it.

**No free box.** Pick TVs and a named set are the only paths that need a free box. If a free box exists, Take claims it even when the selected TVs already share a box (Patio after All 35 uses ENC-02, not ENC-01). If every selected TV is already on exactly one box and none are free, the button becomes **Confirm** before reusing that box. The summary says how many leftover TVs will keep showing the retuned program until reassigned. If the selection spans more than one box and none are free, the middle column lists the programs already on. Tap one. Take becomes **Replace**, then **Confirm** if there are leftover TVs. The summary is one line for the new plan and one still-on-retuned-box line, for example `49ers @ Falcons still on retuned box · TVs 1–6`. Those TVs are not turned off; nothing on this screen turns a TV off. Other programs stay. All 35, 4 Programs, and 9 Programs overwrite their own boxes and never open this chooser.

You plan either a preset or a TV pick, not both. The header and the line above Take are the check before you press the button.

### Take, and what the summary means

Take builds the plan and shows the summary. Under **PRACTICE**, the summary is headed **PRACTICE summary**. No box changes channel. No TV switches input. The PRACTICE Now list still updates, so you can practice. It is kept apart from the LIVE Now list, so practice Takes never show up once the banner is LIVE.

Read the summary before you dismiss it. One line per box, for example:

`ENC-01 · Tennessee @ Duke · TVs 1, 3, 5, 7 · Tune 612`

**Dismiss** closes the summary. The game card gets a badge with the TV count. Open **Now** if you want the full room list.

When a manager turns Live commit on, the banner turns red (**LIVE – TVs WILL change**) and the same Take sends the channel change to the DirecTV box and then switches the TVs. While it is sending, the button reads **Sending…** and cannot be pressed again. The summary is headed **Live summary** and each line ends in `ok` or `error`. A TV row with `error` did not change. Only rows marked `ok` are added to Now. If the summary shows a red error, tell a manager; do not keep pressing Take.

### Now

**Now** is this iPad’s assignment list, not a power switch. It lists TVs 1 through 35. A TV with a plan shows the program name and the channel. A TV with nothing on this iPad’s plan says **Unassigned** and **Still showing last box until reassigned**. The count at the top is how many of the 35 are assigned here.

Now is kept on this iPad only. Another iPad, or a Matrix tap, does not update it. PRACTICE and LIVE each keep their own Now list. Practice Takes fill in the PRACTICE list even though the wall did not change; under the LIVE banner, Now shows only Live Takes. Tap **Clear room state** to empty both lists. A manager may ask the Live iPad to Clear room state before the bar goes Live.

While **Pick TVs** is open, the number buttons on the right also show the channel under the TV number (the pictures show **612 ACC** on 1, 3, 5, and 7).

### What to leave alone

- Do not turn on **Live commit**. It will not turn on until the room inventory is set up, and the yellow line is the reminder.
- Do not expect the TVs on the wall to change after Take while the banner says **PRACTICE**.
- Do not practice on AVAccess Matrix. It is always live.
- Do not hunt the guide for music-radio channels, pay-per-view, or the on-demand menus. They are left out on purpose.
- Do not try to Take a game card that has no channel number. Take is blocked for it.

### If the screen looks wrong

| What you see | What it means |
|---|---|
| **PRACTICE – TVs will not change** | Normal for now. Take only plans. |
| **LIVE – TVs WILL change** (red) | A manager turned Live commit on. Every Take changes the wall. If you did not expect this, tell a manager. |
| **No games in this slate** | DirecTV has nothing in that sport for the days that were loaded. Try another sport, or Guide. |
| **Sports listings unavailable — showing demo games** | The game list did not load. The games are fake. Use Guide. |
| **Guide listings unavailable — channel list only** | The channel list is fine. Program titles are stale. Search by name or number still works. |
| Search returns nothing | Try the channel number, or clear the box. Titles change; yesterday’s show will not match. |
| Take stays gray | You still need a game or channel, and a destination (All 35, 4 Programs with at least one pick, 9 Programs with at least one pick, Pick TVs, or a named set). |
| **Cannot Take: … has no DirecTV channel** (Take gray) | That game has no channel number. Pick another game or use Guide. |
| Button says **Confirm** | Leftover TVs will keep showing the retuned program. Confirm, or Dismiss and change the TVs. |
| Button says **Sending…** | A Live Take is in progress. Wait for the summary. |
| **All DirecTV boxes are in use** | Pick TVs or a named set, and no free box. The middle column says **Choose a program**. Tap the one to retune. Take becomes **Replace**, then Confirm if leftover TVs keep the retuned program. All 35, 4 Programs, and 9 Programs do not hit this. |
| Now shows TVs on games that are not on the wall | Now is this iPad’s list. Under PRACTICE, practice Takes fill it in. Tap **Clear room state** (it empties both the PRACTICE and LIVE lists). |
| **8 sets is the limit** | Delete a set before saving another. Delete only removes the button. |
