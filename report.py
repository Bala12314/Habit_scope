"""Self-contained HTML dashboard (inline SVG, no JS, no network). Light/dark aware."""
from __future__ import annotations

from html import escape

from .analysis import habits as H
from .analysis import insights as I
from .analysis import score as S
from .models import Day, fmt_clock

CSS = """
:root{--bg:#f7f6f3;--card:#fff;--ink:#1d1d1b;--mute:#6b6a66;--line:#e6e4df;
--a:#2a6fdb;--b:#1f9d6b;--c:#d9822b;--d:#8a5fd1;--bad:#d1495b;--good:#1f9d6b}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe7;--mute:#9a988f;
--line:#32312d;--a:#6aa2ff;--b:#4cc79a;--c:#f0a35a;--d:#b693f0;--bad:#ef7585;--good:#4cc79a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:17px;margin:0 0 10px}
.sub{color:var(--mute);margin:0 0 20px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));margin-bottom:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;min-width:0}
.big{font-size:48px;font-weight:700;line-height:1}.pill{display:inline-block;padding:2px 10px;
border-radius:99px;font-size:12px;border:1px solid var(--line);color:var(--mute)}
svg{width:100%;height:auto;display:block}
.axis{stroke:var(--line);stroke-width:1}.lbl{fill:var(--mute);font-size:11px}
.l-a{stroke:var(--a)}.l-b{stroke:var(--b)}.l-c{stroke:var(--c)}.l-d{stroke:var(--d)}
.f-a{fill:var(--a);background:var(--a)}.f-b{fill:var(--b);background:var(--b)}.f-c{fill:var(--c);background:var(--c)}.f-d{fill:var(--d);background:var(--d)}
.ref{stroke:var(--mute);stroke-dasharray:4 4;stroke-width:1;opacity:.7}
.ln{fill:none;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
.ln.soft{opacity:.35;stroke-width:1.5}
table{width:100%;border-collapse:collapse}td,th{padding:7px 6px;text-align:left;
border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mute);font-weight:500;font-size:13px}
.bar{height:8px;border-radius:4px;background:var(--line);overflow:hidden}.bar>i{display:block;height:100%}
.bad{color:var(--bad)}.good{color:var(--good)}.mute{color:var(--mute)}
ul{margin:0;padding-left:18px}li{margin:4px 0}
footer{color:var(--mute);font-size:12px;margin-top:20px}
"""

W, HT, PL, PR, PT, PB = 720, 210, 42, 10, 10, 26
SW = 380  # width of small-card charts (smaller viewBox = larger text)


def _y(v, lo, hi):
    return PT + (1 - (v - lo) / (hi - lo)) * (HT - PT - PB)


def _x(i, n, w=W):
    return PL + (i / max(n - 1, 1)) * (w - PL - PR)


