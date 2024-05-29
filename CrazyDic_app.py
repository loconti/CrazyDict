from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import flash
from flask import session
import re
from datetime import datetime, timedelta

from CrazyDic_2 import Vox, pattern_query, categories_query, category_query, categories_pattern_query
from CrazyDic_2 import category_checker, text_checker
from CrazyDic_2 import ConflictError, IlligalTextError
from history import History

FOLDER = './'
MOBILE_ONLY = True  # mobile comes before
DESKTOP_ONLY = False
SESSIONS_MAX = 6
SESSION_TIMEOUT = timedelta(hours=12)  # done manually on, not current, sessions
CHRON_MAX = 30

app = Flask(__name__)
app.secret_key = b'MaSarannoCazziMiei'
app.permanent_session_lifetime = timedelta(hours=12)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# implemented pages: 'categories' and 'notes'
history = History(pages={'categories': category_checker, 'notes': text_checker},
                  global_check=lambda w: not(w in ('', ' ') or '\n' in w or '\r' in w))

def is_mobile() -> bool:
    if MOBILE_ONLY:
        return True
    if DESKTOP_ONLY:
        return False
    user_agent = request.headers.get('User-Agent')
    return user_agent is not None and ('Android' in user_agent or 'iPhone' in user_agent)


def key_gen() -> str:
    return datetime.now().isoformat()


def go_back() -> int:
    """
    the index of session_data['chron'] to go backward
    else -1
    """
    c_id = session_data['chron-index']
    while c_id >= 0:
        back_path = session_data['chron'][c_id]
        if back_path != request.path:
            return c_id
        c_id -= 1
    return -1


def go_forward() -> int:
    """
        the index of session_data['chron'] to go forward
        else -1
        """
    if len(session_data['chron']) > session_data['chron-index'] + 1:
        return session_data['chron-index'] + 1
    else:
        return -1

class SessionData:
    def __init__(self):
        self._data = {}

    def new(self):
        if 'key-session' not in session:
            raise ValueError('Not logged in yet')
        ordered_keys = sorted(map(datetime.fromisoformat, self._data.keys()), reverse=True)
        self._data = {key.isoformat(): self._data[key.isoformat()]
                      for i, key
                      in enumerate(ordered_keys)
                      if i < SESSIONS_MAX and datetime.now() - key < SESSION_TIMEOUT}
        self._data[session['key-session']] = {'vox': Vox(), 'vox-bis': None,
                                              'chron': [], 'chron-index': -1, 'key-form': '',
                                              'dark-mode': True, 'read-mode': False}

    @property
    def data(self):
        if 'key-session' not in session:
            raise ValueError('Not logged in yet')
        return self._data[session['key-session']]

    def set_session(self, new=False):
        """
        runs at every request, to set the active session:
            checks if session['key-session'] exists, and creates it
            BUT gives the priority to the 'key-session' that may be found in the html form.
        """
        if new:
            session['key-session'] = key_gen()
            self.new()
            return
        if request.method == 'POST' and 'key-session' in request.form:
            key_session = request.form['key-session']
            session['key-session'] = key_session
            if key_session not in self._data:
                self.new()
        elif 'key-session' not in session:
            session['key-session'] = key_gen()
            self.new()
            return
        elif session['key-session'] not in self._data:
            self.new()

        if datetime.now() - datetime.fromisoformat(session['key-session']) > SESSION_TIMEOUT:
            new_key = key_gen()
            session_data[new_key] = session_data.data
            session_data._data.pop(session['key-session'])
            session['key-session'] = new_key

    def render(self, vox=None) -> dict:
        return {'vox': vox if vox is not None else self['vox'].vew(),
                'key-form': self['key-form'], 'key-session': session['key-session'],
                'dark-mode': self['dark-mode'], 'read-mode': self['read-mode'],
                'is-chron-forward': go_forward() >= 0, 'is-chron-back': go_back() >= 0,
                'history': history, 'mobile': is_mobile()}

    def __getitem__(self, item):
        if 'key-session' not in session:
            raise ValueError('Not logged in yet')
        return self._data[session['key-session']][item]

    def __setitem__(self, key, value):
        if 'key-session' not in session:
            raise ValueError('Not logged in yet')
        self._data[session['key-session']][key] = value


session_data = SessionData()


def read_form(key: str) -> list:
    index = 0
    contents = []
    while (key_i := key+str(index)) in request.form:
        contents.append(request.form[key_i])
        index += 1
    return contents


