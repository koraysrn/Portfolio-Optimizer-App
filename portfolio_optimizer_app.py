# portfolio_optimizer_app.py
"""
Portföy Analisti
Çalıştırma: streamlit run portfolio_optimizer_app.py
TD_API_KEY yalnızca .streamlit/secrets.toml içinden okunur; yoksa uygulama durur.
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import logging
import io
from datetime import date, timedelta
from typing import Dict, List, Tuple

from pypfopt import expected_returns, risk_models, EfficientFrontier
import plotly.express as px
import plotly.graph_objects as go

# -------------------------
# Logging & Page Config
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

st.set_page_config(
    page_title="Portföy Analisti",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# CSS 
# -------------------------
st.markdown(
    """
    <style>
    :root {
        --bg: #0b1020;
        --card: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        --muted: #9fb0d6;
        --accent: #4cc9f0;
        --accent-2: #7b61ff;
    }
    .stApp { background: var(--bg); color: #e6eef8; }
    #MainMenu, footer, header {visibility: hidden;}
    .app-header {
        display:flex; align-items:center; gap:16px; padding:18px 22px; border-radius:12px;
        background: linear-gradient(90deg, rgba(16,24,40,0.6), rgba(8,12,20,0.6));
        margin-bottom: 18px; box-shadow: 0 8px 24px rgba(2,6,23,0.7);
    }
    .app-title { font-size:20px; font-weight:700; color: #ffffff; }
    .app-sub { color: var(--muted); font-size:13px; margin-top:4px; }

    .card {
        background: var(--card); border: 1px solid rgba(255,255,255,0.03);
        padding: 14px; border-radius:12px; box-shadow: 0 6px 18px rgba(2,6,23,0.6);
        margin-bottom: 14px;
    }
    .card-title { font-weight:700; margin-bottom:8px; color:#e6eef8; }
    .muted { color: var(--muted); font-size:13px; }

    [data-testid="stSidebar"] img { display:block; margin-left:auto; margin-right:auto; margin-bottom:10px; }

    .small-muted { color: var(--muted); font-size:12px; }

    @media (max-width: 900px) {
        .app-header { flex-direction: column; align-items:flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Session state init
# -------------------------
if 'history' not in st.session_state:
    st.session_state.history = []
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'new_run_recorded' not in st.session_state:
    st.session_state.new_run_recorded = False

# -------------------------
# Mandatory secret: only .streamlit/secrets.toml
# -------------------------
TD_API_KEY = st.secrets.get("TD_API_KEY")
if not TD_API_KEY:
    st.error(
        "⚠️ TD_API_KEY bulunamadı. Lütfen .streamlit/secrets.toml dosyanıza "
        "TD_API_KEY = \"<api_key>\" ekleyin veya Streamlit Cloud'da Secrets olarak ekleyin."
    )
    st.stop()

# -------------------------
# Top header
# -------------------------
with st.container():
    st.markdown(
        """
        <div class="app-header">
            <div style="display:flex;flex-direction:column;">
                <div class="app-title">Pro Portföy Analisti · Premium (GÜNCEL & UYARISIZ)</div>
                <div class="app-sub">Modern portföy optimizasyonu · interaktif analiz · güzel UX</div>
            </div>
            <div style="margin-left:auto; text-align:right;">
                <div class="muted">Versiyon: <strong>1.0.5</strong></div>
                <div class="muted">Data source: TwelveData API</div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )

# -------------------------
# Sidebar - Inputs
# -------------------------
with st.sidebar:
    st.image("https://i.imgur.com/Q0kdl0C.png", width=120)
    st.header("Ayarlar")
    with st.expander("1. Varlıklar & Tarih", expanded=True):
        symbols_input = st.text_input("Semboller (virgül ile ayır)", "AAPL,MSFT,GOOG,AMZN,NVDA,TSLA")
        start_date = st.date_input("Başlangıç", date.today() - timedelta(days=5*365))
        end_date = st.date_input("Bitiş", date.today())
        benchmark_ticker = st.text_input("Benchmark (örn. SPY)", "SPY")
    with st.expander("2. Optimizasyon", expanded=False):
        opt_goal = st.selectbox("Hedef", ["Maksimum Sharpe Oranı", "Minimum Volatilite (Risk)"])
        risk_model_choice = st.selectbox("Risk Modeli", ["Ledoit-Wolf Shrinkage", "Sample Covariance"])
        
        min_weight_pct, max_weight_pct = st.slider("Ağırlık aralığı (%)", 0.0, 100.0, (0.0, 40.0), 0.5)
    with st.expander("3. Backtest & Görünüm", expanded=False):
        initial_capital = st.number_input("Başlangıç ($)", 1000, 10_000_000, 10000, 1000)
        risk_free_rate_pct = st.number_input("Risksiz faiz (%)", 0.0, 10.0, 2.0, 0.1)
    st.markdown("---")
   
    if st.button("🚀 Analizi Başlat", width='stretch'):
        st.session_state.analysis_complete = True
        st.session_state.results = {}
        st.session_state.new_run_recorded = False

# -------------------------
# Utilities & Functions
# -------------------------
@st.cache_data(ttl=3600, show_spinner="📡 Fiyat verileri alınıyor...")
def fetch_twelvedata_prices(symbols: List[str], start_date: date, end_date: date, api_key: str) -> pd.DataFrame:
    base = "https://api.twelvedata.com/time_series"
    all_series = {}
    for i, s in enumerate(symbols):
        params = {"symbol": s, "interval": "1day", "start_date": start_date.strftime("%Y-%m-%d"),
                  "end_date": end_date.strftime("%Y-%m-%d"), "apikey": api_key, "outputsize": 5000}
        try:
            r = requests.get(base, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if "values" in data:
                df = pd.DataFrame(data["values"]).set_index("datetime")
                df.index = pd.to_datetime(df.index)
                all_series[s] = pd.to_numeric(df["close"].sort_index(), errors="coerce")
            else:
                logging.warning(f"Symbol {s} fetch issue: {data.get('message')}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Fetch error for {s}: {e}")
        time.sleep(0.35)
    if not all_series:
        return pd.DataFrame()
    return pd.concat(all_series, axis=1)

def validate_bounds(n_assets: int, min_w: float, max_w: float) -> Tuple[float, float]:
    if min_w > max_w:
        return max_w, min_w
    if n_assets * min_w > 1.0:
        return 0.0, 1.0
    return min_w, max_w

def calculate_performance_metrics(returns: pd.Series, rf_annual_pct: float = 2.0) -> Dict[str, float]:
    if returns.empty or returns.isnull().all() or len(returns) < 2:
        return {"Yıllık Getiri": 0.0, "Yıllık Volatilite": 0.0, "Sharpe": 0.0, "Max Drawdown": 0.0}
    rf_daily = (1 + rf_annual_pct / 100.0) ** (1/252) - 1
    ann_ret = (1 + returns.mean()) ** 252 - 1
    ann_vol = returns.std() * np.sqrt(252)
    excess = returns - rf_daily
    sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() != 0 else 0.0
    cumulative = (1 + returns).cumprod()
    dd = (cumulative / cumulative.cummax() - 1).min()
    return {"Yıllık Getiri": float(ann_ret), "Yıllık Volatilite": float(ann_vol), "Sharpe": float(sharpe), "Max Drawdown": float(dd)}

def run_backtest(portfolio_returns: pd.Series, benchmark_returns: pd.Series, initial_capital: float) -> pd.DataFrame:
    df = pd.DataFrame({"Portföy": portfolio_returns, "Benchmark": benchmark_returns}).dropna()
    return (1 + df).cumprod() * initial_capital

def compute_efficient_frontier_points(mu: pd.Series, S: pd.DataFrame, min_w: float, max_w: float, n_points: int = 100) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, float]]]:
    mu_vals = mu.values
    lo = max(1e-6, mu_vals.min() * 0.8) 
    hi = max(mu_vals.max() * 1.2, lo + 1e-6)
    target_returns = np.linspace(lo, hi, n_points)
    vols, rets, weights_list = [], [], []
    for tr in target_returns:
        try:
            ef_temp = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
            w = ef_temp.efficient_return(target_return=tr) 
            clean_w = ef_temp.clean_weights() 
            w_series = pd.Series(clean_w)
            port_ret = float(np.dot(w_series.values, mu_vals))
            port_vol = float(np.sqrt(w_series.values.T @ S.values @ w_series.values))
            
            vols.append(port_vol)
            rets.append(port_ret)
            weights_list.append({k: float(v) for k, v in clean_w.items()})
        except (ValueError, TypeError):
            continue
    return np.array(vols), np.array(rets), weights_list

def weights_to_csv(weights: Dict[str, float]) -> bytes:
    df = pd.DataFrame.from_dict(weights, orient='index', columns=['weight'])
    df.index.name = 'symbol'
    return df.to_csv().encode('utf-8')

# -------------------------
# Main workflow
# -------------------------
if not st.session_state.analysis_complete:
    st.markdown("""
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div class="card-title">Hoşgeldiniz — Başlamak için sol panelden parametreleri ayarla</div>
                    <div class="muted">Analizi başlattığınızda veriler çekilecek, optimizasyon yapılacak ve sonuçlar interaktif panoda görünecek.</div>
                </div>
                <div style="text-align:right">
                    <div class="muted">İpucu: Etkin Sınır grafiği artık daha pürüzsüz bir görsel için sabit 100 nokta ile hesaplanmaktadır.</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    with st.spinner("Analiz başlatılıyor — veriler çekiliyor ve optimizasyon yapılıyor..."):
        try:
            symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
            if not symbols:
                st.error("Lütfen en az bir sembol girin.")
                st.stop()
            all_symbols = list(dict.fromkeys(symbols + [benchmark_ticker.strip().upper()]))
            price_data = fetch_twelvedata_prices(all_symbols, start_date, end_date, TD_API_KEY)
            if price_data.empty:
                st.error("Hiçbir veri alınamadı. Sembol veya API limiti olabilir.")
                st.stop()
            price_df_raw = price_data.loc[:, [c for c in symbols if c in price_data.columns]].dropna(axis=1, how='all')
            benchmark_df = price_data[[benchmark_ticker]].dropna() if benchmark_ticker in price_data.columns else pd.DataFrame()
            if price_df_raw.empty:
                st.error("Geçerli hisse verisi bulunamadı.")
                st.stop()
            price_df = price_df_raw.ffill().bfill().dropna()
            if len(price_df) < 60:
                st.warning(f"Yetersiz veri: sadece {len(price_df)} gün var. En az 60 gün önerilir.")
            
            mu = expected_returns.mean_historical_return(price_df)
            if "Ledoit-Wolf" in risk_model_choice:
                S = risk_models.CovarianceShrinkage(price_df).ledoit_wolf() 
            else:
                S = risk_models.sample_cov(price_df)

            n_assets = price_df.shape[1]
            min_w, max_w = validate_bounds(n_assets, min_weight_pct / 100.0, max_weight_pct / 100.0)
            ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
            
            if "Sharpe" in opt_goal:
                ef.max_sharpe(risk_free_rate=risk_free_rate_pct / 100.0)
            else:
                ef.min_volatility()
            
            weights = ef.clean_weights()
            exp_ret, exp_vol, exp_sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate_pct / 100.0)
            
            st.session_state.results = {
                "price_df": price_df,
                "benchmark_df": benchmark_df,
                "weights": weights,
                "exp_ret": exp_ret,
                "exp_vol": exp_vol,
                "exp_sharpe": exp_sharpe,
                "mu": mu,
                "S": S,
                "min_w": min_w,
                "max_w": max_w
            }
            st.success("Optimizasyon tamamlandı ✅")
        except Exception as e:
            logging.error("Analiz hatası", exc_info=True)
            st.error(f"Analiz sırasında hata oluştu: {e}")
            st.session_state.analysis_complete = False
            st.stop()

# Results rendering
if st.session_state.results:
    results = st.session_state.results
    price_df = results["price_df"]
    benchmark_df = results["benchmark_df"]
    weights = results["weights"]
    exp_ret, exp_vol, exp_sharpe = results["exp_ret"], results["exp_vol"], results["exp_sharpe"]
    mu, S = results["mu"], results["S"]

    # KPIs
    with st.container():
        st.markdown("<div class='card'><div class='card-title'>Genel Bakış</div>", unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns([1,1,1,1])
        k1.metric("Beklenen Getiri (yıllık)", f"{exp_ret:.2%}")
        k2.metric("Beklenen Volatilite", f"{exp_vol:.2%}")
        k3.metric("Beklenen Sharpe", f"{exp_sharpe:.3f}")
        corr_mat = price_df.pct_change().corr().fillna(0)
        avg_corr = corr_mat.values[np.triu_indices_from(corr_mat.values, k=1)].mean() if price_df.shape[1] > 1 else 0.0
        diversification_index = float(1 - abs(avg_corr))
        k4.metric("Diversification Index", f"{diversification_index:.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Tabs
    tab_summary, tab_backtest, tab_analytics, tab_history = st.tabs(["📊 Veri Özeti", "📈 Backtest", "📉 Analitik Araçlar", "🗂 Geçmiş"])

    # TAB SUMMARY
    with tab_summary:
        st.markdown("<div class='card'><div class='card-title'>Optimal Portföy</div>", unsafe_allow_html=True)
        col_l, col_r = st.columns([0.5, 0.5])
        with col_l:
            weights_df = pd.DataFrame.from_dict(weights, orient='index', columns=['weight']).sort_values('weight', ascending=False)
           
            st.dataframe(weights_df.style.format({"weight": "{:.2%}"}), width='stretch') 
            csv_bytes = weights_to_csv(weights)
           
            st.download_button("📥 Ağırlıkları CSV indir", data=csv_bytes, file_name="weights.csv", mime="text/csv", key="download_weights", width='stretch')
        with col_r:
            fig_pie = px.pie(weights_df.reset_index(), names='index', values='weight', hole=0.36, title="Portföy Dağılımı", template="plotly_dark")
            fig_pie.update_traces(textinfo="percent+label", textposition='inside')
            
            
            st.plotly_chart(fig_pie, config={"responsive": True}) 
            
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'><div class='card-title'>İncelenen Fiyat Verileri</div>", unsafe_allow_html=True)
        
        filter_option = st.radio(
            "Görüntülenecek Veri",
            ('Son 5 Gün', 'Belirli Bir Gün', 'Tarih Aralığı'),
            horizontal=True,
            label_visibility="collapsed"
        )

        filtered_df = pd.DataFrame()
        if not price_df.empty:
            min_date_in_data = price_df.index.min().date()
            max_date_in_data = price_df.index.max().date()
            
            if filter_option == 'Son 5 Gün':
                filtered_df = price_df.tail(5)
            elif filter_option == 'Belirli Bir Gün':
                selected_date = st.date_input("Bir gün seçin", value=max_date_in_data, min_value=min_date_in_data, max_value=max_date_in_data)
                filtered_df = price_df[price_df.index.date == selected_date]
            elif filter_option == 'Tarih Aralığı':
                date_selection = st.date_input(
                    "Bir tarih aralığı seçin",
                    value=(max_date_in_data - timedelta(days=30), max_date_in_data),
                    min_value=min_date_in_data,
                )
                
                if len(date_selection) == 2:
                    start_range, end_range = date_selection
                    if start_range > end_range:
                        st.warning("Başlangıç tarihi bitiş tarihinden sonra olamaz. Lütfen geçerli bir aralık seçin.")
                    else:
                        filtered_df = price_df.loc[start_range.strftime('%Y-%m-%d'):end_range.strftime('%Y-%m-%d')]
                else:
                    st.info("Lütfen bitiş tarihini de giriniz.")

        
        st.dataframe(filtered_df.style.format("{:,.2f}"), width='stretch') 
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB BACKTEST
    with tab_backtest:
        st.markdown("<div class='card'><div class='card-title'>Backtest: Portföy vs Benchmark</div>", unsafe_allow_html=True)
        daily_returns = price_df.pct_change().dropna()
        weights_series = pd.Series(weights)
        common_assets = daily_returns.columns.intersection(weights_series.index)
        if not common_assets.empty:
            port_returns = (daily_returns[common_assets] * weights_series[common_assets]).sum(axis=1)
        else:
             port_returns = pd.Series(dtype=float) 

        if not benchmark_df.empty and benchmark_df.shape[1] > 0:
            bench_returns = benchmark_df.iloc[:, 0].pct_change().dropna()
            p_aligned, b_aligned = port_returns.align(bench_returns, join='inner')
            if p_aligned.empty and not port_returns.empty:
                 p_aligned = port_returns
        else:
            p_aligned = port_returns
            b_aligned = pd.Series(dtype=float)

        if p_aligned.empty:
            st.warning("Backtest için yeterli portföy getirisi verisi yok.")
            bt_df = pd.DataFrame(index=price_df.index)
        else:
             bt_df = run_backtest(p_aligned, b_aligned, initial_capital)
        
        if not bt_df.empty:
            df_reset = bt_df.reset_index()
            idx_col = df_reset.columns[0]
            df_melt = df_reset.melt(id_vars=idx_col, var_name='variable', value_name='value')
            df_melt = df_melt.rename(columns={idx_col: 'Tarih'})

            fig = px.line(df_melt, x='Tarih', y='value', color='variable',
                          labels={'value': 'Değer ($)', 'Tarih': 'Tarih', 'variable': 'Varlık'},
                          title="Portföy Büyümesi vs Benchmark", template="plotly_dark")
            fig.update_layout(margin=dict(t=60,l=40,r=40,b=40))
            
            
            st.plotly_chart(fig, config={"responsive": True})

        c1, c2 = st.columns(2)
        with c1:
            perf = calculate_performance_metrics(p_aligned, risk_free_rate_pct)
            st.markdown("<div class='card'><div class='card-title'>Portföy Performans Metrikleri</div>", unsafe_allow_html=True)
            for k, v in perf.items():
                if "Getiri" in k or "Volatilite" in k or "Drawdown" in k:
                    st.metric(k, f"{v:.2%}")
                else:
                    st.metric(k, f"{v:.3f}")
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            if not b_aligned.empty:
                perf_b = calculate_performance_metrics(b_aligned, risk_free_rate_pct)
                st.markdown("<div class='card'><div class='card-title'>Benchmark Performans</div>", unsafe_allow_html=True)
                for k, v in perf_b.items():
                    if "Getiri" in k or "Volatilite" in k or "Drawdown" in k:
                        st.metric(k, f"{v:.2%}")
                    else:
                        st.metric(k, f"{v:.3f}")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Benchmark verisi yok.")
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB ANALYTICS
    with tab_analytics:
        st.markdown("<div class='card'><div class='card-title'>Analitik Araçlar</div>", unsafe_allow_html=True)
        st.markdown("<div class='muted'>Aşağıda Etkin Sınır interaktif olarak hesaplanır; sağ panelde korelasyon ve hızlı metrikler bulunur.</div>", unsafe_allow_html=True)
        left, right = st.columns([0.7, 0.3])

        with left:
            st.subheader("Etkin Sınır (Interactive)")
            vols, rets, weights_list = compute_efficient_frontier_points(mu, S, results['min_w'], results['max_w'], n_points=100)
            
            if vols.size > 0:
                order = np.argsort(vols)
                vols_sorted = vols[order]
                rets_sorted = rets[order]

                fig_ef = go.Figure()
                fig_ef.add_trace(go.Scatter(x=vols_sorted, y=rets_sorted, mode='lines+markers', name='Efficient Frontier',
                                             hovertemplate="Vol: %{x:.2%}<br>Ret: %{y:.2%}<extra></extra>"))
                asset_vols = np.sqrt(np.diag(S))
                asset_rets = mu.values
                fig_ef.add_trace(go.Scatter(x=asset_vols, y=asset_rets, mode='markers+text', name='Varlıklar',
                                             marker=dict(size=10), text=list(mu.index), textposition='top center',
                                             hovertemplate="%{text}<br>Vol: %{x:.2%}<br>Ret: %{y:.2%}<extra></extra>"))
                fig_ef.add_trace(go.Scatter(x=[exp_vol], y=[exp_ret], mode='markers', name='Optimal Portföy',
                                             marker=dict(size=16, color='gold', symbol='star'),
                                             hovertemplate="Optimal<br>Vol: %{x:.2%}<br>Ret: %{y:.2%}<extra></extra>"))
                fig_ef.update_layout(template="plotly_dark", height=520, xaxis_title="Volatilite (σ)", yaxis_title="Beklenen Getiri", margin=dict(t=60,l=40,r=20,b=40))
                
                st.plotly_chart(fig_ef, config={"responsive": True}) 
                
                if weights_list:
                    st.markdown("<div class='card'><div class='card-title'>Seçili Frontier Noktası Ağırlıkları</div>", unsafe_allow_html=True)
                    st.markdown("<div class='muted' style='margin-bottom:10px;'>Aşağıdaki kaydırıcıyı kullanarak Etkin Sınır üzerindeki farklı bir noktanın ağırlıklarını inceleyebilirsiniz.</div>", unsafe_allow_html=True)
                    
                    ordered_weights = [weights_list[i] for i in order]
                    
                    idx = st.slider("Frontier içinden bir sıra seç (düşük risk/getiri -> yüksek risk/getiri)", 0, max(0, len(ordered_weights)-1), int(len(ordered_weights)//2), width='stretch')
                    safe_idx = max(0, min(idx, len(ordered_weights)-1))
                    chosen_weights = ordered_weights[safe_idx]

                    st.dataframe(pd.DataFrame.from_dict(chosen_weights, orient='index', columns=['weight']).style.format({"weight":"{:.2%}"}), width='stretch') 
                    
                    st.download_button("📥 Bu Noktanın Ağırlıklarını İndir (CSV)", data=weights_to_csv(chosen_weights), file_name="ef_weights.csv", mime="text/csv", key="download_ef", width='stretch')
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("Etkin sınır noktası üretilemedi.")
            else:
                st.info("Etkin sınır noktası üretilemedi (hesaplama başarısız).")

        with right:
            st.subheader("Korelasyon & Hızlı İstatistikler")
            corr = price_df.pct_change().corr().fillna(0)
            fig_corr = px.imshow(corr, text_auto=".2f", aspect="auto", title="Korelasyon Matrisi", template="plotly_dark")
            fig_corr.update_layout(height=420, margin=dict(t=40,l=10,r=10,b=10))
            
            
            st.plotly_chart(fig_corr, config={"responsive": True})

            st.markdown("---")
            st.markdown("<div class='card'><div class='card-title'>Hızlı Bilgiler</div>", unsafe_allow_html=True)
            st.metric("Varlık Sayısı", f"{price_df.shape[1]}")
            st.metric("Veri Günleri", f"{len(price_df)}")
            st.metric("Ortalama Korelasyon", f"{avg_corr:.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # TAB HISTORY
    with tab_history:
        if not st.session_state.new_run_recorded:
            run_record = {
                "Tarih": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                "Hedef": opt_goal,
                "Risk Modeli": risk_model_choice,
                "Varlıklar": ", ".join(price_df.columns),
                "Getiri (%)": f"{exp_ret*100:.2f}",
                "Risk (%)": f"{exp_vol*100:.2f}",
                "Sharpe": f"{exp_sharpe:.2f}"
            }
            st.session_state.history.insert(0, run_record)
            st.session_state.new_run_recorded = True

        st.markdown("<div class='card'><div class='card-title'>Geçmiş Analizler</div>", unsafe_allow_html=True)
        if st.session_state.history:
           
            st.dataframe(pd.DataFrame(st.session_state.history), width='stretch') 
        else:
            st.info("Henüz geçmiş analiz yok.")
        st.markdown("</div>", unsafe_allow_html=True)