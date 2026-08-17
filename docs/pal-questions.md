# Open questions for PAL

**Compiled:** 17 August 2026 · **From:** the RM-Domestic constraint workbook and what we found testing it
**Sources:** `docs/sme-constraints-intake.md` · `docs/waterfall-v2-design.md` · `data/constraints/*.csv`

**Also exported as `docs/pal-questions.csv`** — same 24 rows, one per question, with blank
`answer` / `answered_by` / `answered_date` columns so it round-trips like the constraint workbook did.
Opens in Excel directly (UTF-8 BOM). ⚠️ The two files are maintained by hand — **update both**.

24 items in four groups. **Group A blocks work that is otherwise ready to build.** Everything else
improves quality or closes a loop. Each row carries our recommendation, so most can be answered "agreed".

---

## A. Decisions that block us — 7 items

We cannot ship the taxonomy change without these. A1–A4 are one meeting.

| # | Question | Who | Why it matters | Our recommendation |
|---|---|---|---|---|
| **A1** | Four new segments have no **misclassification cost**. What does it cost PAL to wrongly label a MICE / Ultra Wealthy Leisure / Intl. Student / Outbound International Leisure booking? | Commercial + RM | The model is scored by an asymmetric cost matrix. Without weights the scoring stage cannot run at all. **This is a business input we must not invent.** | Reuse the nearest existing weight as a placeholder only if you want to see the model run — but the real numbers should come from you |
| **A2** | **Budget/Adventure will hold 49.9% of all bookings.** Accept, or split it? | Commercial | Half the customer base in one segment is not a targeting unit | **Accept for now.** We ship fare tier as a *reporting band* (Budget 7.3M / Mid 3.5M) which gives you the split without inventing a customer type. We tested a real split and it failed — the "mid-tier traveller" turned out to be mostly people booking late, which pricing already explains |
| **A3** | **Premium Bleisure shrinks 29%** (481,666 → 343,100) because Ultra Wealthy Leisure takes its top end. Accept? | Commercial | You have persona slides for Premium Bleisure. This is correct behaviour, not a bug — but it changes a published number | Accept. It is the direct consequence of approving Ultra Wealthy Leisure |
| **A4** | **21.8% of bookings change segment.** When should this land? | Commercial + BI | Every published figure, persona card, scorecard and drift baseline goes stale the same day | Land it *before* the next reporting cycle, not mid-cycle, and re-run validation before publishing any new segment size |
| **A5** | A Filipino **family of four flying to Japan in economy** — is that `Family` or `Outbound International Leisure`? | RM Domestic | Decides 190,777 bookings. Family is either 350,527 or 159,821 | Keep it in `Family` (what we drafted). But it is genuinely ambiguous and yours to call |
| **A6** | Does **`Family` have any signal beyond "they booked as a group"**? | RM Domestic | Today it is *only* a group booking that no other rule claimed — 100% of it. We cannot tell a family from three colleagues or a barkada | If there is nothing else, rename it **"Group Travel"**, which is all we actually measure. Naming it Family implies knowledge we do not have |
| **A7** | When a group books 45+ days ahead for a 3–7 night trip to a convention hub — **MICE or Family**? | RM Domestic | 25,064 bookings sit in both definitions | **MICE first.** It has a real definition; Family is a residual |

## B. Data we are asking for — 5 items

Each unlocks something specific. B1 and B2 are the highest value.

