"""Generates a self-contained, aviation-themed HTML EDA report for PAL."""
import base64
from pathlib import Path

OUTPUT_DIR  = Path("eda_output")
REPORT_PATH = Path("PAL_EDA_Report.html")

def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()

imgs = {p.stem: b64(p) for p in sorted(OUTPUT_DIR.glob("*.png"))}

# ── key stats ─────────────────────────────────────────────────────────────────
stats = [
    {"value":"29,999","label":"PNR Records",         "icon":"✈"},
    {"value":"27",    "label":"Features",             "icon":"📋"},
    {"value":"63.6%", "label":"Domestic Bookings",    "icon":"🏠"},
    {"value":"$160",  "label":"Avg Fare (USD)",        "icon":"💰"},
    {"value":"10",    "label":"Proposed Segments",     "icon":"🎯"},
    {"value":"35",    "label":"EDA Charts Total",       "icon":"📈"},
    {"value":"3",     "label":"Critical Null Features","icon":"⚠"},
]

# ── enhanced segments (10, 4 tiers) ───────────────────────────────────────────
segments = [
    # ── Tier 1: Premium ──
    {
        "tier":"Tier 1 — Premium & High-Value",
        "tier_color":"#3B82F6",
        "name":"Corporate Traveler",
        "icon":"💼",
        "penalty":"×10",
        "color":"#3B82F6",
        "description":"Short-haul business travelers, typically flying ASEAN routes in Business or Economy Flex. Highly schedule-sensitive, low price-sensitivity, book within 3–15 days of departure.",
        "signals":["Business cabin (J) or Economy Flex","TMC / Corporate Web Portal channel","Lead time 3–15 days","ASEAN-dominant (SIN, BKK, HKG)","Solo traveler (PAX = 1)"],
        "benchmark":"Lufthansa: Individuality Seekers (10%) — business trips, premium cabins, all routes.",
        "proxy_records":"671","proxy_pct":"2.2%",
        "data_status":"available",
        "ancillary":"Lounge access, priority boarding, flexible rebooking, seat upgrade",
        "revenue_risk":"Highest — avg ₱45,000/ticket; misclassification = ₱40,000 lost per record",
    },
    {
        "tier":"Tier 1 — Premium & High-Value",
        "tier_color":"#3B82F6",
        "name":"Mabuhay Loyalist",
        "icon":"⭐",
        "penalty":"×8",
        "color":"#8B5CF6",
        "description":"High-frequency repeat flyers with active Mabuhay Miles status. Span all routes and cabins but disproportionately in Business and Premium Economy. Highest lifetime value passengers.",
        "signals":["Active Mabuhay Miles tier (Elite/Premier)","10+ flights per year on PAL","Broad route coverage (not corridor-specific)","Mix of business & leisure itineraries","Loyalty redemption bookings"],
        "benchmark":"Singapore Airlines KrisFlyer Elite — multi-segment loyalists driving disproportionate revenue share.",
        "proxy_records":"N/A","proxy_pct":"Loyalty data required",
        "data_status":"blocked",
        "ancillary":"Upgrade bids, companion vouchers, bonus miles, lounge access",
        "revenue_risk":"Very High — retention loss is compounded across future bookings",
    },
    {
        "tier":"Tier 1 — Premium & High-Value",
        "tier_color":"#3B82F6",
        "name":"Premium Bleisure",
        "icon":"🌆",
        "penalty":"×4",
        "color":"#F59E0B",
        "description":"Professionals who extend business trips into leisure stays. Premium Economy or Business cabin, ASEAN and Australasia routes, moderate-to-long stays. Bleisure market is a $816B global segment growing at 17.4% CAGR.",
        "signals":["Premium Economy (W) or Business (J) cabin","Stay 5–14 days (longer than pure corporate)","ASEAN, Australasia, Japan, Korea routes","Book 7–21 days ahead","Weekend departure or return"],
        "benchmark":"Lufthansa: Exclusivity Seekers (5%) — leisure trips in premium cabins. Bleisure market $816B globally in 2025.",
        "proxy_records":"871","proxy_pct":"2.9%",
        "data_status":"partial",
        "ancillary":"Hotel packages, city experiences, travel insurance, lounge day-pass",
        "revenue_risk":"Moderate-High — hybrid traveler easy to mis-route toward either Corporate or Budget Leisure",
    },

    # ── Tier 2: PAL-Specific Philippine Market ──
    {
        "tier":"Tier 2 — PAL-Specific Philippine Market",
        "tier_color":"#EF4444",
        "name":"OFW / Migrant Worker",
        "icon":"🌍",
        "penalty":"×5",
        "color":"#EF4444",
        "description":"Overseas Filipino Workers traveling between the Philippines and work destinations in the Middle East, East Asia, and beyond. High cargo needs, TTA-reliant, economy-only, plan far ahead.",
        "signals":["Middle East corridor (RUH, DOH, DXB) or East Asia","Traditional Travel Agency (TTA) dominant (59%)","Economy Saver or Economy Value","Lead time 30–90+ days","Sea Crew sub-channel","Cargo / excess baggage add-on"],
        "benchmark":"IATA VFR/Migrant sub-segment. Philippines has 1.8M new OFW deployments/year — unique to PAL's network.",
        "proxy_records":"1,189","proxy_pct":"4.0%",
        "data_status":"available",
        "ancillary":"Extra baggage, cargo, travel insurance, remittance partnerships",
        "revenue_risk":"High — misclassifying as Budget Leisure undersells ancillary revenue on cargo/baggage",
    },
    {
        "tier":"Tier 2 — PAL-Specific Philippine Market",
        "tier_color":"#EF4444",
        "name":"Balikbayan / VFR",
        "icon":"🏡",
        "penalty":"×2",
        "color":"#10B981",
        "description":"Filipino diaspora returning home to visit family. INT→DOM beyond itinerary, seasonal peaks in December–January and April, group travel. North America and Middle East origin markets dominant.",
        "signals":["Beyond (INT→DOM) itinerary type (18% of dataset)","Group bookings (PAX 2–6)","North America or Middle East origin","December–January or April travel","Economy Saver, long lead time 45–90 days","TTA and OTA channels"],
        "benchmark":"IATA VFR segment. ~3.5M Balikbayan arrivals in Philippines annually. Heaviest travel period: Christmas season.",
        "proxy_records":"5,376","proxy_pct":"17.9%",
        "data_status":"available",
        "ancillary":"Balikbayan box cargo, family fare bundles, hotel packages, travel insurance",
        "revenue_risk":"Low penalty but high volume — largest identifiable proxy segment in the dataset",
    },
    {
        "tier":"Tier 2 — PAL-Specific Philippine Market",
        "tier_color":"#EF4444",
        "name":"Pilgrimage / Religious Traveler",
        "icon":"🙏",
        "penalty":"×3",
        "color":"#F97316",
        "description":"Faith-motivated travelers — Catholic pilgrims to Rome/Israel/Fatima and Muslim passengers performing Hajj or Umrah to Saudi Arabia. Seasonal peaks: Holy Week (March/April) for Christians; Dhul Hijja month for Muslims. Asia Pacific religious tourism is a $7.9B market growing at 11.4% CAGR.",
        "signals":["Middle East routes (Jeddah, Medina) or Europe","Group bookings (parish groups, travel agencies)","Seasonal: March–April or Hajj months","TTA channel (parish-arranged bookings)","Economy Saver, long lead (planned months ahead)","Specific routing: MNL → Rome, MNL → Tel Aviv, MNL → JED"],
        "benchmark":"Asia Pacific religious tourism $7.9B market (2024), growing to $23.4B by 2034 at 11.4% CAGR.",
        "proxy_records":"~400 est.","proxy_pct":"~1.3% est.",
        "data_status":"partial",
        "ancillary":"Travel insurance, group meals, special religious meal codes (Halal/Kosher), visa assistance",
        "revenue_risk":"Moderate — seasonal volume spike; poor service experience has outsized reputational impact in faith communities",
    },

    # ── Tier 3: Leisure Segments ──
    {
        "tier":"Tier 3 — Leisure Segments",
        "tier_color":"#10B981",
        "name":"Family Vacation Traveler",
        "icon":"👨‍👩‍👧‍👦",
        "penalty":"×2",
        "color":"#06B6D4",
        "description":"Families traveling together for holidays, typically during school breaks. Group of 3–5, economy class, school holiday peaks. Equivalent to Lufthansa's Care Seeking Families (6% of Lufthansa passengers) — highest service expectations per capita.",
        "signals":["PAX Count 3–5","Economy Saver or Economy Value","December–January, March–April, June school breaks","Domestic leisure routes + short international (Japan, Korea, Bali)","Book 30–60 days ahead","OTA or WEB/APP channel"],
        "benchmark":"Lufthansa: Care Seeking Families (6%) — all routes, all classes, leisure purpose, high service expectations.",
        "proxy_records":"~2,953 est.","proxy_pct":"~9.8% est.",
        "data_status":"available",
        "ancillary":"Seat selection together, child meal, priority boarding, travel insurance, hotel bundles",
        "revenue_risk":"Moderate — high ancillary bundle potential; poor family experience drives negative NPS amplification",
    },
    {
        "tier":"Tier 3 — Leisure Segments",
        "tier_color":"#10B981",
        "name":"Budget / Adventure Seeker",
        "icon":"🎒",
        "penalty":"×1",
        "color":"#60A5FA",
        "description":"Price-sensitive solo or couple leisure travelers. Hunt for promo fares, book far ahead for cheap tickets. Domestic-heavy but willing to fly international on deep discounts. Largest segment by volume.",
        "signals":["Economy Supersaver or Economy Saver","MNL HUB or CEB HUB domestic dominance","WEB/APP channel (promo hunters)","Lead time 34+ days (median)","Solo or couple (PAX 1–2)","Promo fare / sale-triggered booking"],
        "benchmark":"Lufthansa: Adventure Seekers (19%) — leisure, long-haul, economy. Largest Lufthansa segment by behavior type.",
        "proxy_records":"5,080","proxy_pct":"16.9%",
        "data_status":"available",
        "ancillary":"Seat selection, extra baggage, travel insurance, activity packages",
        "revenue_risk":"Lowest — high volume but low yield; primary LCC competitive pressure zone",
    },
    {
        "tier":"Tier 3 — Leisure Segments",
        "tier_color":"#10B981",
        "name":"Last-Minute / Urgent Traveler",
        "icon":"⚡",
        "penalty":"×3",
        "color":"#94A3B8",
        "description":"Bookings within 0–3 days of departure. Blend of missed corporate trips, family emergencies, and opportunistic leisure. Willing to pay fare premium. Economy Flex or Business Flex dominant.",
        "signals":["Lead time 0–3 days (15.5% of dataset)","Economy Flex or Business Flex farebrand","Ticket Office and Contact Center channels spike","All routes — not corridor-specific","Higher-than-average fare per PAX (urgency premium)"],
        "benchmark":"Sabre research: Business travelers 'tend to book close to departure date, underlying the price sensitivity' — but for a different reason (urgency, not price-hunting).",
        "proxy_records":"4,659","proxy_pct":"15.5%",
        "data_status":"available",
        "ancillary":"Flexible rebooking, lounge day-pass, airport transfer, travel insurance",
        "revenue_risk":"Moderate — captures premium fares if correctly identified; over-serving risks margin erosion",
    },

    # ── Tier 4: Emerging Segments ──
    {
        "tier":"Tier 4 — Emerging & Growth Segments",
        "tier_color":"#8B5CF6",
        "name":"Digital Nomad / Remote Worker",
        "icon":"💻",
        "penalty":"×3",
        "color":"#A78BFA",
        "description":"Location-independent professionals leveraging remote work flexibility to travel while working. 50M+ worldwide in 2025 (up from 35M in 2023). ASEAN hub-hopping is a primary behavior — Bali, Bangkok, Manila, Cebu as bases. Medium-to-long stays, flexible one-way or open-jaw tickets.",
        "signals":["One-way or open-jaw itinerary","Length of stay 14–90 days (extended stay)","Economy Flex or Economy Value (flexibility needed)","WEB/APP channel (tech-savvy, self-serve)","ASEAN routes — BKK, CGK, DPS, SGN","Solo traveler (PAX = 1)","Multiple bookings on same route in short window"],
        "benchmark":"Digital nomad population: 50M+ globally in 2025. Bleisure market $816B growing at 17.4% CAGR through 2034. Fastest-growing emerging travel segment.",
        "proxy_records":"~1,200 est.","proxy_pct":"~4% est. (needs LOS data)",
        "data_status":"blocked",
        "ancillary":"Co-working partnerships, eSIM data, long-stay hotel packages, flexible ticket upgrades",
        "revenue_risk":"Moderate-High — high frequency, loyalty potential; currently invisible without Length of Stay data",
    },
]

