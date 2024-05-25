import sqlite3 as sql
import re
import copy
from paths import FOLDER


DICT = FOLDER + 'crazy_dict.sqlite'
FORMAT_DELIMETER = '# -> #'
MEANCAT_FORMAT_DELIMETER = '# ! #'
MEAN_FORMAT_DELIMETER = '# !! #'


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
    match1 = re.match(r"[a-zA-Z À-ÿ-'?]+$", term) is not None
    return match1


def category_checker(cat: str) -> bool:
    if cat is None or cat == '':  # cat can be None in case it's a category to be deleted
        return True
    match1 = re.match(r"[a-z .àòùèì]+$", cat) is not None
    return match1


def text_checker(text: str) -> bool:
    if text is None:
        return False
    if FORMAT_DELIMETER in text or MEAN_FORMAT_DELIMETER in text or MEANCAT_FORMAT_DELIMETER in text:
        return False
    if re.findall(r'\(|\)|>|<|\[|\]|\{|\}|\\|\||/|`', text):
        return False
    return True


def de_formatter(formatted_text: str) -> list:
    return formatted_text.split(FORMAT_DELIMETER)


def formatter(sequence: list) -> str:
    return FORMAT_DELIMETER.join(sequence)


def mean_de_formatter(mean: str) -> dict:
    mean_cat_split = []
    if len(split := mean.split(MEAN_FORMAT_DELIMETER)) > 1:
        mean_cat, mean = split
        mean_cat_split = mean_cat.split(MEANCAT_FORMAT_DELIMETER)
    elif MEAN_FORMAT_DELIMETER in mean:
        if search := re.search('r(.+)'+MEAN_FORMAT_DELIMETER, mean):
            mean_cat_split = search[1].split(MEANCAT_FORMAT_DELIMETER)
            mean = ''
        elif search := re.search(MEAN_FORMAT_DELIMETER+'r(.+)', mean):
            mean = search[1]
        else:
            mean = ''

    res = {'mean-cat': mean_cat_split if mean_cat_split else [''], 'mean': mean}
    return res


def mean_formatter(mean: dict) -> str:
    if 'mean-cat' in mean:
        mean_cat = [mc for mc in mean['mean-cat'] if trim(mc)]
        res = MEANCAT_FORMAT_DELIMETER.join(mean_cat) + MEAN_FORMAT_DELIMETER + mean['mean']
    else:
        res = mean['mean']
    return trim(res)


def pattern_query(pattern: str) -> tuple:
    connection = sql.connect(DICT)
    cursor = connection.cursor()
    pattern = trim(pattern)
    query = f"""
    SELECT word
    FROM words
    WHERE word LIKE '{escape_quote(pattern)}';"""
    cursor.execute(query)
    res = cursor.fetchall()
    connection.close()
    return tuple(map(lambda x: x[0], res))


def categories_pattern_query(pattern: str) -> tuple:
    connection = sql.connect(DICT)
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


def search(word: str) -> tuple:
    connection = sql.connect(DICT)
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


def category_query(category: str) -> tuple:
    connection = sql.connect(DICT)
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
    return tuple(map(lambda x: x[0], res))


def categories_query() -> tuple:
    connection = sql.connect(DICT)
    cursor = connection.cursor()
    query = f"""
        SELECT cat.cat, COUNT(cat.cat), COUNT(*) - COUNT(cat.cat)
        FROM words LEFT JOIN cat ON cat.word = words.key
        GROUP BY cat.cat;"""
    cursor.execute(query)
    res = cursor.fetchall()
    connection.close()
    return tuple(map(lambda x: (x[0] if x[0] else '', x[1] if x[0] else x[2]), res))


def look_up_all_ref(key: int) -> tuple:
    connection = sql.connect(DICT)
    cursor = connection.cursor()
    query = f"""
        SELECT key
        FROM words
        WHERE ref = {key};
        """
    cursor.execute(query)
    res = cursor.fetchall()  # returns None or List of Tuple
    connection.close()
    if res is None:
        raise RowNotFoundError('words', 'ref', str(key))
    return tuple(x[0] for x in res)


