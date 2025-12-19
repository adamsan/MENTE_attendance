import pandas as pd


def to_excel(fname, df):
    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)

        worksheet = writer.sheets["Sheet1"]

        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
            col_idx = df.columns.get_loc(column)
            worksheet.set_column(col_idx, col_idx, column_length)

        worksheet.freeze_panes(0, 3)
