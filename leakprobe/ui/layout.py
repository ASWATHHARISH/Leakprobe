"""Sizing compatible with the existing workbench and pinned hosted Streamlit."""
import re
import streamlit as st


def stretch_options(version):
    match = re.match(r'^(\d+)\.(\d+)', version)
    modern = bool(match and tuple(map(int, match.groups())) >= (1, 66))
    return {'width': 'stretch'} if modern else {'use_container_width': True}


STRETCH = stretch_options(st.__version__)
