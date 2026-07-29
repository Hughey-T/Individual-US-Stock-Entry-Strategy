# 設計

文章上の規範は[正本](../instructions/custom-gpt-entry-strategy.md)だけに置く。正本は単独でCustom GPTへ貼り付け可能であり、本docsは重複仕様を作らず実装の対応関係だけを説明する。

`ConversationEngine`は初回8/更新2 Phaseを分離し、各結果に当該Phaseだけの必須sectionを付ける。更新は初回完了後だけ開始できる。`EntryState`は自身のmode/current phaseを使って初回Phase 4でのみ帯を固定し、以後の変更を旧値・新値・Phase・理由・影響の履歴にする。呼出側が任意のphase番号を渡してロックを迂回することはできない。

JSON Schemaはenum、required、additionalProperties、配列数、ロック依存、待機用途依存を担う。Python validatorは比率合計、イベント前に実行可能な購入比率、経路順序、低支配度イベント、鮮度、価格境界などJSON Schemaで表しにくい相互条件を担う。旧判定は新判断へ推測対応させず、全6種を元値・警告・手動確認付きで差し戻す。

`openapi.yaml`はHTTP実装ではなくSchema参照用資料である。`paths: {}`、`servers: []`、`x-runtime-available: false`で誤認を防ぐ。対象は本リポジトリだけで、他テンプレートへの影響はない。
