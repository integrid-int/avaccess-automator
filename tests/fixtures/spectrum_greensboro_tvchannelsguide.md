Spectrum Channel Lineup in Greensboro, NC (2026) — 160+ Channels

{ const bar = this.$refs.stickyBar; if (bar) { this.theadTop = bar.offsetHeight; new ResizeObserver(() => { this.theadTop = bar.offsetHeight; }).observe(bar); } }); }, setPkg(tier, pos) { if (this.pkg === tier) { this.pkg = ''; this.pkgPos = -1; } else { this.pkg = tier; this.pkgPos = pos; } }, visible(index) { const ch = this.channels[index]; if (!ch) return false; const s = this.search.toLowerCase(); const matchSearch = s === '' || ch.name.toLowerCase().includes(s) || ch.number.includes(s); const matchCat = this.category === '' || ch.category === this.category; const matchPkg = this.pkgPos === -1 || (ch.tierFlags && ch.tierFlags[this.pkgPos] === 1); return matchSearch && matchCat && matchPkg; }, get visibleCount() { return this.channels.filter((_, i) => this.visible(i)).length; }, sortTable() { const tbody = this.$refs.tbody; if (!tbody) return; const rows = Array.from(tbody.querySelectorAll('tr[data-index]')); const col = this.sortCol; const asc = this.sortAsc; rows.sort((a, b) => { let va, vb; if (col === 'number' || col.startsWith('tier_')) { va = parseInt(a.dataset[col]) || 0; vb = parseInt(b.dataset[col]) || 0; } else { va = a.dataset[col] || ''; vb = b.dataset[col] || ''; } if (va < vb) return asc ? -1 : 1; if (va > vb) return asc ? 1 : -1; return 0; }); rows.forEach(r => tbody.appendChild(r)); } }">

# Spectrum Channels in Greensboro, North Carolina

Cable 368 channels · Verified Apr 7, 2026

Spectrum in Greensboro, North Carolina stands out for local stations like wcwg on channel 3, wlxi on channel 6, wxlv on channel 7, and wfmy on channel 9, part of 58 channels not found on the other North Carolina Spectrum lineups in our database. The full lineup carries 368 channels across 10 packages. 352 channels are included in base packages and 16 are premium add-ons.

## Unique to Greensboro, NC

These channels are carried on Spectrum in Greensboro, NC but not in other NC markets we track:

- wcwg— channel 3 (Local)
- wlxi— channel 6 (Local)
- wxlv— channel 7 (Local)
- wfmy— channel 9 (Local)
- wghp— channel 10 (Local)
- wxii— channel 11 (Local)
- wgpx— channel 12 (Local)
- Spectrum News 1— channel 14 (News)
- wmyv— channel 15 (Local)
- FanDuel Sports Network South-Carolinas— channel 51 (Sports)
- Univision— channel 56 (Spanish)
- Hallmark Mystery— channel 78 (Entertainment)
- Gem Shopping Network— channel 86 (Shopping)
- UP TV— channel 124 (Entertainment)
- Magnolia Network— channel 161 (Lifestyle)
- BBC News— channel 209 (News)
- CNN International— channel 216 (News)
- Baby First TV— channel 256 (Kids)
- MTV Live— channel 286 (Entertainment)
- Spectrum SportsNet LA— channel 331 (Sports)
- ESPN College Extra— channel 392 (Sports)
- FanDuel TV— channel 413 (Sports)
- Jewish Life Television— channel 469 (Religious)
- HBO Drama— channel 513 (Premium)
- HBO Movies— channel 516 (Premium)
- MGM+ East— channel 595 (Premium)
- CNN en Español— channel 834 (Spanish)
- Mexico 22— channel 841 (Spanish)
- Canal Once— channel 844 (Spanish)
- TVV— channel 867 (Spanish)
- Telemicro Canal 5— channel 871 (Spanish)
- Antena 3 Internacional— channel 877 (Spanish)
- TVE Internacional— channel 878 (Spanish)
- Univision Telenovelas— channel 895 (Spanish)
- MTV Tr3s— channel 899 (Spanish)
- Baby First TV Espanol— channel 928 (Spanish)
- Baby TV— channel 929 (Spanish)
- Aplauso— channel 936 (Spanish)
- wxlv-tv2— channel 1240 (Local)
- wxlv-tv3— channel 1241 (Local)
- wxii-tv2— channel 1245 (Local)
- wghp2— channel 1250 (Local)
- wfmy-dt2— channel 1255 (Local)
- wcwg-dt2— channel 1260 (Local)
- wcwg-dt3— channel 1261 (Local)
- wmyv2— channel 1265 (Local)
- wmyv3— channel 1266 (Local)
- wunc-dt2— channel 1275 (Local)
- wunc-dt3— channel 1276 (Local)
- wunc-dt4— channel 1277 (Local)
- CCTV-4 America— channel 1401 (International)
- SETAsia— channel 1541 (Spanish)
- Channel 1 Russian— channel 1612 (International)
- ART Cable— channel 1632 (Entertainment)
- Music Choice Hit List— channel 1901 (Music)
- Music Choice: Pop Latino— channel 1936 (Music)
- Music Choice Romances— channel 1940 (Music)
- Music Choice Classical Masterpieces— channel 1948 (Music)

Category: All Documentary Entertainment International Kids Lifestyle Local Music News Premium Religious Shopping Spanish Sports Xumo

Package: All TV Stream TV Select Signature TV Select Plus TV Platinum TV Stream Latino Mi Plan Latino

channels shown

✓ Included $ Add-on — Not available

3

4

6

7

9

10

11

12

14

15

16

17

18

20

21

22

23

24

25

26

27

28

29

30

31

32

33

34

35

36

37

38

39

40

41

43

44

45

46

48

49

50

51

52

53

54

55

56

57

59

60

61

62

63

64

65

66

67

70

71

72

73

76

78

79

80

81

86

87

98

109

110

119

124

128

130

131

133

134

135

136

137

140

141

144

145

151

159

161

163

165

169

173

174

175

176

177

179

182

184

185

187

188

189

194

207

209

210

216

222

224

226

227

253

254

255

256

262

263

265

266

286

287

288

290

291

292

295

297

299

302

306

307

308

309

310

311

312

315

316

330

331

339

370

372

373

374

382

384

385

388

392

400

401

402

403

406

408

413

416

417

419

440

442

443

444

461

463

464

465

468

469

470

472

474

481

484

511

512

513

514

515

516

517

531

532

533

534

535

536

537

551

552

553

554

555

556

557

558

571

572

581

582

583

584

585

586

595

597

598

599

602

603

604

605

606

607

608

620

621

622

623

625

627

632

633

640

803

804

806

811

827

834

841

842

843

844

845

847

849

850

855

856

857

860

861

867

870

871

872

874

875

877

878

895

898

899

910

912

913

915

918

919

921

922

923

924

926

928

929

930

931

932

933

935

936

937

945

946

962

971

972

979

980

982

983

984

985

1240

1241

1245

1250

1255

1260

1261

1265

1266

1275

1276

1277

1400

1401

1404

1450

1452

1453

1533

1541

1542

1550

1551

1554

1575

1581

1610

1612

1613

1621

1632

1901

1902

1903

1904

1905

1906

1907

1908

1909

1910

1911

1912

1913

1914

1915

1916

1917

1918

1919

1921

1922

1923

1924

1925

1926

1927

1928

1929

1930

1931

1932

1933

1934

1935

1936

1937

1938

1939

1940

1941

1942

1943

1944

1945

1946

1947

1948

1949

1950

