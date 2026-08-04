# Individual US Stock Entry Strategy

米国個別株について、投資仮説・価値・価格構造・イベント・市場環境を独立に再確認し、条件付き計画を作る資格そのものを判定する contract 3.0 実装です。本システムは買う方法を必ず作るものではなく、`NO_ENTRY`、`WAIT_WITHOUT_PLAN`、`RETURN_TO_INDIVIDUAL_ANALYSIS` は正式結果です。投資助言、価格保証、自動売買、注文執行、株数計算、ポートフォリオ最適化は行いません。

唯一の文章正本は [`instructions/custom-gpt-entry-strategy.md`](instructions/custom-gpt-entry-strategy.md) です。Initial 12 Phase / Update 5 Phaseを、正確な`次`/`更新`と1応答1 Phaseで進めます。イベント確認後のPhase 7でのみ価格帯を固定します。企業価値範囲とテクニカル帯、長期仮説と入口条件、旧計画の事後検証と新計画を分離し、テクニカルは命令でなく証拠として扱います。

## Modes and architecture

* `standalone_static`: 会話内状態のみ（`session_local`）。JSON/Markdownを利用者が保存できます。
* `standalone_runtime`: optional private runtimeがCustom GPT生成artifactを検証・immutable保存します。
* `pipeline`: blind intakeで独立gateを固定後、Phase 3で上流結論を照合します。

判定規則は共通で、mode差は入力projectionと永続化だけです。Runtimeは分析を生成せず、実装が存在してもデプロイ済みとは主張しません。`openapi.yaml`はAPI設計、`Dockerfile`は任意配置用です。Bearer tokenは`ENTRY_STRATEGY_TOKEN`、データは`ENTRY_STRATEGY_DATA`（default `/data`）へ原子的に保存します。認証済みbackup/restore操作はsession lock、staging、全generationのintegrity検証を経て処理し、restore後もintegrity endpointで検証できます。

設計・監査・移行・失敗時動作は [`docs/design.md`](docs/design.md)、[`docs/requirements-audit.md`](docs/requirements-audit.md)、[`docs/migration.md`](docs/migration.md)、[`docs/api.md`](docs/api.md)、[`docs/compliance-matrix.md`](docs/compliance-matrix.md)、[`docs/test-matrix.md`](docs/test-matrix.md) を参照してください。

## 開発・検証

Python 3.11以上で次を**上からすべて**実行します。

```bash
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m entry_strategy.validation --all
ruff check .
ruff format --check .
mypy src
python -m build
python -m pip install --force-reinstall dist/*.whl
python -c "import yaml; yaml.safe_load(open('openapi.yaml'))"
docker build -t entry-strategy:local .
scripts/docker-smoke.sh entry-strategy:local
python scripts/repository_audit.py
git diff --check
```

CIはPython matrix、unit/state/E2E/schema/mutation/strict JSON/publication/storage/backup checksと上記lint/type/build/OpenAPI/Docker相当を実行します。Dockerがない環境ではその制約を明示してください。
