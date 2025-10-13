# Portföy Analisti

<p align="center">
  <img src="https://i.imgur.com/your_gif_url_here.gif" alt="Uygulama Demosu" width="800"/>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3.11-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/Framework-Streamlit-red.svg" alt="Streamlit">
</p>

Modern portföy teorisini, geçmişe dönük performans testlerini ve interaktif veri analizini bir araya getiren; özel olarak tasarlanmış arayüzü ile şık ve profesyonel bir kullanıcı deneyimi sunan gelişmiş portföy optimizasyon platformu.

---

##  Projenin Amacı

Bu platform, bireysel yatırımcıların ve finans meraklılarının, karmaşık finansal araçlara veya pahalı aboneliklere ihtiyaç duymadan, veri odaklı yatırım stratejileri geliştirmelerini, test etmelerini ve optimize etmelerini sağlamak amacıyla geliştirilmiştir. Teorik finans modelleri ile pratik yatırım kararları arasında köprü kurarak, herkes için erişilebilir ve güçlü bir analiz aracı sunar.

##  Öne Çıkan Özellikler

###  Premium Arayüz ve Kullanıcı Deneyimi
* [cite_start]**Modern ve Şık Tasarım:** Özel CSS ile tasarlanmış karanlık mod arayüzü, kart tabanlı düzeni ve akıcı animasyonları ile göz yormayan, profesyonel bir kullanım deneyimi sunar. [cite: 1]
* [cite_start]**Sezgisel Kontrol Paneli:** Tüm ayarlar ve parametreler, sol paneldeki düzenli ve genişletilebilir menüler altında toplanmıştır. [cite: 1]
* **Sekmeli Yapı:** Analiz sonuçları; [cite_start]`Veri Özeti`, `Backtest`, `Analitik Araçlar` ve `Geçmiş` gibi organize sekmeler altında sunularak karmaşıklığı ortadan kaldırır. [cite: 1]

###  Güçlü Analitik Motor
* [cite_start]**Gelişmiş Optimizasyon:** Portföyünüzü "Maksimum Sharpe Oranı" veya "Minimum Volatilite" hedeflerine göre, esnek alt ve üst ağırlık sınırları belirleyerek optimize edin. [cite: 1]
* [cite_start]**Sağlam Risk Modelleri:** Standart "Örnek Kovaryans" modeline ek olarak, istatistiksel gürültüyü azaltarak daha tutarlı sonuçlar üreten **Ledoit-Wolf Kovaryans Shrinkage** modelini kullanın. [cite: 1]
* [cite_start]**Kapsamlı Performans Metrikleri:** Beklenen Getiri, Volatilite, Sharpe Oranı ve yeni eklenen **Çeşitlendirme Endeksi (Diversification Index)** gibi kritik KPI'ları ana panelde anında görün. [cite: 1]

###  Strateji Testi ve İnteraktif Görselleştirme
* [cite_start]**İnteraktif Etkin Sınır (Efficient Frontier):** Etkin Sınır grafiği üzerinde bir kaydırıcı (slider) ile gezerek, grafikteki herhangi bir noktanın (risk-getiri kombinasyonunun) portföy ağırlıklarını anlık olarak inceleyin. [cite: 1]
* [cite_start]**Karşılaştırmalı Backtesting:** Oluşturduğunuz portföyün geçmiş performansını, belirlediğiniz bir başlangıç sermayesiyle test edin ve S&P 500 (SPY) gibi bir endeksle karşılaştırmalı olarak analiz edin. [cite: 1]
* [cite_start]**Oturum Geçmişi:** Aynı oturumda yaptığınız farklı analizlerin özet sonuçlarını "Geçmiş" sekmesinde görüntüleyerek stratejilerinizi kolayca karşılaştırın. [cite: 1]

###  Teknoloji ve Mimari
* [cite_start]**Güvenilir Veri Kaynağı:** Finansal veriler, kararlı ve tutarlı bir akış için **TwelveData API**'si üzerinden sağlanır. [cite: 1]
* [cite_start]**Profesyonel Proje Yapısı:** Güvenli API anahtarı yönetimi (`.streamlit/secrets.toml`), tekrarlanabilir kurulum (`environment.yml`) ve temiz bir sürüm kontrol geçmişi (`.gitignore`) ile sağlam bir mühendislik altyapısı üzerine kurulmuştur. [cite: 1]

---

##  Kurulum ve Çalıştırma

### Ön Gereksinimler
* [Conda](https://docs.conda.io/en/latest/miniconda.html) (veya Miniconda) sisteminizde yüklü olmalıdır.

### Kurulum Adımları
Aşağıdaki komutları terminalinize yapıştırarak projeyi klonlayabilir, bağımlılıkları kurabilir ve çalıştırabilirsiniz.

```bash
# 1. Depoyu klonlayın ve dizine gidin
git clone [https://github.com/koraysrn/Portfolio-Optimizer-App.git](https://github.com/koraysrn/Portfolio-Optimizer-App.git)
cd Portfolio-Optimizer-App

# 2. Conda ortamını oluşturun ve aktifleştirin
conda env create -f environment.yml
conda activate Portfolio_optimizer_env

# 3. API anahtarınızı ayarlayın
# Not: 'YOUR_API_KEY_HERE' kısmını kendi TwelveData API anahtarınızla değiştirmeyi unutmayın.
mkdir -p .streamlit
echo 'TD_API_KEY = "YOUR_API_KEY_HERE"' > .streamlit/secrets.toml

# 4. Uygulamayı başlatın
streamlit run portfolio_optimizer_app.py
```
Uygulama varsayılan tarayıcınızda açılacaktır.

---


