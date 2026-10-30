"""Operator restriction controls. Rendering and signing in never invoke a provider."""
import json
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
        with st.expander('Restricted live access'):
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
        control.ready(token, session)
    except LiveDenied as exc:
        with st.expander('Administrator spending authorization', expanded=True):
            st.info(str(exc))
            challenge = json.dumps(control.challenge(), indent=2)
            st.download_button('Download activation challenge', challenge, 'leakprobe-live-challenge.json', 'application/json')
            st.caption('An administrator must sign this process-specific challenge locally. Restarting the app does not renew spending.')
            with st.form('live_arm', clear_on_submit=True):
                permit = st.text_area('Signed activation permit', max_chars=4000)
                activate = st.form_submit_button('Apply spending authorization')
            if activate:
                try:
                    control.arm(json.loads(permit), token, session)
                    st.rerun()
                except (LiveDenied, ValueError, TypeError):
                    st.warning('Spending authorization was not accepted. Ask the administrator for a current permit.')
        return token, session
    st.caption(f"Maximum reserved spend: ${control.policy.budget} per activation; "
               f"${control.policy.reserve_usd} reserved per attempt. Failed attempts keep their reservation.")
    return token, session
