import sqlite3 as sql
import re
import copy
from typing import Any, Iterable, Type

from paths import DICTIONARY

FORMAT_DELIMETER = '# -> #'
MEANCAT_FORMAT_DELIMETER = '# ! #'
MEAN_FORMAT_DELIMETER = '# !! #'
TERM_MATCH = re.compile(r"[a-zA-Z À-ÿ-'?]+$")
TEXT_MATCH = re.compile(r"[a-z .àòùèì]*$")
CAT_MATCH = re.compile(r'>|<|\[|\]|\{|\}|\\|\||/|`')
REFE_MATCH = re.compile(r'(@[^ \n\r^({})^({})^({})]+)'.format(MEAN_FORMAT_DELIMETER, MEANCAT_FORMAT_DELIMETER, FORMAT_DELIMETER))

# setter-getter use:
# the private key have the db-way data, public setter-getter the user-way
# functions that need to use pivate are:
# __init__; update; delete; copy

# checkers use:
# must act when setter is colled

# formatters use:
# must act when getter is called

def escape_quote(s: str) -> str:
    """
    Escapes all quotes in the input string
    Secures the SQL from Injections and enables the words with "'"
    """
    return s.replace("'", "''")


def trim(word: str) -> str:
    pices = word.split(' ')
    return ' '.join(filter(bool, pices))


def term_checker(term: str) -> bool:
    match1 = re.match(TERM_MATCH, term) is not None
    return match1


def category_checker(cat: str) -> bool:
    # Empty categories raise no error, they are simply discarded
    match1 = re.match(CAT_MATCH, cat) is not None
    return match1


def text_checker(text: str) -> bool:
    if FORMAT_DELIMETER in text or MEAN_FORMAT_DELIMETER in text or MEANCAT_FORMAT_DELIMETER in text:
        return False
    if re.findall(TEXT_MATCH, text):
        return False
    return True


def de_formatter(formatted_text: str) -> list[str]:
    return formatted_text.split(FORMAT_DELIMETER)


def formatter(sequence: Iterable[str]) -> str:
    return FORMAT_DELIMETER.join(sequence)


def mean_de_formatter(mean: str) -> dict[str, Any]:
    mean_cat_split = []
    if len(split := mean.split(MEAN_FORMAT_DELIMETER)) > 1:
        mean_cat, mean = split
        mean_cat_split = mean_cat.split(MEANCAT_FORMAT_DELIMETER)
    elif MEAN_FORMAT_DELIMETER in mean:
        if search := re.search(r'(.+)'+MEAN_FORMAT_DELIMETER, mean):
            mean_cat_split = search[1].split(MEANCAT_FORMAT_DELIMETER)
            mean = ''
        elif search := re.search(MEAN_FORMAT_DELIMETER+r'(.+)', mean):
            mean = search[1]
        else:
            mean = ''

    res = {'mean-cat': mean_cat_split if mean_cat_split else [''], 'mean': mean}
    return res


def mean_formatter(mean: dict[str, Any]) -> str:
    """
    trim, bool, check repetitions
    No None Allowed
    """
    if 'mean' not in mean:
        raise ValueError('mean key not present in meaning dicionaries')
    if not text_checker(text=(_mean := trim(mean['mean']))):
        raise IlligalTextError(mean['mean'], text_checker)
    
    if 'mean-cat' in mean:
        mean_cat = set(filter(bool, map(trim, mean['mean-cat'])))
        if not all(map(category_checker, mean_cat)):
            raise IlligalTextError('", "'.join(mc for mc in mean['mean-cat'] if not category_checker(mc)),
                                    category_checker)
        res = MEANCAT_FORMAT_DELIMETER.join(mean_cat) + MEAN_FORMAT_DELIMETER + _mean
    else:
        res = _mean
    return res


def pattern_query(pattern: str) -> tuple[str, ...] | tuple[()]:
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    pattern = trim(pattern)
    query = f"""
    SELECT word
    FROM words
    WHERE word LIKE '{escape_quote(pattern)}';"""
    cursor.execute(query)
    res = cursor.fetchall()
    connection.close()
    return tuple(x[0] for x in res)


