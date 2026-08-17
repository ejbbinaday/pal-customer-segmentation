# Stage F — feature + proxy-label profile

- Excluded all-non-revenue customers: **12,306**
- Booking feature rows: **22,911,450**  ·  Customer feature rows: **13,435,365**

## Data guards

- **UniqueID persistence:** 19.73% of customers appear in >1 source file → consistent across files (customer rollup valid).
- **Currency sanity:** median-revenue spread across major issue countries = 7.3× (26 countries) → plausibly single-currency.

## Proxy segment — bookings

| proxy_segment    |   bookings |   pct |   avg_rev |
|:-----------------|-----------:|------:|----------:|
| Budget/Adventure |    9037176 | 39.44 |        74 |
| OFW/Migrant      |    3919216 | 17.11 |       312 |
| Last-Minute      |    2945686 | 12.86 |       137 |
| Balikbayan/VFR   |    2911290 | 12.71 |       618 |
| Unassigned       |    2194061 |  9.58 |       360 |
| Corporate        |    1001638 |  4.37 |       493 |
| Premium Bleisure |     481666 |  2.1  |      1504 |
| Family           |     370647 |  1.62 |       235 |
| Pilgrimage       |      43617 |  0.19 |       404 |
| Mabuhay Loyalist |       6453 |  0.03 |       113 |

## Dominant segment — customers

| dominant_segment   |   customers |   pct |
|:-------------------|------------:|------:|
| Budget/Adventure   |     5162374 | 38.42 |
| OFW/Migrant        |     2555625 | 19.02 |
| Balikbayan/VFR     |     2197889 | 16.36 |
| Last-Minute        |     1336045 |  9.94 |
| Unassigned         |     1175158 |  8.75 |
| Corporate          |      430014 |  3.2  |
| Premium Bleisure   |      272406 |  2.03 |
| Family             |      264350 |  1.97 |
| Pilgrimage         |       37770 |  0.28 |
| Mabuhay Loyalist   |        3734 |  0.03 |

## Route region — bookings

| region                 |   bookings |   pct |
|:-----------------------|-----------:|------:|
| Philippines (domestic) |   13218362 | 57.69 |
| East Asia              |    3391154 | 14.8  |
| Southeast Asia         |    2697946 | 11.78 |
| North America          |    1919036 |  8.38 |
| Middle East            |     923123 |  4.03 |
| Oceania                |     761725 |  3.32 |
| South Asia             |        103 |  0    |
| Europe                 |          1 |  0    |

