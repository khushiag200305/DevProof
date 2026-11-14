"""
Quiz engine shared by student practice and recruiter skill tests.

Questions live in app/question_bank.json (10 multiple-choice questions per
catalog skill, each with an explanation). An attempt stores which
questions were asked and the order their options were shown in, so the
browser never needs the correct answers before the attempt is submitted.
Pure logic apart from loading the bank file.
"""
import json
import random
from pathlib import Path

BANK_PATH = Path(__file__).resolve().parent.parent / "question_bank.json"


def _load() -> dict[str, list[dict]]:
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))["skills"]
    for skill, questions in data.items():
        for q in questions:
            if len(q["options"]) < 2 or not 0 <= q["answer"] < len(q["options"]):
                raise ValueError(f"Bad question {q.get('id')} for {skill}")
            q["skill"] = skill
    return data


BANK = _load()
BY_ID = {q["id"]: q for questions in BANK.values() for q in questions}
COUNTS = (5, 10, 15)


def known_skills(skills: list[str]) -> list[str]:
    """The requested skills that have questions, in bank spelling, without repeats."""
    lower = {name.lower(): name for name in BANK}
    out: list[str] = []
    for s in skills:
        name = lower.get(str(s).strip().lower())
        if name and name not in out:
            out.append(name)
    return out


def pick_questions(
    skills: list[str], count: int, rng: random.Random | None = None, avoid: set[str] | None = None
) -> list[dict]:
    """
    Up to `count` questions spread evenly over `skills` (round robin), each
    with a shuffled option order. Returns [{"id", "order"}] where order[i]
    is the bank index of the option shown in position i.

    Question ids in `avoid` (e.g. ones the student already saw in practice)
    are only used once the unseen questions for that skill run out.
    """
    rng = rng or random.Random()
    avoid = avoid or set()
    pools = {}
    for s in known_skills(skills):
        shuffled = rng.sample(BANK[s], len(BANK[s]))
        # pop() takes from the end, so unseen questions go last.
        pools[s] = [q for q in shuffled if q["id"] in avoid] + [q for q in shuffled if q["id"] not in avoid]
    picked: list[str] = []
    while len(picked) < count and any(pools.values()):
        for s in list(pools):
            if pools[s] and len(picked) < count:
                picked.append(pools[s].pop()["id"])
    rng.shuffle(picked)
    out = []
    for qid in picked:
        order = list(range(len(BY_ID[qid]["options"])))
        rng.shuffle(order)
        out.append({"id": qid, "order": order})
    return out


def public_question(item: dict) -> dict:
    """What the browser sees while answering: no correct answer, no explanation."""
    q = BY_ID[item["id"]]
    return {
        "id": q["id"],
        "skill": q["skill"],
        "question": q["question"],
        "options": [q["options"][i] for i in item["order"]],
    }


def grade(items: list[dict], answers: dict[str, int | None]) -> dict:
    """
    Score an attempt. `answers` maps question id -> the shown option index
    the student picked (missing or None = unanswered).
    """
    results, per_skill = [], {}
    for item in items:
        q = BY_ID[item["id"]]
        correct_shown = item["order"].index(q["answer"])
        chosen = answers.get(q["id"])
        chosen = chosen if isinstance(chosen, int) and 0 <= chosen < len(item["order"]) else None
        ok = chosen == correct_shown
        stats = per_skill.setdefault(q["skill"], {"correct": 0, "total": 0})
        stats["total"] += 1
        stats["correct"] += int(ok)
        results.append({
            **public_question(item),
            "chosen": chosen,
            "correct": correct_shown,
            "is_correct": ok,
            "explanation": q["explanation"],
        })
    score = sum(r["is_correct"] for r in results)
    return {
        "score": score,
        "total": len(results),
        "percent": round(100 * score / len(results)) if results else 0,
        "per_skill": [{"skill": s, **v} for s, v in per_skill.items()],
        "questions": results,
    }
