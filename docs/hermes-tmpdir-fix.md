# Hermes TMPDIR Fix — Geçici Dosya Yönlendirme

## Problem

Hermes gateway'i her başlatıldığında `TMPDIR` ortam değişkenini `~/.hermes/cache/scratch` olarak ayarlıyor. Bu yüzden:

- `terminal.temp_dir` config ayarı scratch'e yazıyor (ama `cache/terminal` dizinini prune'dan koruyor, `cache/scratch`'i korumuyor)
- `apply_scratch_tmp_env()` içindeki "user-set temp var is never overwritten" kontrolü nedeniyle, mevcut TMPDIR değiştirilmiyor
- `hermes gateway start` servis dosyasını her seferinde kendi varsayılanıyla overwrite ediyor

## ⚠️ ÖNEMLİ DÜZELTME

Ana servis dosyasına elle satır eklemek **çalışmaz**: `hermes gateway start` içindeki `refresh_systemd_unit_if_needed()` her seferinde dosyayı kendi şablonuyla yeniden yazar; `chmod 444` yapılırsa PermissionError verip gateway başlamaz.

**Doğru yöntem**: drop-in kullan.

### 1. Drop-in Oluştur

```bash
sudo mkdir -p /etc/systemd/user/hermes-gateway.service.d
echo -e "[Service]\nEnvironment=\"TMPDIR=/home/selam/roller/web/lgs-ai-coach\"" | \
  sudo tee /etc/systemd/user/hermes-gateway.service.d/tmpdir.conf
```

### 2. Systemd Yeniden Yükle + Gateway Başlat

```bash
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user daemon-reload
hermes gateway stop && sleep 2 && hermes gateway start
```

### 3. Doğrulama

```bash
python3 -c "import tempfile,os; print('TMPDIR:', tempfile.gettempdir())"
# Çıktı: TMPDIR: /home/selam/roller/web/lgs-ai-coach
```

## Yedek

```bash
sudo cp /home/selam/.config/systemd/user/hermes-gateway.service \
  /home/selam/.config/systemd/user/hermes-gateway.service.bak
```

## Geri Alma

```bash
sudo cp /home/selam/.config/systemd/user/hermes-gateway.service.bak \
  /home/selam/.config/systemd/user/hermes-gateway.service
sudo chmod 644 /home/selam/.config/systemd/user/hermes-gateway.service
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user daemon-reload
hermes gateway stop && hermes gateway start
```

## ⚠️ ÖNEMLİ DÜZELTME (2026-10-10)

Yukarıdaki 1-2. adımlar **UYGULANMAMALIDIR**:

- `hermes gateway start` her çalışta `refresh_systemd_unit_if_needed()` ile servis
  dosyasını yeniden yazar. Dosya salt-okunur (`chmod 444`) yapılırsa `start`
  `PermissionError` ile **başarısız olur ve gateway ayağa kalkmaz**
  (doğrulandı: 2026-10-10).
- Ana servis dosyasına elle eklenen `TMPDIR` satırı da bir sonraki `start`/`update`
  ile silinir — kalıcı değildir.

### Kalıcı ve doğru çözüm: systemd drop-in override

Ana dosyaya dokunulmaz. TMPDIR yalnızca drop-in'den verilir; hermes'in ürettiği
şablonla çakışmadığı için `start`/`update` sonrası da korunur:

```bash
cat /etc/systemd/user/hermes-gateway.service.d/tmpdir.conf
# [Service]
# Environment="TMPDIR=/home/selam/roller/web/lgs-ai-coach"
```

```bash
XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  systemctl --user daemon-reload
hermes gateway start
```

### Doğrulama (gateway sürecinin gerçek ortamı)

```bash
GW_PID=$(systemctl --user show hermes-gateway.service -p MainPID --value)
tr '\0' '\n' < /proc/$GW_PID/environ | grep '^TMPDIR='
# Çıktı: TMPDIR=/home/selam/roller/web/lgs-ai-coach
```

Durum (2026-10-10): gateway çalışıyor (PID 22454), `TMPDIR` süreç ortamında
doğrulandı. Ana servis dosyası hermes yönetiminde (644), drop-in aktif.
