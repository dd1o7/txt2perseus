"""Basic tests. Run with:  python3 -m unittest"""
import unittest
import txt2perseus as tp


class TestParser(unittest.TestCase):

    def test_parses_one_item(self):
        block = ("Question 1\nWhat is $2 + 2$?\n"
                 "A. $3$ [Incorrect : One short.]\n"
                 "B. $4$ [Correct : Two plus two is four.]\n")
        item = tp.parse_item(block, 1)
        choices = item["question"]["widgets"]["radio 1"]["options"]["choices"]
        self.assertEqual(len(choices), 2)
        self.assertTrue(choices[1]["correct"])
        self.assertEqual(choices[1]["rationale"], "Two plus two is four.")

    def test_brackets_inside_math_are_not_rationales(self):
        block = ("Q1\nOn which interval is $x$ defined?\n"
                 "A. $[0, L]$ [Correct : The box runs from $0$ to $L$.]\n"
                 "B. $[0, 2L]$ [Incorrect : That is twice the box length.]\n")
        choices = tp.parse_item(block, 1)["question"]["widgets"]["radio 1"]["options"]["choices"]
        self.assertEqual(choices[0]["content"], "$[0, L]$")

    def test_missing_correct_answer_is_an_error(self):
        block = ("Q1\nPick one.\n"
                 "A. x [Incorrect : No.]\n"
                 "B. y [Incorrect : No.]\n")
        with self.assertRaises(ValueError):
            tp.parse_item(block, 1)

    def test_math_delimiters_are_normalised(self):
        self.assertEqual(tp.normalise_math(r"\(x\) and $$y$$"), "$x$ and $y$")


if __name__ == "__main__":
    unittest.main()
