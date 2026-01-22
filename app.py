import streamlit as st
import pandas as pd

uploaded_files = st.sidebar.file_uploader(
    "Excel dosyalarını yükleyin (3 dosya birden seçin)",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:
    if len(uploaded_files) != 3:
        st.warning(f"Şu an {len(uploaded_files)} dosya seçtiniz. Lütfen tam 3 dosya yükleyin.")
        st.stop()

    # Dosyaları isimlerine göre eşleştirme (anahtar kelimeler)
    def pick_file(files, keywords):
        for f in files:
            name = f.name.lower()
            if any(k in name for k in keywords):
                return f
        return None

    file_data = pick_file(uploaded_files, ["data", "ham", "kalite"])     # DATA sayfası olan dosya
    file_mma  = pick_file(uploaded_files, ["mma", "anket", "memnun"])    # MMA dosyası
    file_3    = pick_file(uploaded_files, ["hedef", "target", "extra", "3"])  # 3. dosya (senin kullanımına göre)

    # Bulunamayanları sırayla doldur (fallback)
    remaining = [f for f in uploaded_files if f not in [file_data, file_mma, file_3]]
    if file_data is None:
        file_data = remaining.pop(0) if remaining else uploaded_files[0]
    if file_mma is None:
        remaining = [f for f in uploaded_files if f not in [file_data, file_mma, file_3]]
        file_mma = remaining.pop(0) if remaining else uploaded_files[1]
    if file_3 is None:
        remaining = [f for f in uploaded_files if f not in [file_data, file_mma]]
        file_3 = remaining[0] if remaining else uploaded_files[2]

    # Okuma
    try:
        df_data = pd.read_excel(file_data, sheet_name="DATA")
    except Exception:
        st.error(f"'{file_data.name}' içinde 'DATA' sayfası bulunamadı.")
        st.stop()

    try:
        df_mma = pd.read_excel(file_mma, sheet_name="Data")
    except Exception:
        st.error(f"'{file_mma.name}' içinde 'Data' (MMA) sayfası bulunamadı.")
        st.stop()

    # 3. dosya nasıl bir dosya ise ona göre sheet_name ver (şimdilik ilk sayfa)
    try:
        df_3 = pd.read_excel(file_3)  # gerekiyorsa sheet_name="..."
    except Exception:
        st.error(f"'{file_3.name}' okunamadı.")
        st.stop()

    st.sidebar.success(
        f"Yüklendi:\n- DATA: {file_data.name}\n- MMA: {file_mma.name}\n- 3. Dosya: {file_3.name}"
    )

    # Bundan sonra mevcut kodunda uploaded_file yerine df_data/df_mma kullanarak devam et
else:
    st.warning("Lütfen 3 Excel dosyasını aynı anda yükleyin.")
    st.stop()
