# 此專案為給資料期末專題DEMO應用

## 說明
本系統為訂單管理系統，以訂單、庫存作為核心理念設計

## 啟用專案流程

1. 修改專案環境擋，並產生secret_key
```
cp .env.example .env
```

2. 修改envrc檔並帶入shell envirement
```
cp .envrc.example .envrc

source .envrc
```

3. 啟用容器執行本專案服務
```
docker compose up -d
```

4. 確保服務啟動
```
docker compse ps
```

5. 進入容器內部交互模式
```
docker compose exec -u 1000 web bash
```

6. 進行migration
```
python manage.py migrate
```

7. 資料匯入
- 資料庫管理工具進行 csv匯入
  - 假設使用csv匯入需要照./seed_csv底下的序號進行import

8. 在local環境確認是否正常假設.envrc設定NGINX_PORT=8088那進到網址http://localhost:8088 即可登入
```
admin
account: admin
password: admin12345

staff
account: staff1
password: staff12345
```