# ── Competitor benchmark table ─────────────────────────────────────────────────
benchmarks = [
    {"airline":"Lufthansa Group",      "model":"6 behavioral segments",
     "segments":"Efficiency Seekers (46%) · Convenience Seekers (14%) · Individuality Seekers (10%) · Exclusivity Seekers (5%) · Adventure Seekers (19%) · Care Seeking Families (6%)",
     "approach":"Behavioral + trip-purpose hybrid; tailored USP per segment"},
    {"airline":"Singapore Airlines",   "model":"Cabin-tier + loyalty",
     "segments":"Suites (ultra-premium) · Business (corporate/bleisure) · Premium Economy · Economy · KrisFlyer loyalty tiers cutting across all",
     "approach":"Premium service differentiation; loyalty program as a cross-segment overlay"},
    {"airline":"Emirates",             "model":"Cabin-tier + VIP",
     "segments":"First Class · Business Class · Economy; high-value leisure and corporate in premium; VFR and migrant workers in economy",
     "approach":"Product experience differentiation per cabin; heavy reliance on lounge and in-flight as retention tools"},
    {"airline":"AirAsia",              "model":"Price-tier + loyalty",
     "segments":"Budget Leisure · OFW/Migrant (economy dominant) · Budget Business; BIG Loyalty overlay",
     "approach":"LCC model — price-driven segmentation; ancillary revenue maximization per booking"},
    {"airline":"IATA Framework",       "model":"Trip-purpose taxonomy",
     "segments":"Business · Leisure · VFR (Visiting Friends & Relatives) · Migrant/OFW · Other",
     "approach":"Traditional trip-purpose classification; sub-segments by advance purchase, stay, party size, channel"},
    {"airline":"PAL (Proposed)",       "model":"10-segment ML model",
     "segments":"Corporate · Mabuhay Loyalist · Premium Bleisure · OFW · Balikbayan/VFR · Pilgrim · Family · Budget/Adventure · Last-Minute · Digital Nomad",
     "approach":"Semi-supervised clustering on 40+ PNR features; Philippine-market-specific with global emerging segments"},
]

# ── missing features ───────────────────────────────────────────────────────────
missing_features = [
    {"name":"Loyalty Status / Mabuhay Tier","priority":"P1 — BLOCKING",
     "color":"#EF4444","source":"Mabuhay Miles DB",
     "impact":"Required for 4 of 6 Negative Learning rules; identifies Corporate & Loyalist directly"},
    {"name":"Length of Stay","priority":"P1 — BLOCKING",
     "color":"#EF4444","source":"Return PNR pairing",
     "impact":"Separates Corporate (<4d) from Bleisure (5–14d), Balikbayan (14d+) and Digital Nomad (30d+)"},
    {"name":"Departure Time","priority":"P1 — BLOCKING",
     "color":"#EF4444","source":"Flight schedule data",
     "impact":"Early-AM = Corporate signal; midday/evening = leisure pattern"},
    {"name":"Cargo / Baggage Add-on Flag","priority":"P2 — High Value",
     "color":"#F59E0B","source":"PNR ancillary data",
     "impact":"Required for OFW negative rule; cargo add-on rules out Bleisure; confirms Balikbayan"},
    {"name":"Prior Booking Count (12-month)","priority":"P2 — High Value",
     "color":"#F59E0B","source":"PNR historical DB",
     "impact":"Frequency = Loyalist proxy; repeat same-route = OFW; multi-destination = Digital Nomad"},
    {"name":"Passenger Nationality / Passport","priority":"P2 — High Value",
     "color":"#F59E0B","source":"PNR passenger data",
     "impact":"Filipino passport on international = OFW/Balikbayan; foreign passport inbound = medical tourist or nomad"},
    {"name":"Meal Preference / SSR Codes","priority":"P3 — Useful",
     "color":"#60A5FA","source":"PNR data",
     "impact":"Halal = OFW/Pilgrim signal; Kosher = pilgrimage; Vegetarian = lifestyle; Child meal = Family segment"},
    {"name":"One-way vs. Round-trip Flag","priority":"P3 — Useful",
     "color":"#60A5FA","source":"Ticketed itinerary parse",
     "impact":"One-way = OFW departure leg or Digital Nomad; Round-trip = leisure/Balikbayan return"},
]

