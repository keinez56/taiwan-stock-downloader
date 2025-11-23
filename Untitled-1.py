import streamlit as st
import yfinance as yf
import pandas as pd
from io import BytesIO
import requests
import io
from datetime import datetime, timedelta
import time
import urllib3

# 忽略SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_institutional_trading(stock_code, start_date, end_date):
    """下載三大法人買賣超資訊"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/111.25 (KHTML, like Gecko) Chrome/99.0.2345.81 Safari/123.36'}

    # 轉換日期格式
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    all_data = []

    current_date = start
    while current_date <= end:
        if current_date.weekday() < 5:  # 跳過週末
            date_str = current_date.strftime('%Y%m%d')
            url = f'https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=csv'

            try:
                res = requests.get(url, headers=headers, verify=False)

                if res.status_code == 200 and res.text:
                    lines = [l for l in res.text.split('\n') if len(l.split(',"'))>=10]

                    if lines:
                        df = pd.read_csv(io.StringIO(','.join(lines)))
                        df = df.map(lambda s:(str(s).replace('=','').replace(',','').replace('"','')))

                        # 移除空白欄位和Unnamed欄位
                        df = df.loc[:, ~df.columns.str.startswith('Unnamed:')]
                        df = df.loc[:, df.columns.str.strip() != '']

                        if stock_code in df['證券代號'].values:
                            stock_data = df[df['證券代號'] == stock_code].copy()
                            stock_data['日期'] = current_date.strftime('%Y-%m-%d')
                            for col in stock_data.columns:
                                if col not in ['證券代號', '證券名稱', '日期']:
                                    stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')
                            all_data.append(stock_data)
            except:
                pass

            time.sleep(0.5)  # 避免請求過於頻繁

        current_date += timedelta(days=1)

    if all_data:
        result_df = pd.concat(all_data, ignore_index=True)
        return result_df
    else:
        return pd.DataFrame()

st.title("📈 台股歷史資料下載工具")

st.markdown("""
### 功能說明
- **股價資料**：快速下載個股的開高低收與成交量
- **三大法人資料**：包含外資、投信、自營商等17個詳細買賣超欄位
- **整合分析**：將股價與法人資料合併，方便進行投資分析

