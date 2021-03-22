#!/usr/bin/python
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------

import sys
from collections import deque
from contextlib import closing, suppress
from itertools import chain, groupby, product, zip_longest
from io import StringIO
from operator import attrgetter, itemgetter
from pathlib import Path
from pprint import pprint
import re
import readline
from wsutils import Pattern, Catalog

#---------------------------------------------------------------------------
class Letters:
    "A bitmask of possible (lowercase) letters"
    ALL_BITS = 0x3ffffff

    def __init__(self, letters="", *, bits=0b0):
        self.bits  = bits
        self.set(letters)

    @classmethod
    def all(cls):
        return cls(bits=cls.ALL_BITS)

    def __str__(self):
        return "".join(self)

    def __repr__(self):
        return "Letters('{}')".format(self)

    def __iter__(self):
        for x in range(26):
            if 1 << x & self.bits:
                yield chr(0x61 + x)

    def __contains__(self, letters):
        v = self._bits(letters)
        return self.bits & v == v

    def __eq__(self, other):
        return self.bits == self._bits(other)

    def __lt__(self, other):
        return self.bits < self._bits(other)

    def __len__(self):
        v = self.bits
        count = 0
        while v:
            v &= v-1
            count += 1
        return count

    @property
    def solved(self):
        "return True iff only 1 bit is set"
        v = self.bits
        return not v & v-1 and v

    def clear(self):
        self.bits = 0x0

    def set(self, letters):
        self.bits |= self._bits(letters)

    def unset(self, letters):
        self.bits &= ~self._bits(letters)

    def assign(self, letters):
        self.bits = self._bits(letters)

    def glob(self):
        if self.bits == self.ALL_BITS:
            retval = "?"
        else:
            retval = str(self)
            if len(retval) > 1:
                retval = "[{}]".format(retval)
        return retval

    def asbits(self):
        bit = 0b1
        for x in range(26):
            if bit & self.bits:
                yield bit
            bit <<= 1

    @classmethod
    def _bits(cls, letters):
        if isinstance(letters, cls):
            return letters.bits
        bits = 0b0
        for letter in letters:
            bits |= 1 << ord(letter) - 0x61
        return bits


#---------------------------------------------------------------------------
class Cipher:
    def __init__(self, crypted, decrypted=""):
        self.map = {}
        for cipherLetter, plainLetter in zip_longest(crypted, decrypted):
            if cipherLetter.islower() and cipherLetter not in self.map:
                if plainLetter is not None and plainLetter.islower():
                    self.map[cipherLetter] = Letters(plainLetter)
                else:
                    self.map[cipherLetter] = Letters.all()
        if decrypted:
            self.reduce()

    def __repr__(self):
        letters = []
        globs = []
        for cipherLetter, possibles in self.map.items():
            letters.append(cipherLetter)
            globs.append(possibles.glob())
        return "Cipher {}->{}".format("".join(letters),
                                      "".join(globs))

    def keys(self):               return self.map.keys()
    def values(self):             return self.map.values()
    def items(self):              return self.map.items()
    def __contains__(self, key):  return key in self.map
    def __getitem__(self, key):   return self.map[key]

    def process(self, crypted, possibleDecrypts):
        self.batchProcess([(crypted, possibleDecrypts)])

    def batchProcess(self, cryptedWords):
        processed = set()
        for (crypted, possibleDecrypts) in cryptedWords:
            for i, cipherLetter in enumerate(crypted):
                if cipherLetter in processed:
                    continue  # only process the same letter once
                processed.add(cipherLetter)
                if cipherLetter.islower():
                    possibles = self.map[cipherLetter]
                    possibles.clear()
                    for guess in possibleDecrypts:
                        possibles.set(guess[i])

    @property
    def solved(self):
        return all(possibles.solved for possibles in self.values())

    def reduce(self):
        # for all len(1) remove from others
        # for all len(2) if there is a matching len(2) remove from others
        # for all len(3) if 2 other matching len(3) remove from others
        # for all len(4) if 3 other matching len(4) remove from others
        # etc...
        possiblesByLen = self._preparePossiblesByLen(self.values())
        if possiblesByLen[0]:
            print ("No possibles for {}"
                               .format([k for k,v in self.map.items()
                                        if len(v) == 0]))
        reductionsTotal = 0
        for go in range(1, 12):
            reductionsThisGo = 0
            for n in range(1, 13-go):
                reductions = self._reduceBy(n, possiblesByLen)
                reductionsThisGo += reductions
                reductionsTotal  += reductions
            if reductionsThisGo == 0:
                break
            possiblesToPrepare = chain.from_iterable(possiblesByLen)
            possiblesByLen = self._preparePossiblesByLen(possiblesToPrepare)
        return reductionsTotal

    def _preparePossiblesByLen(self, possiblesToPrepare):
        possiblesByLen = [[] for l in range(27)]
        for possibles in possiblesToPrepare:
            possiblesByLen[len(possibles)].append(possibles)
        return possiblesByLen

    def _reduceBy(self, n, possiblesByLen):
        reductions = 0
        possiblesByLen[n].sort()
        unreducingPossibles = []
        for letters, group in groupby(possiblesByLen[n]):
            matchingPossibles = list(group)
            lenMatching = len(matchingPossibles)
            if lenMatching == n:
                self._reducePossibles(letters, n+1, possiblesByLen)
                reductions += 1
            elif lenMatching < n:
                unreducingPossibles.extend(matchingPossibles)
            else:
                # FIXME work on a copy of possibles and only
                # assign if there are no errors
                print("Homophonic substitution to {}".format(letters))
        possiblesByLen[n] = unreducingPossibles
        return reductions

    def _reducePossibles(self, letters, m, possiblesByLen):
        for o in range(m, 27):
            possiblesToReduce = possiblesByLen[o]
            for possibles in possiblesToReduce:
                possibles.unset(letters)

    def decrypt(self, crypted):
        buffer = StringIO()
        for letter in crypted:
            if letter.islower():
                possibles = self.map[letter]
                if possibles.solved:
                    buffer.write(str(possibles))
                else:
                    buffer.write('_')
            else:
                buffer.write(letter)
        return buffer.getvalue()

