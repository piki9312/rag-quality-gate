# RAG Quality Gate

RAG システムの品質を自動検証し、リリース可否を判定するプラットフォーム。

## What is this?

RAG（Retrieval-Augmented Generation）で作った FAQ ボットや社内検索の回答品質を、**テストケース駆動で自動評価**し、CI に組み込んで品質劣化を検知します。

```
Documents --> [RAG Pipeline] --> Answer
                                    |
Test Cases --> [Quality Runner] --> EvalResult --> [Gate Check] --> PASS / FAIL
```

## Why?

- RAG は「作って動いた」で終わりがち。プロンプトや検索パラメータを変えたら**どのケースが壊れたか**を検出する仕組みが必要
- LLM 回答の品質は定量化しにくい → **キーワードマッチ + 検索ヒット + 引用整合性**の 3 軸で自動スコアリング
- `S1`（重大）ケースは全件パス必須、`S2` は閾値ベースの柔軟な判定

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# 1) 文書を投入
rqg ingest packs/hr/documents/

# 2) テストケースで品質評価 (API key なしで試すなら --mock)
rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock

# 3) ゲート判定
rqg check --log-dir runs/quality --config .rqg.yml
```

## Project Structure

```
src/rqg/
  serving/          # RAG パイプライン (FAISS + sentence-transformers + OpenAI)
    rag.py          #   チャンク化・埋め込み・検索
    llm_client.py   #   OpenAI 呼び出し + リトライ + コスト推定
  quality/          # 品質評価エンジン
    models.py       #   QATestCase, EvalResult, EvalRun, QARunRecord
    loader.py       #   CSV ケースローダー
    runner.py       #   RAGQualityRunner (検索 -> 生成 -> 評価)
    aggregate.py    #   パス率・レイテンシ集計
    check.py        #   ゲート判定 (閾値 + ベースライン比較)
    evaluators/     #   キーワード / 検索ヒット / 引用整合性
  cli.py            # rqg コマンド (ingest / eval / check)
packs/              # ドメイン別 Quality Pack
  hr/               #   人事・労務 FAQ 向けパック
    cases.csv       #     テストケース 10 件
    quality-pack.yml #    KPI / SLO 定義
    documents/      #     サンプル社内文書
tests/              # 65 tests, all passing
```

## Quality Pack

ドメインごとに **Quality Pack** を用意:

| ファイル | 内容 |
|---------|------|
| `cases.csv` | テストケース (質問 + 期待キーワード + severity) |
| `quality-pack.yml` | KPI 定義 + SLO + ROI メモ |
| `documents/` | 対象ドメインの文書 |

### テストケース CSV

```csv
case_id,name,severity,question,expected_chunks,expected_keywords,golden_answer,category,owner,min_pass_rate
QA001,有給申請期限,S1,"有給の申請期限は？","","5営業日前;申請","",就業規則,hr-team,100
```

- `severity`: `S1`（重大 = 100% パス必須） / `S2`（通常 = 閾値ベース）
- `expected_keywords`: セミコロン区切り。回答に含まれるべきキーワード
- `expected_chunks`: セミコロン区切り。検索結果に含まれるべき chunk_id

## Gate Config (.rqg.yml)

```yaml
thresholds:
  s1_pass_rate: 100.0      # S1 ケース全件パス
  overall_pass_rate: 80.0   # 全体 80% 以上
  retrieval_precision: 70.0 # 検索精度 70% 以上
```

## Evaluators

| Evaluator | 検証内容 | S1 閾値 | S2 閾値 |
|-----------|---------|---------|---------|
| keyword_match | 回答に期待キーワードが含まれるか | 80% | 50% |
| retrieval_hit | 正しいチャンクが検索結果にあるか | 必須 | - |
| reference_accuracy | 回答中の引用が実在するか | 50% | 50% |

## CI Integration

```yaml
# .github/workflows/ci.yml に追加
- name: RAG Quality Gate
  run: |
    rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock
    rqg check --log-dir runs/quality --config .rqg.yml
```

## Development

```bash
# テスト
pytest tests/ -v

# フォーマット
black src/ tests/
isort src/ tests/

# カバレッジ
pytest tests/ --cov=rqg --cov-report=term-missing
```

## Architecture

This project fuses two pre-existing codebases:

- **rag_app** → `src/rqg/serving/` (RAG pipeline: FAISS + OpenAI)
- **llmops-lab** → `src/rqg/quality/` (CI gate: CSV cases + threshold check + JSONL persistence)
- **New bridge** → `src/rqg/quality/runner.py` (connects RAG pipeline to quality evaluation)

## License

MIT
