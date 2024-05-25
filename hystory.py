import pandas as pd
from paths import FOLDER
from datetime import datetime, timedelta

HYSTORY_MAX = 8
HYSTORY_FILE = FOLDER + 'hystory.csv'
TIME_FORMAT = "%d/%m/%y %H:%M:%S"
TIME_PARSER = lambda d: datetime.strptime(d, TIME_FORMAT) if pd.notna(d) else d
UPDATE_TIME = timedelta(seconds=60)
NAN_REP = '#NA'

"""
This module creates an hystory divided in pages
Access hystory of <page> by Hystory[<page>]
Add new words by Hystory[<page>] = <word>
    even more with Hystory[<page>] = [<word>, ...]
If you add with stop == None: all words will be replaced: Hystory[<page>:]
Updates in file with .update() or Automatically when adding after UPDATE_TIME
All duplicates are removed (same page) and only HISTORY_MAX words are kept, at every update,
    dropping from older ones
If pages is given than only those page will be permitted and others are lackily to desappear from the file too
    pages doesn't control when adding
    DO NOT ADD UNWANTED PAGES or ...
If checks is passed: dictionary of boolean functions with  pages as keeys {<page1>: <check1>, ...}
    than this is a necessary condition for new words beeing accepted in hystory pages
NO CORRELATION BETWEEN pages AND checks
"""

def trim(word: str) -> str:
    pices = word.split(' ')
    return ' '.join(filter(bool, pices))

class Hystory:
    def __init__(self, pages: tuple=(), checks: dict=()):
        if any(map(lambda x: not isinstance(x, str), pages)):
            raise ValueError("pages aren't strings")
        if any(map(lambda x: not isinstance(x, str) or not callable(checks[x]), checks)):
            raise ValueError("Not valid checks")
        self.modified = False
        self.checks = checks
        self.pages = pages
        self.time = datetime.now() - UPDATE_TIME
        try:
            self.hystory = pd.read_csv(HYSTORY_FILE)
            self.hystory.set_index('page', drop=False, inplace=True)
            self.hystory['date'] = self.hystory['date'].apply(TIME_PARSER)
            if pages:
                self.hystory = self.hystory[self.hystory.index.isin(pages)]
            if checks:
                def word_check(row):
                    if pd.isna(row['word']):
                        return False
                    return self.check(row['page'], row['word'])
                self.hystory = self.hystory[self.hystory.apply(word_check, axis=1)]
                a = 0
        except FileNotFoundError:
            self.hystory = None

    def add(self, page: str, word):
        if isinstance(word, str):
            word = [word]
        word_new = {trim(w) for w in word}
        word_new = list(filter(lambda x: self.check(page, x), word_new))
        new_df = pd.DataFrame([{'date': datetime.now(), 'word': w, 'page': page} for w in  word_new
                               ],
                              index=[page]*len(word_new))
        if not new_df.empty and self.hystory is not None and not self.hystory.empty:
            self.hystory = pd.concat((self.hystory, new_df))
        elif self.hystory is None or self.hystory.empty:
            self.hystory = new_df
        self.hystory.sort_values(axis=0, by='date', ascending=False, inplace=True, na_position='first')
        self.hystory.drop_duplicates(['word', 'page'], inplace=True, keep='first')
        self.modified = True
        if self:
            self.update()

    def update(self):
        if self.hystory is None:
            self.time = datetime.now()
            self.modified = False
            return
        index = self.hystory.index.unique()
        filtered = []
        for ind in index:
            ind_df = self.hystory.loc[[ind]]
            ind_df.sort_values(axis=0, by='date', ascending=False, inplace=True, na_position='first')
            filtered.append(ind_df.head(HYSTORY_MAX))
        self.hystory = pd.concat(filtered)
        self.hystory.to_csv(HYSTORY_FILE, index=False,
                                          date_format=TIME_FORMAT, na_rep=NAN_REP)
        self.time = datetime.now()
        self.modified = False

    def check(self, page: str, word: str) -> bool:
        word = trim(word)
        if word in ('', ' ') or '\n' in word or '\r' in word:
            return False
        if page in self.checks:
            return self.checks[page](word)
        return True

    def __getitem__(self, item: str) -> list:
        if self.hystory is None:
            return []
        if item not in self.hystory.index:
            if item not in self.pages:
                raise Exception(f'No {item} page in hystory')
            return []
        return self.hystory.loc[self.hystory.index == item, 'word'].tolist()

    def __setitem__(self, key: str, value: str):
        if isinstance(key, slice):
            if self.hystory is not None and key.stop is None:
                self.hystory.drop(key.start)
            self.add(key.start, value)
        else:
            self.add(key, value)

    def __bool__(self):
        if self.hystory is None:
            return False
        return (datetime.now() - self.time > UPDATE_TIME) and self.modified

    def __len__(self):
        if self.hystory is None:
            return 0
        return len(self.hystory.index)
