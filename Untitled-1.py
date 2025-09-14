import streamlit as st
import yfinance as yf
import pandas as pd
from io import BytesIO

st.title("📈 台股歷史資料下載工具")

# 使用者輸入
code = st.text_input("請輸入台股代碼 (例如 2330 或 00878)", "2330")
market = st.radio("請選擇市場：", ["上市 (TW)", "上櫃 (TWO)"])
price_type = st.radio("股價類型：", ["調整後股價", "未調整股價"])
start_date = st.date_input("開始日期")
end_date = st.date_input("結束日期")

# 轉換成 yfinance 的 ticker 格式
suffix = ".TW" if market == "上市 (TW)" else ".TWO"
ticker = f"{code}{suffix}"

if st.button("下載資料"):
    st.write(f"正在下載 {ticker} 的資料...")

    # 根據使用者選擇決定是否調整股價
    auto_adjust = True if price_type == "調整後股價" else False
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=auto_adjust)

    if data.empty:
        st.error("查無資料，請確認代碼或日期。")
    else:
        st.success("下載完成！")

        # 轉 Excel
        output = BytesIO()
        data.to_excel(output)
        output.seek(0)

        filename = f"{code}_{start_date}_{end_date}.xlsx"

        st.download_button(
            label="📥 點此下載 Excel",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.dataframe(data.tail(10))  # 顯示最後 10 筆資料
