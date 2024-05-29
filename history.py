import json
from typing import Callable
from paths import HISTORY_FILE
from datetime import datetime, timedelta


UPDATE_TIME = timedelta(seconds=60*5)

"""
This module creates an history divided in pages
Access history of <page> by History[<page>]
Add new words by History[<page>] = <word>
    even more with History[<page>] = [<word>, ...]
    all words will be replaced if: History[<page>:] = [<word>, ...]
Updates in file with History.update() or Automatically when adding after UPDATE_TIME
All duplicates are removed (same page) and only HISTORY_MAX words are kept, at every change,
    dropping from older ones
"""

def trim(word: str) -> str:
    pices = word.split(' ')
    return ' '.join(filter(bool, pices))

def default_check(word: str) -> bool:
    return True

class History:
    def __init__(self, pages: dict[str, Callable[[str], bool]] | set[str], 
                 global_check: Callable[[str], bool] | None=None, history_max=6):
        """A class to store data in LIFO lists with backup in .json file

        Parameters
        ----------
        pages : dict[str, Callable[[str], bool]] | set[str]
            Names of each list, if it's a dictionary, a check can be added to each page
            The check will be performed on each word, when it's False it will be discarded
        global_check : Callable[[str], bool] | None, optional
            A check for all word in all pages, by default None
        history_max : int, optional
            No more data will be stored, by default 6
        """
        if any(map(lambda x: not isinstance(x, str), pages)):
            raise ValueError("Pages aren't strings")
        if isinstance(pages, dict):
            if any(map(lambda x: not callable(pages[x]), pages)):
                raise ValueError("Not valid checks")
            self.pages = pages
        else:
            self.pages = {pg: default_check for pg in pages}
        self.HISTORY_MAX = history_max
        self.modified = False
        self.global_check = global_check
        self.time = datetime.now() - UPDATE_TIME
        try:
            with open(HISTORY_FILE) as json_file:
                self.history = json.load(json_file)  # {'page': [LIFO list]}
            # selects only pages in pages argument
            self.history = {pg: (self.history[pg] if pg in self.history else []) for pg in pages}
            # delete all words according to checks
            for pg in pages:
                self.history[pg] = [word for word in self.history[pg] if self.check(pg, word)]
        except FileNotFoundError:
            self.history = {pg: [] for pg in pages}

    def add(self, page: str, word: str | list[str]):
        '''
        adds a word or list of words
        USE __setitem__ instead

        add works also if page is not in history
        '''
        if isinstance(word, str):
            word = [word]
        word = list(map(trim, word))
        word_new = []
        if page in self.history:
            [word_new.append(w) for w in (word + self.history[page]) if w not in word_new and self.check(page, w)]
        else:
            [word_new.append(w) for w in word if w not in word_new and self.check(page, w)]
        self.history[page] = word_new[:self.HISTORY_MAX]
        self.modified = True
        if self:
            self.update()

    def update(self):
        with open(HISTORY_FILE, 'w') as json_file:
            json.dump(self.history, json_file)
        self.time = datetime.now()
        self.modified = False

    def check(self, page: str, word: str) -> bool:
        word = trim(word)
        if self.global_check is not None and not self.global_check(word):
            return False
        if page in self.pages:
            return self.pages[page](word)
        return True

    def __getitem__(self, page: str) -> list:
        if page not in self.history:
            raise KeyError(f"History: {page} isn't a page of history")
        return self.history[page]

    def __setitem__(self, key: str | slice, value: str | list):
        '''
        sets new history
        YOU can set only pages from initialization!

        History[page] = [...] will add words at the beginning of page
        History[page:] = [...] will replace the entire page
        '''
        if isinstance(key, slice):
            if key.start not in self.history:
                raise KeyError(f"History: can't write on new page of history such as: {key.start}")
            if key.stop is None:
                self.history.pop(key.start)
            self.add(key.start, value)
        else:
            if key not in self.history:
                raise KeyError(f"History: can't write on new page of history such as: {key}")
            self.add(key, value)

    def __bool__(self):
        '''
        checks if it is time to update the json file
        '''
        return self.modified and (datetime.now() - self.time > UPDATE_TIME)

    def __len__(self):
        return sum(len(self.history[key]) for key in self.history)
