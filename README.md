# Individual US Stock Entry Strategy

米国個別株の条件付きエントリー計画を Custom GPT で一貫して作るための、正本指示・状態機械・検証器です。投資助言、価格保証、注文執行、株数計算、ポートフォリオ最適化は行いません。

## 正本と構成

唯一の文章仕様は [`instructions/custom-gpt-entry-strategy.md`](instructions/custom-gpt-entry-strategy.md) です。コードと JSON Schema はその契約を機械検証し、`entry_strategy.export.canonical_instructions()` が同じファイルを Custom GPT 用に出力します。設計資料は正本を複製せず、実装上の判断と参照先だけを説明します。

* 初回分析: Phase 1–8（1応答1 Phase、Phase 1–7 のみ「次」を要求）
* 更新: 更新Phase 1–2（「更新」で開始し、更新Phase 1 の次の「次」で事後検証）
* Phase 4 で価格帯を固定し、変更は旧値・新値・理由・影響を監査記録へ保存
* 行動、購入経路、比率、リスクを独立管理

## 開発

Python 3.11 以上を使用します。ランタイム依存はありません。

```bash
python -m unittest discover -s tests -v
python -m entry_strategy.validation --all
ruff check .
ruff format --check .
mypy src
```

ローカル実行時は `PYTHONPATH=src` が必要です（テストは `tests/__init__.py` が設定します）。サンプルは `samples/`、正常・異常・旧形式データは `fixtures/` にあります。API 契約は `openapi.yaml` です。

## 免責

比率は「今回構築する目標ポジション=100%」に対する参考値であり総資産比率ではありません。期限切れの計画は価格到達だけで有効にならず、更新による再評価が必要です。
