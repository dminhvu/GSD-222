import io
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="GSD-222: Redpath")
st.title("GSD-222: Redpath")


def process_file(file):
    # Read incoming file (no header)
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file, header=None)
    elif file.name.lower().endswith((".xls", ".xlsx")):
        df = pd.read_excel(file, header=None)
    else:
        st.error("Unsupported file format. Please upload a CSV or Excel file.")
        return None

    if df.empty:
        st.error("The uploaded file is empty.")
        return None

    # Store original data for processing
    original_df = df.copy()

    # Step 1: Unhide all hidden rows (handled automatically when reading file)

    # Step 2: Delete Rows 1-13 (0-indexed: delete rows 0-12)
    df = df.iloc[13:].reset_index(drop=True)

    # Step 3: Delete Columns B, E-M, O-T (keep A, C, D, N)
    # Columns to keep: A(0), C(2), D(3), N(13)
    if df.shape[1] < 14:  # Need at least column N (index 13)
        st.error("Input file must have at least 14 columns to process.")
        return None

    # Keep only required columns
    df = df.iloc[:, [0, 2, 3, 13]]  # A, C, D, N

    # Step 4: Move all content in column A down 1 cell
    if not df.empty:
        df.iloc[1:, 0] = df.iloc[:-1, 0].values
        df.iloc[0, 0] = ""

    # Step 5: Add Column Names
    column_names = [
        "Debtor Reference",
        "Document Number",
        "Document Date",
        "Document Balance",
        "Document Type",
    ]
    output = pd.DataFrame(columns=column_names)

    # Step 6: Move all content in Column A down by 1 cell (already done in step 4)

    # Step 7: Filter all data in columns A-E by blanks if Column B, and delete all blanks
    # Since we don't have column B anymore, we'll filter out rows where key columns are blank

    # Step 8: Remove filter (no specific action needed)

    # Create output DataFrame with proper structure
    if not df.empty:
        # Copy data to output with proper column names
        output["Debtor Reference"] = df.iloc[:, 0] if len(df.columns) > 0 else ""
        output["Document Number"] = df.iloc[:, 1] if len(df.columns) > 1 else ""
        output["Document Date"] = df.iloc[:, 2] if len(df.columns) > 2 else ""
        output["Document Balance"] = df.iloc[:, 3] if len(df.columns) > 3 else ""

        # Step 9: Copy down the Debtor reference for each section of invoices
        debtor_ref = ""
        for i in range(len(output)):
            if pd.notna(output.iloc[i, 0]) and str(output.iloc[i, 0]).strip() != "":
                debtor_ref = output.iloc[i, 0]
            else:
                output.iloc[i, 0] = debtor_ref

        # Step 10: Populate Column E with INV if data in column D is positive, or CRD if negative
        def determine_doc_type(balance):
            try:
                balance_val = float(str(balance).replace(",", "").replace("$", ""))
                return "INV" if balance_val >= 0 else "CRD"
            except:
                return "INV"  # default

        output["Document Type"] = output["Document Balance"].apply(determine_doc_type)

        # Step 11: Reorder columns - already in correct order based on requirements
        # A remains, E->B, C remains, D remains, E becomes Document balance

        # Step 12: Reformat Column E (Document Balance) as Number with 2 decimals
        def format_balance(val):
            try:
                return f"{float(str(val).replace(',', '').replace('$', '')):.2f}"
            except:
                return "0.00"

        output["Document Balance"] = output["Document Balance"].apply(format_balance)

        # Step 13: Reformat Column D (Document Date) as Date in DD/MM/YYYY format
        def parse_date(val):
            if pd.isna(val) or str(val).strip() == "":
                return ""

            # Try common date formats
            for fmt in (
                "%d/%m/%Y",
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%Y/%m/%d",
                "%d-%b-%Y",
                "%d %b %Y",
            ):
                try:
                    return datetime.strptime(str(val), fmt).strftime("%d/%m/%Y")
                except:
                    continue

            try:
                # Fallback to pandas
                parsed_date = pd.to_datetime(val, dayfirst=True, errors="coerce")
                if pd.notna(parsed_date):
                    return parsed_date.strftime("%d/%m/%Y")
            except:
                pass

            return str(val)  # Return original if can't parse

        output["Document Date"] = output["Document Date"].apply(parse_date)

        # Filter out rows where essential data is missing
        output = output[
            (output["Debtor Reference"].notna())
            & (output["Debtor Reference"].astype(str).str.strip() != "")
            & (output["Document Number"].notna())
            & (output["Document Number"].astype(str).str.strip() != "")
        ].reset_index(drop=True)

    return output


def get_csv_download_link(df):
    csv = df.to_csv(index=False)
    return io.BytesIO(csv.encode())


st.write("Upload your Excel or CSV file for Redpath processing:")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    processed_df = process_file(uploaded_file)
    if processed_df is not None:
        st.write("Processed Data:")
        st.dataframe(processed_df)

        csv_buffer = get_csv_download_link(processed_df)
        st.download_button(
            label="Download Processed File",
            data=csv_buffer,
            file_name="redpath_upload.csv",
            mime="text/csv",
        )
    else:
        st.error(
            "Failed to process the file. Please check the file format and content."
        )