| Ch # | Channel | Category | TV Stream | TV Select Signature | TV Select Plus | TV Platinum | TV Stream Latino | Mi Plan Latino |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| wcwg | Local | — | ✓ | ✓ | ✓ | — | — |
| WUNC (PBS) | Local | — | ✓ | ✓ | ✓ | — | — |
| wlxi | Local | — | ✓ | ✓ | ✓ | — | — |
| wxlv | Local | — | ✓ | ✓ | ✓ | — | — |
| wfmy | Local | — | ✓ | ✓ | ✓ | — | — |
| wghp | Local | — | ✓ | ✓ | ✓ | — | — |
| wxii | Local | — | ✓ | ✓ | ✓ | — | — |
| wgpx | Local | — | ✓ | ✓ | ✓ | — | — |
| Spectrum News 1 | News | — | ✓ | ✓ | ✓ | — | — |
| wmyv | Local | — | ✓ | ✓ | ✓ | — | — |
| ESPN2 | Sports | — | ✓ | ✓ | ✓ | — | — |
| ESPN | Sports | — | ✓ | ✓ | ✓ | — | — |
| Paramount Network | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Freeform | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| TNT | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| BET | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| TBS | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| AMC | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Discovery | Documentary | — | ✓ | ✓ | ✓ | — | — |
| Weather Channel | News | — | ✓ | ✓ | ✓ | — | — |
| MTV | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| A&E | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| National Geographic | Documentary | — | ✓ | ✓ | ✓ | — | — |
| CNBC | News | — | ✓ | ✓ | ✓ | — | — |
| HLN | News | — | ✓ | ✓ | ✓ | — | — |
| Nickelodeon | Kids | — | ✓ | ✓ | ✓ | — | — |
| Lifetime | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| CNN | News | — | ✓ | ✓ | ✓ | — | — |
| CMT | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| VH1 | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Comedy Central | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| NBC Sports | Sports | — | — | ✓ | ✓ | — | — |
| C-SPAN | News | — | ✓ | ✓ | ✓ | — | — |
| Fox News | News | — | ✓ | ✓ | ✓ | — | — |
| truTV | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Bravo | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| TLC | Lifestyle | — | ✓ | ✓ | ✓ | — | — |
| Syfy | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| E! | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Cartoon Network | Kids | — | ✓ | ✓ | ✓ | — | — |
| Hallmark Channel | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| USA Network | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| FanDuel Sports Network South-Carolinas | Sports | — | — | ✓ | ✓ | — | — |
| Golf Channel | Sports | — | — | — | ✓ | — | — |
| History | Documentary | — | ✓ | ✓ | ✓ | — | — |
| Nick Jr | Kids | — | — | — | ✓ | — | — |
| HGTV | Lifestyle | — | ✓ | ✓ | ✓ | — | — |
| Univision | Spanish | — | — | — | — | — | ✓ |
| TCM | Entertainment | — | — | — | ✓ | — | — |
| MS NOW | News | — | ✓ | ✓ | ✓ | — | — |
| FX | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| MTV Classic | Entertainment | — | — | — | ✓ | — | — |
| TV Land | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Animal Planet | Documentary | — | ✓ | ✓ | ✓ | — | — |
| Discovery Life | Documentary | — | — | — | ✓ | — | — |
| Food Network | Lifestyle | — | ✓ | ✓ | ✓ | — | — |
| Eternal Word Television Network | Religious | — | ✓ | ✓ | ✓ | — | — |
| FanDuel Sports Network Southeast | Sports | — | — | ✓ | ✓ | — | — |
| Oxygen | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| WE tv | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Lifetime Movie Network | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Disney Channel | Kids | — | ✓ | ✓ | ✓ | — | — |
| Investigation Discovery | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Hallmark Mystery | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| CNBC World | News | — | — | — | ✓ | — | — |
| DISCOVERY TURBO TV | Xumo | — | ✓ | ✓ | ✓ | — | — |
| Fox Business | News | — | ✓ | ✓ | ✓ | — | — |
| Gem Shopping Network | Shopping | — | ✓ | ✓ | ✓ | — | — |
| Shop LC | Shopping | — | ✓ | ✓ | ✓ | — | — |
| NewsNation | News | — | ✓ | ✓ | ✓ | — | — |
| FXX | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| BBC America | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| MTV2 | Entertainment | — | — | — | ✓ | — | — |
| UP TV | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| REELZ | Entertainment | — | — | — | ✓ | — | — |
| Nat Geo Wild | Documentary | — | — | — | ✓ | — | — |
| Smithsonian Channel | Documentary | — | — | — | ✓ | — | — |
| VICE | Entertainment | — | — | — | ✓ | — | — |
| FYI | Entertainment | — | — | — | ✓ | — | — |
| Destination America | Documentary | — | ✓ | ✓ | ✓ | — | — |
| Science Channel | Documentary | — | — | — | ✓ | — | — |
| Crime + Investigation | Entertainment | — | — | — | ✓ | — | — |
| American Heroes Channel | Documentary | — | — | — | ✓ | — | — |
| Military History Channel | Documentary | — | — | — | ✓ | — | — |
| Fusion | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| El Rey Network | Spanish | — | — | — | — | — | ✓ |
| Heroes & Icons | Entertainment | — | — | — | ✓ | — | — |
| QVC | Shopping | — | ✓ | ✓ | ✓ | — | — |
| Magnolia Network | Lifestyle | — | ✓ | ✓ | ✓ | — | — |
| Cooking Channel | Lifestyle | — | ✓ | ✓ | ✓ | — | — |
| Travel Channel | Lifestyle | — | ✓ | ✓ | ✓ | — | — |
| Fuse | Entertainment | — | — | — | ✓ | — | — |
| OWN | Entertainment | — | — | — | ✓ | — | — |
| Lifetime Real Women | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Pop | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| HSN | Shopping | — | ✓ | ✓ | ✓ | — | — |
| Game Show Network | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Logo | Entertainment | — | — | — | ✓ | — | — |
| BET Her | Entertainment | — | — | — | ✓ | — | — |
| TV One | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| ASPiRE | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Ovation | Entertainment | — | — | — | ✓ | — | — |
| Jewelry Television | Shopping | — | ✓ | ✓ | ✓ | — | — |
| Cleo TV | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| ShopHQ | Shopping | — | ✓ | ✓ | ✓ | — | — |
| Bloomberg Business Television | News | — | ✓ | ✓ | ✓ | — | — |
| BBC News | News | — | ✓ | ✓ | ✓ | — | — |
| i24 News | News | — | — | — | ✓ | — | — |
| CNN International | News | — | ✓ | ✓ | ✓ | — | — |
| Newsmax | News | — | ✓ | ✓ | ✓ | — | — |
| Scripps News | News | — | ✓ | ✓ | ✓ | — | — |
| C-SPAN 2 | News | — | ✓ | ✓ | ✓ | — | — |
| C-SPAN 3 | News | — | ✓ | ✓ | ✓ | — | — |
| Boomerang | Kids | — | — | — | ✓ | — | — |
| Disney Junior | Kids | — | — | — | ✓ | — | — |
| Universal Kids | Kids | — | ✓ | ✓ | ✓ | — | — |
| Baby First TV | Kids | — | ✓ | ✓ | ✓ | — | — |
| Nicktoons | Kids | — | — | — | ✓ | — | — |
| TeenNick | Kids | — | — | — | ✓ | — | — |
| Disney XD | Kids | — | — | — | ✓ | — | — |
| Discovery Family | Documentary | — | — | — | ✓ | — | — |
| MTV Live | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| BET Jams | Music | — | — | — | ✓ | — | — |
| Nick Music | Music | — | — | — | ✓ | — | — |
| BET Soul | Music | — | — | — | ✓ | — | — |
| Revolt | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| FM | Music | — | — | — | ✓ | — | — |
| GAC Family | Entertainment | — | — | — | ✓ | — | — |
| RFD TV | Lifestyle | — | — | — | ✓ | — | — |
| AXS TV | Music | — | ✓ | ✓ | ✓ | — | — |
| ESPNews | Sports | — | — | — | ✓ | — | — |
| MLB Network | Sports | — | — | ✓ | ✓ | — | — |
| MLB Strike Zone | Sports | — | — | — | ✓ | — | — |
| NBA TV | Sports | — | — | ✓ | ✓ | — | — |
| BravesVision | Sports | — | — | ✓ | ✓ | — | — |
| NFL Network | Sports | — | — | ✓ | ✓ | — | — |
| NFL RedZone | Sports | — | — | — | ✓ | — | — |
| NHL Network | Sports | — | — | ✓ | ✓ | — | — |
| CBS Sports Network | Sports | — | — | — | ✓ | — | — |
| Olympic Channel | Sports | — | — | — | ✓ | — | — |
| Spectrum SportsNet | Sports | — | — | — | ✓ | — | — |
| Spectrum SportsNet LA | Sports | — | — | ✓ | ✓ | — | — |
| YES Network | Sports | — | — | ✓ | ✓ | — | — |
| ESPNU | Sports | — | — | — | ✓ | — | — |
| Stadium College Sports Atlantic | Sports | — | — | ✓ | ✓ | — | — |
| Stadium College Sports Central | Sports | — | — | ✓ | ✓ | — | — |
| Stadium College Sports Pacific | Sports | — | — | ✓ | ✓ | — | — |
| Big Ten Network | Sports | — | ✓ | ✓ | ✓ | — | — |
| SEC Network | Sports | — | ✓ | ✓ | ✓ | — | — |
| SEC Network Alternate | Sports | — | — | ✓ | ✓ | — | — |
| BTN Extra 1 | Sports | — | — | — | ✓ | — | — |
| ESPN College Extra | Sports | — | — | ✓ | ✓ | — | — |
| Fox Sports 1 | Sports | — | ✓ | ✓ | ✓ | — | — |
| FOX Sports 2 | Sports | — | ✓ | ✓ | ✓ | — | — |
| RACER Network | Sports | — | — | ✓ | ✓ | — | — |
| Motor Trend | Documentary | — | — | — | ✓ | — | — |
| Tennis Channel | Sports | — | — | ✓ | ✓ | — | — |
| Outdoor Channel | Sports | — | — | — | ✓ | — | — |
| FanDuel TV | Sports | — | — | ✓ | ✓ | — | — |
| GOL TV | Sports | — | — | — | ✓ | — | — |
| beIN Sports | Sports | — | ✓ | ✓ | ✓ | — | — |
| Fox Soccer Plus | Sports | — | — | — | ✓ | — | — |
| ESPN Deportes | Spanish | — | ✓ | ✓ | ✓ | — | — |
| Fox Deportes | Spanish | — | ✓ | ✓ | ✓ | — | — |
| beIN Sports Spanish | Sports | — | ✓ | ✓ | ✓ | — | — |
| TUDN | Spanish | — | ✓ | ✓ | ✓ | — | — |
| INSP | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| Daystar Television Network | Religious | — | ✓ | ✓ | ✓ | — | — |
| Trinity Broadcasting Network | Religious | — | ✓ | ✓ | ✓ | — | — |
| BYU-TV | International | — | — | — | ✓ | — | — |
| Cowboy Channel | Sports | — | — | — | ✓ | — | — |
| Jewish Life Television | Religious | — | ✓ | ✓ | ✓ | — | — |
| SonLife Broadcasting Network | Religious | — | ✓ | ✓ | ✓ | — | — |
| TBN Inspire | Religious | — | ✓ | ✓ | ✓ | — | — |
| Impact TV Network | International | — | ✓ | ✓ | ✓ | — | — |
| QVC2 | Shopping | — | ✓ | ✓ | ✓ | — | — |
| HSN2 | Shopping | — | ✓ | ✓ | ✓ | — | — |
| HBO | Entertainment | — | — | — | ✓ | — | — |
| HBO Hits | Premium | — | — | — | ✓ | — | — |
| HBO Drama | Premium | — | — | — | ✓ | — | — |
| HBO Family | Entertainment | — | — | — | — | — | — |
| HBO Comedy | Entertainment | — | — | — | ✓ | — | — |
| HBO Movies | Premium | — | — | — | ✓ | — | — |
| HBO Latino | Entertainment | — | — | — | ✓ | — | — |
| Cinemax | Entertainment | — | — | — | ✓ | — | — |
| MoreMAX | Premium | — | $ | $ | ✓ | — | — |
| Cinemax Action | Premium | — | — | — | ✓ | — | — |
| ThrillerMAX | Premium | — | — | — | — | — | — |
| OuterMAX | Premium | — | — | — | — | — | — |
| Cinemax Spanish | Premium | — | — | — | ✓ | — | — |
| Cinemax Classics | Premium | — | — | — | ✓ | — | — |
| Paramount+ with Showtime | Premium | — | $ | $ | ✓ | — | — |
| Showtime 2 | Entertainment | — | $ | $ | ✓ | — | — |
| SHO x BET | Premium | — | — | — | ✓ | — | — |
| Showtime Extreme | Entertainment | — | — | — | ✓ | — | — |
| Showtime Showcase | Premium | — | — | — | ✓ | — | — |
| Showtime Next | Premium | — | — | — | ✓ | — | — |
| Showtime Women | Premium | — | — | — | ✓ | — | — |
| Showtime Familyzone | Premium | — | — | — | ✓ | — | — |
| The Movie Channel | Premium | — | — | — | ✓ | — | — |
| The Movie Channel Extra | Premium | — | — | — | ✓ | — | — |
| Starz | Entertainment | — | — | — | ✓ | — | — |
| Starz Edge | Entertainment | — | — | — | ✓ | — | — |
| Starz in Black | Premium | — | — | — | ✓ | — | — |
| Starz Kids & Family | Kids | — | — | — | ✓ | — | — |
| Starz Cinema | Entertainment | — | — | — | ✓ | — | — |
| Starz Comedy | Entertainment | — | — | — | ✓ | — | — |
| MGM+ East | Premium | — | $ | $ | ✓ | — | — |
| MGM+ Hits | Premium | — | — | — | ✓ | — | — |
| MGM+ Marquee | Premium | — | — | — | ✓ | — | — |
| MGM+ Drive-In | Premium | — | — | — | ✓ | — | — |
| Starz Encore | Entertainment | — | — | — | ✓ | — | — |
| Starz Encore Action | Entertainment | — | — | — | ✓ | — | — |
| Starz Encore Black | Premium | — | — | — | ✓ | — | — |
| Starz Encore Classic | Entertainment | — | — | — | ✓ | — | — |
| Starz Encore Suspense | Premium | — | — | — | ✓ | — | — |
| Starz Encore Westerns | Entertainment | — | — | — | ✓ | — | — |
| Starz Encore Family | Premium | — | — | — | ✓ | — | — |
| MoviePlex | Premium | — | — | — | ✓ | — | — |
| IndiePlex | Premium | — | — | — | ✓ | — | — |
| RetroPlex | Premium | — | — | — | ✓ | — | — |
| Flix | Entertainment | — | — | — | ✓ | — | — |
| SundanceTV | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| IFC | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| FX Movie Channel | Entertainment | — | ✓ | ✓ | ✓ | — | — |
| MGM HD | Entertainment | — | $ | $ | ✓ | — | — |
| HDNet Movies | Entertainment | — | — | — | ✓ | — | — |
| Telemundo | Spanish | — | — | — | — | — | ✓ |
| UniMás | Spanish | — | — | — | — | — | ✓ |
| Azteca America | Spanish | — | — | — | — | — | ✓ |
| Estrella TV | Spanish | — | — | — | — | — | ✓ |
| Galavisión | Spanish | — | ✓ | ✓ | ✓ | — | — |
| CNN en Español | Spanish | — | — | — | — | — | ✓ |
| Mexico 22 | Spanish | — | — | — | — | — | ✓ |
| Estudio 5 | Spanish | — | — | — | — | — | ✓ |
| Multimedios USA | Spanish | — | — | — | — | — | ✓ |
| Canal Once | Spanish | — | — | — | — | — | ✓ |
| Teleformula | Spanish | — | — | — | — | — | ✓ |
| FOROtv | Spanish | — | — | — | — | — | ✓ |
| Ultra Docu | Spanish | — | — | — | — | — | ✓ |
| Canal Sur | Spanish | — | — | — | — | — | ✓ |
| TV Chile | Spanish | — | — | — | — | — | ✓ |
| CARACOL INTERNATIONAL | Spanish | — | — | — | — | — | ✓ |
| Nuestra Tele Internacional | Spanish | — | — | — | — | — | ✓ |
| CentroAméricaTV | Spanish | — | — | — | — | — | ✓ |
| Tele El Salvador | Spanish | — | — | — | — | — | ✓ |
| TVV | Spanish | — | — | — | — | — | ✓ |
| Super Canal | Spanish | — | — | — | — | — | ✓ |
| Telemicro Canal 5 | Spanish | — | — | — | — | — | ✓ |
| Televisión Dominicana | Spanish | — | — | — | — | — | ✓ |
| WAPA America | Spanish | — | — | — | — | — | ✓ |
| Cuba Play | Spanish | — | — | — | — | — | ✓ |
| Antena 3 Internacional | Spanish | — | — | — | — | — | ✓ |
| TVE Internacional | Spanish | — | — | — | — | — | ✓ |
| Univision Telenovelas | Spanish | — | — | — | — | — | ✓ |
| UNIVERSO | Spanish | — | ✓ | ✓ | ✓ | — | — |
| MTV Tr3s | Spanish | — | — | — | — | — | ✓ |
| Bandamax | Spanish | — | — | — | — | — | ✓ |
| Telehit | Spanish | — | — | — | — | — | ✓ |
| Video Rola | Spanish | — | — | — | — | — | ✓ |
| Ultra Fiesta | Spanish | — | — | — | — | — | ✓ |
| Ultra Familia | Spanish | — | — | — | — | — | ✓ |
| Ultra Kids | Spanish | — | — | — | — | — | ✓ |
| Cartoon Network (Espanol) | Spanish | — | — | — | — | — | ✓ |
| Semillitas | Spanish | — | — | — | — | — | ✓ |
| Sorpresa | Spanish | — | — | — | — | — | ✓ |
| Discovery Familia | Spanish | — | — | — | — | — | ✓ |
| Atres Series | Spanish | — | — | — | — | — | ✓ |
| Baby First TV Espanol | Spanish | — | — | — | — | — | ✓ |
| Baby TV | Spanish | — | — | — | — | — | ✓ |
| Discovery en Español | Spanish | — | — | — | — | — | ✓ |
| Nat Geo Mundo | Spanish | — | — | — | — | — | ✓ |
| History Channel En Español | Spanish | — | — | — | — | — | ✓ |
| HITN | Spanish | — | — | — | — | — | ✓ |
| Mexicanal | Spanish | — | — | — | — | — | ✓ |
| Aplauso | Spanish | — | — | — | — | — | ✓ |
| Ultra Macho | Spanish | — | — | — | — | — | ✓ |
| EWTN Español | Spanish | — | — | — | — | — | ✓ |
| TBN Enlace | Spanish | — | — | — | — | — | ✓ |
| AyM Sports | Spanish | — | — | — | — | — | ✓ |
| Cine Latino US | Spanish | — | — | — | — | — | ✓ |
| Cine Mexicano | Spanish | — | — | — | — | — | ✓ |
| De Pelicula Clasico | Spanish | — | — | — | — | — | ✓ |
| De Película | Spanish | — | — | — | — | — | ✓ |
| ViendoMovies | Spanish | — | — | — | — | — | ✓ |
| Ultra Mex | Spanish | — | — | — | — | — | ✓ |
| Ultra Cine | Spanish | — | — | — | — | — | ✓ |
| Ultra Clasico | Spanish | — | — | — | — | — | ✓ |
| wxlv-tv2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wxlv-tv3 | Local | — | ✓ | ✓ | ✓ | — | — |
| wxii-tv2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wghp2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wfmy-dt2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wcwg-dt2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wcwg-dt3 | Local | — | ✓ | ✓ | ✓ | — | — |
| wmyv2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wmyv3 | Local | — | ✓ | ✓ | ✓ | — | — |
| wunc-dt2 | Local | — | ✓ | ✓ | ✓ | — | — |
| wunc-dt3 | Local | — | ✓ | ✓ | ✓ | — | — |
| wunc-dt4 | Local | — | ✓ | ✓ | ✓ | — | — |
| CTI Zhong Tian Channel | International | — | $ | $ | $ | — | — |
| CCTV-4 America | International | — | — | — | — | — | — |
| Phoenix Info News | International | — | ✓ | ✓ | ✓ | — | — |
| The Filipino Channel | International | — | $ | $ | $ | — | — |
| GMA Pinoy TV | International | — | $ | $ | $ | — | — |
| GMA Life TV | International | — | $ | $ | $ | — | — |
| Zee TV | International | — | $ | $ | $ | — | — |
| SETAsia | Spanish | — | — | — | — | — | — |
| TV Asia | International | — | $ | $ | $ | — | — |
| ATN Max 2 | Entertainment | — | — | — | — | — | — |
| ATN ABP News | International | — | $ | $ | $ | — | — |
| Willow Cricket | International | — | $ | $ | $ | — | — |
| TV5MONDE | International | — | — | — | ✓ | — | — |
| Rai Italia | International | — | — | — | ✓ | — | — |
| RTN Plus | International | — | $ | $ | $ | — | — |
| Channel 1 Russian | International | — | — | — | — | — | — |
| RTVI | International | — | $ | $ | $ | — | — |
| Russian Kino | International | — | $ | $ | $ | — | — |
| ART Cable | Entertainment | — | — | — | — | — | — |
| Music Choice Hit List | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice: Max | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice Dance | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Indie | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Hip-Hop and R&B | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Rap | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Hip-Hop Classics | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Throwback Jams | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice R&B Classics | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: R&B Soul | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice Gospel | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Reggae | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Rock | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Metal | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Alternative | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Adult Alternative | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Rock Hits | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice Classic Rock | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Soft Rock | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Pop Hits | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Party Favorites | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Teen Beats | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Kidz Only! | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice: Toddler Tunes | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Y2K | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice '90s | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice '80s | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice '70s | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Solid Gold Oldies | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Pop & Country | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Today's Country | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Country Hits | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice Classic Country | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Contemporary Christian | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Pop Latino | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice: Musica Urbana | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Mexicana | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Tropicales | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Romances | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice Sounds of the Seasons | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice: Stage & Screen | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Soundscapes | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Smooth Jazz | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Jazz | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Blues | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Singers & Swing | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Classical Masterpieces | Music | ✓ | ✓ | ✓ | ✓ | — | — |
| Music Choice Easy Listening | Music | — | ✓ | ✓ | ✓ | — | — |
| Music Choice Light Classical | Music | — | ✓ | ✓ | ✓ | — | — |

