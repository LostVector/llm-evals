# Inkling 2 Mini Q8_0 oracle fixtures

These generated prompts reproduce the inputs to the extended
[Inkling deployment check](inkling-q8-0.md). They contain synthetic data.

```python
from pathlib import Path

Path("prose.txt").write_text(
    "Read the following field notes before responding. A team measured the "
    "temperature of a lake at dawn, noon, and sunset. The instruments agreed "
    "within a small margin in the morning. At noon one sensor became unreliable "
    "after direct exposure to the sun. Explain how the team should report the "
    "discrepancy without discarding the entire day of observations. Use ordinary language.",
    encoding="utf-8",
)
Path("code.txt").write_text(
    "def stable_groups(rows):\n"
    "    groups = {}\n"
    "    for key, value in rows:\n"
    "        if key not in groups:\n"
    "            groups[key] = []\n"
    "        groups[key].append(value)\n"
    "    return list(groups.items())\n\n"
    "# Document the ordering guarantee, show an example input, and give the expected result.\n",
    encoding="utf-8",
)
Path("table.txt").write_text(
    "Invented shipment ledger. Use only the rows below.\n"
    + "".join(f"Batch {i:03d} | cartons {i*7+2} | dock {'East' if i%2 else 'West'}\n"
              for i in range(20)),
    encoding="utf-8",
)
```

Use `inkling2_oracle`, `llama_dump.cpp`, and `compare_dumps.py` from
Gufo's Inkling oracle tests. Build `llama_dump` against the b12600 CPU
libraries. With a dynamic backend build, include `ggml-backend.h` and call
`ggml_backend_load_all_from_path` on the release library directory before
`llama_backend_init`. Set `MODEL` to the exact checkpoint in the deployment
check. These example commands run the first fixture.

```sh
inkling2_oracle --model "$MODEL" --text prose.txt --n 48 \
  --ids-out prose-ids.bin --out prose-gufo.bin
llama_dump "$MODEL" prose-ids.bin prose-llama.bin 8 1 prose-gufo.bin 0
python3 compare_dumps.py prose-gufo.bin prose-llama.bin
```

Use 48 positions for `code.txt` and 96 for `table.txt`. The ID files
contain little-endian 32-bit token IDs.

| Fixture | Token ID file SHA-256 |
| --- | --- |
| Prose | `2439d4213aed2b69bc5012255566a09fb65de1fd0cdba3b2248c306f6ae1bb1d` |
| Python | `28cfd23be72ea2ef753e8263ea1b903e11b58e0974ecc0282acf99d2745f3446` |
| Table | `ff83e4b3ecec65495b68e7aaa75b5648c56f76efc34ab5a08c0d66403cb15a66` |
