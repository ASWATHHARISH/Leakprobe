"""Operator restriction controls. Rendering and signing in never invoke a provider."""
import uuid

import streamlit as st

from leakprobe.ui.live_policy import LiveDenied, authority, restricted_profile

TOKEN, SESSION = 'leakprobe_live_access_token', 'leakprobe_live_browser_session'


def credentials():
    return st.session_state.get(TOKEN), st.session_state.get(SESSION)


def can_read_live():
    if not restricted_profile():
        return False
    try:
        return authority().authorized(*credentials())
    except LiveDenied:
        return False


def render_access():
    if not restricted_profile():
        return None, None
    try:
        control = authority()
    except LiveDenied as exc:
        st.caption(str(exc))
        return None, None
    if SESSION not in st.session_state:
        st.session_state[SESSION] = uuid.uuid4().hex
    token, session = credentials()
    if not control.authorized(token, session):
        with st.expander('Operator login'):
            st.caption('Saved reports work offline. Only authorized operators may initiate paid requests.')
            with st.form('live_operator_login', clear_on_submit=True):
                password = st.text_input('Operator access code', type='password', max_chars=256)
                submitted = st.form_submit_button('Sign in for live investigations')
            if submitted:
                try:
                    st.session_state[TOKEN] = control.authenticate(password, session)
                    st.rerun()
                except LiveDenied as exc:
                    st.warning(str(exc))
        return None, session
    st.caption('Restricted live mode · operator access expires after 15 minutes. Each investigation uses Nebius credits.')
    if st.button('Sign out of live access'):
        control.logout(token)
        st.session_state.pop(TOKEN, None)
        st.rerun()
    try:
        control.can_start(token, session)
    except LiveDenied as exc:
        st.info(str(exc))
        return token, session
    with st.expander('AI usage limits'):
        st.caption(f"{len(control.runs)} of {control.policy.max_runs} attempts used; "
                   f"${control.spent} of ${control.policy.budget} reserved. "
                   f"Each attempt reserves ${control.policy.reserve_usd}, including failures.")
        st.caption('Limits are shared across browsers for this server process. Server restarts reset them. '
                   'This is an application allowance, not a provider-side spending cap.')
    return token, session
