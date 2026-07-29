# OpenAPI設計資料

`openapi.yaml` は `components.schemas` から状態Schemaと最終出力Schemaを参照する、移植用の設計資料である。`paths` は空、`servers` は空、`x-runtime-available` は `false` であり、HTTPサーバーまたは実在する検証エンドポイントを表さない。実装済みの検証入口はPython関数と `python -m entry_strategy.validation --all` だけである。注文APIは対象外である。
