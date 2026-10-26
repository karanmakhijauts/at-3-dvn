"""Smarter, or slipping? A dashboard for a C-suite reader.

Three views: Adoption, Output vs skill, What it means.
Data: data/evidence.csv (hand-built from papers) and raw CSVs you place in data/raw/.
"""
import pathlib

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
RAW = DATA / "raw"

INK, AMBER, GREY = "#1B1F3B", "#F2A541", "#8A90AD"
STRENGTH_ORDER = ["High", "Medium", "Low"]
STRENGTH_COLORS = {"High": INK, "Medium": AMBER, "Low": GREY}

st.set_page_config(page_title="Smarter, or slipping?", layout="wide")


@st.cache_data
def load_evidence() -> pd.DataFrame:
    return pd.read_csv(DATA / "evidence.csv")


def load_raw(filename: str):
    """Return (dataframe, origin text) from data/raw/<filename>, else (None, None)."""
    path = RAW / filename
    if path.exists():
        return pd.read_csv(path), f"data/raw/{filename}"
    return None, None


# Optional: set a column name here if the automatic guess is wrong for your file.
# Example: COLUMNS["owid"] = {"group": "Entity", "time": "Year", "value": "Share of adults"}
COLUMNS = {"owid": {}, "btos": {}, "piaac": {}}


def guess(cols, names, fallback):
    lowered = {c.lower(): c for c in cols}
    for n in names:
        if n.lower() in lowered:
            return lowered[n.lower()]
    return fallback


def series_panel(df: pd.DataFrame, origin: str, key: str, value_label: str):
    """Let the viewer map columns, filter entities and see a chart, headline and trace."""
    cols = list(df.columns)
    ent_guess = guess(cols, ["Entity", "Country", "Sector", "Geography", "geo"], cols[0])
    per_guess = guess(cols, ["Year", "Day", "Period", "Date", "Time"], cols[1] if len(cols) > 1 else cols[0])
    numeric = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and c not in (ent_guess, per_guess)]
    val_guess = numeric[-1] if numeric else cols[-1]

    chosen = COLUMNS.get(key, {})
    ent = chosen.get("group", ent_guess)
    per = chosen.get("time", per_guess)
    val = chosen.get("value", val_guess)
    st.caption(f"Charting `{val}` by `{ent}` over `{per}`.")

    work = df[[ent, per, val]].copy()
    work[val] = pd.to_numeric(work[val], errors="coerce")
    work = work.dropna()
    options = sorted(work[ent].astype(str).unique())
    sel = st.multiselect("Show", options, default=options[:4], key=f"{key}_sel")
    sub = work[work[ent].astype(str).isin(sel)]
    if sub.empty:
        st.info("Pick at least one group to chart.")
        return

    if pd.api.types.is_numeric_dtype(sub[per]):
        sub = sub.sort_values(per)
        order = None
    else:
        order = list(dict.fromkeys(work[per].astype(str)))
        sub[per] = sub[per].astype(str)

    first = sel[0]
    one = sub[sub[ent].astype(str) == first]
    if len(one) >= 2:
        a, b = one.iloc[0], one.iloc[-1]
        st.subheader(f"{first}: {value_label} went from {a[val]:.1f} ({a[per]}) to {b[val]:.1f} ({b[per]})")
    else:
        a = one.iloc[0]
        st.subheader(f"{first}: {value_label} was {a[val]:.1f} ({a[per]})")

    fig = px.line(sub, x=per, y=val, color=ent, markers=True,
                  category_orders={per: order} if order else None)
    fig.update_layout(height=380, yaxis_title=value_label, xaxis_title=None, legend_title=None)
    st.plotly_chart(fig, width="stretch")

    with st.expander("Trace the headline number back to the source"):
        last_idx = one.index[-1]
        st.write(f"**1. On screen:** {b[val] if len(one) >= 2 else a[val]:.1f} for {first}")
        st.write(f"**2. Processed:** kept columns `{ent}`, `{per}`, `{val}`; converted `{val}` to numbers; "
                 f"dropped empty rows; filtered `{ent}` to your selection.")
        st.write(f"**3. Raw source:** {origin}, data row {last_idx + 1} (line {last_idx + 2} of the file including the header):")
        st.dataframe(df.loc[[last_idx]], width="stretch")
        st.download_button("Download the processed rows as CSV", sub.to_csv(index=False), f"{key}_processed.csv", "text/csv")


# ---------------------------------------------------------------- sidebar
ev = load_evidence()
with st.sidebar:
    st.title("Smarter, or slipping?")
    st.caption("Is the rise of AI making people smarter, or eroding their cognitive ability? "
               "For: a COO deciding how to roll out AI.")
    st.markdown("**Evidence filters**")
    strengths = st.multiselect("Evidence strength", STRENGTH_ORDER, default=STRENGTH_ORDER)
    st.markdown("**Data files**")
    for name in ["owid_genai.csv", "btos_ai.csv", "piaac.csv"]:
        st.write(("✅ " if (RAW / name).exists() else "⬜ ") + f"data/raw/{name}")

