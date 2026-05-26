"""Data & identity — how messy CRM data resolves into accounts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    get_diagnostic, page, require_csv, sidebar_inputs,
)

page("Data & identity")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)
df = res["data"]
ov = res["overview"]

st.subheader("Identity resolution")
st.caption("Real CRM exports have the same account spelled several ways and "
           "missing IDs. We normalize names (strip case, punctuation, and "
           "corporate suffixes) and backfill a single account per entity.")

c1, c2, c3 = st.columns(3)
c1.metric("Opportunities", f"{ov['opportunities']:,}")
c2.metric("Resolved accounts", f"{ov['resolved_accounts']:,}")
c3.metric("Rows missing account_id",
          f"{int((df['account_id'].astype(str).str.strip() == '').sum()):,}",
          help="Resolved from the account name instead.")

# show a few accounts where multiple raw spellings collapsed into one entity
st.markdown("**Examples: messy names → one resolved account**")
grp = (df.groupby("resolved_account_id")
         .agg(resolved_account_name=("resolved_account_name", "first"),
              raw_spellings=("account_name", lambda s: sorted(set(s.astype(str).str.strip()))),
              opportunities=("opportunity_id", "count")))
grp = grp[grp["raw_spellings"].map(len) > 1].sort_values("opportunities", ascending=False)
if grp.empty:
    st.caption("No multi-spelling accounts in this dataset.")
else:
    show = grp.head(12).copy()
    show["raw_spellings"] = show["raw_spellings"].map(lambda xs: "  |  ".join(xs))
    st.dataframe(show.reset_index(drop=True), hide_index=True, use_container_width=True)

st.subheader("Raw data preview")
st.caption("The enriched table the diagnostic runs on (first 200 rows).")
st.dataframe(df.head(200), hide_index=True, use_container_width=True)
