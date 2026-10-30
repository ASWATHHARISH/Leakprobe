"""Shared visible product branding for Streamlit pages."""
import streamlit as st


PRODUCT_NAME = "LeakProbe"
PRODUCT_SUBTITLE = "AI-Assisted Water Leak Monitoring & Investigation"


def render_compact_style():
    """Page-local typography and spacing; leave Streamlit controls and navigation intact."""
    st.markdown("""<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
    .block-container h1 { font-size: 1.65rem; line-height: 1.25; padding-bottom: .15rem; }
    .block-container h2 { font-size: 1.1rem; line-height: 1.35; padding-top: .3rem; }
    .block-container h3 { font-size: 1rem; line-height: 1.35; padding-top: .2rem; }
    .block-container [data-testid="stMetricValue"] { font-size: 1.3rem; line-height: 1.35; }
    .block-container [data-testid="stMetricLabel"] p { font-size: .8rem; }
    .block-container [data-testid="stAlert"] { padding: .5rem .7rem; }
    .block-container [data-testid="stAlert"] p { font-size: .85rem; line-height: 1.4; }
    .block-container [data-testid="stCaptionContainer"] p { font-size: .78rem; line-height: 1.4; }
    .block-container [data-testid="stVerticalBlock"] { gap: .7rem; }
    </style>""", unsafe_allow_html=True)


def render_product_header(compact=True) -> None:
    """Consistent short product title with a restrained subtitle."""
    if compact:
        render_compact_style()
    st.title(PRODUCT_NAME)
    st.caption(PRODUCT_SUBTITLE)
