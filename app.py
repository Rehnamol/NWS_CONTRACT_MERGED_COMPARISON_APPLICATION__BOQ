from __future__ import annotations
import io
from io import BytesIO
from typing import List

import numpy as np
import pandas as pd
import streamlit as st

# ----------------------
# Page config
# ----------------------
st.set_page_config(page_title="BOQ Comparator", layout="wide")
st.title("📊 BOQ Comparator – Merge & Compare Contractors' Quotations")

st.markdown(
    """
Upload 2 or more contractor quotations (Excel/CSV) to merge and compare.
Supports large files; files are loaded safely in the background.
"""
)

# ----------------------
# File upload
# ----------------------
uploads = st.file_uploader(
    "Upload files",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

match_mode = st.selectbox(
    "Match items by",
    ["ITEM + DESCRIPTION", "DESCRIPTION only", "ITEM only"],
    index=0
)

run = st.button(
    "🔍 Compare Quotations",
    type="primary",
    disabled=not uploads or len(uploads) < 2
)

# ----------------------
# Helper functions
# ----------------------
def normalize_name(idx: int) -> str:
    return f"Contractor_{idx}"


def load_table(file) -> pd.DataFrame:
    """Load a single Excel/CSV file safely."""
    try:
        if file.name.lower().endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file, engine="openpyxl")
        return df
    except Exception as e:
        st.error(f"Could not read {file.name}: {e}")
        return pd.DataFrame()


def merge_contractors(files: List, mode: str) -> pd.DataFrame:
    """Merge multiple contractor files."""
    frames = []

    for i, f in enumerate(files, start=1):
        df = load_table(f)
        if df.empty:
            continue

        contractor_name = normalize_name(i)

        # Standardize RATE/AMOUNT columns
        if "RATE" not in df.columns:
            for c in df.columns:
                if "rate" in c.lower():
                    df.rename(columns={c: "RATE"}, inplace=True)
        rename_map = {}
        if "RATE" in df.columns:
            rename_map["RATE"] = f"{contractor_name}_RATE"
        if "AMOUNT" in df.columns:
            rename_map["AMOUNT"] = f"{contractor_name}_AMOUNT"
        df = df.rename(columns=rename_map)

        frames.append(df)

    if not frames:
        st.warning("No valid files to merge!")
        return pd.DataFrame()

    # Merge all frames
    combined = frames[0]
    for part in frames[1:]:
        if mode == "ITEM + DESCRIPTION":
            keys = [k for k in ("ITEM", "DESCRIPTION") if k in combined.columns and k in part.columns]
        elif mode == "DESCRIPTION only":
            keys = ["DESCRIPTION"] if "DESCRIPTION" in combined.columns and "DESCRIPTION" in part.columns else []
        else:
            keys = ["ITEM"] if "ITEM" in combined.columns and "ITEM" in part.columns else []

        if keys:
            combined = pd.merge(combined, part, on=keys, how="outer")
        else:
            combined = pd.concat([combined, part], axis=1)

    return combined


def make_columns_unique(df: pd.DataFrame) -> pd.DataFrame:
    """Rename duplicate columns automatically."""
    new_cols = []
    seen = {}
    for col in df.columns:
        if col not in seen:
            seen[col] = 0
            new_cols.append(col)
        else:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
    df.columns = new_cols
    return df


# ----------------------
# Run comparison
# ----------------------
if run:
    with st.spinner("Merging files, please wait..."):
        result = merge_contractors(uploads, match_mode)

    if not result.empty:
        st.success("✅ Files merged successfully!")

        # Handle duplicate columns
        result = make_columns_unique(result)

        # Display in Streamlit
        st.dataframe(result, width="stretch")

        # Option to download merged result
        output = BytesIO()
        result.to_excel(output, index=False, engine="xlsxwriter")
        st.download_button(
            label="💾 Download Merged Excel",
            data=output.getvalue(),
            file_name="Merged_BOQ.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No data to display.")