def init(func):
    # init decorator needs to be present in the declaration of every route function of CrazyDict
    # here take place all the operations of session, chronology, search etc...
    # common to all pages
    def wrappe(**kwargs):
        if __name__ == '__main__':
            print('initializing... :    '+'; '.join([k+' = '+kwargs[k] for k in kwargs]))

        # here it goes the inizializiation of func()
        if request.args.get('new_session'):
            session_data.set_session(new=True)
        else:
            session_data.set_session()

        # catches evasion with no update
        if session_data['vox'].name and request.path != (url_for('dictionary') + session_data['vox'].name):
            if session_data['vox'] != session_data['vox-bis']:
                if request.args.get('confirm_update') and request.args.get('key_form') != session_data['key-form']:
                    flash('Sorry, you were using an old page', 'warning')
                else:
                    if request.args.get('confirm_update') == 'yes':
                        try:
                            session_data['vox'].update()
                        except ConflictError as e:
                            flash(str(e), 'danger')
                            return redirect(url_for('dictionary', word=session_data['vox'].name))
                        else:
                            session_data['vox'] = Vox()
                    elif request.args.get('confirm_update') == 'no':
                        session_data['vox'] = Vox()
                    else:
                        if not session_data['key-form']:
                            session_data['key-form'] = key_gen()
                        # confirm update?
                        return render_template('confirm_update.html', link=request.full_path,
                                               session=session_data.render(), anchor='')
            else:
                session_data['vox'] = Vox()

        if request.method == 'POST':
            if 'btn-search' in request.form and not re.search(r'/dictionary/[^/]*$', request.path):
                # the search in /dictionary/<word> is handled by dictionary()
                return redirect(url_for('search_pattern', word=request.form['search']))
            if 'btn-category-search' in request.form:
                return redirect(url_for('search_pattern_category', category=request.form['category-search']))
            if 'go-back' in request.form and (c_id := go_back()) >= 0:
                session_data['chron-index'] = c_id
                return redirect(session_data['chron'][c_id])
            elif 'go-forward' in request.form and (c_id := go_forward()) >= 0:
                session_data['chron-index'] = c_id
                return redirect(session_data['chron'][c_id])
            if 'dark-mode' in request.form:
                if (mode := request.form['dark-mode']) == 'dark':
                    session_data['dark-mode'] = True
                elif mode == 'light':
                    session_data['dark-mode'] = False
            if 'read-mode' in request.form:
                if (mode := request.form['read-mode']) == 'read':
                    session_data['read-mode'] = True
                elif mode == 'write':
                    session_data['read-mode'] = False

        # add path in chronology
        if 'word' in kwargs and request.path == (url_for('dictionary') + kwargs['word']):
            if session_data['chron-index'] >= 0 \
                    and request.path != session_data['chron'][session_data['chron-index']]:

                if session_data['chron-index'] == len(session_data['chron']) - 1:
                    session_data['chron'].append(request.path)
                else:
                    session_data['chron'] = session_data['chron'][:session_data['chron-index'] + 1] + [request.path]
                session_data['chron-index'] += 1
                remove = len(session_data['chron']) - CHRON_MAX
                if remove > 0:
                    session_data['chron'] = session_data['chron'][remove:]
                    session_data['chron-index'] -= remove
            elif not session_data['chron']:
                session_data['chron'].append(request.path)
                session_data['chron-index'] = 0

        return func(kwargs) if kwargs else func()
    return wrappe


@app.route('/dictionary/search/pattern/category/', endpoint='search_categories', methods={'POST', 'GET'})
@app.route('/dictionary/search/categories', endpoint='search_categories', methods=['POST', 'GET'])
@init
def search_categories():
    categories = categories_query()
    if not categories:
        flash('No Category exist yet!', 'warning')
        return redirect('/')
    if len(categories) == 1:
        if categories[0][1] == 1:
            flash(f'Only {categories[0][0]} found, with only one term', 'success')
            return redirect(url_for('dictionary', word=category_query(categories[0][0])[0]))
        return redirect(url_for('search_category', category=categories[0][0]))
    return render_template('search_categories.html', listed=categories,
                           title='All existing categories:', session=session_data.render({'name': ''}), anchor='')


@app.route('/dictionary/search/pattern/category/<string:category>', endpoint='search_pattern_category',
           methods={'POST', 'GET'})