# ── negative learning rules ────────────────────────────────────────────────────
nl_rules = [
    {"condition":"Booked 60+ days out · Economy · No Loyalty ID",
     "outcome":"Cannot be Corporate","available":2,"missing":1,"blocked_by":"Loyalty status"},
    {"condition":"Cargo add-on · Economy · Manila–Riyadh route",
     "outcome":"Cannot be Premium Bleisure","available":1,"missing":2,"blocked_by":"Loyalty status, Cargo flag"},
    {"condition":"0–3 day booking · Promo fare · No flexibility",
     "outcome":"Cannot be Last-Minute Emergency","available":3,"missing":0,"blocked_by":"—"},
    {"condition":"Group booking 5+ · Dec–Jan travel dates",
     "outcome":"Cannot be Solo Budget Leisure","available":3,"missing":0,"blocked_by":"—"},
    {"condition":"Business cabin · Same-day return · Loyalty status",
     "outcome":"Corporate or Premium Bleisure only","available":1,"missing":2,"blocked_by":"Loyalty status, Length of stay"},
    {"condition":"Middle East corridor · No Mabuhay Miles · Cargo",
     "outcome":"OFW Traveler or Balikbayan only","available":1,"missing":2,"blocked_by":"Loyalty status, Cargo flag"},
    {"condition":"Group 5+ · Mar–Apr · TTA channel · Middle East",
     "outcome":"Cannot be Budget Leisure — likely Pilgrimage","available":3,"missing":0,"blocked_by":"—"},
    {"condition":"PAX 3–5 · School holiday months · Economy Value",
     "outcome":"Cannot be Corporate — likely Family segment","available":3,"missing":0,"blocked_by":"—"},
    {"condition":"One-way · ASEAN · Economy Flex · Solo · WEB/APP",
     "outcome":"Cannot be VFR — possible Digital Nomad","available":2,"missing":1,"blocked_by":"Length of stay"},
]

# ── chart definitions ──────────────────────────────────────────────────────────
charts = [
    ("01_missing_values","Missing Value Rate by Feature",
     "Three features — <strong>Loyalty status</strong>, <strong>Departure Time</strong>, and <strong>Length of stay</strong> — are 100% null across all 29,999 records. These are blocking inputs for 4 of 6 Negative Learning rules and must be sourced from PAL's Mabuhay Miles DB and flight schedule systems before modelling can begin."),
    ("02_entity_split","Domestic vs International Split",
     "63.6% of bookings are domestic (DOM) and 36.4% international (INT). The model must perform well across both, with distinct segment distributions expected — Corporate and OFW are INT-heavy, while Budget Leisure and Family are DOM-heavy."),
    ("03_region_distribution","Booking Volume by Region",
     "MNL HUB drives 54% of all bookings, reflecting PAL's domestic dominance. ASEAN (18%) is the primary international region — home of Corporate short-haul travel. Middle East (4%) is the OFW corridor proxy. North America (3.8%) is the primary Balikbayan origin market."),
    ("04_cabin_distribution","Cabin Class Distribution",
     "Economy (Y) accounts for 95.2% of bookings. Business (J) — the cleanest Corporate proxy — represents only 2.2% (671 records). Premium Economy (W) at 2.9% signals the Bleisure segment. The class imbalance must be addressed via the cost-sensitive asymmetric penalty matrix."),
    ("05_farebrand_distribution","Farebrand Distribution",
     "Economy Saver and Economy Value together account for 56% of bookings — dominant across Budget Leisure and OFW fare types. Economy Supersaver (17%) is the deepest discount tier, tied to promo fares and Adventure Seekers. Business brands combined cover only 2.2%."),
    ("06_ticketing_channel","Booking Volume by Ticketing Channel",
     "Traditional Travel Agency (TTA) is the single largest channel at 33%, strongly associated with OFW, Balikbayan, and Pilgrimage travelers. WEB/APP (28%) reflects Budget Leisure and Digital Nomads. TMC (1.3%) and Corporate Web Portal (1.2%) are key Corporate identifiers despite low volume."),
    ("07_itinerary_type","Itinerary Type Distribution",
     "Point-to-Point accounts for 64%. Beyond (INT→DOM) at 18% is the strongest Balikbayan/VFR proxy. Beyond (INT→INT) at 11% likely captures connecting OFW and Pilgrimage legs. Open Jaw (1%) is a potential Digital Nomad or Bleisure signal."),
    ("08_fare_distribution","Average Fare Distribution",
     "Fare is strongly right-skewed (mean $160, median $94). The log-scale plot reveals a multi-modal distribution consistent with distinct segments paying fundamentally different price points — from $40 CEB HUB domestic to $5,383 Business long-haul."),
    ("09_fare_by_cabin","Average Fare by Cabin Class",
     "Business cabin (J) commands a mean fare of $440 — nearly 3× Economy's $154. This gap underpins the ×10 Corporate penalty: a single misclassified Corporate passenger costs PAL ~₱40,000 in missed revenue."),
    ("10_fare_by_region","Average Fare by Region",
     "North America commands the highest median fare (~$635), reflecting Balikbayan and OFW long-haul routes. Australasia follows at ~$388 (Bleisure). CEB HUB sits at just $40 — the ultra-competitive domestic market most exposed to LCC pressure."),
    ("11_lead_time_distribution","Booking Lead Time Distribution",
     "27% of passengers book 60+ days ahead (OFW, Balikbayan, Pilgrimage, Adventure Seekers). 15.5% book within 3 days (Last-Minute / Urgent). The median of 20 days sits in the corporate-to-leisure transition zone. Lead time is the single most differentiating feature available in the current dataset."),
    ("12_lead_time_by_farebrand","Lead Time by Farebrand",
     "Economy Supersaver shows the longest median lead time (34 days) — fare hunters planning ahead. Economy Flex and Business Flex have the shortest leads, consistent with flexible Corporate and Last-Minute travelers. This confirms lead time as a strong fare-flexibility signal for the clustering model."),
    ("13_pax_count","PAX Count per Booking",
     "67% are solo (PAX=1) — consistent with Corporate, OFW, and solo Adventure Seekers. PAX 2 (19.4%) signals couples or Bleisure pairs. PAX 3–5 (9.8%) = Family segment. PAX 6+ (3.7%) = Balikbayan group or tour group — directly usable in Negative Learning rules."),
    ("14_day_of_week","Departure Day of Week",
     "Friday is the peak departure day, driven by Corporate travelers starting weekend trips and leisure travelers beginning holidays. Tuesday is the slowest — useful as a Corporate day signal (mid-week meetings) combined with cabin class. Weekend departures skew leisure/family."),
    ("15_channel_entity_heatmap","Ticketing Channel × Entity Heatmap",
     "OTA skews strongly international (3,054 INT vs 908 DOM) — international leisure and Corporate bookings converge here. TTA is heavily domestic (6,469 DOM). Sea Crew is evenly split, confirming its OFW sub-type nature spanning both domestic and international routes."),
    ("16_segment_proxy_volumes","Segment Proxy Record Counts",
     "Balikbayan (Beyond INT-DOM) and Budget Leisure proxies dominate by volume. Last-Minute (15.5%) is a behavioral cross-segment, not a standalone segment. Corporate (2.2%) and OFW (4.0%) are minority but high-value segments requiring the asymmetric penalty matrix to avoid being drowned out."),
    ("17_lead_time_kde_by_proxy","Lead Time Distribution by Segment Proxy",
     "OFW travelers show a clear far-ahead planning peak. Corporate travelers are bimodal — some urgent, some planned. Budget Leisure and Last-Minute overlap at short lead times, requiring additional features (fare flexibility, PAX count, cabin) to disambiguate. Family and Pilgrim segments are expected to cluster in the 30–60d range."),
    ("18_fare_per_pax_by_proxy","Fare per PAX by Segment Proxy",
     "Corporate (Business J) sits far above all others with minimal overlap. OFW shows moderate fares with wide variance (short-haul Middle East vs. long-haul North America). Budget Leisure is at the bottom. This fare separation is one of the strongest clustering signals available."),
    ("19_channel_by_proxy_heatmap","Ticketing Channel Mix by Segment Proxy (%)",
     "OFW travelers book 59% through TTA — the highest channel concentration of any segment, making it a near-definitive OFW signal. Corporate uses WEB/APP and OTA. Balikbayan splits between TTA and WEB/APP. Last-Minute spikes toward Ticket Office and Contact Center — walk-ins and phone bookings under urgency."),
    ("20_top_sectors","Top 15 O&D Sectors",
     "BCDMNL (Bacolod–Manila) dominates at 34% — high-frequency domestic route. Bangkok (BKK) is the top international sector. The top 5 O&D pairs account for 63% of bookings, meaning the model must perform strongly on a concentrated set of routes before generalising across the network's long tail."),
    ("21_negative_learning_feasibility","Negative Learning Rule Feature Coverage",
     "Only 2 of 9 proposed Negative Learning rules can be fully executed with current sample data. The blocked rules all depend on Loyalty status, Cargo flag, or Length of stay — confirming these as the highest-priority data requests before the annotation pipeline begins."),
    ("22_missing_features_priority","Recommended Missing Features — Priority Matrix",
     "Loyalty status and Length of stay sit in the top-right quadrant (high impact + high feasibility from PAL systems). All three P1-blocking features have clear internal sources at PAL. Requesting them before the first clustering run is the single highest-leverage action the team can take."),
]