def categories_pattern_query(pattern: str) -> list[tuple[str, int]]:
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    pattern = trim(pattern)
    query = f"""
            SELECT cat.cat, COUNT(cat.cat)
            FROM words LEFT JOIN cat ON cat.word = words.key
            WHERE cat.cat LIKE '{escape_quote(pattern)}'
            GROUP BY cat.cat;"""
    cursor.execute(query)
    res = cursor.fetchall()
    connection.close()
    return res


def search(word: str) -> tuple[int | None, int | None]:
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    query = f"""
    SELECT key, ref
    FROM words
    WHERE word = '{escape_quote(word)}';
    """
    cursor.execute(query)
    res = cursor.fetchone()  # returns None or Tuple
    connection.close()
    if res is None:
        return None, None
    return res


def category_query(category: str) -> tuple[str, ...]:
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    category = trim(category)
    # escape_quote necessary to protect from Injections
    # and for future compatibility
    query = f"""
        SELECT words.word
        FROM words LEFT JOIN cat ON cat.word = words.key
        WHERE cat.cat {"= '" + escape_quote(category) + "'" if category else 'IS NULL'};"""
    cursor.execute(query)
    res = cursor.fetchall()
    connection.close()
    return tuple(x[0] for x in res)


def categories_query() -> tuple[tuple[str, int], ...]:
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    query = f"""
        SELECT cat.cat, COUNT(cat.cat), COUNT(*) - COUNT(cat.cat)
        FROM words LEFT JOIN cat ON cat.word = words.key
        GROUP BY cat.cat;"""
    cursor.execute(query)
    res = cursor.fetchall()
    connection.close()
    return tuple((x[0] if x[0] else '', x[1] if x[0] else x[2]) for x in res)


def look_up_all_ref(key: int) -> tuple[int, ...]:
    """
    Find all words referenced to key
    """
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    query = f"""
        SELECT key
        FROM words
        WHERE ref = {key};
        """
    cursor.execute(query)
    res = cursor.fetchall()  # returns [] or List of Tuple
    connection.close()
    return tuple(x[0] for x in res)


def look_up(key: int) -> dict[str, tuple]:
    """
    Must find word, can find cat
        call after search
    keys of dict are:
        'word': (key: int, word: str, mean: str, ref: int, note: str)
        'cat': ((key, cat), ...) or ()
    """
    connection = sql.connect(DICTIONARY)
    cursor = connection.cursor()
    query = f"""
        SELECT key, word, mean, ref, note
        FROM words
        WHERE key = {key};
        """
    cursor.execute(query)
    word = cursor.fetchone()  # returns None or tuple
    query = f"""
    SELECT key, cat FROM cat
    WHERE word = {key};
    """
    cursor.execute(query)
    cat = cursor.fetchall()  # returns [] or list of tuple
    connection.close()
    if word is None:
        raise RowNotFoundError('words', 'key',key)

    return {'word': word, 'cat': tuple(cat)}


