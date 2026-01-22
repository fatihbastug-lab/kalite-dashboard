import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Kalite & Performans Analiz Dashboard", layout="wide")

st.markdown("""
<style>
.main { background-color: #f5f7f9; }
.stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

st.title("📊 Çağrı Merkezi Kalite ve Kırılım Raporu")

# ✅ TEK uploader - 3 dosya
uploaded_files = st.sidebar.file_uploader(
    "Excel dosyalarını yükleyin (3 dosya birden seçin)",
    type=["xlsx"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.warning("Lütfen işlem yapmak için 3 Excel dosyasını yükleyin.")
    st.stop()

if len(uploaded_files) != 3:
    st.warning(f"Şu an {len(uploaded_files)} dosya seçtiniz. Lütfen tam 3 dosya yükleyin.")
    st.stop()

def pick_file(files, keywords):
    for f in files:
        name = f.name.lower()
        if any(k in name for k in keywords):
            return f
    return None

file_data = pick_file(uploaded_files, ["ham", "veri", "data", "kalite"])
file_mma  = pick_file(uploaded_files, ["mma", "anket", "memnun"])
file_3    = pick_file(uploaded_files, ["sikayet", "şikayet", "complaint"])

# fallback (bulamazsa sıraya göre)
remaining = [f for f in uploaded_files if f not in [file_data, file_mma, file_3]]
if file_data is None:
    file_data = remaining.pop(0)
remaining = [f for f in uploaded_files if f not in [file_data, file_mma, file_3]]
if file_mma is None:
    file_mma = remaining.pop(0)
remaining = [f for f in uploaded_files if f not in [file_data, file_mma]]
if file_3 is None:
    file_3 = remaining[0]

# ✅ Excel okuma
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

# 3. dosya (Şikayet vb.)
try:
    df_sikayet = pd.read_excel(file_3)
except Exception:
    df_sikayet = pd.DataFrame()

st.sidebar.success(
    f"Yüklendi:\n- DATA: {file_data.name}\n- MMA: {file_mma.name}\n- 3. Dosya: {file_3.name}"
)

# ---------------------------------------------------------
# ✅ BURADAN SONRASI: SENİN ESKİ DASHBOARD KODUN
# df_data ve df_mma kullanarak aynı şekilde devam
# ---------------------------------------------------------

st.sidebar.header("🔍 Filtre Paneli")
lokasyonlar = df_data['Grup Adı'].unique()
selected_loc = st.sidebar.multiselect("Lokasyon Seçin", lokasyonlar, default=lokasyonlar)

takimlar = df_data[df_data['Grup Adı'].isin(selected_loc)]['Takım Adı'].unique()
selected_tl = st.sidebar.multiselect("Takım Lideri", takimlar, default=takimlar)

f_df = df_data[(df_data['Grup Adı'].isin(selected_loc)) & (df_data['Takım Adı'].isin(selected_tl))]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Genel Puan Ortalaması", f"{f_df['Form Puan'].mean():.2f}" if len(f_df) else "0.00")
c2.metric("Toplam Dinleme", f"{len(f_df)}")
c3.metric("Kritik Hata (0 Puan)", f"{len(f_df[f_df['Form Puan'] == 0])}")
c4.metric("Hata Oranı", f"%{((len(f_df[f_df['Form Puan'] < 100]) / len(f_df)) * 100):.1f}" if len(f_df) else "%0.0")

tab1, tab2, tab3, tab4 = st.tabs(["Kümüle Performans", "Hata Kırılımları", "Sıfırlama Detay", "MMA Analiz"])

with tab1:
    st.subheader("MT Kalite Performans Listesi")
    pivot_mt = f_df.groupby(['Personel', 'Takım Adı', 'Grup Adı']).agg({
        'Form Puan': 'mean',
        'SantralNo': 'count' if 'SantralNo' in f_df.columns else 'size'
    }).reset_index().rename(columns={'Form Puan': 'Ort. Puan', 'SantralNo': 'Dinleme Sayısı'})

    def color_score(val):
        color = 'red' if val < 75 else 'green' if val > 90 else 'black'
        return f'color: {color}'

    st.dataframe(pivot_mt.style.applymap(color_score, subset=['Ort. Puan']), use_container_width=True)

with tab2:
    st.subheader("Hata Konusu Dağılımı (Top 10)")
    hata_listesi = ['Doğru Bilgilendirme', 'Sistem Kullanımı', 'Süreç Yönetimi', 'Üslup Sorunu', 'Can ve Mal Güvenliği']
    exist_errors = [c for c in hata_listesi if c in f_df.columns]

    if exist_errors:
        hata_counts = f_df[exist_errors].apply(lambda x: (x < 100).sum() if pd.api.types.is_numeric_dtype(x) else (x == 1).sum()).sort_values(ascending=False)
        fig_hata = px.bar(hata_counts, orientation='h', labels={'value':'Hata Sayısı', 'index':'Kriter'})
        st.plotly_chart(fig_hata, use_container_width=True)
    else:
        st.info("Hata sütunları bulunamadı.")

with tab3:
    st.subheader("Çağrı Sıfırlama (0 Puan) Kayıtları")
    cols = [c for c in ['Tarih', 'Personel', 'Takım Adı', 'Açıklama Detay'] if c in f_df.columns]
    zero_df = f_df[f_df['Form Puan'] == 0][cols]
    st.dataframe(zero_df, use_container_width=True)

with tab4:
    st.subheader("MMA (Müşteri Memnuniyeti) Özeti")
    if not df_mma.empty:
        if 'Anket Sonucu' in df_mma.columns:
            mma_summary = df_mma['Anket Sonucu'].value_counts()
        elif 'Müşteri Temsilcisi Müşteriye Anket Sordu Mu?' in df_mma.columns:
            mma_summary = df_mma['Müşteri Temsilcisi Müşteriye Anket Sordu Mu?'].value_counts()
        else:
            mma_summary = None

        if mma_summary is not None:
            st.bar_chart(mma_summary)

        show_cols = [c for c in ['Müşteri Temsilcisi Adı', 'Anket Tarihi', 'Çağrı Konusu'] if c in df_mma.columns]
        if show_cols:
            st.dataframe(df_mma[show_cols].tail(10), use_container_width=True)
    else:
        st.info("MMA verisi boş.")
