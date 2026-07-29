# 移行

実保存データは初期リポジトリに存在しないため実データ移行は **not applicable**。ただし `migration.is_legacy` が旧判定または5 Phase印を検出する。`migrate_legacy` は一対一対応を推測せず、元判定、警告、`manual_review_required=true` を保持して「個別銘柄分析へ差し戻し」にする。不明な旧判定は明示的エラーとする。ユーザー向け現行出力には旧ラベルを出さない。
