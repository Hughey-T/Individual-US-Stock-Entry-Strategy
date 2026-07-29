# 設計

文章上の規範は[正本](../instructions/custom-gpt-entry-strategy.md)だけに置く。`ConversationEngine` は初回8/更新2 Phaseを分離し、`EntryState` は帯をPhase 4で固定する。JSON Schemaは形、Python validatorは比率合計・鮮度・境界・イベント支配度などの相互条件を担う。この分離によりCustom GPTの表示契約と保存データの不変条件を独立して検査できる。

重要な判断は、(1) 比率を条件ごとの配列として保持し各要素40%以下を検査、(2) 帯変更を上書きではなく監査履歴付き操作に限定、(3)曖昧な旧判定は安全側で個別分析へ差し戻す、の3点である。対象は本リポジトリだけで、他テンプレートへの影響はない。
