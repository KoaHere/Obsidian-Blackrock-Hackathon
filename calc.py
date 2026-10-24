"""
calc.py - pure functions for UK student loan repayment + investment growth.

No Streamlit, no database: everything takes plain numbers and returns plain
data, so it is easy to unit test and to sanity-check before the demo.

All money is in GBP. All rates are annual decimals (0.09 == 9%).

Policy figures below were checked against GOV.UK / HMRC announcements for
2026/27 (threshold figures, 10 Aug 2026 interest rate update). They change
every year, so in the real app load them from the `loan_plans` table (seed.py)
and re-verify on gov.uk before presenting.
"""

from dataclasses import dataclass
from typing import Optional


# --------------------------------------------------------------------------
# Plan definitions (2026/27 figures)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class LoanPlan:
    name: str
    threshold: float              # annual repayment threshold (2026/27)
    repayment_rate: float         # share of income ABOVE threshold
    write_off_years: int          # years after repayment starts
    rpi_margin_max: float         # extra interest on top of RPI at high income
    interest_cap: Optional[float] # max annual interest rate (None = no cap)
    income_upper: Optional[float] = None  # income at which max margin applies


PLANS = {
    "Plan 2": LoanPlan(
        name="Plan 2",
        threshold=29_385,
        repayment_rate=0.09,
        write_off_years=30,
        rpi_margin_max=0.03,
        interest_cap=0.06,         # cap applies Sep 2026 - Aug 2027 only
        income_upper=52_000,       # APPROXIMATE - verify on gov.uk
    ),
    "Plan 5": LoanPlan(
        name="Plan 5",
        threshold=25_000,
        repayment_rate=0.09,
        write_off_years=40,
        rpi_margin_max=0.0,        # RPI only
        interest_cap=None,
    ),
    "Postgraduate": LoanPlan(
        name="Postgraduate",
        threshold=21_000,
        repayment_rate=0.06,
        write_off_years=30,
        rpi_margin_max=0.03,       # RPI + 3% flat
        interest_cap=0.06,
        income_upper=21_000,       # margin is flat, not income-linked
    ),
}

CURRENT_RPI = 0.041  # 4.1%, Sep 2026 - Aug 2027 (year 1 of the simulation)
LONG_RUN_RPI = 0.03  # assumption used for every year after year 1


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def loan_interest_rate(plan: LoanPlan, salary: float, rpi: float = CURRENT_RPI,
                       threshold: Optional[float] = None,
                       apply_cap: bool = True) -> float:
    """Annual interest rate on the loan for a given salary."""
    threshold = plan.threshold if threshold is None else threshold

    if plan.rpi_margin_max == 0:
        rate = rpi
    elif plan.name == "Postgraduate":
        rate = rpi + plan.rpi_margin_max
    else:
        # Sliding scale: RPI at/below threshold, RPI+margin at/above upper.
        span = max((plan.income_upper or threshold) - threshold, 1)
        share = min(max((salary - threshold) / span, 0.0), 1.0)
        rate = rpi + share * plan.rpi_margin_max

    if apply_cap and plan.interest_cap is not None:
        rate = min(rate, plan.interest_cap)
    return rate


def monthly_mandatory_repayment(plan: LoanPlan, salary: float,
                                threshold: Optional[float] = None) -> float:
    """Repayment taken through PAYE: rate x (salary - threshold) / 12."""
    threshold = plan.threshold if threshold is None else threshold
    return max(0.0, salary - threshold) * plan.repayment_rate / 12


def future_value(monthly: float, annual_return: float, years: float,
                 initial: float = 0.0) -> float:
    """Value of a pot with a fixed monthly contribution, compounded monthly."""
    r = annual_return / 12
    n = int(round(years * 12))
    if r == 0:
        return initial + monthly * n
    growth = (1 + r) ** n
    return initial * growth + monthly * (growth - 1) / r


def growth_curve(monthly: float, annual_return: float, years: int,
                 initial: float = 0.0) -> list[dict]:
    """Year-by-year pot for charting: contributions vs growth."""
    rows = []
    for y in range(years + 1):
        value = future_value(monthly, annual_return, y, initial)
        contributed = initial + monthly * 12 * y
        rows.append({
            "year": y,
            "value": value,
            "contributed": contributed,
            "growth": value - contributed,
        })
    return rows


def to_real(amount: float, years: float, inflation: float) -> float:
    """Convert a future nominal amount into today's money."""
    return amount / ((1 + inflation) ** years)


# --------------------------------------------------------------------------
# Loan simulation
# --------------------------------------------------------------------------

