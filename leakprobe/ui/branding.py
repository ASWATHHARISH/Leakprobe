"""Shared visible product branding for Streamlit pages."""
import streamlit as st


PRODUCT_NAME = "LeakProbe"
PRODUCT_SUBTITLE = "AI-Assisted Water Leak Monitoring & Investigation"


def render_compact_style():
    """Page-local typography and spacing; leave Streamlit controls and navigation intact."""
    st.markdown("""<style>
    .block-container { padding-top: 1.35rem; padding-bottom: 1.5rem; max-width: 1440px; }
    .block-container h1 { font-size: 1.65rem; line-height: 1.25; padding-bottom: .15rem; }
    .block-container h2 { font-size: 1.1rem; line-height: 1.35; padding-top: .3rem; }
    .block-container h3 { font-size: 1rem; line-height: 1.35; padding-top: .2rem; }
    .block-container [data-testid="stMetricValue"] { font-size: 1.3rem; line-height: 1.35; }
    .block-container [data-testid="stMetricLabel"] p { font-size: .8rem; }
    .block-container [data-testid="stAlert"] { padding: .5rem .7rem; }
    .block-container [data-testid="stAlert"] p { font-size: .85rem; line-height: 1.4; }
    .block-container [data-testid="stCaptionContainer"] p { font-size: .78rem; line-height: 1.4; }
    .block-container [data-testid="stVerticalBlock"] { gap: .7rem; }
    .block-container [data-testid="stColumn"] { min-width: 0; }
    .block-container p, .block-container li { overflow-wrap: anywhere; line-height: 1.5; }
    .block-container [data-testid="stMetricValue"] { white-space: normal; }
    .block-container [data-testid="stDataFrame"],
    .block-container [data-testid="stVegaLiteChart"] { max-width: 100%; }
    .block-container [data-testid="stVerticalBlockBorderWrapper"] { border-radius: .55rem; }
    .block-container [data-baseweb="tab-list"] { gap: .25rem; flex-wrap: wrap; height: auto; }
    .block-container [data-baseweb="tab"] { padding: .5rem .75rem; height: auto; white-space: normal; }
    .block-container :focus-visible { outline: 2px solid #087E8B; outline-offset: 3px; }
    @media (max-width: 900px) {
      .block-container { padding-left: 1rem; padding-right: 1rem; }
      .block-container [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
      .block-container [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        width: 100%; flex: 1 1 100%; min-width: 0;
      }
      .block-container [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem;
      }
      .block-container h1 { font-size: 1.45rem; }
    }
    </style>""", unsafe_allow_html=True)


def render_product_header(compact=True) -> None:
    """Consistent short product title with a restrained subtitle."""
    if compact:
        render_compact_style()
    st.title(PRODUCT_NAME)
    st.caption(PRODUCT_SUBTITLE)
