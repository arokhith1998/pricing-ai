"""Data and identity. How messy CRM data becomes clean accounts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from _app_lib import (  # noqa: E402
    assist, field_label, get_column_map, get_diagnostic, page, relabel,
    require_csv, sidebar_inputs,
)

page("Data and identity")
csv, policy = sidebar_inputs()
require_csv(csv)
res = get_diagnostic(csv, policy)
df = res["data"]
ov = res["overview"]

st.subheader("Cleaning up account names")
st.caption("Real exports spell the same company several ways and often leave the "
           "account ID blank. We standardize the name (case, punctuation, and "
           "company suffixes) and link every record to one account.")

c1, c2, c3 = st.columns(3)
c1.metric("Opportunities", f"{ov['opportunities']:,}")
c2.metric("Accounts after cleanup", f"{ov['resolved_accounts']:,}")
c3.metric("Records with no account ID",
          f"{int((df['account_id'].astype(str).str.strip() == '').sum()):,}",
          help="Linked by company name instead.")

st.markdown("**Examples: several spellings that became one account**")
grp = (df.groupby("resolved_account_id")
         .agg(account=("resolved_account_name", "first"),
              spellings=("account_name", lambda s: sorted(set(s.astype(str).str.strip()))),
              opportunities=("opportunity_id", "count")))
grp = grp[grp["spellings"].map(len) > 1].sort_values("opportunities", ascending=False)
if grp.empty:
    st.caption("No multi-spelling accounts in this dataset.")
else:
    show = grp.head(12).copy()
    show["spellings"] = show["spellings"].map(lambda xs: "   |   ".join(xs))
    show = show.rename(columns={"account": "Account", "spellings": "Spellings we merged",
                                "opportunities": "Opportunities"})
    st.dataframe(show.reset_index(drop=True), hide_index=True, use_container_width=True)

# --- AI column mapping -------------------------------------------------------
st.subheader("Bring your own CSV")
st.caption("Upload a closed-deal export and we match your columns to ours, so "
           "getting started is a quick confirmation rather than a data project. "
           "Only the column names are sent to the AI, never the rows of data.")
up = st.file_uploader("Closed-deal CSV", type=["csv"])
if up is not None:
    headers = list(pd.read_csv(up, nrows=0).columns)
    st.write("**Your columns:** " + ", ".join(headers))
    if not assist.has_llm():
        st.caption("Add an API key to .env to enable automatic matching.")
    else:
        try:
            mapping = get_column_map(tuple(headers))
            targets = assist.mapping_targets()
            table = pd.DataFrame([
                {"Our field": field_label(t["field"]),
                 "Required": "Yes" if t["required"] else "",
                 "Your column": mapping.get(t["field"]) or "not matched"}
                for t in targets])
            st.dataframe(table, hide_index=True, use_container_width=True)
            missing = [field_label(t["field"]) for t in targets
                       if t["required"] and not mapping.get(t["field"])]
            if missing:
                st.warning("These required fields still need a match: "
                           + ", ".join(missing))
            else:
                st.success("Every required field matched. Ready to run.")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Matching is unavailable right now: {exc}")

st.subheader("Data preview")
st.caption("The table the diagnostic runs on (first 200 rows).")
st.dataframe(relabel(df.head(200)), hide_index=True, use_container_width=True)