Local TV Select Signature+2

3

Local TV Select Signature+2

4

Local TV Select Signature+2

6

Local TV Select Signature+2

7

Local TV Select Signature+2

9

Local TV Select Signature+2

10

Local TV Select Signature+2

11

Local TV Select Signature+2

12

News TV Select Signature+2

14

Local TV Select Signature+2

15

Sports TV Select Signature+2

16

Sports TV Select Signature+2

17

Entertainment TV Select Signature+2

18

Entertainment TV Select Signature+2

20

Entertainment TV Select Signature+2

21

Entertainment TV Select Signature+2

22

Entertainment TV Select Signature+2

23

Entertainment TV Select Signature+2

24

Documentary TV Select Signature+2

25

News TV Select Signature+2

26

Entertainment TV Select Signature+2

27

Entertainment TV Select Signature+2

28

Documentary TV Select Signature+2

29

News TV Select Signature+2

30

News TV Select Signature+2

31

Kids TV Select Signature+2

32

Entertainment TV Select Signature+2

33

News TV Select Signature+2

34

Entertainment TV Select Signature+2

35

Entertainment TV Select Signature+2

36

Entertainment TV Select Signature+2

37

Sports TV Select Plus+1

38

News TV Select Signature+2

39

News TV Select Signature+2

40