# ══════════════════════════════════════════════════════════════════════════════
# helpers
# ══════════════════════════════════════════════════════════════════════════════
def hex_to_rgb(h):
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))

def segment_cards_html(segs):
    tiers = {}
    for s in segs:
        tiers.setdefault(s["tier"], []).append(s)

    out = []
    for tier_name, items in tiers.items():
        tc = items[0]["tier_color"]
        out.append(f"""
        <div class="tier-header">
          <span class="tier-line" style="background:{tc}"></span>
          <span class="tier-label" style="color:{tc}">{tier_name}</span>
          <span class="tier-line" style="background:{tc}"></span>
        </div>
        <div class="segments-grid">""")

        for s in items:
            rgb = hex_to_rgb(s["color"])
            signals_html = "".join(f'<span class="sig-pill">{sig}</span>' for sig in s["signals"])
            status_html = (
                '<span class="ds-badge ds-ok">✓ Data available</span>'
                if s["data_status"] == "available" else
                '<span class="ds-badge ds-blocked">⚠ Data blocked</span>'
                if s["data_status"] == "blocked" else
                '<span class="ds-badge ds-partial">~ Partial data</span>'
            )
            out.append(f"""
          <div class="segment-card" style="border-color:rgba({rgb},0.3)">
            <div class="segment-accent" style="background:linear-gradient(90deg,{s['color']},{tc})"></div>
            <div class="seg-top-row">
              <span class="seg-icon">{s['icon']}</span>
              <span class="seg-name" style="color:{s['color']}">{s['name']}</span>
              <span class="seg-penalty" style="color:{s['color']};border-color:{s['color']}">Penalty {s['penalty']}</span>
            </div>
            <p class="seg-desc">{s['description']}</p>
            <div class="sig-pills">{signals_html}</div>
            <div class="seg-meta">
              <div class="seg-stat-row">
                <div class="seg-stat"><div class="seg-stat-val" style="color:{s['color']}">{s['proxy_records']}</div><div class="seg-stat-lbl">Proxy Records</div></div>
                <div class="seg-stat"><div class="seg-stat-val" style="color:{s['color']}">{s['proxy_pct']}</div><div class="seg-stat-lbl">of Dataset</div></div>
                <div style="display:flex;align-items:flex-end">{status_html}</div>
              </div>
              <div class="seg-benchmark">📚 {s['benchmark']}</div>
              <div class="seg-ancillary">💳 <strong>Ancillary Opps:</strong> {s['ancillary']}</div>
              <div class="seg-revenue">⚠ <strong>Revenue Risk:</strong> {s['revenue_risk']}</div>
            </div>
          </div>""")
        out.append("</div>")
    return "\n".join(out)


def chart_card(i):
    key, title, insight = charts[i]
    return f"""<div class="chart-card">
      <div class="chart-header"><div class="chart-title">{title}</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs[key]}" alt="{title}">
      <div class="chart-insight">{insight}</div>
    </div>"""


def chart_grid(indices, single=False):
    cls = "charts-grid single" if single else "charts-grid"
    return f'<div class="{cls}">{"".join(chart_card(i) for i in indices)}</div>'


def dq_rows():
    rows = [
        ("Market Segment (TARGET)","float",100.0,"⚠ Must be generated by ML pipeline"),
        ("Loyalty status","float",100.0,"⚠ Request from Mabuhay Miles DB"),
        ("Departure Time","float",100.0,"⚠ Request from flight schedule data"),
        ("Length of stay","float",100.0,"⚠ Request from return PNR pairing"),
        ("Ticketing Channel","str",10.19,"Investigate: likely grouped/charter bookings"),
        ("POS Country","str",10.19,"Investigate: paired with Ticketing Channel nulls"),
        ("POS City","str",10.19,"Investigate: paired with Ticketing Channel nulls"),
        ("FareBasis","str",9.26,"Investigate: Non-revenue or group fare records"),
        ("POO","str",9.26,"Paired with FareBasis nulls"),
        ("Issue Date","str",9.26,"Paired with FareBasis nulls"),
        ("POO Country","str",9.26,"Paired with FareBasis nulls"),
        ("POS Region","str",6.60,"Acceptable — impute from POS Country"),
        ("PNRCreationDate","str",0.05,"Minimal — safe to drop or impute"),
        ("Flight Date","str",0.0,"✓ Complete"),
        ("Entity","str",0.0,"✓ Complete"),
        ("Cabin","str",0.0,"✓ Complete"),
        ("Farebrand","str",0.0,"✓ Complete"),
        ("Average Fare","str",0.0,"✓ Complete (requires $ strip → float)"),
        ("PAX Count","int",0.0,"✓ Complete"),
    ]
    out = []
    for name, typ, pct, note in rows:
        color = "#EF4444" if pct >= 50 else "#F59E0B" if pct >= 5 else "#10B981"
        fill_cls = "null-red" if pct >= 50 else "null-gold" if pct >= 5 else "null-green"
        out.append(f"""<tr>
          <td style="color:var(--white);font-weight:500">{name}</td>
          <td><span class="type-tag">{typ}</span></td>
          <td><div class="null-bar-wrap">
            <div class="null-bar-bg"><div class="null-bar-fill {fill_cls}" style="width:{min(pct,100)}%"></div></div>
            <span class="null-val" style="color:{color}">{pct:.1f}%</span>
          </div></td>
          <td style="font-size:.75rem;color:{color}">{note}</td>
        </tr>""")
    return "\n".join(out)


def nl_rows():
    out = []
    for r in nl_rules:
        pips = ("".join('<div class="nl-pip pip-ok"></div>' for _ in range(r["available"])) +
                "".join('<div class="nl-pip pip-bad"></div>' for _ in range(r["missing"])))
        out.append(f"""<tr>
          <td class="nl-rule-text">{r['condition']}</td>
          <td class="nl-outcome">{r['outcome']}</td>
          <td><div class="nl-bar">{pips}<span style="font-size:.72rem;color:var(--grey);margin-left:.25rem">{r['available']}/3</span></div></td>
          <td class="nl-blocked">{r['blocked_by']}</td>
        </tr>""")
    return "\n".join(out)


def benchmark_rows():
    out = []
    for b in benchmarks:
        is_pal = "PAL" in b["airline"]
        highlight = "background:rgba(240,165,0,0.06);border-left:3px solid var(--gold);" if is_pal else ""
        out.append(f"""<tr style="{highlight}">
          <td style="font-weight:{'700' if is_pal else '500'};color:{'var(--gold)' if is_pal else 'var(--white)'}">{b['airline']}</td>
          <td style="color:var(--grey);font-size:.8rem">{b['model']}</td>
          <td style="font-size:.78rem;color:var(--grey)">{b['segments']}</td>
          <td style="font-size:.78rem;color:var(--grey)">{b['approach']}</td>
        </tr>""")
    return "\n".join(out)


def missing_items_html():
    out = []
    for f in missing_features:
        rgb = hex_to_rgb(f["color"])
        out.append(f"""<div class="missing-item">
          <div class="missing-dot" style="background:{f['color']}"></div>
          <div>
            <div class="missing-name">{f['name']}</div>
            <div class="missing-impact">{f['impact']}</div>
            <div class="missing-source">Source: <span>{f['source']}</span></div>
          </div>
          <span class="priority-badge" style="background:rgba({rgb},0.15);color:{f['color']};border:1px solid {f['color']}">{f['priority']}</span>
        </div>""")
    return "\n".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════════════════════
stats_html = "".join(f"""<div class="stat-card">
  <div class="stat-icon">{s['icon']}</div>
  <div class="stat-value">{s['value']}</div>
  <div class="stat-label">{s['label']}</div>
</div>""" for s in stats)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PAL Customer Segmentation — EDA Report</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --navy:#0A1628;--blue:#003B8E;--sky:#1E5BAD;
  --gold:#F0A500;--red:#C0392B;--white:#F8FAFF;
  --grey:#94A3B8;--card:#111827;--border:rgba(255,255,255,0.08);
}}
html{{scroll-behavior:smooth}}
body{{background:var(--navy);color:var(--white);font-family:'Segoe UI',system-ui,sans-serif;line-height:1.6;overflow-x:hidden}}
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:var(--navy)}}
::-webkit-scrollbar-thumb{{background:var(--blue);border-radius:3px}}

/* NAV */
nav{{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(10,22,40,0.94);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);padding:0 2rem;display:flex;align-items:center;gap:1.5rem;height:58px}}
.nav-logo{{display:flex;align-items:center;gap:.5rem;font-weight:700;font-size:.95rem;color:var(--gold);text-decoration:none;white-space:nowrap}}
.nav-logo span{{color:var(--white);font-weight:400}}
.nav-links{{display:flex;gap:.15rem;overflow-x:auto;scrollbar-width:none;flex:1}}
.nav-links::-webkit-scrollbar{{display:none}}
.nav-links a{{color:var(--grey);text-decoration:none;font-size:.75rem;padding:.28rem .7rem;border-radius:20px;white-space:nowrap;transition:all .2s}}
.nav-links a:hover,.nav-links a.active{{color:var(--gold);background:rgba(240,165,0,.1)}}
.nav-badge{{margin-left:auto;background:var(--blue);color:var(--gold);font-size:.68rem;padding:.22rem .7rem;border-radius:20px;white-space:nowrap;font-weight:600;border:1px solid rgba(240,165,0,.4)}}

