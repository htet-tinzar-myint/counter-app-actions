# counter-app（GitHub Actions だけで CI/CD）

`counting-service` と `dashboard-service` の2つのバイナリを、**GitHub Actions だけ**で CI/CD するリポジトリです。
クラウドのアカウントや認証の設定は不要で、GitHub に push すればすぐに動きます。

## 全体の流れ

```
 ブランチで変更 ──PR作成──▶ CI（ci.yml）
                              ├─ イメージをビルド
                              ├─ docker compose で2サービスを起動
                              └─ スモークテスト（dashboard → counting の通信まで確認）
                                        │ 成功したらマージ
                                        ▼
 main にマージ ───────────▶ CD（cd.yml）
                              ├─ publish：イメージを GHCR に公開（タグ：コミットSHA と latest）
                              └─ verify ：公開したイメージを取得して起動し、スモークテスト
```

| サービス | 役割 |
| --- | --- |
| counting-service | 呼ばれるたびにカウントを返す（`{"count":1,...}`） |
| dashboard-service | counting-service の値を WebSocket で画面に表示する |

どちらも環境変数 `PORT` で待ち受けポートを決めます（counting-service：9003、dashboard-service：9002）。dashboard-service は `COUNTING_SERVICE_URL`（`http://counting:9003`）で呼び出し先を受け取ります。
ホストからは `compose.yaml` の `8080:9002` により http://localhost:8080 で dashboard にアクセスできます。

## ファイル構成

```
.
├── services/
│   ├── counting-service/   Dockerfile, bin/counting-service
│   └── dashboard-service/  Dockerfile, bin/dashboard-service
├── compose.yaml            2サービスをまとめて起動する定義（ローカル・CI・CD 共通）
├── scripts/
│   └── smoke_test.py       dashboard に WebSocket で接続し、count が届くか確認
└── .github/workflows/
    ├── ci.yml              PR 時：ビルド → 起動 → スモークテスト
    └── cd.yml              main 反映時：GHCR に公開 → 公開イメージで再テスト
```

## 手順

### 1. GitHub にリポジトリを作って push する

GitHub で空のリポジトリ（例：`counter-app`）を作り、このフォルダで次を実行します。

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<OWNER>/counter-app.git
git push -u origin main
```

main に push したので、この時点で **CD が1回動きます**。**Actions** タブで確認できます。

### 2. CD の結果を確認する

1. **Actions → CD** を開き、`publish`（2つ）と `verify` が緑になっていることを確認
2. 実行結果の **Summary** に、公開したイメージ名が表示される
3. リポジトリのトップ画面右側の **Packages** に、`counting-service` と `dashboard-service` が表示される

### 3. CI を試す（PR を作る）

```bash
git checkout -b test-ci
echo "" >> README.md
git commit -am "Test CI"
git push -u origin test-ci
```

GitHub で **Pull request** を作ると CI が動き、PR の画面に結果（✓ または ✗）が表示されます。
CI が成功したらマージします。マージすると CD が動きます。

### 4.（任意）マージ前に CI の成功を必須にする

**Settings → Branches → Add branch ruleset**（または Branch protection rule）で `main` を対象にし、
**Require status checks to pass** に `Build & smoke test` を追加します。CI が失敗した PR はマージできなくなります。
※ 無料プランでは、公開リポジトリでのみ使えます。

### 5.（任意）CD に承認を入れる

`cd.yml` の `verify` ジョブは `environment: production` を使っています。
**Settings → Environments → production** で **Required reviewers** を設定すると、承認されるまで待機します。
※ 無料プランでは、承認ルールは公開リポジトリでのみ使えます。

## ローカルで動かす

```bash
docker compose up -d --build
# ブラウザで http://localhost:8080 を開く

pip install websocket-client
python scripts/smoke_test.py http://localhost:8080

docker compose down
```

GHCR に公開したイメージをローカルで動かす場合（非公開パッケージは `docker login ghcr.io` が必要）:

```bash
COUNTING_IMAGE=ghcr.io/<owner>/counting-service:latest \
DASHBOARD_IMAGE=ghcr.io/<owner>/dashboard-service:latest \
docker compose up -d --no-build
```

## ポイント

- **CI と CD で同じ起動方法**：どちらも `compose.yaml` で起動するので、「CI では動いたのに公開イメージでは動かない」を防げます。
- **スモークテストは通信まで確認**：dashboard の `/health` だけでなく、WebSocket でカウントを受け取れるかまで確認します。counting-service に届かない場合は失敗します。
- **イメージのタグ = コミット SHA**：どのコミットのイメージか追跡できます。`latest` は最新の main を指します。
- **認証情報の登録は不要**：GHCR への push は、ワークフローに自動で渡される `GITHUB_TOKEN` を使います。

## 注意点

- バイナリは **linux/amd64** 用です。Apple Silicon の Mac では `docker compose build` の前に `export DOCKER_DEFAULT_PLATFORM=linux/amd64` を設定します。
- 個人アカウントの GHCR パッケージは、最初は**非公開**で作られます。公開する場合は Packages の設定画面で変更します。
- `/health/api` は正常時でも 503 を返すため、動作確認には使っていません。

## 次のステップ：GCP（Cloud Run）へのデプロイ

この CI/CD が動いたら、CD の最後に「GCP へのデプロイ」を追加します。
Terraform で Cloud Run の環境を作り、GitHub Actions から Workload Identity Federation で認証してデプロイする構成は、別途お渡しした `counter-app-gcp` にまとめています。