Entertainment TV Select Signature+2

41

Entertainment TV Select Signature+2

43

Lifestyle TV Select Signature+2

44

Entertainment TV Select Signature+2

45

Entertainment TV Select Signature+2

46

Kids TV Select Signature+2

48

Entertainment TV Select Signature+2

49

Entertainment TV Select Signature+2

50

FanDuel Sports Network South-Carolinas

Sports TV Select Plus+1

51

Sports TV Platinum

52

Documentary TV Select Signature+2

53

Kids TV Platinum

54

Lifestyle TV Select Signature+2

55

Spanish Mi Plan Latino

56

Entertainment TV Platinum

57

News TV Select Signature+2

59

Entertainment TV Select Signature+2

60

Entertainment TV Platinum

61

Entertainment TV Select Signature+2

62

Documentary TV Select Signature+2

63

Documentary TV Platinum

64

Lifestyle TV Select Signature+2

65

Eternal Word Television Network

Religious TV Select Signature+2

66

FanDuel Sports Network Southeast

Sports TV Select Plus+1

67

Entertainment TV Select Signature+2

70

Entertainment TV Select Signature+2

71

Entertainment TV Select Signature+2

72

Kids TV Select Signature+2

73

Entertainment TV Select Signature+2

76

Entertainment TV Select Signature+2