| # | Field | What it unlocks | Why we cannot proceed without it |
|---|---|---|---|
| **B1** | **`FarebasisCode`** (already in PAL's own data dictionary) | Closes the one open confound on our best finding | Manila–Gulf traffic shows a real one-month travel rhythm, which RM Domestic attributes to employer-mandated leave. But if Gulf economy fares carry a **one-month maximum-stay condition**, the fare rule produces the identical pattern. We cannot tell these apart without the fare basis, and the difference decides whether the rule generalises |
| **B2** | **`Isupgrade`** · **`IsTourCode`** · **`IsFrequentFlyer`** | Replacement independent checks | To measure whether our segments are right, we need facts the rules never used. We are down to **two** such fields, and the new rules spend one. All three of these are in your dictionary, and **no rule in the workbook touches any of them** — so they are clean |
| **B3** | **PNR party size** (passengers per booking) | One SME rule, and the whole Family question | The extract's passenger count is always 1 per sector, so "MICE cannot be business class if party > 10" is unimplementable. RM Domestic noted this themselves. **Can the group indicator plus a group fare class stand in?** |
| **B4** | **Loyalty tier / Mabuhay status** | The Mabuhay Loyalist segment | It is currently **0.03% of bookings** — not because the segment is small, but because we can only see award redemptions. The segment is real; our ability to see it is not. Standing request |
| **B5** | Confirmation of the **revenue currency** | Every revenue figure we quote | Our own check says the extract is *plausibly* single-currency (7.3× spread across 26 issuing countries) but we have never had it confirmed |

## C. Changes we made to your rules — please confirm — 8 items

We did not transcribe the workbook literally. Each change below is recorded in
`data/constraints/*.csv` against the original row, with the reasoning. **We need RM Domestic to confirm we
did not misrepresent them.**

| # | Their rule | What we changed | Why |
|---|---|---|---|
| **C1** | Row 21 — OFW, `[Middle East / East Asia Hubs]` | **Narrowed to the Gulf only** (Dubai, Riyadh, Dammam, Doha) | Hong Kong and Taipei show the pattern on only 1.9% of their trips vs 19.1% for the Gulf. Including them makes the rule *worse than a coin flip* |
| **C2** | All route rules written as `MNLDXB`, `MNLRUH`, … | **Made direction-agnostic** where the rule is about workers coming *home* | Gulf round trips start in the Gulf **260,216** times vs Manila's **26,195**. A worker based in Riyadh flying home is `RUHMNL`. Read literally, your best rule matched 5,166 bookings instead of 118,841 — **23× fewer** |
| **C3** | Row 21 — "~30 **or ~45** days" | **Kept 28–45 as stated, but the 45-day half is not supported** | The 30-night pattern is strong and Gulf-specific. There is no excess at 45 |
| **C4** | Row 50 — Intl. Student, academic months | **Dropped the month clause**, kept the 90–150 night stay | We are protecting departure month as an independent check on our own work. The stay length was the primary signal and works alone. Rule now fires on 51,223 instead of 17,354 |
| **C5** | Rows 34 and 38 — `cannot be` at *moderate* confidence | **Demoted to strong tendencies**, not vetoes | Row 34 would have vetoed **63% of all bookings** and row 38 **33% of round trips**, on moderate confidence. Too large a lever for anything but *certain* |
| **C6** | Row 9 — Family **must be** a group booking | **Demoted to a tendency** | "Must be" means *no matter what else is true* — it would have outranked Corporate, Pilgrimage and OFW, pulling 162,556 bookings into Family and growing it 44%. Your own later rules claim those same bookings for five other segments |
| **C7** | Row 20 — sea crew connecting to another airline | **Transcribed partially** | The extract's operating-carrier field is constant 'PR' throughout, so we cannot verify the other-airline leg. The rule fires wider than you intended |
| **C8** | Five rules about **departure month** (peak season, Q4–Q1 peak, summer spike, Lent/Easter, off-peak) | **Set aside, not deleted** | Same reason as C4 — we are keeping departure month as an independent check. They are in the file marked `withdrawn` so you can see exactly what we held back and argue with it |

## D. Still unanswered from the original ask — 4 items

| # | Item | Status |
|---|---|---|
| **D1** | **The Power BI wish list** — which fields and views does each department want? | Sheet came back with **headers only**. That was half the ask |
| **D2** | **Digital Nomad** — how do we identify one in anonymous booking data? | Untouched. This is the one segment in the original requirement we have **never implemented**, and our own placeholder still reads "pending SME input" |
| **D3** | **Pilgrimage** — exact religious-hub airport codes and seasonal date ranges | Untouched. Partly answered by measurement: the Catholic hubs (Rome, Tel Aviv, Paris, Lisbon) carry only 28,224 trip endpoints against 70,650 for Jeddah/Medina, so **all four of your pilgrimage rules fire on under 700 bookings each.** Worth knowing before you invest more in them |
| **D4** | **Four segments got no input at all** — Mabuhay Loyalist, Family, Budget/Adventure, Digital Nomad | Twelve rules came back for three segments we did not model; four segments we *do* model got nothing |

### And one observation, not a question

**The ask was for domestic constraints. The answer is mostly international.** Of the 39 rules: **1** names
domestic routes, **14** name international corridors or international-only concepts, and 24 are
route-agnostic. Three of the new segments are inherently international.

The rules are usable — but the domestic-specific ask is substantially unanswered, and the two fields
domestic rules most need are weakest there: **`Age` is populated on only 0.98% of domestic bookings**
(it is captured for international operations), and **stay length does not exist for one-way trips**, which
is most domestic point-to-point flying. A second domestic-focused round would be worth more than a
follow-up on the international rules.

---

## Suggested sequencing

1. **A1–A4 in one meeting** with Commercial — these gate the build, and A1 (cost weights) gates the
   scoring stage entirely.
2. **A5–A7 to RM Domestic** with C1–C8 — same conversation, since both are about their rules.
3. **B1–B3 as a single data request** — B1 and B2 are small asks with disproportionate value.
4. **D1–D4 as a second round**, ideally with a domestic-focused constraint sheet.
