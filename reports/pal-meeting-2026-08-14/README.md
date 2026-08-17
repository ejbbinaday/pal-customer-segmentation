# PAL meeting pack — Friday 14 August 2026

**Session:** EDA & initial results · **30 minutes** (19 min talk · 11 min Q&A)
**Audience:** PAL stakeholders + mentors — mixed technical and commercial

> **Everything you need for tomorrow is in this folder.** It is a **snapshot** taken 13 Aug 2026 —
> self-contained and safe to zip and send. The repo remains the source of truth; if anything changes
> before the meeting, re-copy from `docs/` and `reports/study_guide/`.

---

## Open these two, in this order

| Order | File | Why |
|---|---|---|
| **1** | **`01-SLIDE-GUIDE.html`** | **Your talk track — open this in a browser.** Every slide as a card with its chart inline, the script to say, and a **live timing rail** that tells you which slide you should be on. Prints cleanly too |
| 1b | `01-SLIDE-GUIDE.md` | Same content as markdown, if you'd rather search it in an editor |
| **2** | `02-full-study-guide.html` | **Keep open in a second window.** Every number in the deck, with the detail behind it. Double-click to open in a browser — figures are embedded, nothing external loads |

`02-full-study-guide.md` is the same content as markdown, if you prefer to search it in an editor.

---

## What's here

```
01-SLIDE-GUIDE.html            ← start here: talk track + charts + live timer
01-SLIDE-GUIDE.md              ← same, as markdown
02-full-study-guide.html       ← drill-down reference (open in browser)
02-full-study-guide.md         ← same, as markdown

figures/                       ← drop into slides in number order
  slide-06-timing-and-value.png
  slide-07-route-region.png
  slide-08-no-elbow-THE-PIVOT.png     ⭐ the one that matters
  slide-09-separation-ceiling.png
  slide-11-segment-results.png
  slide-12-construct-validity.png
  backup/                      ← loaded but hidden; pull up only if asked
    B1-what-a-continuum-looks-like.png
    B2-detection-floor.png
    B3-temporal-stability.png
    B4-lca-sub-types.png
    B5-cross-method-agreement.png

reference/                     ← the exact numbers, for Q&A
  segment-counts.md            segment sizes and revenue per booking
  rule-confidence.md           how settled each label is
  full-eda-report.md           the complete EDA write-up
  data-dictionary.md           field definitions and the fare ladder
  powerbi-export-summary.md    what shipped to Power BI, and its caveats
```

**The figures are numbered by slide.** Build the deck by dropping `figures/*.png` in order — 6, 7, 8, 9,
11, 12 — and the narrative assembles itself.

---

## The running order, at a glance

| Slides | Beat | Minutes |
|---|---|---|
| 1–2 | Setup — what we were given | 1.5 |
| 3–5 | **What the data actually looks like** (the three facts, quality, the modelling row) | 4.0 |
| 6–7 | Distributions — timing, value, geography, channel | 3.0 |
| **8–9** | ⭐ **The pivot — no natural clusters, confirmed four ways** | **4.0** |
| 10–11 | **What we built instead, and the first results** | 3.5 |
| 12–13 | Does it hold up · gaps and asks | 3.0 |
| — | Q&A | 11.0 |

**Running late?** Cut slide 7, then 4, then 9. **Never cut 8 or 11.**
**Cut to 10 minutes?** Slides 1, 3, 8, 11, 13 still tell the whole story.

---

## Three numbers to know cold

**38.1M coupons → 22.9M bookings → 9 named segments + 9.6% Unassigned.**

---

## Five things not to claim

1. ❌ Any **accuracy or recall figure** — there is no honest one yet, and that is by design
2. ❌ That the **segment names are validated** — say *"behaviourally validated; names not externally confirmed"*
3. ❌ That the **sub-types are actionable** — they are provisional
4. ❌ **Absolute revenue in a stated currency** — the unit is undocumented; quote ratios, not amounts
5. ❌ **"Ten segments"** — it is **nine named plus Unassigned**; Digital Nomad is not implemented

---

## The four asks, if the meeting goes well

1. **~1,000 hand-labelled bookings** from a commercial expert — the critical path to a real accuracy number
2. **A definition for the 9.6% Unassigned** — 2.19M bookings we deliberately left blank
3. **Mabuhay tier on the booking record** — without it the loyalty segment is invisible
4. **Repeated dated extracts** — the only route to genuine booking-curve analysis

---

*Snapshot taken 13 August 2026 from `docs/` and `reports/study_guide/`. Source of truth is the repo.*