@init
def search_pattern_category(kwargs):
    if 'category' not in kwargs:
        raise ValueError
    category = kwargs['category']

    categories = categories_pattern_query(category[1:] if category[0] == '@' else category + '%')
    if not categories:
        flash('No Category matched', 'warning')
        return redirect(url_for('search_categories'))
    if len(categories) == 1:
        if (categories[0])[1] == 1:
            flash(f'This is the only term matching {categories[0][0]} category', 'success')
            # str() casting was added due to editor
            return redirect(url_for('dictionary', word=category_query(str(categories[0][0]))[0]))
        return redirect(url_for('search_category', category=categories[0][0]))

    return render_template('search_categories.html', listed=categories, title=f'Categories matching: {category}',
                           session=session_data.render({'name': ''}), anchor='')


@app.route('/dictionary/search/category/', endpoint='search_category', methods={'POST', 'GET'})
@app.route('/dictionary/search/category/<string:category>', endpoint='search_category', methods=['POST', 'GET'])
@init
def search_category(kwargs=None):
    if kwargs is None:
        category = ''
    else:
        category = kwargs['category']

    words = category_query(category)
    if not words:
        flash(f"No term found with category: {category}", 'danger')
        return redirect('/')
    if len(words) == 1:
        return redirect(url_for('dictionary', word=words[0]))
    return render_template('search.html',
                           title=f'All terms in {category} category:' if category else 'Terms with no category:',
                           listed=words, session=session_data.render({'name': ''}), anchor='',
                           searched='')


@app.route('/dictionary/search/pattern/<string:word>', endpoint='search_pattern', methods=['POST', 'GET'])
@init
def search_pattern(kwargs):
    if 'word' not in kwargs:
        raise ValueError
    word = kwargs['word']

    words = pattern_query(word.removeprefix('@') if word.startswith('@') else word + '%')
    if len(words) == 1 and words[0] == word.removeprefix('@'):
        if word.startswith('@'):
            flash('Term Match!', 'success')
            return redirect(url_for('dictionary', word=word.removeprefix('@')))
        return redirect(url_for('dictionary', word=word))
    if not words and not word.startswith('@'):
        return redirect(url_for('dictionary', word=word))
    if word.startswith('@'):
        if words:
            return render_template('search.html', title='Matching terms:', listed=words,
                                   session=session_data.render({'name': word}), anchor='', searched='')
        else:
            flash('No term matched', 'warning')
            return redirect('/')
    return render_template('search.html', title='Matching terms:', listed=words,
                           session=session_data.render({'name': word}), anchor='', searched=word)


