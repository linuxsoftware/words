#!/usr/bin/env python3
#---------------------------------------------------------------------------
# Utility tests
#---------------------------------------------------------------------------

import unittest
from wsutils import Pattern
from wssolve import Letters, Cipher, Word, Solver

#---------------------------------------------------------------------------
class TestPattern(unittest.TestCase):
    def testEmpty(self):
        p = Pattern()
        self.assertEqual(p.patt, "")

    def testBuild(self):
        p = Pattern.build("abccad")
        self.assertEqual(p.patt, "1_221_")

    def testMatches(self):
        p = Pattern("122_3_1_3__")
        self.assertTrue(p.matches("application"))

    def testGroups(self):
        p = Pattern("122_3_1_3__")
        self.assertCountEqual(p.groups(), [('1', 2), ('2', 2), ('3', 2)])

#---------------------------------------------------------------------------
class TestLetters(unittest.TestCase):
    def testEmpty(self):
        l = Letters()
        self.assertEqual(l.bits,  0b0)

    def testInit(self):
        l = Letters("abcda")
        self.assertEqual(l.bits,  0b1111)

    def testAll(self):
        l = Letters.all()
        self.assertEqual(l.bits,  0x3ffffff)

    def testLen(self):
        l = Letters("alphabet")
        self.assertEqual(len(l), 7)

    def testIter(self):
        l = Letters("alphabet")
        self.assertCountEqual(list(l), ['a', 'l', 'p', 'h', 'b', 'e', 't'])

    def testStr(self):
        l = Letters("alphabet")
        self.assertEqual(str(l), "abehlpt")

    def testContains(self):
        l = Letters("alphabet")
        self.assertIn("a", l)
        self.assertIn("abe", l)
        self.assertNotIn("c", l)
        self.assertNotIn("to", l)

    def testSolved(self):
        l0 = Letters("")
        self.assertFalse(l0.solved)
        l1 = Letters("a")
        self.assertTrue(l1.solved)
        l2 = Letters("eo")
        self.assertFalse(l2.solved)

    def testClear(self):
        l = Letters("alphabet")
        l.clear()
        self.assertEqual(l.bits,  0b0)

    def testSet(self):
        l = Letters("alphabet")
        l.set("cd")
        self.assertEqual(str(l), "abcdehlpt")

    def testUnset(self):
        l = Letters("alphabet")
        l.unset("a")
        self.assertEqual(str(l), "behlpt")

    def testAssign(self):
        l = Letters("alphabet")
        l.assign("xyz")
        self.assertEqual(str(l), "xyz")

    def testGlob(self):
        l1 = Letters("a")
        g1 = l1.glob()
        self.assertEqual(g1, "a")
        l5 = Letters("alpha")
        g5 = l5.glob()
        self.assertEqual(g5, "[ahlp]")
        l26 = Letters.all()
        g26 = l26.glob()
        self.assertEqual(g26, "?")

    def testEquality(self):
        l1 = Letters("alpha")
        l2 = Letters("beta")
        l3 = Letters("bbeat")
        self.assertEqual(l1, l1)
        self.assertEqual(l1, "ahlp")
        self.assertNotEqual(l1, l2)
        self.assertEqual(l2, l3)

    def testLt(self):
        l1 = Letters("a")
        l2 = Letters("z")
        self.assertLess(l1, l2)
        self.assertLess(l1, "ca")

    def testAsbits(self):
        l0 = Letters()
        b0 = list(l0.asbits())
        self.assertEqual(b0, [])
        l1 = Letters("delta")
        b1 = list(l1.asbits())
        self.assertEqual(b1, [0b00000000000000000000000001,
                              0b00000000000000000000001000,
                              0b00000000000000000000010000,
                              0b00000000000000100000000000,
                              0b00000010000000000000000000])
        l3 = Letters.all()
        b3 = list(l3.asbits())
        self.assertEqual(b3[-1], 0b10000000000000000000000000)

#---------------------------------------------------------------------------
class TestCipher(unittest.TestCase):
    def testInit(self):
        x = Cipher("yvggyr xvggra")
        self.assertCountEqual(x.keys(), ['y', 'v', 'g',  'r', 'x', 'a'])
        self.assertIn("i", x['v'])

    def testProcess(self):
        x = Cipher("yvggyr xvggra")
        x.process("yvggyr", ["eiffel", "tweets", "little", "eassel", "outtop",
                             "shiism", "sloosh", "snoose", "swoosh", "squush"])
        self.assertEqual(x['y'], "etlos")
        self.assertEqual(x['v'], "iwauhlnq")
        self.assertEqual(x['g'], "fetiosu")
        self.assertEqual(x['r'], "lsepmh")

    def testSolved(self):
        x = Cipher("png")
        x['p'].assign("c")
        x['n'].assign("a")
        self.assertFalse(x.solved)
        x['g'].assign("t")
        self.assertTrue(x.solved)

    def testReduce2(self):
        x = Cipher("yvggyr xvggra")
        x['v'].assign("iut")
        x['x'].assign("bdfhkmpsw")
        x['r'].assign("iut")
        x['g'].assign("t")
        reductions = x.reduce()
        self.assertEqual(reductions, 2)
        self.assertFalse(x.solved)
        self.assertNotIn("t", x['y'])
        self.assertIn("i", x['v'])
        self.assertIn("u", x['v'])
        self.assertIn("i", x['r'])
        self.assertIn("u", x['r'])
        self.assertTrue(x['g'].solved)
        self.assertFalse(x['v'].solved)

    def testReduce3(self):
        x = Cipher("yvggyr xvggra")
        x['v'].assign("iu")
        x['x'].assign("kniu")
        x['a'].assign("kniu")
        x['r'].assign("iu")
        x['g'].assign("t")
        reductions = x.reduce()
        self.assertEqual(reductions, 3)
        self.assertFalse(x.solved)
        self.assertNotIn("t", x['y'])
        self.assertIn("i", x['v'])
        self.assertIn("u", x['v'])
        self.assertIn("i", x['r'])
        self.assertIn("u", x['r'])
        self.assertTrue(x['g'].solved)
        self.assertFalse(x['v'].solved)
        self.assertIn("k", x['x'])
        self.assertIn("n", x['a'])
        self.assertNotIn("n", x['y'])

    def testDecrypt(self):
        x = Cipher("yvggyr xvggra")
        x['r'].assign("e")
        x['v'].assign("i")
        x['g'].assign("t")
        x['x'].assign("k")
        self.assertEqual(x.decrypt("yvggyr xvggra"), "_itt_e kitte_")

