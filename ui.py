import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8086")

st.set_page_config(page_title="Table Selector Agent", layout="centered")
st.title("Table Selector Agent")
st.caption("Sorunuza göre ilgili veritabanı tablosunu/tablolarını döner.")

if "personel_id" not in st.session_state:
    st.session_state.personel_id = None
if "step" not in st.session_state:
    st.session_state.step = 1

if st.session_state.step == 1:
    st.markdown("## Hoşgeldiniz")
    st.write("Devam etmek için lütfen personel ID'nizi girin.")

    pid_input = st.number_input("Personel ID", min_value=1, max_value=20, step=1, value=1)

    if st.button("Devam Et"):
        st.session_state.personel_id = int(pid_input)
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 2:
    st.info(f"Aktif personel: ID #{st.session_state.personel_id}")

    question = st.text_area("Sorunuzu girin", placeholder="Ahmet'in maaşı ne kadar?", height=100)

    col1, col2 = st.columns([3, 1])
    with col1:
        send_clicked = st.button("Gönder", disabled=not question.strip())
    with col2:
        if st.button("ID Değiştir"):
            st.session_state.personel_id = None
            st.session_state.step = 1
            st.rerun()

    if send_clicked:
        with st.spinner("Yanıt bekleniyor..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/select-table",
                    json={"question": question, "personel_id": st.session_state.personel_id},
                    timeout=180,
                )
                response.raise_for_status()
                data = response.json()

                tables = data.get("tables")
                entities = data.get("entities") or []
                applied_filters = data.get("applied_filters") or []
                if tables:
                    st.markdown("**İlgili tablo(lar):**")
                    for t in tables:
                        st.write(f"→ `{t}`")
                    if applied_filters or entities:
                        st.markdown("**İlgili sütunlar:**")
                    for f in applied_filters:
                        st.write(f"→ `{f['table']}`.`{f['column']}` {f['op']} **{f['value']}**")
                    for e in entities:
                        if e['column']:
                            st.write(f"→ `{e['table']}`.`{e['column']}` = **{e['value']}**")
                        else:
                            st.write(f"→ `{e['table']}` — **{e['value']}**")
                else:
                    st.warning("Soruyla eşleşen bir tablo bulunamadı.")

            except requests.exceptions.ConnectionError:
                st.error(f"API'ye bağlanılamadı. Sunucunun çalıştığından emin olun: `{API_BASE_URL}`")
            except requests.exceptions.HTTPError as e:
                st.error(f"API hatası: {e.response.status_code} — {e.response.text}")
            except Exception as e:
                st.error(f"Beklenmeyen hata: {e}")