/* HERO */
.hero{{min-height:100vh;background:radial-gradient(ellipse at 20% 50%,rgba(0,59,142,.45) 0%,transparent 60%),radial-gradient(ellipse at 80% 20%,rgba(192,57,43,.25) 0%,transparent 50%),linear-gradient(160deg,#0A1628 0%,#0D1F3C 50%,#0A1628 100%);display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:6rem 2rem 4rem;position:relative;overflow:hidden}}
.hero-grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:60px 60px;mask-image:radial-gradient(ellipse at center,black 40%,transparent 80%)}}
.hero-plane{{font-size:3.5rem;margin-bottom:1.5rem;filter:drop-shadow(0 0 30px rgba(240,165,0,.5));animation:float 4s ease-in-out infinite}}
@keyframes float{{0%,100%{{transform:translateY(0) rotate(-5deg)}}50%{{transform:translateY(-12px) rotate(-5deg)}}}}
.hero-eyebrow{{color:var(--gold);font-size:.82rem;letter-spacing:.25em;text-transform:uppercase;font-weight:600;margin-bottom:1rem}}
.hero h1{{font-size:clamp(2rem,5vw,3.8rem);font-weight:800;line-height:1.1;background:linear-gradient(135deg,#ffffff 30%,var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:1rem}}
.hero-sub{{font-size:1.05rem;color:var(--grey);max-width:620px;margin:0 auto 2.5rem}}
.hero-meta{{display:flex;gap:1.5rem;flex-wrap:wrap;justify-content:center;font-size:.78rem;color:var(--grey)}}
.hero-meta span{{display:flex;align-items:center;gap:.3rem}}
.hero-meta strong{{color:var(--white)}}
.hero-line{{position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--gold),transparent)}}
.scroll-hint{{position:absolute;bottom:1.8rem;display:flex;flex-direction:column;align-items:center;gap:.3rem;color:var(--grey);font-size:.72rem;animation:bounce 2.5s infinite}}
@keyframes bounce{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(6px)}}}}

/* LAYOUT */
.section{{padding:4.5rem 2rem;max-width:1300px;margin:0 auto}}
.section-header{{margin-bottom:2.5rem}}
.section-tag{{display:inline-block;color:var(--gold);font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;font-weight:600;margin-bottom:.4rem}}
.section-header h2{{font-size:clamp(1.5rem,3vw,2.2rem);font-weight:700;border-left:3px solid var(--gold);padding-left:1rem}}
.section-header p{{color:var(--grey);margin-top:.6rem;max-width:720px}}
.divider{{height:1px;background:linear-gradient(90deg,transparent,var(--border),transparent)}}

/* STATS */
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin-bottom:3rem}}
.stat-card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.4rem;text-align:center;transition:border-color .2s,transform .2s}}
.stat-card:hover{{border-color:var(--gold);transform:translateY(-3px)}}
.stat-icon{{font-size:1.7rem;margin-bottom:.4rem}}
.stat-value{{font-size:1.9rem;font-weight:800;color:var(--gold)}}
.stat-label{{font-size:.7rem;color:var(--grey);margin-top:.15rem;text-transform:uppercase;letter-spacing:.1em}}

/* CALLOUT */
.callout{{background:linear-gradient(135deg,rgba(0,59,142,.25),rgba(240,165,0,.08));border:1px solid rgba(240,165,0,.3);border-radius:14px;padding:1.8rem;margin:2rem 0}}
.callout h3{{color:var(--gold);margin-bottom:.4rem;font-size:1rem}}
.callout p{{color:var(--grey);font-size:.85rem}}

/* TIER HEADERS */
.tier-header{{display:flex;align-items:center;gap:1rem;margin:2.5rem 0 1.2rem}}
.tier-line{{flex:1;height:1px}}
.tier-label{{font-size:.72rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;white-space:nowrap}}