class VoxEl:
    def __init__(self, word: str='', data: dict[str, Any] | None=None):
        self._key = None
        self._name = word
        self._mean = ''
        self._cat = ()  # contains complete info of cat, with key and so the status
        self._cat_set = set()  # is the set of all active cat
        self._note = ''

        if data is None:
            return

        self._key = data['word'][0]
        self._name = data['word'][1]
        self._mean = data['word'][2] if data['word'][2] is not None else ''  # it's a string
        self._cat = data['cat'] # tuple of double tuples
        self._cat_set = {c for _, c in self._cat}
        self._note = data['word'][4] if data['word'][4] is not None else ''  # 3 is the ref

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str):
        new_name = trim(new_name)
        if term_checker(new_name):
            self._name = new_name
        else:
            raise IlligalTextError(new_name, term_checker)

    @property
    def mean(self) -> list[dict[str, Any]]:
        """
            meanings are represented by a list of dictionaries:
            'mean' key is always present and is the related meaning
            'mean-cat' is'n always present NEED TO CHECK OUT
                        is a list of categories specific to the meaning
        """
        return list(map(mean_de_formatter, de_formatter(self._mean)))

    @mean.setter
    def mean(self, new_meanings: list[dict[str, Any]]):
        """
            new_meanings must be a list of dictionaries:
            'mean' key is always present and is the related meaning
            'mean-cat' is'n always present NEED TO CHECK OUT
                        is a list of categories specific to the meaning
        """

        # trim and check inside mean_formatter
        self._mean = formatter(filter(bool, map(mean_formatter, new_meanings)))

    @property
    def note(self) -> list:
        return de_formatter(self._note)

    @note.setter
    def note(self, new_notes: list[str]):
        # no None in input
        new_notes = list(filter(bool, map(trim, new_notes)))
        if not all(map(text_checker, new_notes)):
            raise IlligalTextError('", "'.join(filter(lambda x: not text_checker(x), new_notes),),
                                   text_checker)
        self._note = formatter(new_notes)

    @property
    def cat(self) -> list:
        return list(self._cat_set) if self._cat_set else ['']

    @cat.setter
    def cat(self, new_categories: list[str]):
        new_set = set(filter(bool, map(trim, new_categories)))  # no None and no empty str
        if not all(map(category_checker, new_set)):
            raise IlligalTextError('", "'.join(filter(lambda x: not category_checker(x), new_categories)),
                                   category_checker)
        self._cat_set = new_set

    def cat_packer(self):
        # takes all cat  from _cat_set and updates _cat
        # marking the cat for remove or update
        new_cat = self._cat_set - {c for _, c in self._cat}
        self._cat = tuple((ck, cc) if cc in self._cat_set else (ck, None) for ck, cc in self._cat)
        self._cat = tuple((ck, cc) for ck, cc in self._cat if ck is not None or cc is not None)
        self._cat += tuple((None, nc) for nc in new_cat)


    def referenced(self) -> tuple[str, ...]:
        # casting is needed because if None is found re.findall returns an empty list
        res = set(re.findall(REFE_MATCH, self._mean)) | set(re.findall(REFE_MATCH, self._note))
        return tuple(map(lambda x: x.replace('_', ' '), res))

    def exists_key(self) -> bool:
        return self._key is not None

    def __eq__(self, other: 'VoxEl'):
        if not isinstance(other, VoxEl):
            return False
        # if self._key != other._key:
        #      return False
        elif self.name != other.name:
            return False
        elif self._cat_set != other._cat_set:
            return False
        elif self.note != other.note:
            return False
        elif self.mean != other.mean:
            return False
        return True

    def __bool__(self):  # checks if Vox is ready to be saved
        return term_checker(self._name)  # at the end all it does is to check if self._name is empty

    def update(self, ref_key: int | None=None):
        self.cat_packer()
        connection = sql.connect(DICTIONARY)
        connection.execute('PRAGMA foreign_keys = ON;')
        connection.commit()
        if not self:
            raise Exception("Vox has no name: can't update")
        if (s := search(self._name))[0] is not None and s[0] != self._key:
            raise ConflictError(self._name)
        ref_key_substr = f", ref = {ref_key}" if ref_key is not None else ''
        if self._key is None:  # New Word into Dictionary
            query = f"""
            INSERT INTO words (word, {'mean,' if self._mean else ''} note, ref)
            VALUES ('{escape_quote(self._name)}',
             {"'" + escape_quote(self._mean) + "'," if self._mean else ''}
             {"'" + escape_quote(self._note) + "'" if self._note else 'NULL'},
             {ref_key if ref_key is not None else 'NULL'});
            """
            connection.execute(query)
            connection.commit()

            self._key = search(self._name)[0]  # in order to search forward all query must be committed
            if self._cat:
                query = f"""
                        INSERT INTO cat (word, cat)
                        VALUES
                        """ + ',\n'.join([f"('{self._key}', '{cat}')" for _, cat in self._cat]) + ';'
                connection.execute(query)
        else:
            for cat in self._cat:
                if cat[1] is None:
                    query = f"""
                    DELETE FROM cat
                    WHERE key = {cat[0]};"""
                    connection.execute(query)
                elif cat[0] is None:
                    query = f"""
                    INSERT INTO cat (word, cat)
                    VALUES ('{self._key}', '{cat[1]}');"""
                    connection.execute(query)

            query = f"""
            UPDATE words
            SET
                word = '{escape_quote(self._name)}',
                {"mean = '" + escape_quote(self._mean) + "'," if self._mean else ''}
                note = {"'" + escape_quote(self._note) + "'" if self._note else 'NULL'}{ref_key_substr}
            WHERE key = {self._key}; 
            """
            connection.execute(query)

        connection.commit()
        connection.close()

    def delete(self):
        if self._key is None:
            return
        self.cat_packer()
        connection = sql.connect(DICTIONARY)
        connection.execute('PRAGMA foreign_keys = ON;')
        connection.commit()
        for cat_key, _ in self._cat:
            if cat_key is None:
                continue
            query = f"""
            DELETE FROM cat
            WHERE key = {cat_key};"""
            connection.execute(query)
            connection.commit()
        query = f"""
        DELETE FROM words
        WHERE key = {self._key};"""
        connection.execute(query)
        connection.commit()

        connection.close()

        self._key = None
        self._name = ''

    def vew(self) -> dict:
        dic = {'name': self.name, 'mean': self.mean, 'note': self.note, 'cat': self.cat,
               'referenced': tuple((x, bool(pattern_query(x.removeprefix('@')))) for x in self.referenced())}
        return dic

    def copy_vox_el(self) -> 'VoxEl':
        """Creates a dummy copy without any key to database
        The use is to detect changes through __eq__

        Returns
        -------
        VoxEl
            the copy
        """
        res = VoxEl()
        res._name = self._name
        res._cat_set = copy.copy(self._cat_set)
        res._note = self._note
        res._mean = self._mean
        return res


