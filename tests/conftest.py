import sys, os
from unittest.mock import MagicMock

# ── Mock Streamlit ───────────────────────────────────────────────
st_mock = MagicMock()
st_mock.session_state = {}
st_mock.secrets = MagicMock()
def _passthrough(*args, **kwargs):
    """Handle @st.cache_data dan @st.cache_data() keduanya benar."""
    if len(args) == 1 and callable(args[0]):
        return args[0]   # @st.cache_data tanpa argumen
    return lambda f: f   # @st.cache_data(...) dengan argumen

st_mock.cache_data = _passthrough
st_mock.cache_resource = _passthrough
st_mock.error   = lambda x, **kw: None
st_mock.warning = lambda x, **kw: None
st_mock.info    = lambda x, **kw: None
st_mock.success = lambda x, **kw: None
st_mock.fragment = lambda run_every=None: (lambda f: f)
sys.modules['streamlit'] = st_mock
sys.modules['streamlit_local_storage'] = MagicMock()
sys.modules['streamlit_lottie']        = MagicMock()

for mod in ['plotly','plotly.express','plotly.graph_objects',
            'altair','prophet','sklearn','sklearn.preprocessing',
            'sklearn.cluster','mlxtend','mlxtend.frequent_patterns',
            'google','google.generativeai','openai']:
    sys.modules[mod] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

@pytest.fixture
def tmp_db(tmp_path):
    """Fresh SQLite DB untuk setiap test."""
    import database
    old = database.DB_FILE
    database.DB_FILE = str(tmp_path / 'test.db')
    database.init_db()
    yield database.DB_FILE
    database.DB_FILE = old