/* SEGMENT CARDS */
.segments-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:1.2rem;margin-bottom:.5rem}}
.segment-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.4rem;position:relative;overflow:hidden;transition:transform .2s,border-color .2s,box-shadow .2s}}
.segment-card:hover{{transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.4)}}
.segment-accent{{position:absolute;top:0;left:0;right:0;height:3px}}
.seg-top-row{{display:flex;align-items:center;gap:.7rem;margin-bottom:.75rem}}
.seg-icon{{font-size:1.5rem}}
.seg-name{{font-size:1rem;font-weight:700;flex:1}}
.seg-penalty{{font-size:.7rem;font-weight:700;padding:.22rem .6rem;border-radius:20px;border:1px solid;background:rgba(255,255,255,.05);white-space:nowrap}}
.seg-desc{{font-size:.82rem;color:var(--grey);margin-bottom:1rem;line-height:1.5}}
.sig-pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:1rem}}
.sig-pill{{font-size:.68rem;padding:.18rem .55rem;border-radius:20px;background:rgba(255,255,255,.06);color:var(--grey);border:1px solid rgba(255,255,255,.1)}}
.seg-meta{{border-top:1px solid var(--border);padding-top:.9rem;display:flex;flex-direction:column;gap:.5rem}}
.seg-stat-row{{display:flex;align-items:flex-end;gap:1.2rem}}
.seg-stat .seg-stat-val{{font-size:.95rem;font-weight:700}}
.seg-stat .seg-stat-lbl{{font-size:.65rem;color:var(--grey);text-transform:uppercase;letter-spacing:.05em}}
.ds-badge{{font-size:.65rem;padding:.18rem .55rem;border-radius:20px;font-weight:600}}
.ds-ok{{background:rgba(16,185,129,.15);color:#10B981;border:1px solid rgba(16,185,129,.3)}}
.ds-blocked{{background:rgba(239,68,68,.15);color:#EF4444;border:1px solid rgba(239,68,68,.3)}}
.ds-partial{{background:rgba(245,158,11,.15);color:#F59E0B;border:1px solid rgba(245,158,11,.3)}}
.seg-benchmark{{font-size:.74rem;color:var(--grey);padding:.4rem .6rem;background:rgba(255,255,255,.03);border-radius:6px;border-left:2px solid rgba(240,165,0,.4)}}
.seg-ancillary{{font-size:.74rem;color:var(--grey)}}
.seg-ancillary strong{{color:var(--sky)}}
.seg-revenue{{font-size:.74rem;color:var(--grey)}}
.seg-revenue strong{{color:var(--red)}}

/* CHARTS */
.charts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(540px,1fr));gap:1.4rem}}
.charts-grid.single{{grid-template-columns:1fr}}
.chart-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;transition:border-color .25s,box-shadow .25s}}
.chart-card:hover{{border-color:rgba(240,165,0,.35);box-shadow:0 6px 28px rgba(0,59,142,.3)}}
.chart-header{{padding:1.1rem 1.4rem .65rem;border-bottom:1px solid var(--border)}}
.chart-title{{font-size:.88rem;font-weight:600}}
.chart-img{{width:100%;display:block}}
.chart-insight{{padding:.9rem 1.4rem 1.1rem;font-size:.79rem;color:var(--grey);line-height:1.6;border-top:1px solid var(--border);background:rgba(0,0,0,.2)}}
.chart-insight strong{{color:var(--gold)}}

/* BENCHMARK TABLE */
.bench-table{{width:100%;border-collapse:collapse;font-size:.8rem}}
.bench-table th{{background:rgba(0,59,142,.4);color:var(--gold);padding:.65rem 1rem;text-align:left;font-size:.7rem;letter-spacing:.06em;text-transform:uppercase}}
.bench-table td{{padding:.75rem 1rem;border-bottom:1px solid var(--border);vertical-align:top}}
.bench-table tr:hover td{{background:rgba(255,255,255,.015)}}

/* NL TABLE */
.nl-table{{width:100%;border-collapse:collapse;font-size:.8rem}}
.nl-table th{{background:rgba(0,59,142,.4);color:var(--gold);padding:.65rem 1rem;text-align:left;font-size:.7rem;letter-spacing:.06em;text-transform:uppercase}}
.nl-table td{{padding:.75rem 1rem;border-bottom:1px solid var(--border);vertical-align:middle}}
.nl-table tr:hover td{{background:rgba(255,255,255,.015)}}
.nl-rule-text{{color:var(--white)}}
.nl-outcome{{color:var(--gold);font-style:italic;font-size:.76rem}}
.nl-bar{{display:flex;align-items:center;gap:.4rem}}
.nl-pip{{width:9px;height:9px;border-radius:50%}}
.pip-ok{{background:#10B981}}.pip-bad{{background:var(--red)}}
.nl-blocked{{font-size:.7rem;color:var(--red)}}

/* DQ TABLE */
.dq-table{{width:100%;border-collapse:collapse;font-size:.8rem}}
.dq-table th{{background:rgba(0,59,142,.4);color:var(--gold);padding:.65rem 1rem;text-align:left;font-size:.7rem;letter-spacing:.06em;text-transform:uppercase}}
.dq-table td{{padding:.65rem 1rem;border-bottom:1px solid var(--border);vertical-align:middle}}
.dq-table tr:hover td{{background:rgba(255,255,255,.015)}}
.null-bar-wrap{{display:flex;align-items:center;gap:.5rem;min-width:110px}}
.null-bar-bg{{flex:1;height:5px;background:rgba(255,255,255,.08);border-radius:3px}}
.null-bar-fill{{height:100%;border-radius:3px}}
.null-red{{background:#EF4444}}.null-gold{{background:#F59E0B}}.null-green{{background:#10B981}}
.null-val{{font-size:.74rem;white-space:nowrap}}
.type-tag{{font-size:.68rem;padding:.12rem .45rem;border-radius:4px;background:rgba(255,255,255,.07);color:var(--grey)}}

/* MISSING */
.missing-list{{display:flex;flex-direction:column;gap:.9rem}}
.missing-item{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.1rem 1.4rem;display:grid;grid-template-columns:auto 1fr auto;gap:.9rem;align-items:start;transition:border-color .2s}}
.missing-item:hover{{border-color:rgba(240,165,0,.3)}}
.missing-dot{{width:9px;height:9px;border-radius:50%;margin-top:5px;flex-shrink:0}}
.missing-name{{font-weight:600;font-size:.9rem;margin-bottom:.25rem}}
.missing-impact{{font-size:.78rem;color:var(--grey)}}
.missing-source{{font-size:.68rem;color:var(--grey);margin-top:.15rem}}
.missing-source span{{color:var(--sky)}}
.priority-badge{{font-size:.68rem;font-weight:700;padding:.18rem .55rem;border-radius:20px;white-space:nowrap;align-self:start}}

/* FOOTER */
footer{{background:rgba(0,0,0,.4);border-top:1px solid var(--border);padding:2.5rem 2rem;text-align:center;color:var(--grey);font-size:.78rem}}
footer strong{{color:var(--gold)}}

/* RESPONSIVE */
@media(max-width:768px){{
  .charts-grid,.segments-grid{{grid-template-columns:1fr}}
  .missing-item{{grid-template-columns:auto 1fr}}
  .priority-badge{{display:none}}
  .bench-table,.nl-table{{font-size:.7rem}}
}}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <a class="nav-logo" href="#hero">✈ <span>PAL EDA Report</span></a>
  <div class="nav-links">
    <a href="#overview">Overview</a>
    <a href="#segments">Segments</a>
    <a href="#benchmark">Benchmark</a>
    <a href="#composition">Composition</a>
    <a href="#fare">Fare</a>
    <a href="#booking">Booking</a>
    <a href="#channels">Channels</a>
    <a href="#routes">Routes</a>
    <a href="#model">Modelling</a>
    <a href="#missing">Missing Data</a>
  </div>
  <span class="nav-badge">Confidential · April 2026</span>
</nav>

<!-- HERO -->
<section class="hero" id="hero">
  <div class="hero-grid"></div>
  <div class="hero-plane">✈</div>
  <p class="hero-eyebrow">Exploratory Data Analysis — Customer Segmentation</p>
  <h1>PAL Passenger<br>Intelligence Report</h1>
  <p class="hero-sub">A research-backed, data-driven analysis of 29,999 PNR booking records to inform an enhanced 10-segment ML model for Philippine Airlines.</p>
  <div class="hero-meta">
    <span>📅 <strong>April 2026</strong></span>
    <span>📊 <strong>29,999 records</strong> · 27 features</span>
    <span>🎯 <strong>10 proposed segments</strong></span>
    <span>📚 <strong>Sabre · IATA · Lufthansa benchmarks</strong></span>
    <span>🔬 <strong>CPT 3 — Binaday · Lim · Versoza · Yamzon</strong></span>
  </div>
  <div class="hero-line"></div>
  <div class="scroll-hint"><span>Scroll to explore</span><span style="font-size:1.1rem">↓</span></div>
</section>

<!-- ── 01 OVERVIEW ── -->
<div class="divider"></div>
<div class="section" id="overview">
  <div class="section-header">
    <span class="section-tag">01 · Dataset Overview</span>
    <h2>At a Glance</h2>
    <p>Key statistics from the sample PNR dataset provided by Philippine Airlines.</p>
  </div>
  <div class="stats-grid">{stats_html}</div>
  <div class="callout">
    <h3>⚠ Critical Data Gap — Action Required Before Modelling</h3>
    <p>Three features — <strong style="color:var(--gold)">Loyalty status</strong>,
    <strong style="color:var(--gold)">Departure Time</strong>, and
    <strong style="color:var(--gold)">Length of Stay</strong> — are <strong style="color:#EF4444">100% null</strong>
    in the sample. These are required inputs for the Negative Learning step and for correctly
    identifying the Mabuhay Loyalist, Corporate, Digital Nomad, and Premium Bleisure segments.
    PAL must provide these from internal systems before the annotation pipeline can begin.</p>
  </div>
  {chart_grid([0], single=True)}
  <h3 style="margin:2.5rem 0 1rem;font-size:.9rem;color:var(--grey);text-transform:uppercase;letter-spacing:.1em">Feature Nullability Summary</h3>
  <table class="dq-table">
    <thead><tr><th>Feature</th><th>Type</th><th>Null Rate</th><th>Status / Action</th></tr></thead>
    <tbody>{dq_rows()}</tbody>
  </table>
</div>

<!-- ── 02 SEGMENTS ── -->
<div class="divider"></div>
<div class="section" id="segments">
  <div class="section-header">
    <span class="section-tag">02 · Enhanced Segment Framework</span>
    <h2>10 Proposed Customer Segments</h2>
    <p>Expanded from the original 6, informed by Lufthansa behavioral research, IATA trip-purpose taxonomy, Sabre's ancillary segmentation model, and Philippine market context. Segments are organised into 4 tiers by revenue value and strategic priority.</p>
  </div>
  <div class="callout">
    <h3>📚 Research Basis</h3>
    <p>
      <strong style="color:var(--white)">Lufthansa</strong> — 6 behavioral segments (Efficiency, Convenience, Individuality, Exclusivity, Adventure Seekers, Care Seeking Families). Research by Expert Journal of Marketing.<br>
      <strong style="color:var(--white)">IATA</strong> — Traditional taxonomy: Business · Leisure · VFR · Migrant Worker. Trip-purpose signals: advance purchase, length of stay, party size, channel, POS country.<br>
      <strong style="color:var(--white)">Sabre</strong> — Customer choice models show strong variation in price vs. schedule sensitivity and ancillary preferences by segment. Recommends 5–25 segments per airline.<br>
      <strong style="color:var(--white)">Market Research</strong> — Bleisure market $816B (2025), growing 17.4% CAGR. Digital nomads 50M+ globally. Asia Pacific religious tourism $7.9B growing to $23.4B by 2034.
    </p>
  </div>
  {segment_cards_html(segments)}
</div>

<!-- ── 03 BENCHMARK ── -->
<div class="divider"></div>
<div class="section" id="benchmark">
  <div class="section-header">
    <span class="section-tag">03 · Competitive Benchmark</span>
    <h2>How PAL's Framework Compares</h2>
    <p>PAL's proposed 10-segment model benchmarked against global airline segmentation approaches.</p>
  </div>
  <table class="bench-table">
    <thead><tr><th>Airline</th><th>Model Type</th><th>Segments</th><th>Strategic Approach</th></tr></thead>
    <tbody>{benchmark_rows()}</tbody>
  </table>
  <div class="callout" style="margin-top:1.5rem">
    <h3>💡 Key Differentiation for PAL</h3>
    <p>Unlike European carriers (Lufthansa) whose segments are behavioral/attitudinal, PAL's framework must capture
    <strong style="color:var(--gold)">Philippine-specific diaspora dynamics</strong> — OFW, Balikbayan, and Pilgrimage segments
    have no direct equivalent in Western airline research. These three segments alone account for an estimated
    <strong style="color:var(--white)">~23% of all international bookings</strong> in the sample and represent
    PAL's most distinct competitive moat versus foreign full-service carriers.</p>
  </div>
</div>

<!-- ── 04 SEGMENT EDA ── -->
<div class="divider"></div>
<div class="section" id="seg-eda">
  <div class="section-header">
    <span class="section-tag">04 · Proposed Segment EDA</span>
    <h2>Data Evidence for Each Segment</h2>
    <p>EDA performed on proxy-assigned records for all 10 segments. <strong style="color:var(--gold)">Note:</strong> All flight dates in the sample are January 2025. Booking dates (PNRCreationDate) span January 2024 – January 2025 and are used for seasonality analysis.</p>
  </div>

  <div class="callout">
    <h3>🔬 Proxy Assignment Logic (Priority Waterfall)</h3>
    <p>
      Since <code style="color:var(--gold)">Market Segment</code> is 100% null, each record was assigned a proxy segment using a priority waterfall:<br>
      <span style="color:#3B82F6">Corporate</span> (Cabin J) →
      <span style="color:#EF4444">OFW</span> (Middle East / Sea Crew) →
      <span style="color:#F59E0B">Premium Bleisure</span> (Cabin W) →
      <span style="color:#10B981">Balikbayan</span> (INT→DOM Beyond) →
      <span style="color:#F97316">Pilgrimage</span> (PAX≥4 + TTA) →
      <span style="color:#06B6D4">Family</span> (PAX 3–5) →
      <span style="color:#94A3B8">Last-Minute</span> (lead≤3d) →
      <span style="color:#A78BFA">Digital Nomad</span> (solo + ASEAN + WEB/APP + Flex/Value) →
      <span style="color:#60A5FA">Budget/Adventure</span> (Eco Supersaver/Saver)
    </p>
  </div>

  <!-- distribution -->
  <div class="charts-grid single">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Proposed Segment Assignment — Record Distribution</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['23_segment_distribution']}" alt="Segment Distribution">
      <div class="chart-insight">Budget/Adventure is the largest assignable segment at 28.3%, followed by Unassigned (23.6%) — records that require Loyalty status or Length of Stay to classify. Balikbayan/VFR (15.6%) and Last-Minute (11.1%) are the next largest. <strong>Mabuhay Loyalist is entirely unassignable</strong> without Loyalty data.</div>
    </div>
  </div>

  <!-- lead time + fare -->
  <h3 style="margin:2rem 0 1rem;font-size:.85rem;color:var(--grey);text-transform:uppercase;letter-spacing:.1em">Cross-Segment Comparisons</h3>
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Lead Time KDE — All 10 Segments</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['24_lead_time_all_segments']}" alt="Lead Time KDE">
      <div class="chart-insight">Clear separation between segments on lead time. <strong>OFW and Balikbayan</strong> cluster on the far right (long advance planning). <strong>Corporate and Bleisure</strong> peak early (3–15 days). <strong>Digital Nomad</strong> shows a flat distribution — flexible, no fixed departure plan. Dotted lines mark key thresholds: 3d (Last-Minute), 14d (Corporate), 60d (OFW/Balikbayan).</div>
    </div>
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Fare per PAX — All 10 Segments</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['25_fare_per_pax_all_segments']}" alt="Fare per PAX">
      <div class="chart-insight"><strong>Corporate</strong> median fare is 3–4× all other segments — a near-clean separator. <strong>OFW</strong> shows wide variance reflecting both short Middle East hops and long North America routes. <strong>Budget/Adventure</strong> sits at the bottom with minimal spread, confirming its price-ceiling behavior.</div>
    </div>
  </div>

  <!-- heatmaps -->
  <h3 style="margin:2rem 0 1rem;font-size:.85rem;color:var(--grey);text-transform:uppercase;letter-spacing:.1em">Feature Mix Heatmaps</h3>
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Ticketing Channel Mix by Segment (%)</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['26_segment_channel_heatmap']}" alt="Channel Heatmap">
      <div class="chart-insight">Channel mix cleanly differentiates segments. <strong>Pilgrimage</strong> is 100% TTA (by definition of the proxy). <strong>OFW</strong> is TTA-dominant. <strong>Corporate</strong> and <strong>Digital Nomad</strong> are WEB/APP-dominant. <strong>Last-Minute</strong> spikes on Contact Center and Ticket Office — urgency walk-ins.</div>
    </div>
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Geographic Region Mix by Segment (%)</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['27_segment_region_heatmap']}" alt="Region Heatmap">
      <div class="chart-insight"><strong>OFW</strong> is almost entirely Middle East. <strong>Corporate</strong> is ASEAN-dominant (72%). <strong>Balikbayan</strong> spreads across North America, Middle East, and Australasia — the diaspora origin markets. <strong>Budget/Adventure and Family</strong> are MNL HUB domestic-heavy. <strong>Digital Nomad</strong> is 100% ASEAN by proxy definition.</div>
    </div>
  </div>
  <div class="charts-grid single">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Farebrand Mix by Segment (%)</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['28_segment_farebrand_heatmap']}" alt="Farebrand Heatmap">
      <div class="chart-insight">Farebrand provides clear segment-level signals. <strong>Corporate</strong> is 100% Business (by cabin definition). <strong>Budget/Adventure</strong> is 100% Economy Supersaver/Saver. <strong>Family and Pilgrimage</strong> spread across Saver/Value/Flex. <strong>Digital Nomad</strong> is concentrated in Economy Value/Flex — needs flexibility without full premium price.</div>
    </div>
  </div>

  <!-- booking month + pax count -->
  <h3 style="margin:2rem 0 1rem;font-size:.85rem;color:var(--grey);text-transform:uppercase;letter-spacing:.1em">Seasonality & Group Patterns</h3>
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">PNR Booking Month by Segment (All Jan 2025 flights)</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['29_booking_month_by_segment']}" alt="Booking Month">
      <div class="chart-insight">Reveals planning horizons by segment. <strong>Budget/Adventure</strong> peaks in January (same-month promo hunters) and December (early planners for the month ahead). <strong>OFW and Balikbayan</strong> show a broad lead with a November–December booking surge. <strong>Digital Nomad</strong> books steadily throughout the year — no seasonal spike, consistent with year-round remote work travel.</div>
    </div>
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">PAX Count Distribution by Segment</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['30_pax_count_by_segment']}" alt="PAX Count">
      <div class="chart-insight"><strong>Corporate and Digital Nomad</strong> are overwhelmingly solo (PAX=1). <strong>Pilgrimage</strong> is skewed toward larger groups (4–8 PAX) by proxy definition, but the actual spread confirms real group travel. <strong>Family</strong> clusters at 3–4 PAX as expected. <strong>OFW</strong> is mostly solo with occasional couples — OFWs traveling to reunite with family abroad.</div>
    </div>
  </div>

  <!-- new segment deep dives -->
  <h3 style="margin:2rem 0 1rem;font-size:.85rem;color:var(--grey);text-transform:uppercase;letter-spacing:.1em">New Segment Deep Dives</h3>
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title" style="color:#F97316">Pilgrimage / Religious Traveler — Deep Dive</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['31_pilgrimage_deep_dive']}" alt="Pilgrimage">
      <div class="chart-insight">The Pilgrimage proxy (n=575, PAX≥4 + TTA) shows: <strong>heaviest booking in Nov–Dec</strong> for January travel (consistent with Christmas/New Year pilgrimages). Top sectors are <strong>BCDMNL and MNLBCD</strong> — domestic group travel likely for regional parish pilgrimages and group tours. The booking month analysis shows a <strong>March–April spike</strong> that aligns with the Holy Week booking window. Group size peaks at 4–6 passengers — typical parish tour group size.</div>
    </div>
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title" style="color:#06B6D4">Family Vacation Traveler — Deep Dive</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['32_family_deep_dive']}" alt="Family">
      <div class="chart-insight">The Family proxy (n=2,235, PAX 3–5) shows: <strong>November–December peak bookings</strong> — families planning Christmas travel. <strong>MNL HUB dominates</strong> (82%) — mostly domestic family travel. <strong>WEB/APP and TTA channels are near equal</strong> — younger parents book online, older families use agents. This segment has the most balanced channel mix of all 10, making channel alone insufficient for classification.</div>
    </div>
  </div>
  <div class="charts-grid single">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title" style="color:#A78BFA">Digital Nomad / Remote Worker — Deep Dive</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['33_digital_nomad_deep_dive']}" alt="Digital Nomad">
      <div class="chart-insight">The Digital Nomad proxy (n=165, solo + ASEAN + WEB/APP + Economy Flex/Value) is the smallest identifiable segment in current data — <strong>undercount is expected</strong> since Length of Stay (the strongest nomad signal) is 100% null. Top route is <strong>MNL→BKK and BKK→MNL</strong> (Bangkok as primary ASEAN nomad hub from Manila). Median lead time of 21 days is shorter than leisure but longer than Corporate, consistent with flexible planning. This segment will expand significantly once LOS data is added.</div>
    </div>
  </div>

  <!-- radar + unassigned -->
  <h3 style="margin:2rem 0 1rem;font-size:.85rem;color:var(--grey);text-transform:uppercase;letter-spacing:.1em">Segment Fingerprints & Gap Analysis</h3>
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Segment Radar Fingerprints — 5 Dimensions</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['34_segment_radar_fingerprints']}" alt="Radar">
      <div class="chart-insight">Each radar shows a segment's normalized profile across: <strong>Fare/PAX · Lead Time · Group Size · International % · Flex Fare %</strong>. <strong>Corporate</strong> has a large Fare + Intl + Flex footprint. <strong>OFW</strong> shows high Lead + Intl with low Flex. <strong>Balikbayan</strong> shows high Group + Intl. <strong>Budget/Adventure</strong> is uniformly flat — the "plain" traveler. These fingerprints directly correspond to the feature dimensions the KNN/DBSCAN clustering will use.</div>
    </div>
    <div class="chart-card">
      <div class="chart-header"><div class="chart-title">Unassigned Records — Gap Analysis</div></div>
      <img class="chart-img" src="data:image/png;base64,{imgs['35_unassigned_analysis']}" alt="Unassigned">
      <div class="chart-insight">23.6% of records (7,084) remain unassigned under the current proxy logic — these are the records most in need of Loyalty status and Length of Stay. Their farebrand spread (Economy Value + Flex dominant) and wide lead time distribution suggest they are a mix of <strong>Mabuhay Loyalists, Digital Nomads, and occasional Corporate travelers</strong> who booked Economy. Once blocking features are provided, this unassigned pool should collapse significantly.</div>
    </div>
  </div>
