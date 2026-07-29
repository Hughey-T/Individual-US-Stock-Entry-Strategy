# 移行

実保存データは初期リポジトリに存在しないため、実データ移行は **not applicable**。互換処理は`migration.is_legacy`が旧判定フィールドまたは5 Phase印を検出し、`migrate_legacy`が認識可能な6判定について元判定と説明、警告、`manual_review_required=true`を保持して「個別銘柄分析へ差し戻し」にする。完全な一対一対応は推測しない。

未知ラベル、ラベル欠落、5以外のPhase数、複数旧判定フィールドの矛盾、現行形式を旧形式として渡す操作は明示的エラーになる。`fixtures/legacy/five-phase.json`と`tests/test_migration.py`が互換仕様を検証する。旧説明はこの移行文脈およびmigration内部にだけ存在し、現行ユーザー向け出力には出さない。