78

News TV Platinum

79

Xumo TV Select Signature+2

80

News TV Select Signature+2

81

Shopping TV Select Signature+2

86

Shopping TV Select Signature+2

87

News TV Select Signature+2

98

Entertainment TV Select Signature+2

109

Entertainment TV Select Signature+2

110

Entertainment TV Platinum

119

Entertainment TV Select Signature+2

124

Entertainment TV Platinum

128

Documentary TV Platinum

130

Documentary TV Platinum

131

Entertainment TV Platinum

133

Entertainment TV Platinum

134

Documentary TV Select Signature+2

135

Documentary TV Platinum

136

Entertainment TV Platinum

137

Documentary TV Platinum

140

Documentary TV Platinum

141

Entertainment TV Select Signature+2

144

Spanish Mi Plan Latino

145

Entertainment TV Platinum

151

Shopping TV Select Signature+2

159

Lifestyle TV Select Signature+2

161

Lifestyle TV Select Signature+2

163

Lifestyle TV Select Signature+2

165

Entertainment TV Platinum

169

Entertainment TV Platinum

173

Entertainment TV Select Signature+2

174

Entertainment TV Select Signature+2

175

Shopping TV Select Signature+2

176

Entertainment TV Select Signature+2

177

Entertainment TV Platinum

179

Entertainment TV Platinum

182

Entertainment TV Select Signature+2

184

Entertainment TV Select Signature+2

185

Entertainment TV Platinum

187

Shopping TV Select Signature+2

188

Entertainment TV Select Signature+2

189

Shopping TV Select Signature+2

194

News TV Select Signature+2

207

News TV Select Signature+2

209

News TV Platinum

210

News TV Select Signature+2

216

News TV Select Signature+2

222

News TV Select Signature+2

224

News TV Select Signature+2

226

News TV Select Signature+2

227

Kids TV Platinum

253

Kids TV Platinum

254

Kids TV Select Signature+2

255

Kids TV Select Signature+2

256

Kids TV Platinum

262

Kids TV Platinum

263

Kids TV Platinum

265

Documentary TV Platinum

266

Entertainment TV Select Signature+2

286

Music TV Platinum

287

Music TV Platinum

288

Music TV Platinum

290

Entertainment TV Select Signature+2

291

Music TV Platinum

292

Entertainment TV Platinum

295

Lifestyle TV Platinum

297

Music TV Select Signature+2

299

Sports TV Platinum

302

Sports TV Select Plus+1

306

Sports TV Platinum

307

Sports TV Select Plus+1

308

Sports TV Select Plus+1

309

Sports TV Select Plus+1

310

Sports TV Platinum

311

Sports TV Select Plus+1

312

Sports TV Platinum

315

Sports TV Platinum

316

Sports TV Platinum

330

Sports TV Select Plus+1

331

Sports TV Select Plus+1

339

Sports TV Platinum

370

Stadium College Sports Atlantic

Sports TV Select Plus+1

372

Stadium College Sports Central

Sports TV Select Plus+1

373

Stadium College Sports Pacific

Sports TV Select Plus+1

374

Sports TV Select Signature+2

382

Sports TV Select Signature+2

384

Sports TV Select Plus+1

385

Sports TV Platinum

388

Sports TV Select Plus+1

392

Sports TV Select Signature+2

400

Sports TV Select Signature+2

401

Sports TV Select Plus+1

402

Documentary TV Platinum

403

Sports TV Select Plus+1

406

Sports TV Platinum

408

Sports TV Select Plus+1

413

Sports TV Platinum

416

Sports TV Select Signature+2

417

Sports TV Platinum

419

Spanish TV Select Signature+2

440

Spanish TV Select Signature+2

442

Sports TV Select Signature+2

443

Spanish TV Select Signature+2

444

Entertainment TV Select Signature+2

461

Religious TV Select Signature+2

463

Religious TV Select Signature+2

464

International TV Platinum

465

Sports TV Platinum

468

Religious TV Select Signature+2

469

Religious TV Select Signature+2

470

Religious TV Select Signature+2

472

International TV Select Signature+2

474

Shopping TV Select Signature+2

481

Shopping TV Select Signature+2

484

Entertainment TV Platinum

511

Premium TV Platinum

512

Premium TV Platinum

513

Entertainment

514

Entertainment TV Platinum

515

Premium TV Platinum

516

Entertainment TV Platinum

517

Entertainment TV Platinum

531

Premium $ Add-on

532

Premium TV Platinum

533

Premium

534

Premium

535

Premium TV Platinum

536

Premium TV Platinum

537

Premium $ Add-on

551

Entertainment $ Add-on

552

Premium TV Platinum

553

Entertainment TV Platinum

554

Premium TV Platinum

555

Premium TV Platinum

556

Premium TV Platinum

557

Premium TV Platinum

558

Premium TV Platinum

571

The Movie Channel Extra

Premium TV Platinum

572

Entertainment TV Platinum

581

Entertainment TV Platinum

582

Premium TV Platinum

583

Starz Kids & Family

Kids TV Platinum

584

Entertainment TV Platinum

585

Entertainment TV Platinum

586

Premium $ Add-on

595

Premium TV Platinum

597

Premium TV Platinum

598

Premium TV Platinum

599

Entertainment TV Platinum

602

Entertainment TV Platinum

603

Premium TV Platinum

604

Entertainment TV Platinum

605

Premium TV Platinum

606

Entertainment TV Platinum

607

Premium TV Platinum

608

Premium TV Platinum

620

Premium TV Platinum

621

Premium TV Platinum

622

Entertainment TV Platinum

623

Entertainment TV Select Signature+2

625

Entertainment TV Select Signature+2

627

Entertainment TV Select Signature+2

632

Entertainment $ Add-on

633

Entertainment TV Platinum

640

Spanish Mi Plan Latino

803

Spanish Mi Plan Latino

804

Spanish Mi Plan Latino

806

Spanish Mi Plan Latino

811

Spanish TV Select Signature+2

827

Spanish Mi Plan Latino

834

Spanish Mi Plan Latino

841

Spanish Mi Plan Latino

842

Spanish Mi Plan Latino

843

Spanish Mi Plan Latino

844

Spanish Mi Plan Latino

845

Spanish Mi Plan Latino

847

Spanish Mi Plan Latino

849

Spanish Mi Plan Latino

850

Spanish Mi Plan Latino

