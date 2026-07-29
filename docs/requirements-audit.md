# 要件監査（1–26）

| 要件 | 判定 | 検証先 |
|---:|---|---|
| 1–2 | implemented and verified | 正本の目的・会話契約、契約テスト |
| 3 | implemented and verified | 正本、engine、model、schema、OpenAPI、fixture、test、docs、sample、export |
| 4 | implemented and verified | 多軸Decision/Allocation、保守的migration |
| 5–6 | implemented and verified | 初回8 Phaseと1応答1 Phase状態機械 |
| 7–8 | implemented and verified | PriceZoneロック/変更監査、自然語表示 |
| 9–10 | implemented and verified | 二軸列挙、比率相互検証 |
| 11–14 | implemented and verified | 3種無効化、イベント支配度、鮮度、価格境界検証 |
| 15–18 | implemented and verified | 期限、カバレッジ、実行カード、更新2 Phase |
| 19 | implemented and verified | 正本対象外、注文機能なし |
| 20–21 | implemented and verified | unittest、全文書・fixture・sample |
| 22 | implemented and verified | 安全な旧形式検出・差戻し・明示エラー |
| 23–25 | implemented and verified | 設計判断、全検証、旧語検索監査 |
| 26 | implemented and verified | commit/PRおよび最終報告 |

実データmigrationは、初期リポジトリに保存データがないため **not applicable**。互換仕様・fixture・テストは実装済み。blocked項目はない。
