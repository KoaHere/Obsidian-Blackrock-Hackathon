"""app.py - server-rendered, no JavaScript.
Run:  pip install flask && python seed.py && python app.py   ->  http://127.0.0.1:5000
Your profile lives in a signed cookie, so every tab prefills from it."""
import os
from flask import Flask, request, session, redirect
import calc
import seed

class LoanPlan:
    def __init__(
        self, name, threshold, repayment_rate, write_off_years,
        rpi_margin_max=0.0, interest_cap=None, income_upper=None
    ):
        self.name = name
        self.threshold = threshold
        self.repayment_rate = repayment_rate
        self.write_off_years = write_off_years
        self.rpi_margin_max = rpi_margin_max
        self.interest_cap = interest_cap
        self.income_upper = income_upper

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

D = dict(age=20, monthly=20, real=1, income=900, rent=450, food=160, transport=40, subs=35,
         out=80, course=30, other=40, salary=28000, ret=67, emp=5.0, er=3.0, pot=0,
         plan="Plan 4", bal=45000, growth=4.0, rpi=3.5, extra=100)
BUD = [("rent", "Rent and bills"), ("food", "Food"), ("transport", "Transport"),
       ("subs", "Phone and subscriptions"), ("out", "Going out"), ("course", "Course costs"), ("other", "Other")]
COL = ["#0f7b6c", "#e8a33d", "#c8553d", "#6a8fd8", "#a06bc7", "#7aa35a", "#8a8a8a"]
TABS = [("growth", "Growth curve"), ("budget", "Budget"), ("retire", "Retirement"), ("loan", "Student loan")]
STATE_PENSION = 241.30  # £/week 2026/27 - VERIFY on gov.uk
f = lambda n: ("-" if n < 0 else "") + "£" + f"{abs(n):,.0f}"


def prof():
    return {**D, **session.get("p", {})}


def save():
    p = prof()
    for k, d in D.items():
        if k in request.form:
            v = request.form[k]
            try:
                p[k] = v if isinstance(d, str) else max(0, int(float(v)) if isinstance(d, int) else float(v))
            except ValueError:
                pass
    session["p"] = p


def num(label, k, p, step=1):
    return f'<div><label for="{k}">{label}</label><input id="{k}" name="{k}" type="number" step="{step}" value="{p[k]}"></div>'


def sel(label, k, p, opts):
    o = "".join(f'<option value="{v}"{" selected" if str(p[k]) == str(v) else ""}>{t}</option>' for v, t in opts)
    return f'<div><label for="{k}">{label}</label><select id="{k}" name="{k}">{o}</select></div>'


def kp(label, val):
    return f"<div><small>{label}</small><span class=big>{val}</span></div>"


def form(fields):
    return f'<form method=post><div class=row>{fields}</div><button>Save and update</button></form>'


def growth(p):
    a, real = p["age"], bool(p["real"])
    months = max(12, (65 - a) * 12)
    S = [calc.growth_curve(p["monthly"], r, months, real) for r in (.03, .05, .07)]
    W, H, L, B = 640, 300, 60, 26
    mx = (max(x[1] for x in S[2]) * 1.05) or 1
    X = lambda m: L + m / months * (W - L - 10)
    Y = lambda v: 12 + (1 - v / mx) * (H - 12 - B)
    pts = lambda s, k: [f"{X(r[0]):.1f},{Y(r[k]):.1f}" for r in s]
    svg = f'<svg viewBox="0 0 {W} {H}" role=img aria-label="Pot growth by age">'
    for k in range(5):
        v = mx * k / 4
        svg += f'<line x1={L} x2={W-10} y1={Y(v):.0f} y2={Y(v):.0f} stroke="var(--line)"/><text x=4 y={Y(v)+4:.0f}>{f(v)}</text>'
    svg += f'<polygon points="{" ".join(pts(S[2],1)+pts(S[0],1)[::-1])}" fill="var(--band)"/>'
    svg += f'<polyline points="{" ".join(pts(S[0],2))}" fill=none stroke="var(--b)" stroke-width=2.5 stroke-dasharray="6 4"/>'
    svg += f'<polyline points="{" ".join(pts(S[1],1))}" fill=none stroke="var(--a)" stroke-width=3 />'
    rows = "<tr><th>Age</th><th>You put in</th><th>Growth (mid)</th><th>Range, low to high</th></tr>"
    for g in (30, 40, 60):
        i = (g - a) * 12 - 1
        if g > a and i < len(S[1]):
            svg += f'<line x1={X(i+1):.0f} x2={X(i+1):.0f} y1=12 y2={H-B} stroke="var(--ink)" stroke-dasharray="2 3"/><text x={X(i+1)-8:.0f} y={H-8}>{g}</text>'
            rows += f"<tr><td>{g}</td><td>{f(S[1][i][2])}</td><td>{f(S[1][i][1]-S[1][i][2])}</td><td><b>{f(S[0][i][1])} to {f(S[2][i][1])}</b></td></tr>"
    svg += f'<text x={L+6} y=26>Shaded: 3% to 7%. Solid: 5%. Dashed: what you put in.</text></svg>'
    return (form(num("Monthly saving (£)", "monthly", p, 5) + num("Your age", "age", p) +
                 sel("Show in", "real", p, [(1, "Today’s money"), (0, "Future money")])) + svg +
            f"<table>{rows}</table><p class=note>3%, 5% and 7% a year, compounded monthly, before fees. "
            "Real returns vary and can be negative. Today’s money deflates at 2.5% a year.</p>")