#---------------------------------------------------------------------------
class TestWord(unittest.TestCase):
    def testInit(self):
        w = Word("yvggyr")
        self.assertEqual(w.crypted, "yvggyr")
        self.assertEqual(w.pattern, Pattern("1_221_"))
        self.assertEqual(w.count, None)

    def testGlob(self):
        x = Cipher("yvggyr xvggra")
        x['v'].assign("iwauhlnq")
        x['g'].assign("ftiosu")
        x['r'].assign("e")
        w = Word("yvggyr")
        g = w.glob(x)
        self.assertEqual(g, "?[ahilnquw][fiostu][fiostu]?e")

    def testSharedLetters(self):
        w1 = Word("zrng")
        w2 = Word("zbfg")
        self.assertCountEqual(w1.sharedLetters(w2), "zg")

#---------------------------------------------------------------------------
class Catalog:
    def __init__(self, data=None):
        self.data = data or {}
    def count(self, pattern, glob):
        return len(self.words(pattern, glob))
    def words(self, pattern, glob):
        pattern = str(pattern)
        return self.data.get(pattern, [pattern]*9)

class TestSolverPrepare(unittest.TestCase):
    def setUp(self):
        cat = Catalog({
        '___':      ["the", "was", "you", "dog"],
        '____':     ["duck", "path", "seat", "post", "shot", "grey"],
        '__11__':   ["happen", "kitten", "yellow"],
        '1_221_':   ["little", "hidden"],
        })
        self.solver = Solver(cat, "gur yvggyr xvggra jnf oynpx", "")

    def testInit(self):
        words = self.solver.words
        self.assertEqual([w.crypted for w in words],
                         ["gur", "yvggyr", "xvggra", "jnf", "oynpx"])
        self.assertEqual(words[0].links, [])

    def testPrepare(self):
        words = self.solver.words
        self.solver.prepare()
        self.assertEqual(self.solver.root.crypted, "yvggyr")
        gur, yvggyr, xvggra, jnf, oynpx = words
        self.assertEqual(yvggyr.links, [("grv", xvggra), ("gr",  gur), ("y",   oynpx)])
        self.assertEqual(xvggra.links, [])
        self.assertEqual(oynpx.links, [("n", jnf)])

class TestSolverFilter(unittest.TestCase):
    def testFilterWithWords(self):
        solver = Solver(Catalog(), "edb bc abcd", "")
        solver.words[0].guesses = ["ula", "uta", "uti"]
        solver.words[1].guesses = ["an", "as", "is"]
        solver.words[2].guesses = ["mast", "mint"]
        numFiltered = solver._filterWithWords()
        self.assertEqual(numFiltered, 5)
        self.assertTrue(solver.solved)
        guess = [word.guesses[0] for word in solver.words]
        self.assertEqual(guess, ["uta", "as", "mast"])

    def testFilterGuesses(self):
        solver = Solver(Catalog(), "gur yvggyr xvggra jnf oynpx", "")
        word1 = Word("oynpx")
        word1.guesses = ["black", "clunk", "plumb", "block", "flask", "slunk", "clank"]
        word2 = Word("jnf")
        word2.guesses = ["was", "bum", "daw", "cab", "bug", "ham", "bay", "day", "yam"]
        sharedLetters = "n"
        solver._filterGuesses(sharedLetters, word1, word2)
        self.assertNotIn("block", word1.guesses)

    def testFilterWithCipher(self):
        solver = Solver(Catalog(), "zrng naq cbgngbrf", "")
        solver.words[0].guesses = ["care", "each", "fate", "meat", "town"]
        solver.words[1].guesses = ["and", "the", "was", "for", "not", "one"]
        solver.words[2].guesses = ["citation", "folklore", "potatoes", "wildlife"]
        solver.cipher['r'].assign("e")
        solver.cipher['b'].assign("o")
        solver.cipher['n'].assign("a")
        numFiltered = solver._filterWithCipher()
        self.assertEqual(numFiltered, 12)
        self.assertTrue(solver.solved)
        guess = [word.guesses[0] for word in solver.words]
        self.assertEqual(guess, ["meat", "and", "potatoes"])

#---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
