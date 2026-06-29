# Vigour cue-mapping parity check

Verifies that the JavaScript vigour task assigns the **same auditory cue to the
same reward×effort condition for a given participant** as the Python lab task
(`pilot5_0.py`). Both use a Latin square keyed on the participant number.

## Files

- `gen_python.py` — `make_latin_square_cue_mapping` copied **verbatim** from
  [`pilot5_0.py`](../../../pilot5_0.py); writes `latin_python.csv`.
- `gen_js.mjs` — `vigourLatinSquareMapping` copied **verbatim** from
  [`vigour-utils.js`](../vigour-utils.js); writes `latin_js.csv`.
- `latin_python.csv`, `latin_js.csv` — mapping for participants 1–50.
- `latin_compare.csv` — side-by-side comparison with an `equal` column.

Each `condN_*` column is the cue identity (1–6) assigned to that condition,
where conditions are ordered `[1p/FR1, 1p/FR5, 1p/FR10, 5p/FR1, 5p/FR5, 5p/FR10]`.
Cue identities map to sounds: 1=bird, 2=bubble, 3=fire, 4=laundry, 5=writing,
6=typing.

## Regenerate / re-check

```sh
python3 gen_python.py
node gen_js.mjs
# content-only comparison (ignores CRLF vs LF: Python's csv module writes \r\n)
diff <(tr -d '\r' < latin_python.csv) <(tr -d '\r' < latin_js.csv) && echo IDENTICAL
```

Last run: all 50 participants identical.

> Note: parity holds only when the **same participant-id string** is used in both
> versions. The seed is `int(id)` when the id is a clean integer, otherwise
> `sum(ord(ch) for ch in id)`. See `vigourParticipantSeed` in `vigour-utils.js`.