def budget(p):
    inc = p["income"]
    sp = [p[k] for k, _ in BUD]
    tot = sum(sp)
    left = inc - tot
    den = max(inc, tot) or 1
    bar = "".join(f'<div style="width:{v/den*100:.1f}%;background:{COL[i]}"></div>' for i, v in enumerate(sp))
    bar += f'<div style="flex:1;background:var(--line)"></div>' if left > 0 else ""
    leg = "".join(f'<div class=leg><span><i class=dot style="background:{COL[i]}"></i>{n}</span>'
                  f'<b>{f(p[k])} ({p[k]/inc*100 if inc else 0:.0f}%)</b></div>' for i, (k, n) in enumerate(BUD))
    tip = (f"Left over {f(left)} a month, invested from 20 to 65 at a mid 5% scenario, would be roughly "
           f"{f(calc.growth_curve(left, .05, 540, True)[-1][1])} in today’s money." if left > 0 else
           "You’re spending more than comes in. Start with the biggest bars; subscriptions and going out are the quickest to trim.")
    return (form(num("Monthly income (loan, wages, parents)", "income", p) + "".join(num(n, k, p) for k, n in BUD)) +
            f'<div class=bar>{bar}</div>{leg}<div class=kpi>{kp("Spent", f(tot))}'
            f'{kp("Left over" if left >= 0 else "Overspent", f(left))}{kp("Per day", f(tot/30))}</div><p class=note>{tip}</p>')


def retire(p):
    yrs = max(0, p["ret"] - p["age"])
    r = (1.05 / 1.025) ** (1 / 12) - 1
    m = max(0, min(p["salary"], 50270) - 6240) * (p["emp"] + p["er"]) / 100 / 12
    pot = float(p["pot"])
    for _ in range(yrs * 12):
        pot = pot * (1 + r) + m
    sp = STATE_PENSION * 52
    return (form(num("Age now", "age", p) + num("Retire at", "ret", p) + num("Salary (£/year)", "salary", p, 1000) +
                 num("Your pension %", "emp", p, .5) + num("Employer %", "er", p, .5) + num("Pot today (£)", "pot", p, 500)) +
            f'<div class=kpi>{kp("Pot (today’s money)", f(pot))}{kp("Pension income a year", f(pot*.04))}'
            f'{kp("State pension a year", f(sp))}{kp("Total a month", f((pot*.04+sp)/12))}{kp("Paid in a month", f(m))}</div>'
            f'<p class=note>Auto-enrolment minimum is 8% of earnings between £6,240 and £50,270 (5% you, 3% employer). '
            f'Growth 5% minus 2.5% inflation; drawdown 4% a year. State pension £{STATE_PENSION} a week <b class=v>verify</b> at gov.uk, '
            f'assumed from 67 <b class=v>verify</b>.</p>')


def loan(p):
    plans = seed.load_plans()
    pl = plans.get(p["plan"]) or next(iter(plans.values()))
    args = (pl, p["bal"], p["salary"], p["growth"] / 100, p["rpi"] / 100)
    b, o = calc.simulate_loan(*args), calc.simulate_loan(*args, extra_monthly=p["extra"])
    c = calc.compare_overpay_vs_invest(b, o, p["extra"], pl.write_off_years)
    share = b["written_off"] / ((b["mandatory"] + b["written_off"]) or 1)
    if b["written_off"] > 0 and c["net_overpay"] <= 0:
        v = (f"Don’t overpay. Part of your balance is written off, so your extra {f(c['paid_in'])} only cuts future repayments by "
             f"{f(c['saved'])}. Invested instead at a mid 5% scenario, {f(p['extra'])} a month could reach about {f(c['pot'])} "
             f"({f(c['growth'])} growth), with no promise.")
    elif b["written_off"] > 0:
        v = f"Close call. Overpaying nets {f(c['net_overpay'])} of savings; investing could add roughly {f(c['growth'])} in growth, with risk."
    else:
        v = (f"You’d clear this loan within the term, so overpaying saves {f(c['saved'])} for {f(c['paid_in'])} paid in. "
             f"That’s a guaranteed return; compare it with investing’s risk.")
    opts = [(n, f"{n} (£{x.threshold:,.0f}, {x.write_off_years}y)") for n, x in plans.items()]
    return (form(sel("Loan plan", "plan", p, opts) + num("Balance (£)", "bal", p, 1000) + num("Starting salary (£)", "salary", p, 1000) +
                 num("Salary growth %", "growth", p, .5) + num("RPI assumption %", "rpi", p, .5) + num("Extra £/month", "extra", p, 25)) +
            f'<div class=kpi>{kp("Monthly repayment (yr 1)", f(b["first_monthly"]))}{kp("Total repaid", f(b["mandatory"]))}'
            f'{kp("Written off", f(b["written_off"]))}{kp("Share written off", f"{share:.0%}")}</div><div class=verdict>{v}</div>'
            f'<p class=note>Scotland: Plan 4. Older England/Wales loans: Plan 1 (often also written off at 65; check). Figures come from seed.py '
            f'(2026/27) <b class=v>verify</b> on gov.uk. Thresholds assumed to rise 3% a year. Not financial advice.</p>')