#---------------------------------------------------------------------------
class Word:
    def __init__(self, cryptedWord):
        self.crypted  = cryptedWord
        self.pattern  = Pattern.build(cryptedWord)
        self.cryptedLetters = set(cryptedWord)
        self.links    = []
        self.count    = None
        self._guesses = []

    def __repr__(self):
        return "{0} ({1})".format(self.crypted, self.count)

    @property
    def solved(self):
        return self.count == 1

    @property
    def unsolvable(self):
        return self.count == 0

    @property
    def guesses(self):
        return self._guesses

    @guesses.setter
    def guesses(self, g):
        self._guesses = g
        self.count = len(g)

    def glob(self, cipher):
        buffer = StringIO()
        for char in self.crypted:
            if char.islower():
                buffer.write(cipher[char].glob())
            else:
                buffer.write(char)
        return buffer.getvalue()

    def regex(self, cipher):
        pattern = self.glob(cipher).replace('?', '.')
        return re.compile(pattern)

    def decrypt(self, cipher):
        return cipher.decrypt(self.crypted)

    def sharedLetters(self, word2):
        shared = self.cryptedLetters & word2.cryptedLetters
        return "".join(sorted(shared))


#---------------------------------------------------------------------------
class Solver:
    def __init__(self, catalog, crypted, known):
        self.cat       = catalog
        cryptedWords   = re.findall(r"[a-z']+", crypted)
        self.crypted   = " ".join(cryptedWords)
        self.words     = [Word(word) for word in cryptedWords]
        cryptedLetters, knownLetters = self._parse(crypted, known)
        self.cipher    = Cipher(cryptedLetters, knownLetters)
        self.root      = None
        self.unlinked  = []

    def _parse(self, crypted, known):
        cLen = len(crypted)
        cryptedLetters = []
        knownLetters   = []
        kMap = {}
        cIdx = kIdx = None
        with suppress(ValueError):
            kIdx = known.index('=')
            cIdx = crypted.index('=')
        if kIdx and (kIdx != cIdx):
            for assignment in re.findall(r"([a-z])=([a-z])", known):
                kMap[assignment[0]] = assignment[1]
            for i in range(cLen):
                cipherLetter = crypted[i]
                if cipherLetter.islower() or cipherLetter == "'":
                    cryptedLetters.append(cipherLetter)
                    knownLetters.append(kMap.get(cipherLetter, ' '))
        else:
            kLen = len(known)
            for i in range(cLen):
                cipherLetter = crypted[i]
                if cipherLetter.islower() or cipherLetter == "'":
                    cryptedLetters.append(cipherLetter)
                    if i < kLen:
                        plainLetter  = known[i]
                        knownLetters.append(plainLetter)
        return "".join(cryptedLetters), "".join(knownLetters)

    @property
    def solved(self):
        return all(word.solved for word in self.words)

    def solve(self):
        self.prepare()
        self.match()
        self.filter()

    def prepare(self):
        for word in self.words:
            glob = word.glob(self.cipher)
            word.count = self.cat.count(word.pattern, glob)
            if word.count == 1:   # too easy
                word.guesses = self.cat.words(word.pattern)
                self.cipher.process(word.crypted, word.guesses)
        words = deque(sorted(self.words, key=attrgetter("count")))
        for n in range(len(words)):
            self._buildTree(words)
            # try for no more than 2 unlinked words
            if len(self.unlinked) < 3:
                break
            for word in words:
                word.links = []
            words.rotate(-1)
        else:
            # back at the beginning
            self._buildTree(self.words)

    def _buildTree(self, words):
        others  = list(words)
        visited = {words[0]}
        queue   = deque(visited)
        while queue:
            word1 = queue.popleft()
            others.remove(word1)
            for word2 in others:
                letters = Word.sharedLetters(word1, word2)
                if letters and word2 not in visited:
                    word1.links.append((letters, word2))
                    visited.add(word2)
                    queue.append(word2)
        self.root = words[0]
        self.unlinked = others

    def match(self):
        startCount = prevCount = sum(word.count for word in self.words)
        stuck = 0
        for go in range(10):
            count  = self._matchLinked()
            count += self._matchUnlinked()
            self.cipher.reduce()
            print("Matching {} possible words at go {}".format(count, go))
            if self.solved:
                break
            if count >= prevCount:
                stuck += 1
                if stuck > 1:
                    break
            else:
                stuck = 0
            prevCount = count
        return startCount - prevCount

    def _matchLinked(self):
        count = 0
        visited = {self.root}
        queue   = deque(visited)
        while queue:
            word1 = queue.popleft()
            self._matchWord(word1)
            count += word1.count
            for letters, word2 in word1.links:
                if word2 not in visited:
                    visited.add(word2)
                    queue.append(word2)
        return count

    def _matchUnlinked(self):
        count = 0
        for word in self.unlinked:
            self._matchWord(word)
            count += word.count
        return count

    def _matchWord(self, word):
        if not word.solved:
            glob = word.glob(self.cipher)
            word.guesses = self.cat.words(word.pattern, glob)
            if word.count:
                self.cipher.process(word.crypted, word.guesses)

    def filter(self):
        totalFiltered = 0
        for go in range(10):
            numFilteredWithWords = self._filterWithWords()
            print("Filtered {} with words in go {}".format(numFilteredWithWords, go))
            totalFiltered += numFilteredWithWords
            if numFilteredWithWords:
                self.cipher.batchProcess(((word.crypted, word.guesses)
                                          for word in self.words
                                          if word.count))
                numReductions = self.cipher.reduce()
                print("Reduced {} possibles in go {}".format(numReductions, go))
            else:
                numReductions = 0
            if numReductions:
                numFilteredWithCipher = self._filterWithCipher()
                totalFiltered += numFilteredWithWords
                print("Filtered {} with cipher in go {}"
                      .format(numFilteredWithCipher, go))
            else:
                break
        return totalFiltered

    def _filterWithWords(self):
        numFilteredThisGo = 0
        for i, word1 in enumerate(self.words):
            if word1.unsolvable:
                continue
            for word2 in self.words[i+1:] + self.words[:i]:
                if word2.unsolvable:
                    continue
                if word1.solved and word2.solved:
                    continue
                sharedLetters = Word.sharedLetters(word1, word2)
                if not sharedLetters:
                    continue
                numFiltered = self._filterGuesses(sharedLetters,
                                                  word1, word2)
                numFilteredThisGo += numFiltered
        return numFilteredThisGo

    def _filterGuesses(self, sharedLetters, word1, word2):
        filtered1 = []
        filtered2 = []
        indices1 = [word1.crypted.index(c) for c in sharedLetters]
        indices2 = [word2.crypted.index(c) for c in sharedLetters]
        getter1 = itemgetter(*indices1)
        getter2 = itemgetter(*indices2)
        guesses1 = sorted(word1.guesses, key=getter1)
        guesses2 = sorted(word2.guesses, key=getter2)
        it1 = iter(guesses1)
        it2 = iter(guesses2)
        guess1 = guess2 = None
        prevLetters1 = prevLetters2 = None
        letters1 = letters2 = None
        def nextLetters1():
            nonlocal guess1, prevLetters1, letters1
            guess1 = next(it1, None)
            prevLetters1 = letters1
            letters1 = getter1(guess1) if guess1 else ""
        def nextLetters2():
            nonlocal guess2, prevLetters2, letters2
            guess2 = next(it2, None)
            prevLetters2 = letters2
            letters2 = getter2(guess2) if guess2 else ""
        nextLetters1()
        nextLetters2()
        while guess1 is not None or guess2 is not None:
            if letters1 == letters2:
                filtered1.append(guess1)
                filtered2.append(guess2)
                nextLetters1()
                nextLetters2()
            elif letters1 == prevLetters2:
                filtered1.append(guess1)
                nextLetters1()
            elif guess2 is None:
                nextLetters1()
            elif letters2 == prevLetters1:
                filtered2.append(guess2)
                nextLetters2()
            elif guess1 is None:
                nextLetters2()
            elif letters1 < letters2:
                nextLetters1()
            else:
                nextLetters2()
        numFiltered = 0
        newCount1 = len(filtered1)
        newCount2 = len(filtered2)
        if word1.count != newCount1 and newCount2:
            numFiltered += word1.count - newCount1
            word1.guesses = filtered1
        if word2.count != newCount2 and newCount1:
            numFiltered += word2.count - newCount2
            word2.guesses = filtered2
        return numFiltered

    def _filterWithCipher(self):
        numFiltered = 0
        for word in self.words:
            regex = word.regex(self.cipher)
            filtered = []
            for guess in word.guesses:
                if regex.fullmatch(guess):
                    filtered.append(guess)
            newCount = len(filtered)
            if word.count != newCount:
                numFiltered += word.count - newCount
                word.guesses = filtered
        return numFiltered

    def decrypt(self):
        return self.cipher.decrypt(self.crypted)

    def _debug(self):
        print(self.crypted)
        for word1 in self.words:
            print(word1)
            pprint(word1.guesses)
            for (letters, word2) in word1.links:
                print("  {} -> {}".format(letters, word2.crypted))
        print("")

    def print(self):
        print(self.crypted)
        print(self.cipher)
        print()
        print(self.decrypt())
        self._printColumns()
        #self._printProduct()

    def _printColumns(self):
        height = max((len(word.guesses) for word in self.words))
        spaces = [" " * len(word.crypted) for word in self.words]
        for y in range(height):
            for x in range(len(self.words)):
                word = self.words[x]
                if y < len(word.guesses):
                    guess = word.guesses[y]
                else:
                    guess = spaces[x]
                print(guess+" ", end='')
            print()
            if (y+1) % 40 == 0:
                cont = input("Type b to break, or push return to continue...")
                if cont == 'b':
                    break

    def _printProduct(self):
        guesses = []
        for word in self.words:
            if word.unsolvable:
                guesses.append([word.decrypt(self.cipher)])
            else:
                guesses.append(word.guesses)
        for decrypt in product(*guesses):
            print(" ".join(decrypt))


#---------------------------------------------------------------------------
def main():
    if len(sys.argv) != 2:
        print("usage: wssolve CATALOG-FILE")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.is_file():
        print("File %s not found")
        sys.exit(1)

    cryptogram = input("Enter the cryptogram:    ").lower()
    known      = input("Enter any known letters: ").lower()
    with closing(Catalog(path)) as cat:
        solver = Solver(cat, cryptogram, known)
        solver.solve()
        solver.print()

if __name__ == "__main__":
    main()

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
