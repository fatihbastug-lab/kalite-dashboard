import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Kalite & Performans Analiz Dashboard", layout="wide")

# CSS ile Excel benzeri bir stil veriyoruz
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Çağrı Merkezi Kalite ve Kırılım Raporu")

# --- DOSYA YÜKLEME ---
uploaded_file = st.sidebar.file_uploader("Ham Veri (Excel) Dosyasını Yükleyin", type=['xlsx'])

if uploaded_file:
    # Tüm sayfaları oku
    try:
        df_data = pd.read_excel(uploaded_file, sheet_name='DATA')
        df_mma = pd.read_excel(uploaded_file, sheet_name='Data', engine='openpyxl') # MMA dosyası için
    except:
        st.error("Lütfen sayfa isimlerinin 'DATA' ve 'Data' (MMA için) olduğundan emin olun.")
        st.stop()

    # --- FİLTRELEME ---
    st.sidebar.header("🔍 Filtre Paneli")
    lokasyonlar = df_data['Grup Adı'].unique()
    selected_loc = st.sidebar.multiselect("Lokasyon Seçin", lokasyonlar, default=lokasyonlar)
    
    takimlar = df_data[df_data['Grup Adı'].isin(selected_loc)]['Takım Adı'].unique()
    selected_tl = st.sidebar.multiselect("Takım Lideri", takimlar, default=takimlar)

    # Filtrelenmiş Data
    f_df = df_data[(df_data['Grup Adı'].isin(selected_loc)) & (df_data['Takım Adı'].isin(selected_tl))]

    # --- ÜST KPI PANELİ ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Genel Puan Ortalaması", f"{f_df['Form Puan'].mean():.2f}")
    c2.metric("Toplam Dinleme", f"{len(f_df)}")
    c3.metric("Kritik Hata (0 Puan)", f"{len(f_df[f_df['Form Puan'] == 0])}")
    c4.metric("Hata Oranı", f"%{(len(f_df[f_df['Form Puan'] < 100]) / len(f_df)) * 100:.1f}")

    # --- SEKMELER (EXCEL SAYFALARI GİBİ) ---
    tab1, tab2, tab3, tab4 = st.tabs(["Kümüle Performans", "Hata Kırılımları", "Sıfırlama Detay", "MMA Analiz"])

    with tab1:
        st.subheader("MT Kalite Performans Listesi")
        # Örnek dosyadaki Kümüle Pivot görünümü
        pivot_mt = f_df.groupby(['Personel', 'Takım Adı', 'Grup Adı']).agg({
            'Form Puan': 'mean',
            'SantralNo': 'count'
        }).reset_index().rename(columns={'Form Puan': 'Ort. Puan', 'SantralNo': 'Dinleme Sayısı'})
        
        # Renklendirme (75 altı kırmızı)
        def color_score(val):
            color = 'red' if val < 75 else 'green' if val > 90 else 'black'
            return f'color: {color}'
        
        st.dataframe(pivot_mt.style.applymap(color_score, subset=['Ort. Puan']), use_container_width=True)

    with tab2:
        st.subheader("Hata Konusu Dağılımı (Top 10)")
        # Hata sütunlarını analiz et (Sütunlarda 1 olanları sayar)
        hata_listesi = ['Doğru Bilgilendirme', 'Sistem Kullanımı', 'Süreç Yönetimi', 'Üslup Sorunu', 'Can ve Mal Güvenliği']
        # Mevcut olan hata sütunlarını bul
        exist_errors = [c for c in hata_listesi if c in f_df.columns]
        hata_counts = f_df[exist_errors].apply(lambda x: (x < 100).sum()).sort_values(ascending=False)
        
        fig_hata = px.bar(hata_counts, orientation='h', labels={'value':'Hata Sayısı', 'index':'Kriter'}, color_discrete_sequence=['#EF553B'])
        st.plotly_chart(fig_hata, use_container_width=True)

    with tab3:
        st.subheader("Çağrı Sıfırlama (0 Puan) Kayıtları")
        zero_df = f_df[f_df['Form Puan'] == 0][['Tarih', 'Personel', 'Takım Adı', 'Açıklama Detay']]
        st.table(zero_df)

    with tab4:
        st.subheader("MMA (Müşteri Memnuniyeti) Özeti")
        if not df_mma.empty:
            mma_summary = df_mma['Anket Sonucu'].value_counts() if 'Anket Sonucu' in df_mma.columns else df_mma['Müşteri Temsilcisi Müşteriye Anket Sordu Mu?'].value_counts()
            st.bar_chart(mma_summary)
            st.dataframe(df_mma[['Müşteri Temsilcisi Adı', 'Anket Tarihi', 'Çağrı Konusu']].tail(10))

else:
    st.warning("Lütfen işlem yapmak için Excel dosyasını yükleyin.")