def simulate_loan(
    plan: LoanPlan,
    balance: float,
    starting_salary: float,
    salary_growth: float = 0.035,
    rpi: float = CURRENT_RPI,
    voluntary_monthly: float = 0.0,
    max_years: Optional[int] = None,
    long_run_rpi: float = LONG_RUN_RPI,
) -> dict:
    """
    Month-by-month loan simulation from the first repayment month.

    - Salary grows each year by `salary_growth`.
    - Year 1 uses `rpi` (current) and the temporary interest cap; later years
      use `long_run_rpi` with no cap.
    - Threshold grows each year with `long_run_rpi` (Plan 2/5 rise with RPI).
    - Interest accrues monthly at the plan's rate for that salary.
    - Mandatory repayment = rate x income above threshold.
    - Voluntary overpayments (if any) are paid on top, until balance is zero.
    - Any balance left at the write-off date is cancelled.

    Returns a dict with a yearly timeline and summary totals.
    """
    years = max_years or plan.write_off_years
    years = min(years, plan.write_off_years)

    salary = starting_salary
    threshold = plan.threshold
    bal = balance

    total_mandatory = 0.0
    total_voluntary = 0.0
    total_interest = 0.0
    cleared_month = None
    timeline = [{"year": 0, "balance": bal, "salary": salary,
                 "paid_to_date": 0.0}]

    for m in range(1, years * 12 + 1):
        if bal > 0:
            first_year = m <= 12
            rate = loan_interest_rate(plan, salary,
                                      rpi if first_year else long_run_rpi,
                                      threshold, apply_cap=first_year)
            interest = bal * rate / 12
            bal += interest
            total_interest += interest

            mandatory = min(bal, monthly_mandatory_repayment(plan, salary,
                                                            threshold))
            bal -= mandatory
            total_mandatory += mandatory

            voluntary = min(bal, voluntary_monthly)
            bal -= voluntary
            total_voluntary += voluntary

            if bal <= 0.005:
                bal = 0.0
                cleared_month = cleared_month or m

        if m % 12 == 0:
            salary *= 1 + salary_growth
            threshold *= 1 + long_run_rpi
            timeline.append({
                "year": m // 12,
                "balance": bal,
                "salary": salary,
                "paid_to_date": total_mandatory + total_voluntary,
            })

    written_off = bal  # whatever remains is cancelled at the end
    return {
        "timeline": timeline,
        "total_paid": total_mandatory + total_voluntary,
        "total_mandatory": total_mandatory,
        "total_voluntary": total_voluntary,
        "total_interest": total_interest,
        "cleared_month": cleared_month,
        "cleared_year": (cleared_month / 12) if cleared_month else None,
        "written_off": written_off,
        "repaid_in_full": cleared_month is not None,
    }


# --------------------------------------------------------------------------
# The headline comparison: overpay the loan vs invest the same money
# --------------------------------------------------------------------------

def compare_overpay_vs_invest(
    plan: LoanPlan,
    balance: float,
    starting_salary: float,
    spare_monthly: float,
    annual_return: float = 0.06,
    salary_growth: float = 0.035,
    rpi: float = CURRENT_RPI,
    inflation: float = 0.025,
    horizon_years: Optional[int] = None,
) -> dict:
    """
    Same spare cash every month, two strategies:

      A) Overpay: spare cash goes to the loan until it is cleared, then is
         invested for the rest of the horizon.
      B) Invest: spare cash is invested from day one; only mandatory PAYE
         repayments hit the loan.

    Compared on net position = investment pot - total paid to the loan.
    Both use identical monthly outlay while A still has a balance, so the
    comparison is like for like.
    """
    horizon = horizon_years or plan.write_off_years
    horizon = min(horizon, plan.write_off_years)
    r_m = annual_return / 12

    # --- B: invest from day one -------------------------------------------
    loan_b = simulate_loan(plan, balance, starting_salary, salary_growth,
                           rpi, voluntary_monthly=0.0, max_years=horizon)
    pot_b = future_value(spare_monthly, annual_return, horizon)

    # --- A: overpay, then invest the freed-up cash ------------------------
    loan_a = simulate_loan(plan, balance, starting_salary, salary_growth,
                           rpi, voluntary_monthly=spare_monthly,
                           max_years=horizon)
    pot_a = 0.0
    months_overpaying = (loan_a["cleared_month"] or horizon * 12)
    for m in range(1, horizon * 12 + 1):
        pot_a *= 1 + r_m
        if m > months_overpaying:
            pot_a += spare_monthly

    net_a = pot_a - loan_a["total_paid"]
    net_b = pot_b - loan_b["total_paid"]
    advantage = net_b - net_a  # positive => investing wins

    return {
        "horizon_years": horizon,
        "overpay": {**loan_a, "pot": pot_a, "net_position": net_a},
        "invest": {**loan_b, "pot": pot_b, "net_position": net_b},
        "invest_advantage": advantage,
        "invest_advantage_real": to_real(advantage, horizon, inflation),
        "winner": "invest" if advantage > 0 else "overpay",
    }


# --------------------------------------------------------------------------
# Quick self-check:  python calc.py
# --------------------------------------------------------------------------

if __name__ == "__main__":
    # 1) Compounding sanity check: GBP 20/month at 6% for 40 years
    print("GBP 20/month, 6%, 40y:",
          round(future_value(20, 0.06, 40)))  # ~ 39,800

    # 2) Mandatory repayment: Plan 2, GBP 40k salary -> 9% of (40,000-29,385)
    print("Plan 2 @ 40k, monthly:",
          round(monthly_mandatory_repayment(PLANS["Plan 2"], 40_000), 2))

    # 3) Typical Plan 5 graduate
    p5 = PLANS["Plan 5"]
    res = compare_overpay_vs_invest(
        p5, balance=45_000, starting_salary=30_000,
        spare_monthly=100, annual_return=0.06, horizon_years=40)
    print(f"\nPlan 5, GBP 45k loan, GBP 30k start, GBP 100/month spare:")
    print(f"  Overpay net position: GBP {res['overpay']['net_position']:,.0f}")
    print(f"  Invest net position:  GBP {res['invest']['net_position']:,.0f}")
    print(f"  Winner: {res['winner']} "
          f"(GBP {abs(res['invest_advantage']):,.0f} nominal)")