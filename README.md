# Portföy Optimizasyon & Backtest Platformu

Bu proje, Streamlit kullanılarak geliştirilmiş interaktif bir web uygulamasıdır. Kullanıcıların belirlediği hisse senetleri için modern portföy teorisi prensiplerini kullanarak portföy optimizasyonu yapmalarına, stratejilerini geçmiş verilerle test etmelerine (backtesting) ve sonuçları analiz etmelerine olanak tanır.


## Temel Özellikler

* **Kararlı Veri Akışı:** `yfinance` kütüphanesinin kısıtlamalarından kaçınmak için güvenilir [TwelveData](https://twelvedata.com/) API'si üzerinden veri çeker.
* **Gelişmiş Optimizasyon:**
    * **Hedef Seçimi:** "Maksimum Sharpe Oranı" veya "Minimum Volatilite" hedeflerine göre optimizasyon.
    * **Sağlam Risk Modelleri:** Standart "Örnek Kovaryans" modeline ek olarak istatistiksel olarak daha tutarlı sonuçlar veren "Ledoit-Wolf Kovaryans Shrinkage" modeli seçeneği.
    * **Esnek Kısıtlar:** Her bir varlık için minimum ve maksimum ağırlık belirleyerek aşırı odaklanmış portföyleri engelleme.
* **Geçmiş Performans Testi (Backtesting):**
    * Oluşturulan optimal portföyün geçmiş performansını, belirlenen bir başlangıç sermayesi üzerinden simüle eder.
    * Portföy performansını S&P 500 (SPY) gibi bir endeksle (benchmark) karşılaştırmalı olarak grafik üzerinde gösterir.
* **Kapsamlı Performans Metrikleri:** Sharpe Oranı, Sortino Oranı ve Maksimum Düşüş (Max Drawdown) gibi kritik metrikleri hesaplayarak portföyün risk ve getiri profilini detaylı analiz eder.
* **Sonuçları Karşılaştırma:** Farklı parametrelerle yapılan analizlerin sonuçları oturum boyunca saklanır ve karşılaştırmalı bir tabloda sunulur.
* **Profesyonel Yapı:**
    * API anahtarları için güvenli `secrets.toml` yönetimi.
    * Proje bağımlılıkları için `environment.yml` dosyası.
    * Hata ayıklama için `app.log` dosyasına loglama.

---

## Kurulum ve Çalıştırma

### 1. Ön Gereksinimler
* [Conda](https://docs.conda.io/en/latest/miniconda.html) (veya Miniconda) yüklü olmalıdır.

### 2. Depoyu Klonlama
```bash
git clone [https://github.com/kullanici-adiniz/Portfolio-Optimizer-App.git](https://github.com/kullanici-adiniz/Portfolio-Optimizer-App.git)
cd Portfolio-Optimizer-App
```

### 3. Conda Ortamını Oluşturma
Projenin ihtiyaç duyduğu tüm kütüphaneleri `environment.yml` dosyasını kullanarak kurun:
```bash
conda env create -f environment.yml
conda activate portfolio_optimizer_env
```

### 4. API Anahtarını Ayarlama
Bu proje [TwelveData](https://twelvedata.com/) API'sini kullanmaktadır. Ücretsiz bir API anahtarı alın ve proje ana dizininde `.streamlit` adında bir klasör oluşturun. Bu klasörün içine `secrets.toml` adında bir dosya oluşturup anahtarınızı ekleyin:
```toml
# .streamlit/secrets.toml
TD_API_KEY = "BURAYA_KENDİ_API_ANAHTARINIZI_YAPIŞTIRIN"
```

### 5. Uygulamayı Çalıştırma
Aşağıdaki komut ile Streamlit uygulamasını başlatın:
```bash
streamlit run portfolio_optimizer_app.py
```
Uygulama varsayılan tarayıcınızda açılacaktır.

---
