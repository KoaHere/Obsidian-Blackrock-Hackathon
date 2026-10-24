Here's the plan. The idea is that one student profile feeds all five features, so the demo tells a single story: here's your loan, here's what small habits become, here's your retirement, and here's real market data behind it.

Two corrections before we build

1. HMRC isn't a market data source. HMRC publishes tax, NI and student loan thresholds, but nothing on stock prices. Split feature 5 into two jobs:

Policy numbers (thresholds, rates): these are on gov.uk, and we already seed them from seed.py. A live fetch is optional, and a seeded table is safer for a demo.
Market numbers (returns and volatility): use yfinance for historical prices of iShares ETFs. That's BlackRock's own product range, so it's a good hook. Inflation can come from ONS data. I'd confirm the tickers and endpoints when we build it.

2. You're in Glasgow, so Scottish students are on Plan 4, which calc.py doesn't have yet. The 2026/27 threshold is £33,795 at 9%, and I'll add it and verify its interest rule before we demo.

How it fits together
app.py: Streamlit dashboard with a sidebar profile (plan, loan, salary, spare £/month, return assumption) shared by every tab via st.session_state.
calc.py: the maths we already have, plus a retirement module.
market.py: API calls plus an SQLite cache.
charts.py: Plotly figures.
SQLite tables: loan_plans (done), scenarios (saved profiles) and market_cache (last good API result with a timestamp).

The cache matters because hackathon wifi is unreliable. If the API fails mid-demo, the app quietly uses the last stored data and labels it "as of [date]".

The five features

Feature 1: Future You compounding visualiser

The user sees: a slider for £/month and a curve showing the pot at 30, 40 and 60, split into "what you put in" and "growth".
Under the hood: growth_curve() compounds monthly. We show low/mid/high return scenarios (say 3%, 5%, 7%) as a band, never a single promised number, plus a "today's money" toggle that deflates for inflation.
Pitch line: "£20 a month feels like nothing. Here's the curve that says otherwise."

Feature 2: Investment scaling visual (my interpretation, please confirm)

The user sees: a heatmap of final pot size against monthly amount and years invested, plus a "relatable ladder" such as "your weekly takeaway budget, invested, becomes this."
Under the hood: the same future_value() run across a grid.
Pitch line: "Time matters more than amount. Starting at 20 beats doubling your contribution at 30."

Feature 3: Retirement calculation

The user sees: a target retirement age, an estimated pot, and an estimated annual income in today's money, including the state pension.
Under the hood: contributions grow until retirement, then a drawdown assumption (e.g. 4% a year) converts the pot to income. We add auto-enrolment (the minimum is split between employee and employer) and the state pension, with figures pulled from gov.uk and flagged "verify".
Pitch line: "Retirement feels abstract at 20. This turns it into a monthly income figure."

Feature 4: Student loan reality check

The user sees: monthly repayment, total repaid, total written off, and the verdict on overpaying vs investing.
Under the hood: simulate_loan() and compare_overpay_vs_invest(). The key insight is that for many graduates the loan is mostly written off, so overpaying wastes money.
Pitch line: "Most students are never told their loan behaves more like a graduate tax than a debt."

Feature 5: Real market data

The user sees: a "backtest" of what £50/month would have become in a real iShares fund since 2010, and a "use real historical return" button that fills the return slider.
Under the hood: market.py fetches prices, computes annualised return and volatility, and writes them to market_cache.
Pitch line: "Our assumptions aren't made up. Here's what actually happened."
Build order (in case time is short)
Shared sidebar profile and Feature 1 (this alone is a demoable product)
Feature 4, which is our differentiator and the logic is already written
Feature 2 (cheap, since it reuses the maths)
Feature 3
Feature 5, last, with the cache so it can't break the demo
Suggested 2-minute demo

Start with one persona (a second-year with a £45k loan). Show the loan reality check, then ask what happens if they invest £100/month instead. Move to the compounding curve, the retirement income number, and finish on the real-data backtest. End with the guardrails slide: projections are illustrative, not advice, and ranges are shown instead of single outcomes. Finance judges notice that.

One question to settle before I build: is my reading of Feature 2 (heatmap plus relatable ladder) what you had in mind, or did you mean something different, like comparing several investment types? Once you confirm, I'll start on app.py with the shared profile and Feature 1.

If you'd like this plan as a shareable doc for your team, I can put it in one.