855

Spanish Mi Plan Latino

856

Spanish Mi Plan Latino

857

Spanish Mi Plan Latino

860

Spanish Mi Plan Latino

861

Spanish Mi Plan Latino

867

Spanish Mi Plan Latino

870

Spanish Mi Plan Latino

871

Spanish Mi Plan Latino

872

Spanish Mi Plan Latino

874

Spanish Mi Plan Latino

875

Spanish Mi Plan Latino

877

Spanish Mi Plan Latino

878

Spanish Mi Plan Latino

895

Spanish TV Select Signature+2

898

Spanish Mi Plan Latino

899

Spanish Mi Plan Latino

910

Spanish Mi Plan Latino

912

Spanish Mi Plan Latino

913

Spanish Mi Plan Latino

915

Spanish Mi Plan Latino

918

Spanish Mi Plan Latino

919

Spanish Mi Plan Latino

921

Spanish Mi Plan Latino

922

Spanish Mi Plan Latino

923

Spanish Mi Plan Latino

924

Spanish Mi Plan Latino

926

Baby First TV Espanol

Spanish Mi Plan Latino

928

Spanish Mi Plan Latino

929

Spanish Mi Plan Latino

930

Spanish Mi Plan Latino

931

History Channel En Español

Spanish Mi Plan Latino

932

Spanish Mi Plan Latino

933

Spanish Mi Plan Latino

935

Spanish Mi Plan Latino

936

Spanish Mi Plan Latino

937

Spanish Mi Plan Latino

945

Spanish Mi Plan Latino

946

Spanish Mi Plan Latino

962

Spanish Mi Plan Latino

971

Spanish Mi Plan Latino

972

Spanish Mi Plan Latino

979

Spanish Mi Plan Latino

980

Spanish Mi Plan Latino

982

Spanish Mi Plan Latino

983

Spanish Mi Plan Latino

984

Spanish Mi Plan Latino

985

Local TV Select Signature+2

1240

Local TV Select Signature+2

1241

Local TV Select Signature+2

1245

Local TV Select Signature+2

1250

Local TV Select Signature+2

1255

Local TV Select Signature+2

1260

Local TV Select Signature+2

1261

Local TV Select Signature+2

1265

Local TV Select Signature+2

1266

Local TV Select Signature+2

1275

Local TV Select Signature+2

1276

Local TV Select Signature+2

1277

CTI Zhong Tian Channel

International $ Add-on

1400

International

1401

International TV Select Signature+2

1404

International $ Add-on

1450

International $ Add-on

1452

International $ Add-on

1453

International $ Add-on

1533

Spanish

1541

International $ Add-on

1542

Entertainment

1550

International $ Add-on

1551

International $ Add-on

1554

International TV Platinum

1575

International TV Platinum

1581

International $ Add-on

1610

International

1612

International $ Add-on

1613

International $ Add-on

1621

Entertainment

1632

Music Choice Hit List

Music TV Stream+3

1901

Music TV Stream+3

1902

Music TV Select Signature+2

1903

Music TV Select Signature+2

1904

Music Choice Hip-Hop and R&B

Music TV Select Signature+2

1905

Music TV Select Signature+2

1906

Music Choice Hip-Hop Classics

Music TV Select Signature+2

1907

Music Choice Throwback Jams

Music TV Select Signature+2

1908

Music Choice R&B Classics

Music TV Select Signature+2

1909

Music Choice: R&B Soul

Music TV Stream+3

1910

Music TV Select Signature+2

1911

Music TV Select Signature+2

1912

Music TV Select Signature+2

1913

Music TV Select Signature+2

1914

Music TV Select Signature+2

1915

Music Choice Adult Alternative

Music TV Select Signature+2

1916

Music Choice: Rock Hits

Music TV Stream+3

1917

Music Choice Classic Rock

Music TV Select Signature+2

1918

Music Choice Soft Rock

Music TV Select Signature+2

1919

Music Choice Pop Hits

Music TV Select Signature+2

1921

Music Choice: Party Favorites

Music TV Select Signature+2

1922

Music Choice: Teen Beats

Music TV Select Signature+2

1923

Music Choice: Kidz Only!

Music TV Stream+3

1924

Music Choice: Toddler Tunes

Music TV Select Signature+2

1925

Music TV Select Signature+2

1926

Music TV Select Signature+2

1927

Music TV Select Signature+2

1928

Music TV Select Signature+2

1929

Music Choice Solid Gold Oldies

Music TV Select Signature+2

1930

Music Choice Pop & Country

Music TV Select Signature+2

1931

Music Choice Today's Country

Music TV Select Signature+2

1932

Music Choice: Country Hits

Music TV Stream+3

1933

Music Choice Classic Country

Music TV Select Signature+2

1934

Music Choice Contemporary Christian

Music TV Select Signature+2

1935

Music Choice: Pop Latino

Music TV Stream+3

1936

Music Choice: Musica Urbana

Music TV Select Signature+2

1937

Music TV Select Signature+2

1938

Music TV Select Signature+2

1939

Music TV Stream+3

1940

Music Choice Sounds of the Seasons

Music TV Select Signature+2

1941

Music Choice: Stage & Screen

Music TV Select Signature+2

1942

Music TV Select Signature+2

1943

Music Choice Smooth Jazz

Music TV Select Signature+2

1944

Music TV Select Signature+2

1945

Music TV Select Signature+2

1946

Music Choice Singers & Swing

Music TV Select Signature+2

1947

Music Choice Classical Masterpieces

Music TV Stream+3

1948

Music Choice Easy Listening

Music TV Select Signature+2

1949

Music Choice Light Classical

Music TV Select Signature+2

1950

No channels match your search.

Print this lineup

Jump to: Packages Documentary Entertainment International Kids Lifestyle Local Music News Premium Religious Shopping Spanish Sports Xumo

## Spectrum Packages Overview

### Spectrum TV Stream (9 channels)

- Music Choice Hit List - Ch 1901
- Music Choice: Max - Ch 1902
- Music Choice: R&B Soul - Ch 1910
- Music Choice: Rock Hits - Ch 1917
- Music Choice: Kidz Only! - Ch 1924
- Music Choice: Country Hits - Ch 1933
- Music Choice: Pop Latino - Ch 1936
- Music Choice Romances - Ch 1940
- Music Choice Classical Masterpieces - Ch 1948

### Spectrum TV Select Signature (175 channels)

- wcwg - Ch 3
- WUNC (PBS) - Ch 4
- wlxi - Ch 6
- wxlv - Ch 7
- wfmy - Ch 9
- wghp - Ch 10
- wxii - Ch 11
- wgpx - Ch 12
- Spectrum News 1 - Ch 14
- wmyv - Ch 15
- ESPN2 - Ch 16
- ESPN - Ch 17
- Paramount Network - Ch 18
- Freeform - Ch 20
- TNT - Ch 21
- BET - Ch 22
- TBS - Ch 23
- AMC - Ch 24
- Discovery - Ch 25
- Weather Channel - Ch 26
- ...and 155 more

### Spectrum TV Select Plus (193 channels)

- wcwg - Ch 3
- WUNC (PBS) - Ch 4
- wlxi - Ch 6
- wxlv - Ch 7
- wfmy - Ch 9
- wghp - Ch 10
- wxii - Ch 11
- wgpx - Ch 12
- Spectrum News 1 - Ch 14
- wmyv - Ch 15
- ESPN2 - Ch 16
- ESPN - Ch 17
- Paramount Network - Ch 18
- Freeform - Ch 20
- TNT - Ch 21
- BET - Ch 22
- TBS - Ch 23
- AMC - Ch 24
- Discovery - Ch 25
- Weather Channel - Ch 26
- ...and 173 more

### Spectrum TV Platinum (288 channels)

