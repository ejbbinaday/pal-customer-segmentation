# Draft email to PAL — 18 August 2026

Two things need an answer and one is a contradiction we should not resolve on our own. Draft below;
edit the tone to suit the relationship. **Deliberately short** — it asks two questions and makes one
offer, and nothing else.

---

**To:** RM Domestic · RM International
**Cc:** Commercial, Data Analytics
**Subject:** Two quick things on the segmentation rules — one contradiction, one timing question

Hi both,

Thank you for turning the whole question sheet around so quickly, and for answering all 24. Having your
answers in the same file we sent made them straightforward to apply, and almost everything is now in
place. Two items need you.

**1. The Mecca seasonality rule contradicts a decision from the day before, and we would rather ask
than guess.**

You told us Mecca traffic runs outbound from Manila in May and returns in June. That is genuinely useful
and we have written it down.

The difficulty is that it is a rule about *departure month*, and the day before you had agreed we should
stop using departure month in rules (item C8, where we set aside five of your seasonal rules).

The reason for that is worth restating, because it is not arbitrary. To check whether our segments are
*correct*, we need a few facts about a booking that the rules never looked at — otherwise we are just
confirming our own rules with themselves. We are down to two such facts, and departure month is one of
them. Every rule that uses it costs us the ability to check our own work.

So: **which would you prefer?**

- **(a) Leave the Mecca seasonality out** and keep departure month as an independent check. Pilgrimage
  is already identified by destination (Jeddah/Medina), so we would lose the seasonal refinement but not
  the segment. *This is our recommendation.*
- **(b) Use it**, and accept that we can no longer independently verify segment accuracy on a
  seasonal basis. We would say so plainly in the methodology rather than quietly.

Either is workable. We just should not decide it for you.

**2. When can we expect the four new fields?**

Data Analytics is scraping `FarebasisCode`, `Isupgrade`, `IsTourCode`, `IsFrequentFlyer` and loyalty
tier. Even a rough date helps us sequence, because two of them are unusually load-bearing:

- **`FarebasisCode`** settles an open question on our best finding. Manila–Gulf traffic shows a real
  one-month travel rhythm, which you attributed to employer-mandated leave. But if Gulf economy fares
  carry a one-month maximum-stay condition, the fare rule produces exactly the same pattern. We cannot
  tell those apart without the fare basis — and which one it is decides whether the rule holds up
  elsewhere.
- **`IsFrequentFlyer`** is probably a *stronger* signal than anything we currently have for separating
  overseas workers from Filipinos coming home to visit family. That is the weakest boundary in the model
  today, so this field matters more than its size suggests.

**And one thing you do not need to do yet.**

On the cost of getting each segment wrong — you said "see run first", which is fair. We have put
together a proposed set of weights from your own booking data plus published airline revenue-management
and customer-value research, so there is something concrete to react to rather than a blank form. We
will bring it when we show you the model running. **Two notes on it in advance:**

- Revenue is now confirmed as USD, which lets us quote a real figure for the first time: **the annual
  value at risk per customer ranges from about $495 to $9,800 across segments** — a twentyfold spread.
- Two of the weights we are proposing *disagree with the measurement on purpose*, and we will show you
  why. Mabuhay Loyalist measures as our lowest-value segment purely because we can only see award
  redemptions, not membership. That is a gap in our data, not a fact about your loyalty programme, and we
  have kept the weight high to reflect that.

Thanks again,
[name]

---

## Notes for us, not for the email

**Kept out on purpose:**

- **The Family and Digital Nomad deletions.** Both were their call, both are already applied. Reopening
  them in the same email that asks two questions invites a renegotiation we do not want.
- **The `Budget/Adventure` → `Leisure` rename cost.** It reverses our own Monday position; it is our
  cost to absorb, not their problem.
- **The route-direction correction.** They were right and we have already applied it. Saying so at length
  would read as defensive.
- **The 21.8%-of-labels-change figure.** Belongs in the meeting where the model is shown, with the
  before/after in front of them — not in a text-only email where it will alarm without context.

**The framing to hold onto for item 1.** The temptation is to present the anchor as a technical
constraint. It is not — it is the difference between *"our segments agree with our rules"* and *"our
segments agree with reality"*. Every rule that spends a check makes the accuracy number weaker, and PAL
has consistently asked how accurate this is. That is why the choice is theirs.
