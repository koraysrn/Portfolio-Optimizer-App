# Portföy Optimizasyon & Backtest Platformu

<p align="center">
  <img src="https://i.imgur.com/your_gif_url_here.gif" alt="Uygulama Demosu" width="800"/>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3.11-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/Framework-Streamlit-red.svg" alt="Streamlit">
    <img src="https://img.shields.io/badge/Lisans-MIT-green.svg" alt="License">
</p>

Veri odaklı yatırım stratejileri oluşturmak, test etmek ve analiz etmek için geliştirilmiş, kurumsal düzeyde yeteneklere sahip, açık kaynaklı ve interaktif bir web platformu.

---

##  Projenin Amacı

Karmaşık finansal analiz araçlarına veya pahalı aboneliklere ihtiyaç duymadan, modern portföy teorisi prensiplerini ve geçmiş performans testlerini herkes için erişilebilir kılmak. Bu araç, teorik finans modelleri ile gerçek dünya yatırım kararları arasında bir köprü kurar.

##  Öne Çıkan Özellikler

### Analitik Motor
* **Gelişmiş Optimizasyon:** "Maksimum Sharpe Oranı" veya "Minimum Volatilite" hedeflerine göre, esnek ağırlık kısıtları belirleyerek portföyünüzü optimize edin.
* **Sağlam Risk Modelleri:** Standart "Örnek Kovaryans" modeline ek olarak, istatistiksel olarak daha tutarlı sonuçlar üreten **Ledoit-Wolf Kovaryans Shrinkage** modelini kullanın.
* **Kapsamlı Performans Metrikleri:** Sharpe Oranı, Sortino Oranı ve Maksimum Düşüş (Max Drawdown) gibi kritik metriklerle stratejinizin risk-getiri profilini derinlemesine analiz edin.

### Strateji Testi ve Görselleştirme
* **Geçmiş Performans Testi (Backtesting):** Oluşturduğunuz portföyü, belirlediğiniz bir başlangıç sermayesiyle geçmiş veriler üzerinde test edin ve performansını S&P 500 (SPY) gibi bir endeksle karşılaştırmalı olarak görün.
* **Etkileşimli Grafikler:** Etkin Sınır (Efficient Frontier), portföy dağılımı ve varlık korelasyon matrisi gibi görselleştirmelerle karmaşık verileri kolayca yorumlayın.
* **Sonuçları Karşılaştırma:** Farklı parametrelerle yaptığınız analizlerin sonuçlarını oturum boyunca saklayın ve karşılaştırmalı bir tabloda görüntüleyin.

### Teknoloji ve Mimari
* **Kararlı Veri Akışı:** Güvenilir **TwelveData API**'si üzerinden kararlı ve tutarlı finansal veriler.
* **Profesyonel Yapı:** Güvenli API anahtarı yönetimi (`secrets.toml`), tekrarlanabilir kurulum (`environment.yml`) ve hata ayıklama için dosya tabanlı loglama (`app.log`) ile sağlam bir mühendislik altyapısı.

---

## Kurulum ve Çalıştırma

Bu adımları takip ederek uygulamayı yerel makinenizde 5 dakikadan kısa sürede çalıştırabilirsiniz.

### 1. Ön Gereksinimler
* [Conda](https://docs.conda.io/en/latest/miniconda.html) (veya Miniconda) sisteminizde yüklü olmalıdır.

### 2. Depoyu Klonlama
```bash
git clone [https://github.com/koraysrn/Portfolio-Optimizer-App.git](https://github.com/koraysrn/Portfolio-Optimizer-App.git)
cd Portfolio-Optimizer-App
```

### 3. Conda Ortamını Oluşturma ve Aktifleştirme
Projenin ihtiyaç duyduğu tüm kütüphaneleri `environment.yml` dosyasını kullanarak tek komutla kurun:
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
Bu dosya, `.gitignore` tarafından kasıtlı olarak yoksayılır ve API anahtarınızın güvende kalmasını sağlar.

### 5. Uygulamayı Başlatma
Aşağıdaki komut ile Streamlit uygulamasını başlatın:
```bash
streamlit run portfolio_optimizer_app.py
```
Uygulama varsayılan tarayıcınızda açılacaktır.

---