def look_up(key: int) -> dict:
    connection = sql.connect(DICT)
    cursor = connection.cursor()
    query = f"""
        SELECT key, word, mean, ref, note
        FROM words
        WHERE key = {key};
        """
    cursor.execute(query)
    word = cursor.fetchone()
    query = f"""
    SELECT key, cat FROM cat
    WHERE word = {key};
    """
    cursor.execute(query)
    cat = cursor.fetchall()  # returns None or Tuple
    connection.close()
    if word is None:
        raise RowNotFoundError('words', 'key', str(key))
    if cat is None:
        raise RowNotFoundError('cat', 'word', str(key))

    return {'word': word, 'cat': cat}


class VoxEl:
    def __init__(self, word='', data=None):
        self._key = None
        self._name = word
        self._mean = ''
        self._cat = []
        self._note = ''

        if data is None:
            return

        self._key = data['word'][0]
        self._name = data['word'][1]
        self._mean = data['word'][2] if data['word'][2] is not None else ''  # it's a string
        self._cat = [[ck, c] for ck, c in data['cat']]  # tuple of double tuples to list of lists
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
    def mean(self) -> list:
        """
            meanings are represented by a list of dictionaries:
            'mean' key is always present and is the related meaning
            'mean-cat' is'n always present NEED TO CHECK OUT
                        is a list of categories specific to the meaning
        """
        return list(map(mean_de_formatter, de_formatter(self._mean)))

    @mean.setter
    def mean(self, new_meanings: list):
        """
            new_meanings must be a list of dictionaries:
            'mean' key is always present and is the related meaning
            'mean-cat' is'n always present NEED TO CHECK OUT
                        is a list of categories specific to the meaning
        """

        # self.mean is entirely trimmed by mean_formatter
        for m in new_meanings:
            if 'mean' not in m:
                raise ValueError('mean key not present in dicionaries to @mean.setter')
            if 'mean-cat' in m:
                if not all(map(category_checker, m['mean-cat'])):
                    raise IlligalTextError('`, `'.join(filter(lambda x: not category_checker(x), m['mean-cat'])),
                                           category_checker)
            if not text_checker(m['mean']):
                raise IlligalTextError(m['mean'], text_checker)
        self._mean = formatter(map(mean_formatter, new_meanings))

    @property
    def note(self) -> list:
        return de_formatter(self._note)

    @note.setter
    def note(self, new_notes: list):
        if not all(map(text_checker, new_notes)):
            raise IlligalTextError('`, `'.join(filter(lambda x: not text_checker(x), new_notes),),
                                   text_checker)
        self._note = trim(formatter(new_notes))

    @property
    def cat(self) -> list:
        res = [c for _, c in filter(lambda x: x[1] is not None, self._cat)]
        return res if res else ['']

    @cat.setter
    def cat(self, new_categories: list):
        new_categories = list(filter(lambda x: x is not None, new_categories))
        new_categories = list(map(trim, new_categories))
        if not all(map(lambda x: category_checker(x), new_categories)):
            raise IlligalTextError('`, `'.join(filter(lambda x: not category_checker(x), new_categories)),
                                   category_checker)
        new_categories = list(filter(lambda x: x is not None, new_categories))
        new_cat = set(new_categories) - set([c[1] for c in self._cat])
        for nc in new_cat:
            self._cat.append([None, nc])
        old_cat = set([c[1] for c in self._cat]) - set(new_categories) - {None}  # set cares also of duplicates
        # deletes categories in old_cat, you can delete also new categories!!
        self._cat = [[ck, None] if cc in old_cat else [ck, cc] for ck, cc in self._cat]
        self._cat = list(filter(lambda x: x[0] is not None or x[1] is not None, self._cat))

    def referenced(self) -> tuple:
        # casting is needed because if None is found re.findall returns an empty list
        pattern = r'(@[^ ^({})^({})^({})]+)'.format(MEAN_FORMAT_DELIMETER, MEANCAT_FORMAT_DELIMETER, FORMAT_DELIMETER)
        res = tuple(re.findall(pattern, self._mean)) + tuple(re.findall(pattern, self._note))
        res = tuple(dict.fromkeys(res))  # remove duplicates
        return tuple(map(lambda x: x.replace('_', ' '), res))

    def exists_key(self) -> bool:
        return self._key is not None

    def __eq__(self, other):
        if not isinstance(other, VoxEl):
            return False
        # if self._key != other._key:
        #      return False
        elif self.name != other.name:
            return False
        elif self.cat != other.cat:
            return False
        elif self.note != other.note:
            return False
        elif self.mean != other.mean:
            return False
        return True

    def __bool__(self):  # checks if Vox is ready to be saved
        return term_checker(self._name)  # at the end all it does is to check if self._name is empty

    def update(self, ref_key=None):
        self.remove_all_withe()
        connection = sql.connect(DICT)
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
        connection = sql.connect(DICT)
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

    def copy_vox_el(self):
        res = VoxEl()
        res._name = self._name
        res._cat = copy.deepcopy(self._cat)
        res._note = self._note
        res._mean = self._mean
        return res

    def remove_all_withe(self):
        """
         Removes all empty strings
        """
        self.mean = list(filter(lambda x: x['mean'] or any(x['mean-cat']), self.mean))
        self.note = list(filter(bool, self.note))
        self.cat = [c for _, c in filter(lambda c: c[1] != '', self._cat)]


