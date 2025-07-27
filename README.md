
# 💻 WinPerfAgent

**WinPerfAgent**, Windows makinelerden sistem performans verilerini toplayan, merkezi bir Flask dashboard'a gönderen ve PostgreSQL'de saklayarak izlenebilir hale getiren açık kaynak ajan + sunucu çözümüdür.

![WinPerfAgent](https://raw.githubusercontent.com/kullanici_adin/WinPerfAgentServer/main/preview.png)

---

## 🚀 Özellikler

- ✅ Çoklu istemci desteği
- ✅ Gerçek zamanlı izleme (CPU, RAM, Disk, Ağ, Uptime)
- ✅ Tavsiye sistemi (yüksek kullanımda öneriler)
- ✅ Tray uygulaması ve GUI detay ekranı
- ✅ PostgreSQL tabanlı geçmiş veritabanı
- ✅ Modern, responsive dashboard (HTML + CSS + Chart.js)
- ✅ Docker desteği ile kolay kurulum

---

## 📁 Proje Yapısı

```
WinPerfAgent/
├── agent.py                # Tray uygulaması (Windows ajan)
├── app.py                  # Flask sunucu
├── db.py                   # PostgreSQL işlemleri
├── monitor.py              # Sistem verisi toplama
├── recommender.py          # Otomatik öneri üretici
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── static/                 # CSS / JS dosyaları
├── templates/              # HTML sayfaları
├── updates/                # (Opsiyonel) güncelleme klasörü
├── VERSION
└── README.md
```

---

## ⚙️ Sunucu Kurulumu

### Seçenek 1: 🐳 Docker (Önerilir)

```bash
git clone https://github.com/kullanici_adin/WinPerfAgentServer.git
cd WinPerfAgentServer
docker-compose up -d
```

- `http://localhost:5000` adresinden dashboard'a erişebilirsin

---

### Seçenek 2: Manuel Kurulum (Geliştirici Modu)

> 🧠 Gerekenler: Python 3.10+ ve PostgreSQL 13+

```bash
# 1. Projeyi klonla
git clone https://github.com/kullanici_adin/WinPerfAgentServer.git
cd WinPerfAgentServer

# 2. Sanal ortam oluştur
python -m venv venv
source venv/bin/activate

# 3. Gereksinimleri yükle
pip install -r requirements.txt

# 4. PostgreSQL yapılandır
sudo apt install postgresql
sudo -u postgres psql
```

SQL shell içinde:

```sql
CREATE DATABASE winperf;
CREATE USER admin WITH PASSWORD 'secret';
GRANT ALL PRIVILEGES ON DATABASE winperf TO admin;
```

Ardından `.env` oluştur:

```
DATABASE_URL=postgresql://admin:secret@localhost:5432/winperf
```

Veritabanını başlat:

```bash
python db.py
```

Sunucuyu başlat:

```bash
python app.py
```

---

## 🖥️ Windows Ajan Kurulumu

### Seçenek 1: Python ile Çalıştır

> Gerekli: Python 3.10+

```bash
pip install -r requirements.txt
python agent.py
```

- Tray icon sistem çubuğunda görünür
- Üzerine çift tıklayarak detayları görebilirsin

### Seçenek 2: `.exe` Formatında

```bash
pip install pyinstaller
pyinstaller agent.py --noconsole --onefile --name WinPerfAgent
```

- `dist/WinPerfAgent.exe` dosyasını çalıştır
- Başlangıç klasörüne kısayol ekleyerek otomatik başlatma yapılabilir

---

## 🔧 Ajan Ayarları (`agent_config.json`)

```json
{
  "dashboard_url": "http://10.0.0.10:5000/api/report",
  "report_interval": 10,
  "connection_timeout": 5
}
```

---

## 🧠 Tavsiye Sistemi

`recommender.py` ile yüksek CPU/RAM/Disk kullanımı tespit edilip öneri üretir:

```text
High CPU usage detected (93%). Consider closing 'chrome.exe'.
```

---

## 🧪 Veritabanı Yapısı

- `reports` → geçmiş veriler
- `clients_current` → anlık cihaz durumu
- `cleanup_old_data()` fonksiyonu ile eski loglar temizlenebilir

---

## 📡 API Endpoint’ler

| Yöntem | URL                            | Açıklama                         |
|--------|--------------------------------|----------------------------------|
| POST   | `/api/report`                 | Ajan veri gönderir               |
| GET    | `/api/clients`                | Tüm aktif istemcileri döner      |
| GET    | `/api/reports`                | Tüm geçmiş veriler               |
| GET    | `/api/client/<hostname>`      | Belirli cihaz geçmişi            |
| GET    | `/api/health`                 | Sağlık kontrolü                  |

---

## 📸 Ekran Görüntüsü

![WinPerfAgent Dashboard](https://raw.githubusercontent.com/kullanici_adin/WinPerfAgentServer/main/preview-dashboard.png)

---

## 🧾 Lisans

MIT Lisansı ile lisanslanmıştır. Tüm ticari ve kişisel projelerde kullanılabilir.
