# Rule-confidence diagnostics — the deterministic waterfall

Full population: **22,911,450** bookings, no sampling. Source: `data/interim/pal_features_booking.parquet`.

> **These measure how *determined* a label is by the rule set — not whether it is right.** A booking can be 100% uncontested and still sit in the wrong segment if the rule itself is wrong. External validity is Stages V1-V4 and, ultimately, SME ground truth.

## 1. Rule competition — how contested is each label?

How many of the 10 branch predicates each booking satisfies. **1 = uncontested** · **2 = the priority order broke a tie** · **3+ = the label is a priority artefact.**

| proxy_segment    |   bookings |   pct_uncontested |   pct_2_rules |   pct_3plus |   mean_rules |
|:-----------------|-----------:|------------------:|--------------:|------------:|-------------:|
| Budget/Adventure |    9037176 |             100   |           0   |         0   |         1    |
| Premium Bleisure |     481666 |              95.5 |           4.5 |         0   |         1.05 |
| Balikbayan/VFR   |    2911290 |              89.2 |          10.3 |         0.5 |         1.11 |
| Mabuhay Loyalist |       6453 |              63.6 |          21   |        15.4 |         1.52 |
| OFW/Migrant      |    3919216 |              61.5 |          31.3 |         7.1 |         1.46 |
| Family           |     370647 |              45.8 |          47.2 |         7   |         1.61 |
| Pilgrimage       |      43617 |              35.2 |          56.1 |         8.7 |         1.74 |
| Last-Minute      |    2945686 |              15.9 |          84.1 |         0   |         1.84 |
| Corporate        |    1001638 |               6.4 |          68   |        25.6 |         2.2  |
| Unassigned       |    2194061 |               0   |           0   |         0   |         0    |

**Overall**

|   pct_exactly_1 |   pct_2_or_more |   pct_none |
|----------------:|----------------:|-----------:|
|            66.5 |              24 |        9.6 |

`Unassigned` matches zero rules by definition — it is a coverage gap, not a tie.


> Read `Budget/Adventure` at 100% uncontested with care: it is the terminal catch-all, so 'nothing else claimed it' is close to true by construction.


## 2. Runner-up — what the booking would be called one priority step lower

Top two alternatives per segment. A very high share means the two segments overlap heavily and the boundary between them is our priority order, not the data.

| proxy_segment    | runner_up        |   bookings |   pct_of_segment |
|:-----------------|:-----------------|-----------:|-----------------:|
| Last-Minute      | Budget/Adventure |    2476607 |             84.1 |
| Family           | Budget/Adventure |     139130 |             37.5 |
| Corporate        | Budget/Adventure |     280582 |             28   |
| Corporate        | OFW/Migrant      |     197696 |             19.7 |
| OFW/Migrant      | Last-Minute      |     703013 |             17.9 |
| Family           | Last-Minute      |      61919 |             16.7 |
| Pilgrimage       | Budget/Adventure |       7217 |             16.5 |
| Pilgrimage       | OFW/Migrant      |       6739 |             15.5 |
| Mabuhay Loyalist | Family           |        793 |             12.3 |
| Mabuhay Loyalist | Last-Minute      |        771 |             11.9 |
| OFW/Migrant      | Budget/Adventure |     261919 |              6.7 |
| Balikbayan/VFR   | Last-Minute      |     181319 |              6.2 |
| Premium Bleisure | Last-Minute      |      19151 |              4   |
| Balikbayan/VFR   | Family           |     109966 |              3.8 |
| Premium Bleisure | Family           |       2433 |              0.5 |


## 3. Boundary fragility — label flips when one threshold moves a notch

Separates rules resting on an **identity** (channel, destination) from rules resting on an **arbitrary number** (lead ≤ 3 days, tier ≤ 4).

| scenario                 |   n_flipped |   pct_of_book_flipped |
|:-------------------------|------------:|----------------------:|
| Last-Minute lead ≤3 → ≤7 |     1963598 |                  8.57 |
| Last-Minute lead ≤3 → ≤2 |      658401 |                  2.87 |
| Last-Minute lead ≤3 → ≤4 |      575206 |                  2.51 |
| Value cut tier ≤4 → ≤3   |      387327 |                  1.69 |
| Value cut tier ≤4 → ≤5   |      109152 |                  0.48 |
| Corporate lead ≤7 → ≤10  |       38157 |                  0.17 |
| Corporate lead ≤7 → ≤5   |       33648 |                  0.15 |


### Per-segment retention under each perturbation


**Last-Minute lead ≤3 → ≤2**

| proxy_segment   |   pct_kept |
|:----------------|-----------:|
| Last-Minute     |      77.65 |

**Last-Minute lead ≤3 → ≤4**

| proxy_segment    |   pct_kept |
|:-----------------|-----------:|
| Budget/Adventure |      94.55 |
| Unassigned       |      96.25 |

**Last-Minute lead ≤3 → ≤7**

| proxy_segment    |   pct_kept |
|:-----------------|-----------:|
| Budget/Adventure |      81.35 |
| Unassigned       |      87.31 |

**Corporate lead ≤7 → ≤5**

| proxy_segment   |   pct_kept |
|:----------------|-----------:|
| Corporate       |      96.64 |

**Corporate lead ≤7 → ≤10**

| proxy_segment    |   pct_kept |
|:-----------------|-----------:|
| Premium Bleisure |      94.45 |
| Unassigned       |      99.53 |
| Pilgrimage       |      99.84 |
| OFW/Migrant      |      99.97 |

**Value cut tier ≤4 → ≤3**

| proxy_segment   |   pct_kept |
|:----------------|-----------:|
| Balikbayan/VFR  |      93.06 |
| OFW/Migrant     |      95.28 |

**Value cut tier ≤4 → ≤5**

| proxy_segment    |   pct_kept |
|:-----------------|-----------:|
| Premium Bleisure |      81.44 |
| Unassigned       |      99.28 |
| Last-Minute      |      99.87 |