### 使用注意事項
- 三大法人資料下載較耗時，建議日期範圍控制在2個月內
- 為確保下載效率，超過60天範圍時將無法選擇三大法人資料
- 股價資料可選擇較長期間，不受此限制
""")

st.divider()

# 使用者輸入
code = st.text_input("請輸入台股代碼 (例如 2330 或 00878)", "2330")
market = st.radio("請選擇市場：", ["上市 (TW)", "上櫃 (TWO)"])
price_type = st.radio("股價類型：", ["調整後股價", "未調整股價"])
include_institutional = st.checkbox("包含三大法人買賣超資訊", value=False)

if include_institutional:
    st.warning("⚠️ 注意：下載三大法人資料需要較長時間，建議選擇較短的日期範圍")
    st.info("💡 提示：三大法人資料包含17個詳細欄位，提供完整的買賣超分析資訊")
    st.error("📅 重要限制：證交所三大法人買賣超 API 僅提供 2015 年之後的資料，如需下載 2015 年之前的資料，請取消勾選此選項")

# 設定預設日期範圍（最近30天到昨天）
from datetime import date
today = date.today()
default_end = today - timedelta(days=1)  # 昨天
default_start = default_end - timedelta(days=30)  # 30天前

start_date = st.date_input("開始日期", value=default_start)
end_date = st.date_input("結束日期", value=default_end)

# 日期驗證
if start_date > end_date:
    st.error("開始日期不能晚於結束日期")
elif end_date > today:
    st.warning("結束日期不能是未來日期")

# 檢查日期範圍限制
date_range = (end_date - start_date).days

# 檢查三大法人資料的日期限制（2015年之前）
institutional_date_warning = False
if include_institutional:
    min_institutional_date = date(2015, 1, 1)
    if start_date < min_institutional_date:
        st.error(f"❌ 三大法人資料僅支援 2015/01/01 之後的日期！您選擇的開始日期為 {start_date}，這將導致無法取得三大法人資料。")
        st.info("💡 解決方案：請將開始日期調整為 2015/01/01 之後，或取消勾選「包含三大法人買賣超資訊」選項以下載純股價資料")
        institutional_date_warning = True

if include_institutional and date_range > 60:
    st.error("⚠️ 選擇三大法人資料時，日期範圍不能超過2個月（60天）")
    st.info("建議縮短日期範圍以確保下載效率")
elif include_institutional and date_range > 30:
    st.warning(f"⏰ 已選擇 {date_range} 天的資料，下載三大法人資料可能需要 {date_range//2} 分鐘以上")

# 轉換成 yfinance 的 ticker 格式
suffix = ".TW" if market == "上市 (TW)" else ".TWO"
ticker = f"{code}{suffix}"

# 禁用下載按鈕如果日期範圍超過限制或日期早於2015年
download_disabled = (include_institutional and date_range > 60) or institutional_date_warning

if st.button("下載資料", disabled=download_disabled):
    st.write(f"正在下載 {ticker} 的資料...")

    try:
        # 根據用戶選擇設定auto_adjust參數
        auto_adjust = True if price_type == "調整後股價" else False
        st.info(f"股價類型設定: {'調整後股價' if auto_adjust else '未調整股價'}")

        # 下載股價資料
        stock_data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=auto_adjust)

        # 如果沒有資料，嘗試延長日期範圍
        if stock_data.empty:
            st.warning("首次嘗試沒有資料，嘗試延長日期範圍...")
            extended_end = end_date + timedelta(days=7)  # 延長一週
            stock_data = yf.download(ticker, start=start_date, end=extended_end, auto_adjust=auto_adjust)

        # 如果是未調整股價，移除Adj Close欄位
        if not stock_data.empty and price_type == "未調整股價":
            if 'Adj Close' in stock_data.columns:
                stock_data = stock_data.drop('Adj Close', axis=1)
            # 處理多層級欄位的情況
            elif isinstance(stock_data.columns, pd.MultiIndex):
                adj_close_cols = [col for col in stock_data.columns if 'Adj Close' in str(col)]
                if adj_close_cols:
                    stock_data = stock_data.drop(adj_close_cols, axis=1)

        # 顯示調試資訊
        if not stock_data.empty:
            st.success(f"成功下載 {len(stock_data)} 筆股價資料")
            st.info(f"欄位結構: {list(stock_data.columns)}")
        else:
            st.info(f"嘗試的參數: ticker={ticker}, start={start_date}, end={end_date}")

    except Exception as e:
        st.error(f"下載股價資料時發生錯誤: {e}")
        stock_data = pd.DataFrame()

    if stock_data.empty:
        st.error("查無股價資料，請確認以下幾點：")
        st.markdown("""
        - 股票代碼是否正確 (例如：2330 for 台積電)
        - 日期範圍是否包含交易日
        - 該股票在選定日期範圍內是否有交易
        - 網路連線是否正常
        """)

        # 提供一些建議
        st.info("建議：")
        st.markdown(f"- 嘗試使用較長的日期範圍")
        st.markdown(f"- 確認 {code} 是正確的台股代碼")
        st.markdown(f"- 確認選擇的市場 ({market}) 是正確的")
    else:
        # 下載三大法人資料
        institutional_data = None
        if include_institutional:
            st.write("正在下載三大法人買賣超資料...")
            try:
                institutional_data = get_institutional_trading(code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                if not institutional_data.empty:
                    st.success("三大法人資料下載完成！")
                else:
                    st.warning("無法取得三大法人資料")
            except Exception as e:
                st.warning(f"三大法人資料下載失敗: {e}")

        # 合併資料
        if institutional_data is not None and not institutional_data.empty:
            # 準備合併用的股價資料
            stock_df = stock_data.reset_index()

            # 處理多層級欄位名稱（如果存在）
            if isinstance(stock_df.columns, pd.MultiIndex):
                # 扁平化多層級欄位，保留第一層（價格類型）
                stock_df.columns = [col[0] if col[0] != 'Date' else 'Date' for col in stock_df.columns]

            stock_df['Date'] = pd.to_datetime(stock_df['Date']).dt.strftime('%Y-%m-%d')

            # 準備合併用的三大法人資料
            inst_df = institutional_data.copy()
            inst_df = inst_df.rename(columns={'日期': 'Date'})

            # 選擇所有三大法人欄位（排除證券代號、證券名稱和空白欄位）
            excluded_cols = ['證券代號', '證券名稱']
            inst_cols = [col for col in inst_df.columns
                        if col not in excluded_cols
                        and not col.startswith('Unnamed:')
                        and col.strip() != '']

            if inst_cols:
                inst_df_selected = inst_df[inst_cols]
                # 合併資料
                combined_data = pd.merge(stock_df, inst_df_selected, on='Date', how='left')
                st.info(f"已包含 {len(inst_cols)-1} 個三大法人欄位")  # -1 因為Date也在其中
            else:
                combined_data = stock_df
                st.warning("三大法人欄位格式異常，僅包含股價資料")
        else:
            combined_data = stock_data.reset_index()

            # 處理多層級欄位名稱（如果存在）
            if isinstance(combined_data.columns, pd.MultiIndex):
                # 扁平化多層級欄位，保留第一層（價格類型）
                combined_data.columns = [col[0] if col[0] != 'Date' else 'Date' for col in combined_data.columns]

            combined_data['Date'] = pd.to_datetime(combined_data['Date']).dt.strftime('%Y-%m-%d')

        st.success("資料處理完成！")

        # 轉 Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 股價資料工作表
            combined_data.to_excel(writer, sheet_name='股價與三大法人', index=False)

            # 如果有三大法人完整資料，另外建立工作表
            if institutional_data is not None and not institutional_data.empty:
                institutional_data.to_excel(writer, sheet_name='三大法人完整資料', index=False)

        output.seek(0)

        filename = f"{code}_{start_date}_{end_date}.xlsx"

        st.download_button(
            label="📥 點此下載 Excel",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.dataframe(combined_data.tail(10))  # 顯示最後 10 筆資料