</div>

<!-- ── 05 COMPOSITION ── -->
<div class="divider"></div>
<div class="section" id="composition">
  <div class="section-header">
    <span class="section-tag">04 · Dataset Composition</span>
    <h2>Who's Flying?</h2>
    <p>Breakdown of the booking population across entity, region, cabin, farebrand, and itinerary type.</p>
  </div>
  {chart_grid([1,2,3,4,6])}
</div>

<!-- ── 05 FARE ── -->
<div class="divider"></div>
<div class="section" id="fare">
  <div class="section-header">
    <span class="section-tag">05 · Revenue &amp; Fare Analysis</span>
    <h2>What Are Passengers Paying?</h2>
    <p>Fare signals that underpin the asymmetric cost matrix and segment revenue stratification.</p>
  </div>
  {chart_grid([7,8,9])}
  <div class="callout">
    <h3>💡 Revenue Stratification Across 10 Segments</h3>
    <p>
      The ~$286 average fare gap between Business and Economy validates the <strong style="color:var(--gold)">×10 Corporate penalty</strong>.
      However, the North America fare (~$778) also confirms that <strong style="color:var(--white)">Balikbayan/VFR</strong> passengers —
      despite a lower penalty weight (×2) — represent significant revenue on a per-route basis.
      The emerging <strong style="color:var(--white)">Digital Nomad</strong> segment, once identifiable via Length of Stay,
      is expected to cluster in the $150–$300 range with high repeat-booking frequency — making it a high-CLV growth segment.
    </p>
  </div>
