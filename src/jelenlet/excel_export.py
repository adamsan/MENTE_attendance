import pandas as pd


def to_excel(fname, df):
    with pd.ExcelWriter(fname, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)

        worksheet = writer.sheets["Sheet1"]

        # set columns widhts to it's max text length
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
            col_idx = df.columns.get_loc(column)
            worksheet.set_column(col_idx, col_idx, column_length)

        worksheet.freeze_panes(1, 3)
        color_alternating_rows(writer, worksheet, df)


def color_alternating_rows(writer, worksheet, df):
    # row_format_even = writer.book.add_format({"bg_color": "#DDDDDD", "border": 1})
    # row_format_odd = writer.book.add_format({"bg_color": "#FFFFFF", "border": 1})
    row_format_even = writer.book.add_format({"bg_color": "#DDDDDD", "right": 1})
    row_format_odd = writer.book.add_format({"bg_color": "#FFFFFF", "right": 1})

    worksheet.conditional_format(
        first_row=1,
        first_col=0,
        last_row=len(df),
        last_col=len(df.columns) - 1,
        options={
            "type": "formula",
            "criteria": "=MOD(ROW(),2)=0",
            "format": row_format_even,
        },
    )

    worksheet.conditional_format(
        first_row=1,
        first_col=0,
        last_row=len(df),
        last_col=len(df.columns) - 1,
        options={
            "type": "formula",
            "criteria": "=MOD(ROW(),2)=1",
            "format": row_format_odd,
        },
    )
