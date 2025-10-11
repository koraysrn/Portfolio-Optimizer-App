# portfolio_optimizer_app.py 
"""
Portföy Optimizasyon & Backtest (TwelveData)
Çalıştırma: streamlit run portfolio_optimizer_app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import date, timedelta
from pypfopt import expected_returns, risk_models, EfficientFrontier, plotting, exceptions
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from typing import Dict

# -------------------------
# Logging ve Sayfa Ayarları
# -------------------------
logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
st.set_page_config(page_title="Portföy Optimizasyon & Backtest", layout="wide")
st.title("Portföy Optimizasyon & Backtest Platformu")
st.markdown("Bu uygulama TwelveData üzerinden veri çekip portföy optimizasyonu, backtest ve performans metriklerini gösterir.")

# -------------------------
# Session State ve API Key
# -------------------------
if 'history' not in st.session_state:
    st.session_state.history = []
try:
    TD_API_KEY = st.secrets["TD_API_KEY"]
except Exception:
    TD_API_KEY = "ee8144ea9ae04f3e9eb92a6cf2967ff5"
    st.warning("TwelveData API anahtarı bulunamadı. Lütfen .streamlit/secrets.toml içinde TD_API_KEY ekleyin.")

# -------------------------
# Sidebar - Kullanıcı Girdileri
# -------------------------
with st.sidebar:
    st.header("1. Veri & Zaman")
    symbols_input = st.text_input("Hisse Senedi Sembolleri (virgülle ayırın)", value="AAPL,MSFT,GOOG,AMZN,NVDA,TSLA")
    start_date = st.date_input("Başlangıç Tarihi", value=date.today() - timedelta(days=5*365))
    end_date = st.date_input("Bitiş Tarihi", value=date.today())

    st.header("2. Optimizasyon")
    opt_goal = st.selectbox("Hedef", ["Maksimum Sharpe Oranı", "Minimum Volatilite (Risk)"])
    risk_model_choice = st.selectbox("Risk Modeli", ["Sample Covariance", "Ledoit-Wolf Shrinkage"])
    min_weight_pct = st.number_input("Her varlık için minimum ağırlık (%)", 0.0, 40.0, 0.0, step=0.5, help="Genellikle 0 olarak bırakılır.")
    max_weight_pct = st.number_input("Her varlık için maksimum ağırlık (%)", 1.0, 100.0, 40.0, step=0.5, help="Aşırı odaklanmayı önler.")

    st.header("3. Backtest & Raporlama")
    initial_capital = st.number_input("Başlangıç Sermayesi ($)", min_value=100, value=10000, step=100)
    benchmark_ticker = st.text_input("Benchmark (ETF)", value="SPY")
    risk_free_rate_pct = st.number_input("Risksiz Faiz (%) (annual)", min_value=0.0, value=2.0, step=0.1)

    optimize_button = st.button("🚀 Analizi Başlat")

# -------------------------
# Fonksiyonlar
# -------------------------
@st.cache_data(ttl=3600, show_spinner="📡 Fiyat verileri alınıyor...")
def fetch_twelvedata_prices(symbols, start_date, end_date, api_key):
    all_series = {}
    base_url = "https://api.twelvedata.com/time_series"
    start_str, end_str = pd.to_datetime(start_date).strftime("%Y-%m-%d"), pd.to_datetime(end_date).strftime("%Y-%m-%d")
    for sym in symbols:
        params = {"symbol": sym, "interval": "1day", "start_date": start_str, "end_date": end_str, "apikey": api_key, "outputsize": 5000}
        try:
            r = requests.get(base_url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if "values" in data:
                df = pd.DataFrame(data["values"]).set_index("datetime")
                df.index = pd.to_datetime(df.index)
                all_series[sym] = pd.to_numeric(df["close"].sort_index(), errors="coerce")
            else:
                st.warning(f"{sym} alınamadı: {data.get('message', 'Bilinmeyen API hatası')}")
        except Exception as e:
            st.error(f"Veri çekme hatası: {sym} - {e}")
        time.sleep(0.5)
    if not all_series: return pd.DataFrame()
    return pd.concat(all_series, axis=1)

def validate_bounds(n_assets, min_w, max_w):
    if min_w > max_w:
        st.warning(f"Min ağırlık > Max ağırlık. Değerler değiştirildi.")
        return max_w, min_w
    if n_assets * min_w > 1.0:
        st.error(f"Min ağırlıklar toplamı > %100. Kısıtlar yok sayılacak.")
        return 0.0, 1.0
    if n_assets * max_w < 1.0:
        st.error(f"Max ağırlıklar toplamı < %100. Kısıtlar yok sayılacak.")
        return 0.0, 1.0
    return min_w, max_w
    
def calculate_performance_metrics(returns: pd.Series, rf_annual_pct: float = 0.0) -> Dict[str, float]:
    if returns.empty or returns.isnull().all():
        return {"Sharpe": np.nan, "Sortino": np.nan, "Max Drawdown": np.nan}
    rf_daily = (1 + rf_annual_pct/100.0) ** (1/252) - 1
    excess = returns - rf_daily
    ann_factor = np.sqrt(252)
    sharpe = ann_factor * excess.mean() / (excess.std(ddof=0) if excess.std(ddof=0) != 0 else np.nan)
    downside = returns[returns < 0]
    down_stdev = downside.std(ddof=0)
    sortino = ann_factor * (returns.mean() - rf_daily) / (down_stdev if down_stdev != 0 else np.nan)
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative / rolling_max - 1).min()
    return {"Sharpe": float(sharpe), "Sortino": float(sortino), "Max Drawdown": float(drawdown)}

@st.cache_data(show_spinner="⏳ Backtest hesaplanıyor...")
def run_backtest(portfolio_returns: pd.Series, benchmark_returns: pd.Series, initial_capital: float) -> pd.DataFrame:
    port_cum = (1 + portfolio_returns).cumprod() * initial_capital
    bench_cum = (1 + benchmark_returns).cumprod() * initial_capital
    return pd.DataFrame({"Portföy": port_cum, "Benchmark": bench_cum})

# -------------------------
# Ana İş Akışı
# -------------------------
if optimize_button:
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    if not symbols:
        st.warning("Lütfen en az bir sembol girin."); st.stop()

    st.info(f"{len(symbols)} sembol için veri çekilecek: {', '.join(symbols)}")
    price_df_raw = fetch_twelvedata_prices(symbols, start_date, end_date, TD_API_KEY)
    
    if price_df_raw.empty:
        st.error("Hiçbir sembol için veri alınamadı."); st.stop()

   
    price_df = price_df_raw.dropna(axis='columns', how='all')
    removed_symbols = set(symbols) - set(price_df.columns)
    if removed_symbols:
        st.warning(f"Aşağıdaki semboller için veri bulunamadı ve analizden çıkarıldı: {', '.join(removed_symbols)}")
    if price_df.empty:
        st.error("Geçerli veri içeren hiçbir sembol kalmadı."); st.stop()
    price_df = price_df.ffill().bfill()
    price_df.dropna(how='any', inplace=True)
   

    if len(price_df) < 20:
        st.error(f"Hesaplama için yetersiz veri! ({len(price_df)} gün). Lütfen daha uzun bir zaman aralığı seçin.")
        st.stop()
        
    benchmark_df = fetch_twelvedata_prices([benchmark_ticker], start_date, end_date, TD_API_KEY)
    
    st.subheader("🔎 Veri Özeti")
    st.write(f"Veri aralığı: {price_df.index.min().strftime('%Y-%m-%d')} - {price_df.index.max().strftime('%Y-%m-%d')}")
    st.write(f"Analize dahil edilen sembol sayısı: {price_df.shape[1]}")
    st.dataframe(price_df.head())

    try:
        mu = expected_returns.mean_historical_return(price_df)
        if "Ledoit-Wolf" in risk_model_choice:
            S = risk_models.CovarianceShrinkage(price_df).ledoit_wolf()
        else:
            S = risk_models.sample_cov(price_df)
        
        n_assets = price_df.shape[1]
        min_w, max_w = validate_bounds(n_assets, min_weight_pct/100.0, max_weight_pct/100.0)
        bounds = tuple((min_w, max_w) for _ in range(n_assets))
        
        ef = EfficientFrontier(mu, S, weight_bounds=bounds)
        if "Sharpe" in opt_goal:
            ef.max_sharpe(risk_free_rate=risk_free_rate_pct/100.0)
        else:
            ef.min_volatility()
        weights = ef.clean_weights()
        ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate_pct/100.0)

        st.success("✅ Optimizasyon başarılı!")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Portföy", "📈 Backtest", "📉 Etkin Sınır", "🔍 Korelasyon & Geçmiş"])
        
        with tab1:
            st.subheader("Optimal Ağırlıklar ve Beklenen Performans")
            col1, col2 = st.columns([1,2])
            with col1:
                weights_df = pd.DataFrame(list(weights.items()), columns=["Hisse", "Ağırlık"])
                st.dataframe(weights_df[weights_df["Ağırlık"]>0].sort_values("Ağırlık", ascending=False).style.format({"Ağırlık":"{:.2%}"}))
            with col2:
                 if not weights_df[weights_df["Ağırlık"]>0].empty:
                    fig_pie = px.pie(weights_df[weights_df["Ağırlık"]>0], names="Hisse", values="Ağırlık", title="Portföy Dağılımı")
                    st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("Beklenen Performans Metrikleri")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Yıllık Beklenen Getiri", f"{ret*100:.2f}%")
            kpi2.metric("Yıllık Volatilite (Risk)", f"{vol*100:.2f}%")
            kpi3.metric("Sharpe Oranı", f"{sharpe:.2f}")

        with tab2:
            st.subheader(f"Geçmiş Performans: Portföy vs. {benchmark_ticker}")
            daily_returns = price_df.pct_change()
            portfolio_returns = (daily_returns * pd.Series(weights)).sum(axis=1)
            benchmark_returns = benchmark_df.pct_change().iloc[:, 0] if not benchmark_df.empty else pd.Series(dtype=float)
            aligned_p, aligned_b = portfolio_returns.align(benchmark_returns, join='inner')
            backtest_results = run_backtest(aligned_p, aligned_b, initial_capital)
            st.line_chart(backtest_results)
            
            st.subheader("Backtest Performans Metrikleri")
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.write("**Portföy**")
                st.json(calculate_performance_metrics(aligned_p, rf_annual_pct=risk_free_rate_pct))
            with metrics_col2:
                st.write(f"**{benchmark_ticker}**")
                st.json(calculate_performance_metrics(aligned_b, rf_annual_pct=risk_free_rate_pct))

        with tab3:
            st.subheader("Etkin Sınır (Efficient Frontier)")
            fig_ef, ax_ef = plt.subplots(figsize=(10, 6))
            plotting.plot_efficient_frontier(EfficientFrontier(mu, S), ax=ax_ef, show_assets=False)
            ax_ef.scatter(vol, ret, marker='*', color='red', s=200, label=f'Optimal Portföy ({opt_goal})')
            ax_ef.legend()
            st.pyplot(fig_ef)
            
        with tab4:
            st.subheader("Varlık Korelasyon Matrisi")
            corr_matrix = price_df.pct_change().corr()
            fig_corr, ax_corr = plt.subplots(figsize=(10, 7))
            
            sns.heatmap(corr_matrix, annot=True, cmap='viridis', fmt=".2f", ax=ax_corr)
            st.pyplot(fig_corr)

            st.subheader("Geçmiş Analizler")
            run_record = {"Tarih": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'), "Hedef": opt_goal, "Risk Modeli": risk_model_choice, "Varlıklar": ", ".join(price_df.columns), "Getiri (%)": f"{ret*100:.2f}", "Risk (%)": f"{vol*100:.2f}", "Sharpe": f"{sharpe:.2f}"}
            st.session_state.history.append(run_record)
            st.dataframe(pd.DataFrame(st.session_state.history).iloc[::-1])

    except exceptions.OptimizationError as e:
        st.error(f"Optimizasyon bir çözüm bulamadı. Hata: {e}")
        st.warning("Bu durum genellikle çok kısıtlayıcı ağırlık limitlerinden kaynaklanır. Lütfen kısıtları daha esnek hale getirip tekrar deneyin.")
        st.stop()
    except Exception as e:
        st.error(f"Analiz sırasında beklenmedik bir hata oluştu: {e}")
        logging.exception("Analysis failed")
        st.stop()
