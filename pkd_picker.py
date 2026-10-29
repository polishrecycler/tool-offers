"""Searchable PKD checklist with a compact, codes-only closed state."""
import re
import unicodedata

import streamlit as st

from pkd_catalog import DEFAULT_SELECTED_PKD, PKD_OPTIONS, pkd_label


def _option_key(code: str) -> str:
    return f"pkd_option_{code}"


def _search_text(text: str) -> str:
    normalized = "".join(char for char in unicodedata.normalize("NFKD", text.casefold())
                         if not unicodedata.combining(char)).replace("ł", "l")
    # Match common Polish inflections, e.g. "akumulatory" / "akumulatorów".
    return re.sub(r"\b(akumulator|bateri|opakowa)\w*\b", r"\1", normalized)


def _toggle(code: str) -> None:
    selected = set(st.session_state["selected_pkd"])
    if st.session_state[_option_key(code)]:
        selected.add(code)
    else:
        selected.discard(code)
    st.session_state["selected_pkd"] = [code for code in PKD_OPTIONS if code in selected]


def _clear() -> None:
    st.session_state["selected_pkd"] = []
    for code in PKD_OPTIONS:
        key = _option_key(code)
        if key in st.session_state:
            st.session_state[key] = False


def pkd_picker() -> list[str]:
    if "selected_pkd" not in st.session_state:
        st.session_state["selected_pkd"] = list(DEFAULT_SELECTED_PKD)
    selected = st.session_state["selected_pkd"]
    st.markdown("Branże — kody PKD", help=(
        "PKD to Polska Klasyfikacja Działalności. Otwórz listę i wyszukaj kod lub opis. "
        "Możesz zaznaczyć wiele branż. Wyszukiwanie firm obejmuje działalność "
        "przeważającą i dodatkową."))
    field, clear = st.columns([9, 1], gap="small", vertical_alignment="top")
    with field:
        summary = ", ".join(selected) if selected else "Wybierz kody PKD"
        with st.popover(summary, width="stretch", wrap=True, key="pkd_picker"):
            query = st.text_input("Szukaj kodu lub opisu", key="pkd_search",
                                  placeholder="Np. 38.21 lub akumulatory", live=True,
                                  icon=":material/search:")
            terms = _search_text(query).split()
            visible = [code for code in PKD_OPTIONS
                       if all(term in _search_text(pkd_label(code)) for term in terms)]
            with st.container(height=min(320, max(56, len(visible) * 64)), border=False):
                if not visible:
                    st.caption("Brak kodów pasujących do wyszukiwania.")
                for code in visible:
                    key = _option_key(code)
                    if key not in st.session_state:
                        st.session_state[key] = code in selected
                    st.checkbox(pkd_label(code), key=key, on_change=_toggle, args=(code,))
            st.caption(f"Wybrano: {len(selected)} · Widocznych kodów: {len(visible)}")
    with clear:
        st.button("", icon=":material/filter_alt_off:", key="clear_pkd",
                  help="Wyczyść wszystkie wybrane kody PKD", width="stretch",
                  on_click=_clear, disabled=not selected)
    return list(st.session_state["selected_pkd"])