</div>

<!-- ── 06 BOOKING ── -->
<div class="divider"></div>
<div class="section" id="booking">
  <div class="section-header">
    <span class="section-tag">06 · Booking Behaviour</span>
    <h2>How &amp; When Do Passengers Book?</h2>
    <p>Lead time, group size, and day-of-week patterns that are primary differentiators across all 10 segments.</p>
  </div>
  {chart_grid([10,11,12,13])}
</div>

<!-- ── 07 CHANNELS ── -->
<div class="divider"></div>
<div class="section" id="channels">
  <div class="section-header">
    <span class="section-tag">07 · Channel Analysis</span>
    <h2>How Passengers Reach PAL</h2>
    <p>Ticketing channel is one of the highest-signal features in the dataset — it alone can narrow a record from 10 candidate segments to 2–3.</p>
  </div>
  {chart_grid([5,14,18])}
</div>

<!-- ── 08 ROUTES ── -->
<div class="divider"></div>
<div class="section" id="routes">
  <div class="section-header">
    <span class="section-tag">08 · Route &amp; O&amp;D Analysis</span>
    <h2>Where Passengers Fly</h2>
    <p>O&amp;D sector concentration and its implications for model generalisation across PAL's network.</p>
  </div>
  {chart_grid([19], single=True)}
</div>

<!-- ── 09 MODELLING ── -->
<div class="divider"></div>
<div class="section" id="model">
  <div class="section-header">
    <span class="section-tag">09 · Modelling Readiness</span>
    <h2>Negative Learning Rules (Enhanced)</h2>
    <p>9 proposed impossibility rules — 3 new rules added for Family, Pilgrimage, and Digital Nomad segments based on available features.</p>
  </div>
  <table class="nl-table">
    <thead><tr><th>Condition</th><th>Ruled-Out / Narrowed To</th><th>Feature Coverage</th><th>Blocked By</th></tr></thead>
    <tbody>{nl_rows()}</tbody>
  </table>
  <br>
  {chart_grid([20], single=True)}
  <div class="callout" style="margin-top:1.5rem">
    <h3>📈 Segment Proxy Signal Summary</h3>
    <p>
      The charts below show how proxy records for each segment separate cleanly on lead time (KDE) and fare per PAX (boxplot).
      These two features alone produce strong visual cluster separation — the ML model should be able to exploit them
      as primary dimensions before richer features like Loyalty status and Length of Stay are added.
    </p>
  </div>
  {chart_grid([15,16,17])}
</div>

<!-- ── 10 MISSING DATA ── -->
<div class="divider"></div>
<div class="section" id="missing">
  <div class="section-header">
    <span class="section-tag">10 · Data Recommendations</span>
    <h2>Features to Request from PAL</h2>
    <p>Prioritised list of features absent from the sample dataset, with source system and segment impact.</p>
  </div>
  <div class="missing-list">{missing_items_html()}</div>
  <br>
  {chart_grid([21], single=True)}
  <div class="callout" style="margin-top:1.5rem">
    <h3>🚀 Recommended Next Steps</h3>
    <p>
      <strong style="color:var(--gold)">1.</strong> Request <strong style="color:var(--white)">Loyalty status + Mabuhay Miles tier</strong>
      from the loyalty DB — unblocks 4 of 9 Negative Learning rules and enables the Mabuhay Loyalist segment entirely.<br><br>
      <strong style="color:var(--gold)">2.</strong> Source <strong style="color:var(--white)">Length of Stay</strong>
      by joining return PNRs — differentiates Corporate (&lt;4d), Bleisure (5–14d), Balikbayan (14d+), and Digital Nomad (30d+).<br><br>
      <strong style="color:var(--gold)">3.</strong> Append <strong style="color:var(--white)">Departure Time</strong>
      from PAL's flight schedule — zero collection cost, adds early-AM Corporate signal immediately.<br><br>
      <strong style="color:var(--gold)">4.</strong> Engineer <strong style="color:var(--white)">9 derived features</strong>
      (lead bucket, group flag, promo flag, ME corridor, beyond itinerary, holiday season, fare per PAX, is-solo, is-TMC)
      from existing columns — no additional data required and directly usable in 3 of the 9 Negative Learning rules today.
    </p>
  </div>
</div>

<!-- FOOTER -->
<footer>
  <div style="font-size:2rem;margin-bottom:.5rem">✈</div>
  <p><strong>PAL Customer Segmentation — Exploratory Data Analysis Report</strong></p>
  <p style="margin-top:.4rem">CPT 3 · Edyll Joshua Binaday · Jeremy Jay Lim · Arien Jadd Versoza · Martin Aloysius Yamzon (PL)</p>
  <p style="margin-top:.4rem">April 2026 · <em>Confidential — For Philippine Airlines internal use only</em></p>
  <p style="margin-top:.8rem;font-size:.7rem;color:rgba(148,163,184,.5)">
    Research sources: Expert Journal of Marketing (Lufthansa segments) · IATA Trip-Purpose Framework ·
    Sabre Customer Segmentation for Airline Marketing · Precedence Research (Bleisure Market) ·
    Future Market Insights (Asia Pacific Religious Tourism) · NomadStays (Digital Nomad Statistics 2025)
  </p>
</footer>

<script>
const sections = document.querySelectorAll('[id]');
const navLinks = document.querySelectorAll('.nav-links a');
const obs = new IntersectionObserver(entries => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      navLinks.forEach(a => a.classList.remove('active'));
      const a = document.querySelector(`.nav-links a[href="#${{e.target.id}}"]`);
      if (a) a.classList.add('active');
    }}
  }});
}}, {{rootMargin:'-40% 0px -55% 0px'}});
sections.forEach(s => obs.observe(s));
</script>
</body>
</html>"""

REPORT_PATH.write_text(HTML, encoding="utf-8")
print(f"Report saved → {REPORT_PATH}  ({REPORT_PATH.stat().st_size/1024:.0f} KB)")