CSS = """:root{--bg:#eef3f1;--card:#fff;--ink:#12302f;--mut:#5c7371;--line:#d4e0dd;--a:#0f7b6c;--b:#e8a33d;--band:#0f7b6c33}
@media(prefers-color-scheme:dark){:root{--bg:#0d1b1a;--card:#142928;--ink:#e6f1ee;--mut:#8fa9a5;--line:#244240;--a:#3fc4ae;--b:#f0b457;--band:#3fc4ae33}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}
.w{max-width:860px;margin:auto;padding:20px 16px 48px}h1{font-size:clamp(28px,6vw,42px);line-height:1.1;margin:8px 0}
nav{display:flex;gap:6px;overflow-x:auto;margin:14px 0}nav a{padding:9px 14px;border:1px solid var(--line);border-radius:99px;color:var(--ink);text-decoration:none;font-weight:600;white-space:nowrap}
nav a.on{background:var(--ink);color:var(--bg)}main{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}
.pitch{font-size:20px;font-weight:600;margin:0 0 12px}.row,.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:12px 0}
label,small{display:block;font-size:14px;color:var(--mut)}input,select{width:100%;font:inherit;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}
button{font:inherit;font-weight:600;padding:9px 16px;border:0;border-radius:8px;background:var(--a);color:#fff;cursor:pointer}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--b);outline-offset:2px}
.big{font-size:28px;font-weight:800}.kpi div{border-left:4px solid var(--a);padding:2px 10px}svg{width:100%;height:auto;margin-top:12px}svg text{fill:var(--mut);font-size:11px}
.bar{display:flex;height:34px;border-radius:8px;overflow:hidden;margin:12px 0}.leg{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--line)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}.note{font-size:13px;color:var(--mut)}.v{background:var(--b);color:#222;border-radius:4px;padding:0 5px;font-size:12px}
.verdict{border:2px solid var(--b);border-radius:10px;padding:12px;font-weight:600}table{width:100%;border-collapse:collapse}td,th{padding:6px 4px;text-align:left;border-bottom:1px solid var(--line)}"""
PITCH = {"growth": "£20 a month feels like nothing. Here’s the curve that says otherwise.",
         "budget": "See where every pound goes before the month does it for you.",
         "retire": "Retirement feels abstract at 20. This turns it into a monthly income figure.",
         "loan": "Most students are never told their loan behaves more like a graduate tax than a debt."}
VIEW = dict(growth=growth, budget=budget, retire=retire, loan=loan)


@app.route("/")
def home():
    return redirect("/growth")


@app.route("/<tab>", methods=["GET", "POST"])
def page(tab):
    if tab not in VIEW:
        return redirect("/")
    if request.method == "POST":
        save()
        return redirect(f"/{tab}")
    nav = "".join(f'<a href="/{t}"{" class=on" if t == tab else ""}>{n}</a>' for t, n in TABS)
    return (f'<!doctype html><html lang=en-GB><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
            f'<title>Small Pots</title><style>{CSS}</style><div class=w><h1>Small pots, big futures.</h1><nav>{nav}</nav>'
            f'<main><p class=pitch>{PITCH[tab]}</p>{VIEW[tab](prof())}</main>'
            f'<p class=note>Your answers are saved in your browser cookie and shared across tabs. Educational estimates, not regulated advice.</p></div>')


if __name__ == "__main__":
    seed.seed()
    app.run(debug=True)

def growth_curve(monthly, rate, months, real=False):
    """Calculate investment growth and contributions month by month."""
    inflation = 0.025
    monthly_rate = (1 + rate) ** (1 / 12) - 1

    pot = 0.0
    contributions = 0.0
    results = [(0, 0.0, 0.0)]

    for month in range(1, months + 1):
        pot = pot * (1 + monthly_rate) + monthly
        contributions += monthly

        if real:
            deflator = (1 + inflation) ** (month / 12)
        else:
            deflator = 1.0

        results.append((
            month,
            pot / deflator,
            contributions / deflator
        ))

    return results