class Vox(VoxEl):
    def __init__(self, word=''):
        self.links = []
        if not word:
            super().__init__()
            return
        word = trim(word)
        key, ref_key = search(word)
        if key is None:  # word not found so lets you create it
            super().__init__(word)
            return
        if ref_key is not None:
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

    def __eq__(self, other):
        if not isinstance(other, Vox):
            return False
        other.remove_all_withe()  # comparation makes sense if no withe remains
        self.remove_all_withe()
        if self.links != other.links:
            return False
        return super().__eq__(other)

    def update(self, _=None):
        # super first to prevent orphans (update can also insert new row)
        super().update()

        for i, ref in enumerate(self.links):
            self.links[i] = ref.update(self._key)
        return Vox(self._name)

    def delete(self):
        # reference first to prevent orphans
        for link in self.links:
            link.delete()
        super().delete()

    def add_link(self):
        if all(map(lambda x: x != VoxEl(), self.links)):
            self.links.append(VoxEl())

    def delete_link(self, link_name):
        for link in self.links:
            if link._name == link_name:
                link.delete()
                self.links.remove(link)
                break

    def vew(self):
        dic = super().vew()
        dic.update({'links': [link.vew() for link in self.links]})
        return dic

    def copy_vox(self):
        res = Vox()
        res._name = self._name
        res._cat = copy.deepcopy(self._cat)
        res._note = self._note
        res._mean = self._mean

        for link in self.links:
            res.links.append(link.copy_vox_el())
        return res

    def remove_all_withe(self):
        self.links = list(filter(lambda x: x != VoxEl(), self.links))
        for link in self.links:
            link.remove_all_withe()
        super().remove_all_withe()


class RowNotFoundError(Exception):
    def __init__(self, table: str, alias: str, key):
        super().__init__(f'Row: ({alias})=({key}) not found in `{table}`')


class IlligalTextError(Exception):
    def __init__(self, text: str, purpose):
        pupose_dic = {text_checker: 'text', category_checker: 'category', term_checker: "term's name"}
        super().__init__(f'`{text}` is invalid as {pupose_dic[purpose]}')


class ConflictError(Exception):
    def __init__(self, name):
        super().__init__(f'{name} already exists')
