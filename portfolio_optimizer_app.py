# portfolio_optimizer_app.py
"""
Portföy Optimizasyon & Backtest (TwelveData)
Çalıştırma: streamlit run portfolio_optimizer_app.py
Not: TwelveData API anahtarınızı st.secrets["TD_API_KEY"] olarak saklayın.
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import date, timedelta
from pypfopt import expected_returns, risk_models, EfficientFrontier, plotting
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from typing import Dict

# -------------------------
# Logging (basit dosya loglama)
# -------------------------
logging.basicConfig(filename="app.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# -------------------------
# Sayfa Ayarları
# -------------------------
st.set_page_config(page_title="Portföy Optimizasyon & Backtest", layout="wide")
st.title("Portföy Optimizasyon & Backtest Platformu")
st.markdown("""
Bu uygulama TwelveData üzerinden veri çekip portföy optimizasyonu (Sharpe / Min Vol), backtest ve performans metriklerini gösterir.  
""")

# -------------------------
# Session state - geçmiş saklama
# -------------------------
if 'history' not in st.session_state:
    st.session_state.history = []

# -------------------------
# API Key
# -------------------------
try:
    TD_API_KEY = st.secrets["TD_API_KEY"]
except Exception:
    TD_API_KEY = None
    st.warning("TwelveData API anahtarı bulunamadı. Lütfen .streamlit/secrets.toml içinde TD_API_KEY ekleyin. (Devam etmek için fallback kullanılabilir.)")

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
    min_weight_pct = st.number_input("Her varlık için minimum ağırlık (%)", 0.0, 40.0, 0.0, step=0.5)
    max_weight_pct = st.number_input("Her varlık için maksimum ağırlık (%)", 1.0, 100.0, 40.0, step=0.5)

    st.header("3. Backtest & Raporlama")
    initial_capital = st.number_input("Başlangıç Sermayesi ($)", min_value=100, value=10000, step=100)
    benchmark_ticker = st.text_input("Benchmark (ETF)", value="SPY")
    risk_free_rate_pct = st.number_input("Risksiz Faiz (%) (annual)", min_value=0.0, value=2.0, step=0.1)

    st.header("Diğer")
    save_raw_csv = st.checkbox("Ham verileri CSV olarak kaydet", value=False)
    optimize_button = st.button("🚀 Analizi Başlat")

# -------------------------
# Yardımcı Fonksiyonlar
# -------------------------
@st.cache_data(ttl=3600, show_spinner="📡 Fiyat verileri cache'den alınıyor (1 saat)...")
def fetch_twelvedata_prices(symbols, start_date, end_date, api_key, interval="1day", sleep_between=0.6) -> pd.DataFrame:
    """
    TwelveData time_series endpoint ile sembol başına 'close' serisi alır.
    Dönen DataFrame sütunları: semboller; index: datetime (sorted)
    """
    if api_key is None:
        raise RuntimeError("TwelveData API anahtarı yok. Lütfen st.secrets['TD_API_KEY'] ekleyin.")

    all_series = {}
    base_url = "https://api.twelvedata.com/time_series"
    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")

    for sym in symbols:
        params = {
            "symbol": sym,
            "interval": interval,
            "start_date": start_str,
            "end_date": end_str,
            "apikey": api_key,
            "outputsize": 5000
        }
        try:
            r = requests.get(base_url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if "values" in data:
                df = pd.DataFrame(data["values"])
                # datetime sütununu index yap
                if "datetime" in df.columns:
                    df["datetime"] = pd.to_datetime(df["datetime"])
                    df = df.set_index("datetime").sort_index()
                # close'a çevir
                if "close" in df.columns:
                    series = pd.to_numeric(df["close"], errors="coerce")
                    all_series[sym] = series
                else:
                    st.warning(f"{sym}: 'close' verisi yok.")
                    logging.warning(f"{sym}: 'close' not found in API response: {data}")
            else:
                msg = data.get("message", "Unknown API error")
                st.warning(f"{sym} alınamadı: {msg}")
                logging.warning(f"TwelveData message for {sym}: {data}")
        except requests.exceptions.HTTPError as he:
            st.error(f"{sym} HTTP hatası: {he}")
            logging.error(f"{sym} HTTP error: {he}")
        except Exception as e:
            st.error(f"{sym} veri çekme hatası: {e}")
            logging.exception(e)

        time.sleep(sleep_between)  # nazikçe bekle (rate limit koruması)

    if not all_series:
        return pd.DataFrame()

    price_df = pd.concat(all_series, axis=1)
    price_df.columns = price_df.columns  # semboller zaten sütun isimleri
    price_df = price_df.sort_index().ffill().bfill().dropna(how="any")
    return price_df

def validate_bounds(n_assets: int, min_w: float, max_w: float):
    """Kullanıcı tarafından girilen min/max ağırlıkları doğrula, gerekirse düzelt."""
    if min_w > max_w:
        st.warning("Min ağırlık > Max ağırlık; yerleri değiştirildi.")
        min_w, max_w = max_w, min_w
    # Toplam min ağırlıklar %100'ü aşıyorsa sıfırla
    if n_assets * min_w > 1.0:
        st.warning("Toplam min ağırlıklar %100'ü aşıyor; min/max kısıtları kaldırıldı.")
        return 0.0, 1.0
    # Toplam max ağırlıklar %100'ün altındaysa kısıtları kaldır
    if n_assets * max_w < 1.0:
        st.warning("Toplam max ağırlıklar %100'e ulaşmıyor; min/max kısıtları kaldırıldı.")
        return 0.0, 1.0
    return min_w, max_w

def calculate_performance_metrics(returns: pd.Series, rf_annual_pct: float = 0.0) -> Dict[str, float]:
    """
    Temel performans metrikleri: Sharpe (annual), Sortino (annual), Max Drawdown.
    returns: günlük getiri serisi (arithmetic)
    rf_annual_pct: yıllık risksiz faiz yüzde (örn 2.0)
    """
    if returns.empty or returns.isnull().all():
        return {"Sharpe": np.nan, "Sortino": np.nan, "Max Drawdown": np.nan}

    rf_daily = (1 + rf_annual_pct/100.0) ** (1/252) - 1
    excess = returns - rf_daily
    ann_factor = np.sqrt(252)
    sharpe = ann_factor * excess.mean() / (excess.std(ddof=0) if excess.std(ddof=0) != 0 else np.nan)

    # Sortino: downside std
    downside = returns[returns < 0]
    down_stdev = downside.std(ddof=0)
    sortino = ann_factor * (returns.mean() - rf_daily) / (down_stdev if down_stdev != 0 else np.nan)

    # Max Drawdown
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative / rolling_max - 1).min()

    return {"Sharpe": float(sharpe) if np.isfinite(sharpe) else np.nan,
            "Sortino": float(sortino) if np.isfinite(sortino) else np.nan,
            "Max Drawdown": float(drawdown) if np.isfinite(drawdown) else np.nan}

@st.cache_data(show_spinner="⏳ Backtest hesaplanıyor...")
def run_backtest(portfolio_returns: pd.Series, benchmark_returns: pd.Series, initial_capital: float) -> pd.DataFrame:
    """Cumulative değerleri döndürür."""
    port_cum = (1 + portfolio_returns).cumprod() * initial_capital
    bench_cum = (1 + benchmark_returns).cumprod() * initial_capital
    df = pd.DataFrame({"Portföy": port_cum, "Benchmark": bench_cum})
    return df

# -------------------------
# Ana İş Akışı
# -------------------------
if optimize_button:
    # Parse semboller
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    if len(symbols) == 0:
        st.warning("Lütfen en az bir sembol girin.")
        st.stop()

    # İleri kullanıcı bilgilendirmesi
    st.info(f"{len(symbols)} sembol için veri çekilecek: {', '.join(symbols)}")
    logging.info(f"Run started for symbols: {symbols}, range: {start_date} - {end_date}")

    # Veri çek
    try:
        price_df = fetch_twelvedata_prices(symbols, start_date, end_date, TD_API_KEY)
    except Exception as e:
        st.error(f"Veri çekme sırasında beklenmeyen hata: {e}")
        logging.exception("fetch_twelvedata_prices failed")
        st.stop()

    # Benchmark verisi
    benchmark_df = pd.DataFrame()
    try:
        benchmark_df = fetch_twelvedata_prices([benchmark_ticker], start_date, end_date, TD_API_KEY)
    except Exception:
        pass

    # Kontroller
    if price_df.empty:
        st.error("Veri alınamadı. Lütfen API anahtarınızı, sembolleri ve tarih aralığını kontrol edin.")
        st.stop()

    if benchmark_df.empty:
        st.warning("Benchmark verisi alınamadı veya eksik. Backtest karşılaştırması sınırlı olabilir.")

    if save_raw_csv:
        try:
            price_df.to_csv("prices_raw.csv")
            st.success("Ham veriler prices_raw.csv olarak kaydedildi.")
        except Exception as e:
            st.warning(f"Ham veriler kaydedilemedi: {e}")

    # Temel istatistikler göster
    st.subheader("🔎 Veri Özeti")
    st.write(f"Veri aralığı: {price_df.index.min().strftime('%Y-%m-%d')} - {price_df.index.max().strftime('%Y-%m-%d')}")
    st.write(f"Gözlem sayısı: {price_df.shape[0]} satır, {price_df.shape[1]} sembol")
    st.dataframe(price_df.head())

    # Optimizasyon ön hazırlık
    try:
        mu = expected_returns.mean_historical_return(price_df)
    except Exception as e:
        st.error(f"Getiri hesaplanırken hata: {e}")
        logging.exception("mean_historical_return failed")
        st.stop()

    # Risk matrisi seçimi
    try:
        if "Ledoit" in risk_model_choice:
            S = risk_models.CovarianceShrinkage(price_df).ledoit_wolf()
        else:
            S = risk_models.sample_cov(price_df)
    except Exception as e:
        st.error(f"Kovaryans matrisi oluşturulamadı: {e}")
        logging.exception("covariance calculation failed")
        st.stop()

    # Bound doğrulama
    n_assets = price_df.shape[1]
    min_w, max_w = validate_bounds(n_assets, min_weight_pct/100.0, max_weight_pct/100.0)
    bounds = tuple((min_w, max_w) for _ in range(n_assets))

    # Optimizasyon
    try:
        ef = EfficientFrontier(mu, S, weight_bounds=bounds)
        if "Sharpe" in opt_goal:
            ef.max_sharpe(risk_free_rate=risk_free_rate_pct/100.0)
        else:
            ef.min_volatility()
        weights = ef.clean_weights()
        ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate_pct/100.0)
    except Exception as e:
        st.error(f"Optimizasyon başarısız: {e}")
        logging.exception("Optimization failed")
        st.stop()

    # Sonuçların gösterimi
    st.success("✅ Optimizasyon başarılı!")
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Portföy", "📈 Backtest", "📉 Etkin Sınır", "🔍 Korelasyon & Geçmiş"])

    # --- TAB 1: Portföy ---
    with tab1:
        st.subheader("Optimal Ağırlıklar")
        weights_df = pd.DataFrame(list(weights.items()), columns=["Hisse", "Ağırlık"]).sort_values("Ağırlık", ascending=False)
        st.dataframe(weights_df.style.format({"Ağırlık": "{:.2%}"}))

        # Pasta grafiği
        nonzero = weights_df[weights_df["Ağırlık"] > 0]
        if not nonzero.empty:
            fig_pie = px.pie(nonzero, names="Hisse", values="Ağırlık", title="Portföy Dağılımı", hole=0.3)
            fig_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.write("Tüm ağırlıklar 0 çıktı.")

        st.subheader("Beklenen Performans")
        col1, col2, col3 = st.columns(3)
        col1.metric("Yıllık Beklenen Getiri", f"{ret*100:.2f}%")
        col2.metric("Yıllık Volatilite", f"{vol*100:.2f}%")
        col3.metric("Sharpe Oranı", f"{sharpe:.2f}")

        # Ağırlıkları CSV olarak indir
        csv_weights = weights_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Ağırlıkları CSV Olarak İndir", data=csv_weights, file_name="optimal_weights.csv", mime="text/csv")

    # --- TAB 2: Backtest ---
    with tab2:
        st.subheader("Backtest: Portföy vs Benchmark")
        daily_returns = price_df.pct_change().dropna()

        # weights Series align
        weights_series = pd.Series(weights)
        # Eğer sütun isimleri ile ağırlık anahtarları uyuşmazsa doldur
        weights_series = weights_series.reindex(price_df.columns).fillna(0.0)

        portfolio_returns = (daily_returns * weights_series).sum(axis=1)
        benchmark_returns = pd.Series(dtype=float)
        if not benchmark_df.empty:
            benchmark_returns = benchmark_df.pct_change().dropna().iloc[:, 0]
        else:
            # Eğer benchmark alınamadıysa SPY'ı price_df içinden dene
            if benchmark_ticker in price_df.columns:
                benchmark_returns = price_df[benchmark_ticker].pct_change().dropna()
            else:
                st.warning("Benchmark verisi yok; backtest karşılaştırması atlandı.")

        # Align
        if not benchmark_returns.empty:
            aligned_p, aligned_b = portfolio_returns.align(benchmark_returns, join='inner')
        else:
            aligned_p = portfolio_returns
            aligned_b = pd.Series(0, index=aligned_p.index)  # dummy

        # Backtest dataframe
        backtest_df = run_backtest(aligned_p, aligned_b, initial_capital)
        st.line_chart(backtest_df)

        # Metrikler
        metrics_port = calculate_performance_metrics(aligned_p, rf_annual_pct=risk_free_rate_pct)
        metrics_bench = calculate_performance_metrics(aligned_b, rf_annual_pct=risk_free_rate_pct) if not aligned_b.empty else {}
        st.write("Portföy Metrikleri:")
        st.table(pd.DataFrame([metrics_port]).T.rename(columns={0: "Değer"}).style.format("{:.4f}"))
        if metrics_bench:
            st.write(f"{benchmark_ticker} Metrikleri:")
            st.table(pd.DataFrame([metrics_bench]).T.rename(columns={0: "Değer"}).style.format("{:.4f}"))

    # --- TAB 3: Etkin Sınır ---
    with tab3:
        st.subheader("Etkin Sınır (Efficient Frontier)")
        fig_ef, ax_ef = plt.subplots(figsize=(10, 6))
        try:
            plotting.plot_efficient_frontier(EfficientFrontier(mu, S), ax=ax_ef, show_assets=False)
            # point for chosen portfolio
            ax_ef.scatter(vol, ret, marker='*', color='red', s=200, label=f'Optimal ({opt_goal})')
            ax_ef.legend()
            st.pyplot(fig_ef)
        except Exception as e:
            st.error(f"Etkin sınır çiziminde hata: {e}")
            logging.exception("Efficient frontier plotting error")

    # --- TAB 4: Korelasyon & Geçmiş Çalışmalar ---
    with tab4:
        st.subheader("Korelasyon Matrisi")
        corr = price_df.pct_change().dropna().corr()
        fig_corr, ax_corr = plt.subplots(figsize=(10, 7))
        sns.heatmap(corr, annot=True, cmap="viridis", fmt=".2f", ax=ax_corr)
        st.pyplot(fig_corr)

        # Çalışma geçmişi kaydet ve göster
        run_record = {
            "Tarih": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Hedef": opt_goal,
            "RiskModel": "Ledoit-Wolf" if "Ledoit" in risk_model_choice else "SampleCov",
            "Varlık Sayısı": n_assets,
            "Getiri (%)": f"{ret*100:.2f}",
            "Risk (%)": f"{vol*100:.2f}",
            "Sharpe": f"{sharpe:.2f}"
        }
        st.session_state.history.append(run_record)
        history_df = pd.DataFrame(st.session_state.history[::-1])  # ters sırada göster (en son başta)
        st.dataframe(history_df)

        # Geçmişi indir
        csv_hist = history_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Geçmişi CSV Olarak İndir", data=csv_hist, file_name="analysis_history.csv", mime="text/csv")

    logging.info(f"Run finished for symbols: {symbols} - Return: {ret:.4f}, Vol: {vol:.4f}, Sharpe: {sharpe:.4f}")


                         # çalıştırmak için: streamlit run portfolio_optimizer_app.py
