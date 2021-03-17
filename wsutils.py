#!/usr/bin/python
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------

import sys
from collections import Counter
from io import StringIO
from pathlib import Path
import sqlite3

#---------------------------------------------------------------------------
class Pattern:
    def __init__(self, patt=""):
        self.patt = patt

    @classmethod
    def build(cls, word):
        charCount = Counter(word)
        groupMap = {}
        nextGroup = '1'
        buffer = StringIO()
        for char in word:
            if not char.islower():
                buffer.write(char)
            elif charCount[char] <= 1:
                buffer.write('_')
            else:
                group = groupMap.setdefault(char, nextGroup)
                if group == nextGroup:
                    if nextGroup == '9':
                        nextGroup = 'A'
                    else:
                        nextGroup = chr(ord(nextGroup) + 1)
                buffer.write(group)
        return cls(buffer.getvalue())

    def __str__(self):
        return self.patt

    def __repr__(self):
        return "Pattern('{}')".format(self.patt)

    def __eq__(self, other):
        return self.patt == other.patt

    def matches(self, word):
        return self == Pattern.build(word)

    def groups(self):
        groupCount = Counter(self.patt)
        del groupCount['_']
        return list(groupCount.items())

#---------------------------------------------------------------------------
class Catalog:
    def __init__(self, path):
        conn = sqlite3.connect(path, isolation_level="EXCLUSIVE")
        self.curs = conn.cursor()

    @classmethod
    def create(cls, path):
        cat = Catalog(path)
        cat._createDatabase()
        return cat

    def add(self, word):
        patt = Pattern.build(word)
        pattern = str(patt)
        self.curs.execute("insert or ignore into words values (?, ?)",
                          (word, pattern))

    def count(self, pattern, glob=None):
        rows = self._query("count(*)", pattern, glob)
        return rows[0][0]

    def words(self, pattern, glob=None):
        rows = self._query("word", pattern, glob)
        return [row[0] for row in rows]

    def _query(self, select, pattern, glob):
        pattern = str(pattern)
        if glob and all(goo == '?' for goo in glob):
            glob = None
        if glob:
            qry = "select {} from words where pattern=? and word glob ?" \
                    .format(select)
            args = (pattern, glob)
        else:
            qry = "select {} from words where pattern=? ".format(select)
            args = (pattern,)
        self.curs.execute(qry, args)
        rows = self.curs.fetchall()
        return rows

    def close(self):
        conn = self.curs.connection
        if conn.in_transaction:
            conn.commit()
        conn.close()

    def _createDatabase(self):
        self.curs.executescript("""
            drop table if exists words;
            create table words (
              word        text not null primary key,
              pattern     text not null
            );
            create index idx_words_pattern on words (pattern);
                          """)

#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
