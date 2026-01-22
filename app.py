import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------
# CONFIG + STYLE
# ----------------------------
st.set_page_config(page_title="Kalite & Performans Analiz Dashboard", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Çağrı Merkezi Kalite ve Kırılım Raporu")

# ----------------------------
# HELPERS
# ----------------------------
def has_sheet(uploaded_file, sheet_name: str) -> bool:
    """Checks whether an uploaded excel file contains a sheet name."""
    try:
        xl = pd.ExcelFile(uploaded_file)
        return sheet_name in xl.sheet_names
    except Exception:
        return False

def safe_read_excel(uploaded_file, sheet_name: str | None = None) -> pd.DataFrame:
    """Reads excel safely and returns empty df on failure."""
    try:
        if sheet_name is None:
            return pd.read_excel(uploaded_file)
        return pd.read_excel(uploaded_file, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame()

def normalize_dt(df: pd.DataFrame, col: str):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

def style_score(val):
    try:
        if pd.isna(val):
            return ""
        if val < 75:
            return "color: red; font-weight: 700;"
        if val > 90:
            return "color: green; font-weight: 700;"
        return "color: black;"
    except Exception:
        return ""

# ----------------------------
# UPLOAD (TEK ALAN, 2 DOSYA)
# ----------------------------
st.sidebar.header("📥 Dosya Yükleme")
uploaded_files = st.sidebar.file_uploader(
    "Excel dosyalarını yükleyin (2 dosya: HAM + MMA)",
    type=["xlsx"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.warning("Lütfen işlem yapmak için **HAM veri** ve **MMA** dosyalarını yükleyin.")
    st.stop()

if len(uploaded_files) != 2:
    st.warning(f"Şu an **{len(uploaded_files)}** dosya seçtiniz. Lütfen **tam 2 dosya** yükleyin.")
    st.stop()

# Dosyaları otomatik ayır:
# - HAM dosya: içinde 'DATA' sheet'i olan
# - MMA dosya: içinde 'Data' sheet'i olan
file_ham = None
file_mma = None

for f in uploaded_files:
    if has_sheet(f, "DATA"):
        file_ham = f
    if has_sheet(f, "Data"):
        file_mma = f

# Eğer sheet ile ayırma tutmazsa isimden dene
if file_ham is None or file_mma is None:
    for f in uploaded_files:
        nm = f.name.lower()
        if file_ham is None and any(k in nm for k in ["ham", "kalite", "data"]):
            file_ham = f
        if file_mma is None and any(k in nm for k in ["mma", "anket", "memnun"]):
            file_mma = f

# Hâlâ bulunamazsa sıraya göre ata
if file_ham is None or file_mma is None:
    file_ham = uploaded_files[0]
    file_mma = uploaded_files[1]

# Okuma
df_data = safe_read_excel(file_ham, sheet_name="DATA")
df_mma = safe_read_excel(file_mma, sheet_name="Data")

if df_data.empty:
    st.error(f"'{file_ham.name}' dosyasında **DATA** sayfası okunamadı/boş.")
    st.stop()

# MMA boş olabilir; sorun etmiyoruz
st.sidebar.success(
    f"Yüklendi:\n- HAM (DATA): {file_ham.name}\n- MMA (Data): {file_mma.name}"
)

# (Sonraki adım için not)
st.sidebar.info("Not: Hata kırılımları dosyasını bir sonraki adımda ayrıca ekleyeceğiz.")

# ----------------------------
# BASIC CLEANUP
# ----------------------------
normalize_dt(df_data, "Tarih")
normalize_dt(df_mma, "Anket Tarihi")

# Zorunlu kolon kontrolü
required = ["Grup Adı", "Takım Adı", "Personel", "Form Puan"]
missing = [c for c in required if c not in df_data.columns]
if missing:
    st.error(f"HAM/DATA içinde eksik kolon(lar): {', '.join(missing)}")
    st.stop()

# ----------------------------
# FILTERS
# ----------------------------
st.sidebar.header("🔍 Filtre Paneli")

lokasyonlar = sorted(df_data["Grup Adı"].dropna().unique())
selected_loc = st.sidebar.multiselect("Lokasyon Seçin", lokasyonlar, default=lokasyonlar)

takimlar = sorted(df_data[df_data["Grup Adı"].isin(selected_loc)]["Takım Adı"].dropna().unique())
selected_tl = st.sidebar.multiselect("Takım Lideri", takimlar, default=takimlar)

f_df = df_data[
    (df_data["Grup Adı"].isin(selected_loc)) &
    (df_data["Takım Adı"].isin(selected_tl))
].copy()

# ----------------------------
# KPI PANEL
# ----------------------------
total = len(f_df)
mean_score = float(f_df["Form Puan"].mean()) if total else 0.0
zero_cnt = int((f_df["Form Puan"] == 0).sum()) if total else 0
error_rate = (float((f_df["Form Puan"] < 100).sum()) / total * 100) if total else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Genel Puan Ortalaması", f"{mean_score:.2f}")
c2.metric("Toplam Dinleme", f"{total}")
c3.metric("Kritik Hata (0 Puan)", f"{zero_cnt}")
c4.metric("Hata Oranı (100 altı)", f"%{error_rate:.1f}")

# ----------------------------
# TABS
# ----------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Kümüle Performans", "Hata Kırılımları", "Sıfırlama Detay", "MMA Analiz"]
)

with tab1:
    st.subheader("MT Kalite Performans Listesi")

    # count için SantralNo varsa onu say; yoksa satır say
    if "SantralNo" in f_df.columns:
        count_col = "SantralNo"
        pivot_mt = (
            f_df.groupby(["Personel", "Takım Adı", "Grup Adı"], dropna=False)
            .agg(**{"Ort. Puan": ("Form Puan", "mean"), "Dinleme Sayısı": (count_col, "count")})
            .reset_index()
        )
    else:
        pivot_mt = (
            f_df.groupby(["Personel", "Takım Adı", "Grup Adı"], dropna=False)
            .agg(**{"Ort. Puan": ("Form Puan", "mean"), "Dinleme Sayısı": ("Form Puan", "size")})
            .reset_index()
        )

    pivot_mt = pivot_mt.sort_values(["Ort. Puan", "Dinleme Sayısı"], ascending=[True, False])

    st.dataframe(
        pivot_mt.style.applymap(style_score, subset=["Ort. Puan"]).format({"Ort. Puan": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.subheader("Hata Kırılımları")

    # ŞU AN: hata kırılımları ham dosyadaki kolonlardan yapılır (varsa).
    # BİR SONRAKİ ADIM: buraya ayrıca "hata kırılım" dosyası yükleme ekleyeceğiz.

    hata_listesi = [
        "Doğru Bilgilendirme",
        "Sistem Kullanımı",
        "Süreç Yönetimi",
        "Üslup Sorunu",
        "Can ve Mal Güvenliği",
    ]
    exist_errors = [c for c in hata_listesi if c in f_df.columns]

    if not exist_errors:
        st.info("Ham veride tanımlı hata kolonları bulunamadı. (Sonraki adımda ayrı dosyadan beslenecek.)")
    else:
        def count_error(series: pd.Series) -> int:
            s = series.dropna()
            if s.empty:
                return 0
            if pd.api.types.is_numeric_dtype(s):
                # sayısal ise 100 altını hata kabul et
                return int((s < 100).sum())
            if pd.api.types.is_bool_dtype(s):
                return int(s.sum())
            # metinse evet/1/true vb.
            s2 = s.astype(str).str.strip().str.lower()
            return int(s2.isin(["evet", "yes", "1", "true", "hata"]).sum())

        hata_counts = pd.Series({c: count_error(f_df[c]) for c in exist_errors}).sort_values(ascending=False)
        fig_hata = px.bar(
            hata_counts.head(10),
            orientation="h",
            labels={"value": "Hata Sayısı", "index": "Kriter"},
        )
        fig_hata.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_hata, use_container_width=True)

with tab3:
    st.subheader("Çağrı Sıfırlama (0 Puan) Kayıtları")

    cols = [c for c in ["Tarih", "Personel", "Takım Adı", "Açıklama Detay"] if c in f_df.columns]
    zero_df = f_df[f_df["Form Puan"] == 0][cols].copy()

    if zero_df.empty:
        st.success("Seçili filtrelerde 0 puan kaydı yok.")
    else:
        st.dataframe(zero_df, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("MMA (Müşteri Memnuniyeti) Özeti")

    if df_mma.empty:
        st.info("MMA sayfası boş veya okunamadı.")
    else:
        if "Anket Sonucu" in df_mma.columns:
            mma_col = "Anket Sonucu"
        elif "Müşteri Temsilcisi Müşteriye Anket Sordu Mu?" in df_mma.columns:
            mma_col = "Müşteri Temsilcisi Müşteriye Anket Sordu Mu?"
        else:
            mma_col = None

        if mma_col:
            mma_summary = df_mma[mma_col].value_counts(dropna=False)
            st.bar_chart(mma_summary)
        else:
            st.warning("MMA özet kolonu bulunamadı.")

        show_cols = [c for c in ["Müşteri Temsilcisi Adı", "Anket Tarihi", "Çağrı Konusu"] if c in df_mma.columns]
        if show_cols:
            st.dataframe(df_mma[show_cols].tail(10), use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_mma.tail(10), use_container_width=True, hide_index=True)