- wcwg - Ch 3
- WUNC (PBS) - Ch 4
- wlxi - Ch 6
- wxlv - Ch 7
- wfmy - Ch 9
- wghp - Ch 10
- wxii - Ch 11
- wgpx - Ch 12
- Spectrum News 1 - Ch 14
- wmyv - Ch 15
- ESPN2 - Ch 16
- ESPN - Ch 17
- Paramount Network - Ch 18
- Freeform - Ch 20
- TNT - Ch 21
- BET - Ch 22
- TBS - Ch 23
- AMC - Ch 24
- Discovery - Ch 25
- Weather Channel - Ch 26
- ...and 268 more

### Spectrum TV Stream Latino (0 channels)

### Spectrum Mi Plan Latino (61 channels)

- Univision - Ch 56
- El Rey Network - Ch 145
- Telemundo - Ch 803
- UniMás - Ch 804
- Azteca America - Ch 806
- Estrella TV - Ch 811
- CNN en Español - Ch 834
- Mexico 22 - Ch 841
- Estudio 5 - Ch 842
- Multimedios USA - Ch 843
- Canal Once - Ch 844
- Teleformula - Ch 845
- FOROtv - Ch 847
- Ultra Docu - Ch 849
- Canal Sur - Ch 850
- TV Chile - Ch 855
- CARACOL INTERNATIONAL - Ch 856
- Nuestra Tele Internacional - Ch 857
- CentroAméricaTV - Ch 860
- Tele El Salvador - Ch 861
- ...and 41 more

### All Spectrum Documentary Channels (13)

- Discovery - Ch 25
- National Geographic - Ch 29
- History - Ch 53
- Animal Planet - Ch 63
- Discovery Life - Ch 64
- Nat Geo Wild - Ch 130
- Smithsonian Channel - Ch 131
- Destination America - Ch 135
- Science Channel - Ch 136
- American Heroes Channel - Ch 140
- Military History Channel - Ch 141
- Discovery Family - Ch 266
- Motor Trend - Ch 403

### All Spectrum Entertainment Channels (75)

- Paramount Network - Ch 18
- Freeform - Ch 20
- TNT - Ch 21
- BET - Ch 22
- TBS - Ch 23
- AMC - Ch 24
- MTV - Ch 27
- A&E - Ch 28
- Lifetime - Ch 33
- CMT - Ch 35
- VH1 - Ch 36
- Comedy Central - Ch 37
- truTV - Ch 41
- Bravo - Ch 43
- Syfy - Ch 45
- E! - Ch 46
- Hallmark Channel - Ch 49
- USA Network - Ch 50
- TCM - Ch 57
- FX - Ch 60
- MTV Classic - Ch 61
- TV Land - Ch 62
- Oxygen - Ch 70
- WE tv - Ch 71
- Lifetime Movie Network - Ch 72
- Investigation Discovery - Ch 76
- Hallmark Mystery - Ch 78
- FXX - Ch 109
- BBC America - Ch 110
- MTV2 - Ch 119
- UP TV - Ch 124
- REELZ - Ch 128
- VICE - Ch 133
- FYI - Ch 134
- Crime + Investigation - Ch 137
- Fusion - Ch 144
- Heroes & Icons - Ch 151
- Fuse - Ch 169
- OWN - Ch 173
- Lifetime Real Women - Ch 174
- Pop - Ch 175
- Game Show Network - Ch 177
- Logo - Ch 179
- BET Her - Ch 182
- TV One - Ch 184
- ASPiRE - Ch 185
- Ovation - Ch 187
- Cleo TV - Ch 189
- MTV Live - Ch 286
- Revolt - Ch 291
- GAC Family - Ch 295
- INSP - Ch 461
- HBO - Ch 511
- HBO Family - Ch 514
- HBO Comedy - Ch 515
- HBO Latino - Ch 517
- Cinemax - Ch 531
- Showtime 2 - Ch 552
- Showtime Extreme - Ch 554
- Starz - Ch 581
- Starz Edge - Ch 582
- Starz Cinema - Ch 585
- Starz Comedy - Ch 586
- Starz Encore - Ch 602
- Starz Encore Action - Ch 603
- Starz Encore Classic - Ch 605
- Starz Encore Westerns - Ch 607
- Flix - Ch 623
- SundanceTV - Ch 625
- IFC - Ch 627
- FX Movie Channel - Ch 632
- MGM HD - Ch 633
- HDNet Movies - Ch 640
- ATN Max 2 - Ch 1550
- ART Cable - Ch 1632

### All Spectrum International Channels (18)

- BYU-TV - Ch 465
- Impact TV Network - Ch 474
- CTI Zhong Tian Channel - Ch 1400
- CCTV-4 America - Ch 1401
- Phoenix Info News - Ch 1404
- The Filipino Channel - Ch 1450
- GMA Pinoy TV - Ch 1452
- GMA Life TV - Ch 1453
- Zee TV - Ch 1533
- TV Asia - Ch 1542
- ATN ABP News - Ch 1551
- Willow Cricket - Ch 1554
- TV5MONDE - Ch 1575
- Rai Italia - Ch 1581
- RTN Plus - Ch 1610
- Channel 1 Russian - Ch 1612
- RTVI - Ch 1613
- Russian Kino - Ch 1621

### All Spectrum Kids Channels (12)

- Nickelodeon - Ch 32
- Cartoon Network - Ch 48
- Nick Jr - Ch 54
- Disney Channel - Ch 73
- Boomerang - Ch 253
- Disney Junior - Ch 254
- Universal Kids - Ch 255
- Baby First TV - Ch 256
- Nicktoons - Ch 262
- TeenNick - Ch 263
- Disney XD - Ch 265
- Starz Kids & Family - Ch 584

### All Spectrum Lifestyle Channels (7)

- TLC - Ch 44
- HGTV - Ch 55
- Food Network - Ch 65
- Magnolia Network - Ch 161
- Cooking Channel - Ch 163
- Travel Channel - Ch 165
- RFD TV - Ch 297

### All Spectrum Local Channels (21)

- wcwg - Ch 3
- WUNC (PBS) - Ch 4
- wlxi - Ch 6
- wxlv - Ch 7
- wfmy - Ch 9
- wghp - Ch 10
- wxii - Ch 11
- wgpx - Ch 12
- wmyv - Ch 15
- wxlv-tv2 - Ch 1240
- wxlv-tv3 - Ch 1241
- wxii-tv2 - Ch 1245
- wghp2 - Ch 1250
- wfmy-dt2 - Ch 1255
- wcwg-dt2 - Ch 1260
- wcwg-dt3 - Ch 1261
- wmyv2 - Ch 1265
- wmyv3 - Ch 1266
- wunc-dt2 - Ch 1275
- wunc-dt3 - Ch 1276
- wunc-dt4 - Ch 1277

### All Spectrum Music Channels (54)

