#!/usr/bin/env python3
"""
txt2perseus.py — plain-text exercise questions -> Khan Academy Perseus item JSON.

    python3 txt2perseus.py ch01_waves_ex1.txt     -> ch01_waves_ex1.json (12 items)
    python3 txt2perseus.py 01_Waves/              -> one .json per .txt in the folder
    python3 txt2perseus.py exercise.txt --split   -> also exercise_json/item_01.json ...

The .json is a JSON array holding every item of the exercise, in question order.
Nothing is written for a file with a broken item; the errors are listed instead.
"""

import json
import os
import re
import sys

# Question 1 (Easy) | Q1 | Item 7: | Problem 3 | Question 12 [Hard]
HEADER = re.compile(
    r"(?m)^[ \t]*(?:Question|Item|Problem|Q)[ \t]*#?[ \t]*(\d+)"
    r"[ \t]*[:.\)]?[ \t]*(?:[\(\[]([^)\]]*)[\)\]])?[ \t]*$",
    re.IGNORECASE,
)
# A. text | B) text | (C) text
OPTION = re.compile(r"(?m)^[ \t]*\(?([A-F])[\.\)][ \t]+", re.IGNORECASE)
TAG = re.compile(r"^\[[^$]+\]$")                      # a topic tag on its own line
STEM_TAG = re.compile(r"\s*\[[^\[\]$]*\]\s*$")        # a topic tag closing the stem
LABEL = re.compile(r"^(?:Options|Choose 1 answer)[:.]?$", re.IGNORECASE)
DROP = re.compile(
    r"^(?:Reference|Difficulty|Khan Metric|Source|Answer|Ans)[ \t]*[:.]", re.IGNORECASE
)
VERDICT = re.compile(r"^[ \t]*(in)?correct\b[\s.:,;\-–—]*", re.IGNORECASE)


def normalise_math(text):
    """Perseus renders $...$. Accept $$...$$, \\[...\\] and \\(...\\) too."""
    for old in (r"\[", r"\]", r"\(", r"\)"):
        text = text.replace(old, "$")
    return text.replace("$$", "$")


def flat(text):
    return " ".join(text.split())


def paragraphs(lines):
    """Join wrapped lines, keeping blank-line paragraph breaks."""
    out, buf = [], []
    for line in lines:
        if line.strip():
            buf.append(line.strip())
        elif buf:
            out.append(" ".join(buf))
            buf = []
    if buf:
        out.append(" ".join(buf))
    return "\n\n".join(out)


def groups(s):
    """Yield (start, end, inner) for each top-level [ ... ] or { ... } group that
    sits outside math. Brackets inside $\\frac{a}{b}$ or $[0, L]$ are not groups."""
    i, math = 0, False
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "$":
            math = not math
            i += 1
            continue
        if not math and c in "[{":
            close = "]" if c == "[" else "}"
            depth, inner_math, j = 0, False, i
            while j < len(s):
                d = s[j]
                if d == "\\":
                    j += 2
                    continue
                if d == "$":
                    inner_math = not inner_math
                    j += 1
                    continue
                if not inner_math:
                    if d == c:
                        depth += 1
                    elif d == close:
                        depth -= 1
                        if depth == 0:
                            break
                j += 1
            else:
                raise ValueError(f"unclosed {c} ... {close}")
            yield i, j + 1, s[i + 1:j]
            i = j + 1
            continue
        i += 1


def split_option(seg):
    """One option segment -> (text, rationale, correct).

    Accepts the rationale as [Correct : ...], {Correct. ...}, or a bare
    'Correct. ...' line beneath the option. The verdict word is what identifies
    the key, and it is stripped: live KA items carry no verdict opener."""
    for start, _, inner in groups(seg):
        v = VERDICT.match(inner)
        if v:
            return flat(seg[:start]), flat(inner[v.end():]), not v.group(1)

    lines = seg.splitlines()
    for k, line in enumerate(lines[1:], 1):
        v = VERDICT.match(line)
        if not v:
            continue
        tail = [line[v.end():]]
        for nxt in lines[k + 1:]:
            if not nxt.strip():
                break
            tail.append(nxt)
        return flat("\n".join(lines[:k])), flat(" ".join(tail)), not v.group(1)

    raise ValueError("no rationale found — expected [Correct : ...] after the option")


def option_marks(block):
    """Option markers in A, B, C... order. Anything out of sequence is text inside a
    rationale, not a real option. Shared with check.py so the two never diverge."""
    marks = []
    for m in OPTION.finditer(block):
        if m.group(1).upper() == "ABCDEF"[len(marks)]:
            marks.append(m)
    return marks


