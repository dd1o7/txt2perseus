# txt2perseus

A Python tool that converts multiple-choice questions written in plain text into
[Perseus](https://github.com/Khan/perseus) JSON, the open-source exercise format used by
Khan Academy. I built it to stop formatting questions by hand. It has processed 500+ questions.

- No dependencies: standard-library Python 3 only
- Reads LaTeX math, flexible option and rationale styles, and wrapped lines
- Checks every question and refuses to write a file that has errors
- Prints a quality report: answer-key balance and "longest option is correct" bias

## Quick start

```bash
python3 txt2perseus.py samples/example.txt     # -> samples/example.json
python3 txt2perseus.py some_folder/            # every .txt in the folder
python3 txt2perseus.py samples/example.txt --split   # also one file per question
```

Output for the sample file:

```
samples/example.txt -> samples/example.json   3 items
  keys A:0  B:2  C:1  D:0  |  key is longest in 0/3 (0%, chance 25%)
  difficulty  1E / 1M / 1H
```

## Input format

```
Question 2 (Medium)
The length of a simple pendulum is made four times larger.
What happens to its time period?

A) It halves. {Incorrect. The period grows with length, so it cannot get smaller.}
B) It doubles. {Correct. Since $T = 2\pi\sqrt{L/g}$, multiplying $L$ by $4$ multiplies $T$ by $\sqrt{4} = 2$.}
C) It becomes four times larger. {Incorrect. $T$ depends on $\sqrt{L}$, not on $L$ directly.}
D) It stays the same. {Incorrect. The period depends on length, so changing $L$ changes $T$.}
```

Only three things are required: a question header, 2 to 6 options, and a rationale after
each option starting with **Correct** or **Incorrect**. That word is how the answer key is found.

Everything else is flexible:

| Part       | Accepted styles |
|------------|-----------------|
| Header     | `Question 1 (Easy)`, `Q1`, `Item 7:`, `Problem 3`, `Q12 [Hard]` |
| Options    | `A. text`, `B) text`, `(C) text` |
| Rationale  | `[Correct : ...]`, `{Correct. ...}`, or a bare `Correct. ...` line under the option |
| Math       | `$x$`, `$$x$$`, `\(x\)`, `\[x\]`, all converted to `$x$` |

Topic tags like `[Waves - Wave Speed]` and `Reference:` / `Difficulty:` lines are allowed
in the text file and are left out of the JSON. See `samples/example.txt` for all three
rationale styles in one file.

## Output

One JSON array per input file, one item per question, using a Perseus radio widget.
Each choice looks like this:

```json
{
  "content": "It doubles.",
  "rationale": "Since $T = 2\\pi\\sqrt{L/g}$, multiplying $L$ by $4$ multiplies $T$ by $\\sqrt{4} = 2$.",
  "correct": true,
  "id": "radio-choice-1"
}
```

If two or more options are marked Correct, the item switches to multi-select automatically.

## Error handling

A file with any broken question is not written. All problems are listed at once, so one
editing pass fixes them:

```
$ python3 txt2perseus.py samples/broken.txt
samples/broken.txt: not written — 2 item(s) need fixing
  Q1 option A: no rationale found — expected [Correct : ...] after the option
  Q2: no option marked Correct.
```

The exit code is 1 when any file fails, so it can be used inside scripts.

## How it works

1. **Split** the file into questions using a regular expression that matches headers.
2. **Find options** A, B, C... in order. A letter out of sequence (for example "(D)" inside a
   rationale) is treated as text, not a new option.
3. **Separate option text from rationale** by scanning for bracket groups `[...]` or `{...}`.
   The scanner tracks whether it is inside `$...$` math, so `$[0, L]$` or `$\frac{a}{b}$`
   are never mistaken for rationales.
4. **Validate** each question: at least 2 options, non-empty text and rationale, and at
   least one (but not every) option marked Correct.
5. **Write JSON** and print the quality report.

## Tests

```bash
python3 -m unittest -v
```

## License

MIT