- BET Jams - Ch 287
- Nick Music - Ch 288
- BET Soul - Ch 290
- FM - Ch 292
- AXS TV - Ch 299
- Music Choice Hit List - Ch 1901
- Music Choice: Max - Ch 1902
- Music Choice Dance - Ch 1903
- Music Choice: Indie - Ch 1904
- Music Choice Hip-Hop and R&B - Ch 1905
- Music Choice: Rap - Ch 1906
- Music Choice Hip-Hop Classics - Ch 1907
- Music Choice Throwback Jams - Ch 1908
- Music Choice R&B Classics - Ch 1909
- Music Choice: R&B Soul - Ch 1910
- Music Choice Gospel - Ch 1911
- Music Choice: Reggae - Ch 1912
- Music Choice Rock - Ch 1913
- Music Choice: Metal - Ch 1914
- Music Choice: Alternative - Ch 1915
- Music Choice Adult Alternative - Ch 1916
- Music Choice: Rock Hits - Ch 1917
- Music Choice Classic Rock - Ch 1918
- Music Choice Soft Rock - Ch 1919
- Music Choice Pop Hits - Ch 1921
- Music Choice: Party Favorites - Ch 1922
- Music Choice: Teen Beats - Ch 1923
- Music Choice: Kidz Only! - Ch 1924
- Music Choice: Toddler Tunes - Ch 1925
- Music Choice: Y2K - Ch 1926
- Music Choice '90s - Ch 1927
- Music Choice '80s - Ch 1928
- Music Choice '70s - Ch 1929
- Music Choice Solid Gold Oldies - Ch 1930
- Music Choice Pop & Country - Ch 1931
- Music Choice Today's Country - Ch 1932
- Music Choice: Country Hits - Ch 1933
- Music Choice Classic Country - Ch 1934
- Music Choice Contemporary Christian - Ch 1935
- Music Choice: Pop Latino - Ch 1936
- Music Choice: Musica Urbana - Ch 1937
- Music Choice: Mexicana - Ch 1938
- Music Choice Tropicales - Ch 1939
- Music Choice Romances - Ch 1940
- Music Choice Sounds of the Seasons - Ch 1941
- Music Choice: Stage & Screen - Ch 1942
- Music Choice Soundscapes - Ch 1943
- Music Choice Smooth Jazz - Ch 1944
- Music Choice Jazz - Ch 1945
- Music Choice Blues - Ch 1946
- Music Choice Singers & Swing - Ch 1947
- Music Choice Classical Masterpieces - Ch 1948
- Music Choice Easy Listening - Ch 1949
- Music Choice Light Classical - Ch 1950

### All Spectrum News Channels (19)

- Spectrum News 1 - Ch 14
- Weather Channel - Ch 26
- CNBC - Ch 30
- HLN - Ch 31
- CNN - Ch 34
- C-SPAN - Ch 39
- Fox News - Ch 40
- MS NOW - Ch 59
- CNBC World - Ch 79
- Fox Business - Ch 81
- NewsNation - Ch 98
- Bloomberg Business Television - Ch 207
- BBC News - Ch 209
- i24 News - Ch 210
- CNN International - Ch 216
- Newsmax - Ch 222
- Scripps News - Ch 224
- C-SPAN 2 - Ch 226
- C-SPAN 3 - Ch 227

### All Spectrum Premium Channels (28)

- HBO Hits - Ch 512
- HBO Drama - Ch 513
- HBO Movies - Ch 516
- MoreMAX - Ch 532
- Cinemax Action - Ch 533
- ThrillerMAX - Ch 534
- OuterMAX - Ch 535
- Cinemax Spanish - Ch 536
- Cinemax Classics - Ch 537
- Paramount+ with Showtime - Ch 551
- SHO x BET - Ch 553
- Showtime Showcase - Ch 555
- Showtime Next - Ch 556
- Showtime Women - Ch 557
- Showtime Familyzone - Ch 558
- The Movie Channel - Ch 571
- The Movie Channel Extra - Ch 572
- Starz in Black - Ch 583
- MGM+ East - Ch 595
- MGM+ Hits - Ch 597
- MGM+ Marquee - Ch 598
- MGM+ Drive-In - Ch 599
- Starz Encore Black - Ch 604
- Starz Encore Suspense - Ch 606
- Starz Encore Family - Ch 608
- MoviePlex - Ch 620
- IndiePlex - Ch 621
- RetroPlex - Ch 622

### All Spectrum Religious Channels (6)

- Eternal Word Television Network - Ch 66
- Daystar Television Network - Ch 463
- Trinity Broadcasting Network - Ch 464
- Jewish Life Television - Ch 469
- SonLife Broadcasting Network - Ch 470
- TBN Inspire - Ch 472

### All Spectrum Shopping Channels (8)

- Gem Shopping Network - Ch 86
- Shop LC - Ch 87
- QVC - Ch 159
- HSN - Ch 176
- Jewelry Television - Ch 188
- ShopHQ - Ch 194
- QVC2 - Ch 481
- HSN2 - Ch 484

### All Spectrum Spanish Channels (67)

- Univision - Ch 56
- El Rey Network - Ch 145
- ESPN Deportes - Ch 440
- Fox Deportes - Ch 442
- TUDN - Ch 444
- Telemundo - Ch 803
- UniMás - Ch 804
- Azteca America - Ch 806
- Estrella TV - Ch 811
- Galavisión - Ch 827
- CNN en Español - Ch 834
- Mexico 22 - Ch 841
- Estudio 5 - Ch 842
- Multimedios USA - Ch 843
- Canal Once - Ch 844
- Teleformula - Ch 845
- FOROtv - Ch 847
- Ultra Docu - Ch 849
- Canal Sur - Ch 850
- TV Chile - Ch 855
- CARACOL INTERNATIONAL - Ch 856
- Nuestra Tele Internacional - Ch 857
- CentroAméricaTV - Ch 860
- Tele El Salvador - Ch 861
- TVV - Ch 867
- Super Canal - Ch 870
- Telemicro Canal 5 - Ch 871
- Televisión Dominicana - Ch 872
- WAPA America - Ch 874
- Cuba Play - Ch 875
- Antena 3 Internacional - Ch 877
- TVE Internacional - Ch 878
- Univision Telenovelas - Ch 895
- UNIVERSO - Ch 898
- MTV Tr3s - Ch 899
- Bandamax - Ch 910
- Telehit - Ch 912
- Video Rola - Ch 913
- Ultra Fiesta - Ch 915
- Ultra Familia - Ch 918
- Ultra Kids - Ch 919
- Cartoon Network (Espanol) - Ch 921
- Semillitas - Ch 922
- Sorpresa - Ch 923
- Discovery Familia - Ch 924
- Atres Series - Ch 926
- Baby First TV Espanol - Ch 928
- Baby TV - Ch 929
- Discovery en Español - Ch 930
- Nat Geo Mundo - Ch 931
- History Channel En Español - Ch 932
- HITN - Ch 933
- Mexicanal - Ch 935
- Aplauso - Ch 936
- Ultra Macho - Ch 937
- EWTN Español - Ch 945
- TBN Enlace - Ch 946
- AyM Sports - Ch 962
- Cine Latino US - Ch 971
- Cine Mexicano - Ch 972
- De Pelicula Clasico - Ch 979
- De Película - Ch 980
- ViendoMovies - Ch 982
- Ultra Mex - Ch 983
- Ultra Cine - Ch 984
- Ultra Clasico - Ch 985
- SETAsia - Ch 1541

### All Spectrum Sports Channels (39)

- ESPN2 - Ch 16
- ESPN - Ch 17
- NBC Sports - Ch 38
- FanDuel Sports Network South-Carolinas - Ch 51
- Golf Channel - Ch 52
- FanDuel Sports Network Southeast - Ch 67
- ESPNews - Ch 302
- MLB Network - Ch 306
- MLB Strike Zone - Ch 307
- NBA TV - Ch 308
- BravesVision - Ch 309
- NFL Network - Ch 310
- NFL RedZone - Ch 311
- NHL Network - Ch 312
- CBS Sports Network - Ch 315
- Olympic Channel - Ch 316
- Spectrum SportsNet - Ch 330
- Spectrum SportsNet LA - Ch 331
- YES Network - Ch 339
- ESPNU - Ch 370
- Stadium College Sports Atlantic - Ch 372
- Stadium College Sports Central - Ch 373
- Stadium College Sports Pacific - Ch 374
- Big Ten Network - Ch 382
- SEC Network - Ch 384
- SEC Network Alternate - Ch 385
- BTN Extra 1 - Ch 388
- ESPN College Extra - Ch 392
- Fox Sports 1 - Ch 400
- FOX Sports 2 - Ch 401
- RACER Network - Ch 402
- Tennis Channel - Ch 406
- Outdoor Channel - Ch 408
- FanDuel TV - Ch 413
- GOL TV - Ch 416
- beIN Sports - Ch 417
- Fox Soccer Plus - Ch 419
- beIN Sports Spanish - Ch 443
- Cowboy Channel - Ch 468

### All Spectrum Xumo Channels (1)

- DISCOVERY TURBO TV - Ch 80