class Vox(VoxEl):
    def __init__(self, word: str=''):
        self.links: list['VoxEl'] = []
        if not word:
            super().__init__()
            return
        word = trim(word)
        key, ref_key = search(word)
        if key is None:  # word not found so lets you create it
            super().__init__(word)
            return
        if ref_key is not None:
            # Vox must point only to main word
            key = ref_key
        # obtain data for key-word and key-cat
        data = look_up(key)
        super().__init__(word, data)
        # obtain the ref keys -> ref_keys
        for link in look_up_all_ref(key):
            # obtain data for ref-word and ref-cat
            data = look_up(link)
            self.links.append(VoxEl(data=data))

    def __bool__(self):
        if not all(map(bool, self.links)):
            return False
        return super().__bool__()

    def __eq__(self, other: 'Vox'):
        if not isinstance(other, Vox):
            return False
        if self.links != other.links:
            return False
        return super().__eq__(other)

    def update(self, _=None) -> 'Vox':
        # super first to prevent orphans (update can also insert new row)
        super().update()

        for ref in self.links:
            ref.update(self._key)
        return Vox(self._name)

    def delete(self):
        # reference first to prevent orphans
        for link in self.links:
            link.delete()
        super().delete()

    def add_link(self):
        if all(x != VoxEl() for x in self.links):
            self.links.append(VoxEl())

    def delete_link(self, link_name: str):
        for link in self.links:
            if link._name == link_name:
                link.delete()
                self.links.remove(link)

    def vew(self):
        dic = super().vew()
        dic.update({'links': [link.vew() for link in self.links]})
        return dic

    def copy_vox(self) -> 'Vox':
        """Creates a dummy copy without any key to database
        The use is to detect changes through __eq__

        Returns
        -------
        Vox
            the copy
        """
        res = Vox()
        res._name = self._name
        res._cat_set = copy.copy(self._cat_set)
        res._note = self._note
        res._mean = self._mean

        for link in self.links:
            res.links.append(link.copy_vox_el())
        return res

    def remove_empty_links(self):
        self.links = [link for link in self.links if link != VoxEl()]


class RowNotFoundError(Exception):
    def __init__(self, table: str, alias: str, key: int):
        super().__init__(f'Row: ({alias})=({key}) not found in "{table}"')


class IlligalTextError(Exception):
    def __init__(self, text: str, purpose):
        pupose_dic = {text_checker: 'text', category_checker: 'category', term_checker: "term's name"}
        super().__init__(f'"{text}" is invalid as {pupose_dic[purpose]}')


class ConflictError(Exception):
    def __init__(self, name):
        super().__init__(f'{name} already exists')

if __name__ == '__main__':
    pass