#!/usr/bin/python
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------

import sys
from pathlib import Path
from contextlib import closing
from wsutils import Catalog

#---------------------------------------------------------------------------
class WordList:
    def __init__(self, path):
        self. path = path

    def __iter__(self):
        with self.path.open() as wordsIn:
            for word in wordsIn:
                word = word.replace('\n', '').lower()
                if all('a' <= l <= 'z' or l == "'" for l in word):
                    yield word

#---------------------------------------------------------------------------
def main():
    if not len(sys.argv) in (2, 3):
        print("usage: wsbuild TEXT-FILE [CATALOG-FILE]")
        sys.exit(1)
    pathIn = Path(sys.argv[1])
    if not pathIn.is_file():
        print("File %s not found")
        sys.exit(1)
    if len(sys.argv) == 3:
        pathOut = Path(sys.argv[2])
    else:
        pathOut = pathIn.with_suffix(".db")

    words = WordList(pathIn)
    with closing(Catalog.create(pathOut)) as cat:
        for word in words:
            cat.add(word)

if __name__ == "__main__":
    main()

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
