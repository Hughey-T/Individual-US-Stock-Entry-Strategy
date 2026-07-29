# 検証設計

READMEの6コマンドをローカルとCIで共通使用する。`entry_strategy.validation --all` は正常fixtureと最終サンプルをJSON Schemaへ通し、異常allocation fixtureがcross-field validatorに拒否されることまで確認する。unittestは会話遷移、Phase 4価格帯ロック、比率会計、イベント前上限、鮮度、価格境界、全旧判定、Schemaの条件依存、正本エクスポートを挙動として検証する。