def parse_item(block, num):
    marks = option_marks(block)
    if len(marks) < 2:
        raise ValueError(f"Q{num}: found {len(marks)} options, need at least 2")

    head = block[:marks[0].start()].splitlines()[1:]
    stem = paragraphs(
        l for l in head
        if not TAG.match(l.strip()) and not LABEL.match(l.strip())
        and not DROP.match(l.strip())
    )
    stem = STEM_TAG.sub("", stem).strip()
    if not stem:
        raise ValueError(f"Q{num}: empty stem")

    choices = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(block)
        letter = m.group(1).upper()
        try:
            text, rationale, correct = split_option(block[m.end():end])
        except ValueError as e:
            raise ValueError(f"Q{num} option {letter}: {e}")
        if not text:
            raise ValueError(f"Q{num} option {letter}: no option text")
        if not rationale:
            raise ValueError(f"Q{num} option {letter}: empty rationale")
        choices.append({
            "content": text,
            "rationale": rationale,
            "correct": correct,
            "id": f"radio-choice-{i}",
        })

    n_correct = sum(c["correct"] for c in choices)
    if n_correct == 0:
        raise ValueError(f"Q{num}: no option marked Correct.")
    if n_correct == len(choices):
        raise ValueError(f"Q{num}: every option is marked Correct.")

    return {
        "question": {
            "content": stem + "\n\n[[☃ radio 1]]\n\n",
            "images": {},
            "widgets": {
                "radio 1": {
                    "type": "radio",
                    "alignment": "default",
                    "static": False,
                    "graded": True,
                    "options": {
                        "choices": choices,
                        "randomize": True,
                        "multipleSelect": n_correct > 1,
                        "countChoices": False,
                        "hasNoneOfTheAbove": False,
                        "deselectEnabled": False,
                        "numCorrect": n_correct,
                    },
                    "version": {"major": 3, "minor": 0},
                }
            },
        },
        "answerArea": {
            "calculator": False,
            "financialCalculatorMonthlyPayment": False,
            "financialCalculatorTotalAmount": False,
            "financialCalculatorTimeToPayOff": False,
            "periodicTable": False,
            "periodicTableWithKey": False,
        },
        "hints": [],
    }


def report(items, diffs):
    """Key balance and the length cue, the two defects a reader cannot see."""
    keys, sizes, bias = [], [], 0
    for item in items:
        ch = item["question"]["widgets"]["radio 1"]["options"]["choices"]
        lens = [len(c["content"]) for c in ch]
        ki = [j for j, c in enumerate(ch) if c["correct"]][0]
        keys.append("ABCDEF"[ki])
        sizes.append(len(ch))
        if lens[ki] == max(lens) and lens.count(max(lens)) == 1:
            bias += 1

    n = len(keys)
    letters = "ABCDEF"[:max(sizes)]
    counts = {L: keys.count(L) for L in letters}
    chance = sum(1 / s for s in sizes) / n
    print("  keys " + "  ".join(f"{L}:{counts[L]}" for L in letters)
          + f"  |  key is longest in {bias}/{n} ({bias / n:.0%}, chance {chance:.0%})")

    order = ("Easy", "Medium", "Hard")
    if any(d in order for d in diffs):
        tally = {d: diffs.count(d) for d in order}
        print(f"  difficulty  {tally['Easy']}E / {tally['Medium']}M / {tally['Hard']}H")

    span = max(counts.values()) - min(counts.values())
    if span > 2:
        print(f"  WARN  key balance is uneven — spread of {span} across {letters}")
    if bias / n > 0.30:
        print(f"  WARN  the longest option is the answer in {bias / n:.0%} of items "
              "— expand the distractors")


def convert(path, split=False):
    raw = normalise_math(open(path, encoding="utf-8").read())
    starts = [m.start() for m in HEADER.finditer(raw)]
    if not starts:
        print(f"{path}: no question headers found")
        return False
    starts.append(len(raw))

    items, diffs, errors = [], [], []
    for i in range(len(starts) - 1):
        block = raw[starts[i]:starts[i + 1]]
        head = HEADER.search(block)
        num = int(head.group(1))
        try:
            items.append(parse_item(block, num))
        except ValueError as e:
            errors.append(str(e))
            continue
        diffs.append((head.group(2) or "").strip().title())

    if errors:
        print(f"{path}: not written — {len(errors)} item(s) need fixing")
        for e in errors:
            print(f"  {e}")
        return False

    out = os.path.splitext(path)[0] + ".json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"{path} -> {out}   {len(items)} items")

    if split:
        outdir = os.path.splitext(path)[0] + "_json"
        os.makedirs(outdir, exist_ok=True)
        for n, item in enumerate(items, 1):
            with open(f"{outdir}/item_{n:02d}.json", "w", encoding="utf-8") as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
        print(f"  split into {outdir}/item_01.json ...")

    report(items, diffs)
    return True


def main():
    args = [a for a in sys.argv[1:] if a != "--split"]
    split = "--split" in sys.argv[1:]
    usage = "usage: python3 txt2perseus.py exercise.txt | folder/ [--split]"
    if not args or args[0] in ("-h", "--help"):
        sys.exit(usage)

    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += sorted(os.path.join(a, f) for f in os.listdir(a)
                            if f.endswith(".txt"))
        elif os.path.isfile(a):
            paths.append(a)
        else:
            sys.exit(f"{a}: no such file or folder")

    ok = all([convert(p, split) for p in paths])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
