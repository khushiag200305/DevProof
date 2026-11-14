"""Tests for the pure quiz engine and the question bank (app/services/quiz.py)."""
import json
import random

from app.services import quiz


def test_every_catalog_skill_has_five_valid_questions():
    catalog = {s["name"] for s in json.load(open("app/skills_catalog.json"))["skills"]}
    assert set(quiz.BANK) == catalog
    ids = set()
    for skill, questions in quiz.BANK.items():
        assert len(questions) == 5, skill
        for q in questions:
            assert len(q["options"]) == 4 and len(set(q["options"])) == 4
            assert 0 <= q["answer"] < 4 and q["explanation"]
            assert q["id"] not in ids
            ids.add(q["id"])


def test_questions_are_spread_across_skills_and_options_shuffled():
    items = quiz.pick_questions(["Python", "docker", "Nope"], 6, random.Random(1))
    skills = [quiz.BY_ID[i["id"]]["skill"] for i in items]
    assert sorted(skills) == ["Docker"] * 3 + ["Python"] * 3
    assert len({i["id"] for i in items}) == 6
    assert all(sorted(i["order"]) == [0, 1, 2, 3] for i in items)


def test_count_is_capped_by_available_questions():
    assert len(quiz.pick_questions(["Python"], 15)) == 5
    assert quiz.pick_questions(["Not a skill"], 5) == []


def test_public_questions_hide_the_answer():
    item = quiz.pick_questions(["SQL"], 1, random.Random(2))[0]
    shown = quiz.public_question(item)
    assert set(shown) == {"id", "skill", "question", "options"}
    original = quiz.BY_ID[item["id"]]["options"]
    assert shown["options"] == [original[i] for i in item["order"]]


def test_grading_uses_the_shown_option_order():
    items = quiz.pick_questions(["Python", "SQL"], 4, random.Random(3))
    right = {i["id"]: i["order"].index(quiz.BY_ID[i["id"]]["answer"]) for i in items}
    answers = dict(right)
    first, second = items[0]["id"], items[1]["id"]
    answers[first] = (right[first] + 1) % 4  # wrong
    answers[second] = None  # unanswered
    result = quiz.grade(items, answers)
    assert (result["score"], result["total"], result["percent"]) == (2, 4, 50)
    assert sum(s["total"] for s in result["per_skill"]) == 4
    graded = {q["id"]: q for q in result["questions"]}
    assert graded[first]["is_correct"] is False and graded[first]["correct"] == right[first]
    assert graded[second]["chosen"] is None and graded[second]["explanation"]
