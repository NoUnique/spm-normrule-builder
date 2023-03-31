import re
import unicodedata
import urllib

import pandas as pd
import streamlit as st

# from . import builder

_UNICODE_BLOCKS = {
    "Basic Latin": (0x0000, 0x007F),
    "Latin-1 Supplement": (0x0080, 0x00FF),
    "Latin Extended-A": (0x0100, 0x017F),
    "Latin Extended-B": (0x0180, 0x024F),
    # ...
}

_NORMALIZERS = {
    # "NFC": builder.to_nfc,
    # "NFD": builder.to_nfd,
    # "NFKC": builder.to_nfkc,
    # "NFKD": builder.to_nfkd,
    "NFC": 1,
    "NFD": 2,
    "NFKC": 3,
    "NFKD": 4,
}

_HIGHLIGHTS = {
    "red": lambda block_name: "hangul" in block_name.lower(),
    "blue": lambda block_name: "enclosed" in block_name.lower(),
    "green": lambda block_name: "cjk" in block_name.lower(),
}


def _parse_blocks(text):
    global _UNICODE_BLOCKS
    _UNICODE_BLOCKS = {}

    pattern = re.compile(r"([0-9A-F]+)\.\.([0-9A-F]+);\ (\S.*\S)")
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            start, end, name = m.groups()
            _UNICODE_BLOCKS[name] = (int(start, 16), int(end, 16))


def _parse_datetime(text):
    pattern = re.compile(r"# Date:\s+(\d{4}-\d{2}-\d{2}),\s+(\d{2}:\d{2}:\d{2})\s+GMT")
    match = pattern.search(text)
    if match:
        date, time = match.groups()
    return date, time


url = "http://unicode.org/Public/UNIDATA/Blocks.txt"
with urllib.request.urlopen(url) as response:
    file_content = response.read().decode("utf-8")

_parse_blocks(file_content)
_parse_datetime(file_content)


@st.cache_data
def list_unicode_block(block_name):
    start, end = _UNICODE_BLOCKS[block_name]
    characters = []

    def is_surrogate(char):
        return 0xD800 <= ord(char) <= 0xDFFF

    for code in range(start, end + 1):
        char = chr(code)
        if not is_surrogate(char):
            name = unicodedata.name(char, None)
            if name:
                characters.append({"Code": hex(code), "Character": char, "Name": name})
            else:
                characters.append({"Code": hex(code), "Character": char, "Name": None})
    return pd.DataFrame(characters)


def custom_style(color="red"):
    return f"""
        <style>
        .custom-container-top-{color} {{
            border: 4px solid {color};
            border-bottom: none;
            border-radius: 0.5rem 0.5rem 0 0;
            padding: 0.5rem;
        }}

        .custom-container-bottom-{color} {{
            border: 4px solid {color};
            border-top: none;
            border-radius: 0 0 0.5rem 0.5rem;
            padding: 0.5rem;
            margin-top: -1rem;
            margin-bottom: 1rem;
        }}
        </style>
    """


def make_block(block_name, index):
    def default_block(block_name, index):
        _, col1, col2, _ = st.columns([1, 8, 20, 1])
        with col1:
            _normalizers = list(_NORMALIZERS.keys())
            st.session_state.normalizers[index] = st.selectbox(
                "Normalization Type",
                _normalizers,
                key=f"expander-{index}-normtype",
                index=_normalizers.index(st.session_state.normalizers[index]),
                label_visibility="collapsed",
            )
        with col2:
            with st.expander(block_name):
                st.cache_resource
                st.dataframe(list_unicode_block(block_name), use_container_width=True)

    for color, condition in _HIGHLIGHTS.items():
        if not condition(block_name):
            continue

        with st.container():
            st.markdown(f"<div class='custom-container-top-{color}'></div>", unsafe_allow_html=True)
            default_block(block_name, index)
            st.markdown(f"<div class='custom-container-bottom-{color}'></div>", unsafe_allow_html=True)
        return

    if not st.session_state.hide_blocks:
        with st.container():
            default_block(block_name, index)


def main():
    st.title("Custom Normalization Rule Builder     for SentencePiece")

    block_list = list(_UNICODE_BLOCKS.keys())
    _default_normalizer = list(_NORMALIZERS.keys())[0]
    st.session_state.global_normalizer = _default_normalizer
    st.session_state.normalizers = [_default_normalizer] * len(block_list)
    st.session_state.r_text = "hangul"
    st.session_state.b_text = "enclosed"
    st.session_state.g_text = "cjk"

    global_normalizer = st.selectbox("Global Normalization Type", list(_NORMALIZERS.keys()), index=0)
    if st.session_state.global_normalizer != global_normalizer:
        st.session_state.global_normalizer = global_normalizer
        for i in range(len(block_list)):
            st.session_state.normalizers[i] = global_normalizer

    r_text = st.text_input("Red", st.session_state.r_text)
    b_text = st.text_input("Blue", st.session_state.b_text)
    g_text = st.text_input("Green", st.session_state.g_text)
    st.text("Highlight blocks with a colored border if its name includes the specified words.")
    _HIGHLIGHTS["red"] = lambda block_name: r_text.strip().lower() in block_name.lower()
    _HIGHLIGHTS["blue"] = lambda block_name: b_text.strip().lower() in block_name.lower()
    _HIGHLIGHTS["green"] = lambda block_name: g_text.strip().lower() in block_name.lower()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.checkbox("Show highlighted only", value=False, key="hide_blocks")
    with col2:
        st.download_button("**Download Custom Rule**", "", file_name="custom_norm.tsv", use_container_width=True)
    for color in _HIGHLIGHTS.keys():
        st.markdown(custom_style(color), unsafe_allow_html=True)

    for i, block_name in enumerate(block_list):
        make_block(block_name, i)


if __name__ == "__main__":
    main()