def _frame(labels, lo, hi, fmt, refs=(), w=W):
    n = len(labels)
    out = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        y = _y(v, lo, hi)
        out.append(f'<line class="axis" x1="{PL}" x2="{w - PR}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="lbl" x="{PL - 6}" y="{y + 4:.1f}" text-anchor="end">{fmt(v)}</text>')
    for i in sorted({0, n // 2, n - 1}):
        anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
        out.append(f'<text class="lbl" x="{_x(i, n, w):.1f}" y="{HT - 6}" text-anchor="{anchor}">{escape(labels[i])}</text>')
    for v, text in refs:
        if lo <= v <= hi:
            y = _y(v, lo, hi)
            out.append(f'<line class="ref" x1="{PL}" x2="{w - PR}" y1="{y:.1f}" y2="{y:.1f}"/>'
                       f'<text class="lbl" x="{w - PR}" y="{y - 4:.1f}" text-anchor="end">{escape(text)}</text>')
    return "".join(out)


def _path(vals, lo, hi, w=W):
    n, segs, cur = len(vals), [], []
    for i, v in enumerate(vals):
        if v is None:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(f"{_x(i, n, w):.1f},{_y(min(max(v, lo), hi), lo, hi):.1f}")
    if cur:
        segs.append(cur)
    return " ".join("M" + " L".join(s) for s in segs)


def line_chart(vals, labels, lo, hi, cls="a", fmt=lambda v: f"{v:.0f}", refs=(), smooth=None, title="", w=W):
    body = _frame(labels, lo, hi, fmt, refs, w)
    if smooth:
        body += f'<path class="ln soft l-{cls}" d="{_path(vals, lo, hi, w)}"/>'
        body += f'<path class="ln l-{cls}" d="{_path(smooth, lo, hi, w)}"/>'
    else:
        body += f'<path class="ln l-{cls}" d="{_path(vals, lo, hi, w)}"/>'
    return f'<svg viewBox="0 0 {w} {HT}" role="img" aria-label="{escape(title)}">{body}</svg>'


def bar_chart(vals, labels, lo, hi, cls="a", fmt=lambda v: f"{v:.0f}", refs=(), title="", w=SW):
    n = len(vals)
    bw = max(2.0, (w - PL - PR) / n * 0.7)
    body = _frame(labels, lo, hi, fmt, refs, w)
    for i, v in enumerate(vals):
        if v is None:
            continue
        y, y0 = _y(min(max(v, lo), hi), lo, hi), _y(lo, lo, hi)
        body += (f'<rect class="f-{cls}" x="{_x(i, n, w) - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                 f'height="{max(0, y0 - y):.1f}" rx="1.5"><title>{escape(labels[i])}: {fmt(v)}</title></rect>')
    return f'<svg viewBox="0 0 {w} {HT}" role="img" aria-label="{escape(title)}">{body}</svg>'


def _moving(vals, k=7):
    out = []
    for i in range(len(vals)):
        w = [v for v in vals[max(0, i - k + 1): i + 1] if v is not None]
        out.append(sum(w) / len(w) if w else None)
    return out


def _nice_max(vals, floor):
    m = max([v for v in vals if v is not None] + [floor])
    step = 10 ** (len(str(int(m))) - 1) / 2
    return (int(m / step) + 1) * step


def render(days: list[Day], window: int = 30) -> str:
    days = days[-max(window, 14):] if window else days
    base = S.baseline(days)
    scores = [S.score_day(d, base) for d in days]
    totals = [s.total for s in scores]
    labels = [d.date.strftime("%d %b") for d in days]
    last = scores[-1]
    valid = [t for t in totals if t is not None]
    avg = sum(valid) / len(valid) if valid else 0
    stats = H.evaluate(days, window)
    ins = I.find_insights(days)

    comp_names = {"activity": "Activity", "sleep": "Sleep", "recovery": "Recovery", "digital": "Digital wellbeing"}
    comp_rows = "".join(
        f'<tr><td>{comp_names[k]}</td><td style="width:55%"><div class="bar"><i class="f-{c}" '
        f'style="width:{v:.0f}%"></i></div></td><td>{v:.0f}</td></tr>'
        for (k, v), c in zip(last.components.items(), "abcd"))

    def habit_rows(items, cls):
        if not items:
            return '<tr><td class="mute">Nothing detected.</td></tr>'
        rows = []
        for s in items:
            tr = "improving" if s.improving else "getting worse" if s.worsening else "steady"
            rows.append(f'<tr><td><b class="{cls}">{escape(s.rule.name)}</b><br>'
                        f'<span class="mute">{escape(s.rule.advice)}</span></td>'
                        f'<td>{s.hits}/{s.applicable} days<br><span class="mute">{tr}</span></td></tr>')
        return "".join(rows)

    apps = H.top_apps(days, 14)
    app_rows = "".join(
        f'<tr><td>{escape(a)}</td><td class="mute">{escape(c)}</td><td>{m:.0f} min/day</td></tr>' for a, c, m in apps
    ) or '<tr><td class="mute">No per-app data imported.</td></tr>'

    ins_html = "".join(f"<li>{escape(i.text)}</li>" for i in ins) or \
        '<li class="mute">Not enough data yet for personal patterns (needs ~2 weeks).</li>'

    change_rows = ""
    names = {"steps": "Steps", "sleep_hours": "Sleep (h)", "screen_min": "Screen (min)",
             "night_screen_min": "Night phone (min)", "resting_hr": "Resting HR", "hrv": "HRV"}
    lower_better = {"screen_min", "night_screen_min", "resting_hr"}
    for name, a, b in I.weekly_change(days):
        diff = a - b
        better = (diff < 0) == (name in lower_better)
        cls = "mute" if abs(diff) < 0.02 * max(abs(b), 1) else ("good" if better else "bad")
        change_rows += (f'<tr><td>{names[name]}</td><td>{a:,.1f}</td><td class="mute">{b:,.1f}</td>'
                        f'<td class="{cls}">{diff:+,.1f}</td></tr>')

    steps = [d.steps for d in days]
    sleep = [d.sleep_hours for d in days]
    screen = [d.screen_min / 60 if d.screen_min is not None else None for d in days]
    night = [d.night_screen_min for d in days]
    rhr = [d.resting_hr for d in days]
    bed = [d.bedtime_h for d in days]

    charts = f"""
<div class="card"><h2>Performance score</h2>{line_chart(totals, labels, 0, 100, "a", smooth=_moving(totals),
 refs=[(65, "good")], title="Daily performance score")}
<p class="mute">Faint line = daily, bold = 7-day average.</p></div>
<div class="grid">
<div class="card"><h2>Steps</h2>{bar_chart(steps, labels, 0, _nice_max(steps, 10000), "b",
 fmt=lambda v: f"{v:,.0f}", refs=[(8000, "goal")], title="Steps")}</div>
<div class="card"><h2>Sleep (hours)</h2>{bar_chart(sleep, labels, 0, 10, "d", fmt=lambda v: f"{v:.1f}",
 refs=[(7, "7h")], title="Sleep hours")}</div>
<div class="card"><h2>Phone screen time (hours)</h2>{bar_chart(screen, labels, 0, _nice_max(screen, 6), "c",
 fmt=lambda v: f"{v:.1f}", refs=[(3, "3h"), (6, "6h")], title="Screen time")}</div>
<div class="card"><h2>Late-night phone use (min)</h2>{bar_chart(night, labels, 0, _nice_max(night, 60), "c",
 refs=[(30, "30 min")], title="Night phone use")}</div>
<div class="card"><h2>Resting heart rate (bpm)</h2>{line_chart(rhr, labels, 50, 75, "a", fmt=lambda v: f"{v:.0f}",
 title="Resting heart rate", w=SW)}</div>
<div class="card"><h2>Bedtime</h2>{line_chart(bed, labels, 22, 27, "d", fmt=fmt_clock, refs=[(23.5, "23:30")],
 title="Bedtime", w=SW)}</div>
</div>"""

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>LifeLens report</title>
<style>{CSS}</style></head><body><main>
<h1>LifeLens daily-life report</h1>
<p class="sub">{days[0].date:%d %b %Y} - {days[-1].date:%d %b %Y} &middot; {len(days)} days &middot; all data stays on your device</p>
<div class="grid">
<div class="card"><h2>Latest day ({days[-1].date:%d %b})</h2>
<div class="big">{'-' if last.total is None else f'{last.total:.0f}'}<span class="mute" style="font-size:18px">/100</span></div>
<span class="pill">{last.label}</span> <span class="pill">period avg {avg:.0f}</span>
<table style="margin-top:12px">{comp_rows}</table></div>
<div class="card"><h2>This week vs last week</h2><table><tr><th>Metric</th><th>Now</th><th>Before</th><th>Change</th></tr>
{change_rows or '<tr><td class="mute">Need 2 weeks of data.</td></tr>'}</table></div>
</div>
{charts}
<div class="grid">
<div class="card"><h2>Habits to work on</h2><table>{habit_rows(H.bad_habits(stats), "bad")}</table></div>
<div class="card"><h2>Habits that help you</h2><table>{habit_rows(H.good_habits(stats), "good")}</table></div>
</div>
<div class="grid">
<div class="card"><h2>Patterns in your data</h2><ul>{ins_html}</ul></div>
<div class="card"><h2>Where your phone time goes (14-day avg)</h2><table>{app_rows}</table></div>
</div>
<footer>Scores are lifestyle heuristics from your own baseline, not medical measurements. Correlations are
tendencies, not proof of cause. Generated by LifeLens, created by Abhishek Kaushal.</footer>
</main></body></html>"""
