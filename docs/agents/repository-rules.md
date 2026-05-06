# Repository Rules

## Do

- use stable IDs for cases, patterns, packs, runs, decisions
- keep shared assets anonymized
- update CHANGELOG when modifying packs
- add examples only with demo or anonymized data
- keep docs aligned with actual repo structure
- separate client-specific data from reusable shared assets
- record version context when pack or policy behavior changes

## Do not

- commit client confidential data
- commit API keys or secrets
- commit raw customer documents
- mix client-specific cases into shared packs without abstraction
- overwrite shared assets without version notes
- add unredacted customer names, contracts, logs, or reports to the repo
- rename or restructure governed assets without compatibility review

## 判断に迷ったとき

- 顧客固有性が残るなら repo に入れない
- reusable かどうか曖昧なら、先に Notion で整理する
- 既存 contract に効く変更なら、migration plan を先に考える