@app.route('/dictionary/search/pattern/', endpoint='dictionary', methods=['GET', 'POST'])
@app.route('/dictionary/', endpoint='dictionary', methods=['GET', 'POST'])
@app.route('/dictionary/<string:word>', endpoint='dictionary', methods=['GET', 'POST'])
@init
def dictionary(kwargs=None):
    global session_data
    mobile = is_mobile()
    new_word = ''
    anchor = ''
    vox = session_data['vox']
    if kwargs is None:
        word = ''
    else:
        word = kwargs['word']

    if not word:
        flash('Look Up For Something!', 'warning')
        return redirect('/')
    if request.method == 'POST':
        if 'btn-search' in request.form:
            new_word = request.form['search']
            if new_word and new_word != word:
                return redirect(url_for('search_pattern', word=new_word))
            if not new_word:
                flash('Look Up For Something!', 'warning')
                return redirect('/')

    # if new_word is '', then isn't == word
    if word != vox.name or new_word == word:
        vox = Vox(word)
        session_data['vox'] = vox
        session_data['vox-bis'] = vox.copy_vox()
        if not vox.exists_key():
            flash('New term!', 'success')

    if request.method == 'POST' and 'term' in request.form:
        if request.form['key-form'] != session_data['key-form']:
            flash('Sorry, you were using an old page', 'warning')
            return redirect(url_for('dictionary', word=word))
        if 'btn-remove' in request.form:
            remove_str = request.form['btn-remove']
            if remove_str == 'remove':
                vox.delete()
                session_data['vox'] = Vox()
                session_data['vox-bis'] = None
                session_data['key-form'] = key_gen()
                return redirect('/')
            elif i_search := re.search(r'^remove-(\d+)$', remove_str):
                i = int(i_search[1])
                if len(vox.links) > 1:
                    if i == len(vox.links)-1:
                        anchor = f'anchor-linked-{i-1}'
                    else:
                        anchor = f'anchor-linked-{i}'
                vox.delete_link(vox.links[i].name)
        else:
            try:  # loading to vox class session
                if new_name := request.form['term']:
                    if new_name in [link.name for link in vox.links]:
                        flash('More Terms with same name, in this page', 'danger')
                    else:
                        vox.name = new_name
                else:
                    flash('Fill All Term names', 'warning')
                index = 0
                mean = []
                while (mean_i := f'mean-{index}') in request.form:
                    mean.append({'mean': request.form[mean_i],
                                 'mean-cat': read_form(mean_i+'-mean-cat-')})
                    index += 1
                vox.mean = mean
                notes = read_form('note-')
                vox.note = notes
                history['notes'] = notes
                categories = read_form('cat-')
                vox.cat = categories
                history['categories'] = categories
                for idl, link in enumerate(vox.links):
                    if new_name := request.form[f'linked-{idl}-term']:
                        if new_name in ([link.name for i, link in enumerate(vox.links) if i != idl] + [vox.name]):
                            flash('More Terms with same name, in this page', 'danger')
                        else:
                            link.name = new_name
                    else:
                        flash('Fill All Term names', 'warning')
                    index = 0
                    mean = []
                    while (mean_i := f'linked-{idl}-mean-{index}') in request.form:
                        mean.append({'mean': request.form[mean_i], 
                                     'mean-cat': read_form(mean_i+'-mean-cat-')})
                        index += 1
                    link.mean = mean
                    notes = read_form(f'linked-{idl}-note-')
                    link.note = notes
                    history['notes'] = notes
                    categories = read_form(f'linked-{idl}-cat-')
                    link.cat = categories
                    history['categories'] = categories
            except IlligalTextError as e:
                flash(str(e), 'warning')
                session_data['key-form'] = key_gen()
                return redirect(url_for('dictionary', word=word))
            if 'btn-add-link' in request.form:
                vox.add_link()
                anchor = f'anchor-linked-{len(vox.links)-1}'
            elif 'btn-update' in request.form:
                # updates if it's new word or if it has changed from 'vox-bis'
                if vox and (session_data['vox-bis'] != vox or not vox.exists_key()):
                    try:
                        session_data['vox'] = vox.update()
                        flash('Updated', 'success')
                    except ConflictError as e:
                        flash(str(e), 'danger')
                    else:
                        vox = session_data['vox']
                        session_data['vox-bis'] = vox.copy_vox()
    if vox.name and vox.name != word:
        return redirect(url_for('dictionary', word=vox.name))

    if mobile and session_data['read-mode']:
        return render_template('mobile/crazy_dictionary_read.html', session=session_data.render(),
                               anchor='', findall=re.findall)

    session_data['key-form'] = key_gen()
    if mobile:
        return render_template('mobile/crazy_dictionary.html', session=session_data.render(),
                               anchor=anchor)
    return render_template('crazy_dictionary.html', session=session_data.render(),
                           anchor='')


@app.route('/', endpoint='home', methods=['GET', 'POST'])
def home():
    """
    This is the home page, and isn't preloaded by @init
    The behaviuor is to set a new session each time,
        and to set some parameters as 'read-mode' and 'dark-mode' from GET method too.
    """
    if request.method == 'POST':
        if 'btn-search' in request.form and not re.search(r'/dictionary/[^/]*$', request.path):
            # the search in /dictionary/<word> is handled by dictionary()
            return redirect(url_for('search_pattern', word=request.form['search']))
        if 'btn-category-search' in request.form:
            return redirect(url_for('search_pattern_category', category=request.form['category-search']))
    session_data.set_session(new=True)
    if request.method == 'POST':
        if 'dark-mode' in request.form:
            if (mode := request.form['dark-mode']) == 'dark':
                session_data['dark-mode'] = True
            elif mode == 'light':
                session_data['dark-mode'] = False
        if 'read-mode' in request.form:
            if (mode := request.form['read-mode']) == 'read':
                session_data['read-mode'] = True
            elif mode == 'write':
                session_data['read-mode'] = False
    if request.method == 'GET':
        if mode := request.args.get('dark-mode'):
            if mode == 'dark':
                session_data['dark-mode'] = True
            elif mode == 'light':
                session_data['dark-mode'] = False
        if mode := request.args.get('read-mode'):
            if mode == 'read':
                session_data['read-mode'] = True
            elif mode == 'write':
                session_data['read-mode'] = False

    return render_template('home.html', session=session_data.render(vox={'name': ''}), anchor='')


if __name__ == '__main__':
    app.run(debug=True)
    