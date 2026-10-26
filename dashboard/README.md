# Smarter, or slipping? (dashboard prototype)

Run: `pip install -r requirements.txt` then `streamlit run app.py`

## Data
- `data/evidence.csv` is hand-built from papers. Every row has a source URL, where in the source it comes from,
  and a `check_status` saying how much of the source was actually read. Rows marked "Read a summary only"
  must be checked against the paper before you present them.
- `data/raw/` holds unedited downloads you add yourself. See `data/raw/README.md`.

## Judgement calls to defend
- `evidence_strength` and `strength_rationale` are judgements, not facts from the papers.
- The Output vs skill view uses a log scale on sample size to place each study. It says how large each study is, not how big its effect is.
