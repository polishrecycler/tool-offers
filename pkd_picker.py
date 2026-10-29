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
    selected = set(st.session_state["draft_pkd"])
    if st.session_state[_option_key(code)]:
        selected.add(code)
    else:
        selected.discard(code)
    st.session_state["draft_pkd"] = [code for code in PKD_OPTIONS if code in selected]
    st.session_state["pkd_select_all"] = len(selected) == len(PKD_OPTIONS)


def _set_draft(codes: list[str]) -> None:
    st.session_state["draft_pkd"] = list(codes)
    st.session_state["pkd_select_all"] = len(codes) == len(PKD_OPTIONS)
    selected = set(codes)
    for code in PKD_OPTIONS:
        key = _option_key(code)
        if key in st.session_state:
            st.session_state[key] = code in selected


def _toggle_all() -> None:
    _set_draft(list(PKD_OPTIONS) if st.session_state["pkd_select_all"] else [])


def _menu_changed() -> None:
    # Opening starts from the applied filter; closing without confirmation
    # discards pending edits. Search and checkbox reruns do not reset the draft.
    _set_draft(st.session_state["selected_pkd"])


def _apply() -> None:
    st.session_state["selected_pkd"] = list(st.session_state["draft_pkd"])
    st.session_state["pkd_picker"] = False


def _summary(codes: list[str]) -> str:
    if not codes:
        return "Wybierz kody PKD"
    if len(codes) <= 10:
        return ", ".join(codes)
    # Selecting the full catalogue must not create a 728-line sidebar button.
    return ", ".join(codes[:4]) + f", … (+{len(codes) - 4})"


def _clear() -> None:
    st.session_state["selected_pkd"] = []
    _set_draft([])
    st.session_state["pkd_picker"] = False


def pkd_picker() -> list[str]:
    if "selected_pkd" not in st.session_state:
        st.session_state["selected_pkd"] = list(DEFAULT_SELECTED_PKD)
    if "draft_pkd" not in st.session_state:
        _set_draft(st.session_state["selected_pkd"])
    selected = st.session_state["selected_pkd"]
    draft = st.session_state["draft_pkd"]
    st.markdown("Branże — kody PKD", help=(
        "PKD to Polska Klasyfikacja Działalności. Otwórz listę i wyszukaj kod lub opis. "
        "Dostępny jest pełny wykaz 728 szczegółowych kodów klasyfikacji 2025. "
        "Możesz zaznaczyć wiele branż. Wyszukiwanie firm obejmuje działalność "
        "przeważającą i dodatkową."))
    field, clear = st.columns([9, 1], gap="small", vertical_alignment="top")
    with field:
        with st.popover(_summary(selected), width="stretch", wrap=True, key="pkd_picker",
                        on_change=_menu_changed):
            query = st.text_input("Szukaj kodu lub opisu", key="pkd_search",
                                  placeholder="Wpisz dowolny kod lub nazwę branży", live=True,
                                  icon=":material/search:")
            terms = _search_text(query).split()
            visible = [code for code in PKD_OPTIONS
                       if all(term in _search_text(pkd_label(code)) for term in terms)]
            st.checkbox("Zaznacz wszystkie", key="pkd_select_all", on_change=_toggle_all,
                        help="Zaznacza pełny wykaz 728 kodów, również ukrytych przez wyszukiwanie.")
            with st.container(height=min(320, max(56, len(visible) * 64)), border=False,
                              key="pkd_scroll_list"):
                if not visible:
                    st.caption("Brak kodów pasujących do wyszukiwania.")
                for code in visible:
                    key = _option_key(code)
                    if key not in st.session_state:
                        st.session_state[key] = code in draft
                    st.checkbox(pkd_label(code), key=key, on_change=_toggle, args=(code,))
            with st.container(key="pkd_footer"):
                st.caption(f"Wybrano: {len(draft)} · Widocznych kodów: {len(visible)}")
                st.button("Zatwierdź", key="apply_pkd", type="primary", width="stretch",
                          on_click=_apply)
    with clear:
        st.button("", icon=":material/delete:", key="clear_pkd",
                  help="Wyczyść wszystkie wybrane kody PKD", width="stretch",
                  on_click=_clear, disabled=not selected and not draft)
    return list(st.session_state["selected_pkd"])