tab_adopt, tab_ev, tab_mean = st.tabs(["Adoption", "Output vs skill", "What it means"])

# ---------------------------------------------------------------- adoption
with tab_adopt:
    st.markdown("How widely is AI being used? Two sources, each with limits.")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Working-age adults using generative AI (Our World in Data)")
        st.caption("Modelled estimates from Microsoft usage data for ages 15 to 64, with only three time points. "
                   "Not survey data.")
        df, origin = load_raw("owid_genai.csv")
        if df is None:
            st.caption("Data not added yet.")
        else:
            series_panel(df, origin, "owid", "share of adults using generative AI (%)")
    with right:
        st.markdown("#### Firms using AI (US Census Bureau BTOS)")
        st.caption("US firms only. Check which survey question and reference period each column answers before charting.")
        df, origin = load_raw("btos_ai.csv")
        if df is None:
            st.caption("Data not added yet.")
        else:
            series_panel(df, origin, "btos", "share of firms using AI (%)")

# ---------------------------------------------------------------- output vs skill
with tab_ev:
    f = ev[ev["evidence_strength"].isin(strengths)]
    out, skill = f[f.panel == "output"], f[f.panel == "skill"]
    st.subheader(
        f"{(out.direction == 'gain').sum()} of {len(out)} output findings show gains. "
        f"Of {len(skill)} skill findings, {(skill.direction == 'loss').sum()} show a loss and "
        f"{(skill.direction == 'gain').sum()} a gain."
    )
    st.caption("Skill findings here are task accuracy or self-reported thinking. None is a long-run test of cognitive ability.")

    def panel(df, title):
        st.markdown(f"#### {title}")
        if df.empty:
            st.info("Nothing matches the evidence filter.")
            return
        fig = px.scatter(df, x="sample_size", y="label", color="evidence_strength", text="short_label",
                         log_x=True, category_orders={"evidence_strength": STRENGTH_ORDER},
                         color_discrete_map=STRENGTH_COLORS,
                         hover_data={"design": True, "measure": True, "sample_size": True, "label": False, "short_label": False})
        import math
        lo, hi = math.log10(df.sample_size.min()), math.log10(df.sample_size.max())
        fig.update_traces(marker_size=16, textposition="middle right")
        fig.update_xaxes(range=[lo - 0.3, hi + 2.3], tickvals=[100, 300, 1000, 3000, 10000],
                         ticktext=["100", "300", "1,000", "3,000", "10,000"], title="Sample size (log scale)")
        fig.update_layout(height=340, yaxis_title=None, legend_title=None,
                          legend=dict(orientation="h", y=-0.3, x=0), margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        panel(out, "Output gains")
    with c2:
        panel(skill, "Skill signals")

    st.markdown("#### Findings and sources")
    show = f[["panel", "label", "design", "sample_size", "finding", "direction", "evidence_strength",
              "strength_rationale", "source_url", "location_in_source", "check_status"]]
    st.dataframe(show, width="stretch", hide_index=True,
                 column_config={"source_url": st.column_config.LinkColumn("source")})
    st.caption("Evidence strength is a judgement made for this dashboard (see strength_rationale). Check status says "
               "how much of each source was actually read.")

    with st.expander("Optional: adult skills context (OECD PIAAC)"):
        st.caption("Measures adult literacy and numeracy by country. It is not about AI, so it shows the skills backdrop only.")
        df, origin = load_raw("piaac.csv")
        if df is None:
            st.caption("Data not added yet.")
        else:
            series_panel(df, origin, "piaac", "score")

# ---------------------------------------------------------------- what it means
with tab_mean:
    st.markdown("The dashboard doesn't make the decision. This shows what the evidence loaded so far says about each option.")
    n_gain = int((ev[ev.panel == "output"].direction == "gain").sum())
    n_loss = int((ev[ev.panel == "skill"].direction == "loss").sum())
    options = pd.DataFrame([
        {"Option": "Roll out to everyone",
         "What supports it": f"{n_gain} findings show output gains, biggest for weaker or less experienced workers in all three.",
         "What argues against it": f"{n_loss} findings show a skill or accuracy loss, including worse accuracy where AI can be convincingly wrong."},
        {"Option": "Restrict AI",
         "What supports it": "Skill-loss signals, though the strongest comes from one deliberately tricky task.",
         "What argues against it": "Gains in the larger and randomised studies, and no evidence here of a long-run skill decline."},
        {"Option": "Roll out with training and guardrails",
         "What supports it": "Matches both sides: keeps the gains, and targets the risk where AI is wrong or over-trusted.",
         "What argues against it": "This evidence doesn't test whether training works. That is an open question."},
    ])
    st.table(options.set_index("Option"))
    st.caption("Limits: mostly short-term studies of single firms or tasks, so results may not carry over to your sector.")
