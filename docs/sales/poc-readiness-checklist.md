# 有償PoC / 初回ベースライン診断 readiness checklist

- [ ] external adapter または local evaluation path が確定している
- [ ] execution_mode が artifact に出る
- [ ] `customer-summary.md` などの customer-safe artifact が出る
- [ ] S1 governance が validate-pack / gate で確認できる
- [ ] S1 / NEEDS_REVIEW に manual review を残せる
- [ ] PASS の意味が限定されている
- [ ] customer report と internal report が分かれている
- [ ] secrets / raw payload / private URL が artifact に出ない
- [ ] before / after comparison が再現できる
- [ ] false positive / false negative の記録先がある
