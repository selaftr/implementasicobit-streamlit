"""
Aplikasi Streamlit - Dashboard Penilaian Capability Level COBIT 2019
Jalankan:  streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import cobit_core as cc

st.set_page_config(page_title="Dashboard COBIT 2019", page_icon="📊", layout="wide")
st.title("📊 Dashboard Penilaian Capability Level COBIT 2019")
st.caption("Studi kasus: PT Nusantara Logistik Prima (data simulasi) — "
           "EDM05 · APO13 · BAI09 · DSS05 · MEA03")

# ---------------------------------------------------------------- Sidebar
st.sidebar.header("⚙️ Pengaturan")
sumber = st.sidebar.radio("Sumber data", ["Data contoh (simulasi)", "Unggah CSV sendiri"])
if sumber == "Unggah CSV sendiri":
    up = st.sidebar.file_uploader(
        "CSV dengan kolom: process, level, activity_id, activity, score", type="csv")
    if up is None:
        st.info("Unggah file CSV di sidebar, atau pilih 'Data contoh'.")
        st.stop()
    data = pd.read_csv(up)
    wajib = {"process", "level", "activity_id", "activity", "score"}
    if not wajib.issubset(data.columns):
        st.error(f"Kolom wajib belum lengkap: {sorted(wajib - set(data.columns))}")
        st.stop()
else:
    data = pd.read_csv("data_assessment.csv")

st.sidebar.subheader("🎯 Target capability level")
targets = {}
for p in sorted(data["process"].unique()):
    targets[p] = st.sidebar.slider(
        f"{p} – {cc.PROCESS_NAMES.get(p, '')}", 0, 5, cc.DEFAULT_TARGETS.get(p, 3))

with st.sidebar.expander("📖 Skala rating NPLF"):
    st.markdown("- **N** Not achieved: 0–15 %\n- **P** Partially: >15–50 %\n"
                "- **L** Largely: >50–85 %\n- **F** Fully: >85–100 %")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Ringkasan", "📝 Data Penilaian", "🔍 Detail Level", "💡 Rekomendasi"])

# ----------------------------------------------------- Data (dapat diedit)
with tab2:
    st.subheader("Skor pencapaian aktivitas (%)")
    st.write("Ubah nilai pada kolom **score** untuk mensimulasikan perbaikan; "
             "seluruh dashboard akan terhitung ulang.")
    edited = st.data_editor(
        data, width="stretch", hide_index=True, height=420,
        disabled=["process", "level", "activity_id", "activity"],
        column_config={"score": st.column_config.NumberColumn(
            "score", min_value=0.0, max_value=100.0, step=1.0)})
edited = edited.copy()

result = cc.assess(edited, targets)
sm = cc.summary(result)
ratings = cc.level_ratings(edited)
recs = cc.recommendations(edited, result)

# ------------------------------------------------------------- Ringkasan
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rata-rata level saat ini", sm["rata_level"])
    c2.metric("Rata-rata level target", sm["rata_target"])
    c3.metric("Proses mencapai target", f'{sm["pct_tercapai"]} %')
    c4.metric("Total gap", sm["total_gap"])

    st.subheader("Hasil per proses")
    st.dataframe(result, width="stretch", hide_index=True)

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        cats = result["Proses"].tolist()
        fig.add_trace(go.Scatterpolar(r=result["Level Saat Ini"].tolist() + [result["Level Saat Ini"].iloc[0]],
                                      theta=cats + [cats[0]], fill="toself", name="Saat ini"))
        fig.add_trace(go.Scatterpolar(r=result["Level Target"].tolist() + [result["Level Target"].iloc[0]],
                                      theta=cats + [cats[0]], name="Target", line=dict(dash="dash")))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5], dtick=1)),
                          title="Radar capability level", height=420)
        st.plotly_chart(fig, width="stretch")
    with right:
        m = result.melt(id_vars="Proses", value_vars=["Level Saat Ini", "Level Target"],
                        var_name="Jenis", value_name="Level")
        fig2 = px.bar(m, x="Proses", y="Level", color="Jenis", barmode="group",
                      range_y=[0, 5], title="Perbandingan level saat ini vs target")
        fig2.update_layout(height=420)
        st.plotly_chart(fig2, width="stretch")

# ---------------------------------------------------------- Detail level
with tab3:
    st.subheader("Rating NPLF per proses & level")
    pv = ratings.pivot(index="process", columns="level", values="score").round(1)
    pr = ratings.pivot(index="process", columns="level", values="rating")
    fig3 = px.imshow(pv, text_auto=True, color_continuous_scale="RdYlGn", zmin=0, zmax=100,
                     labels=dict(x="Level", y="Proses", color="Skor %"), aspect="auto",
                     title="Heatmap skor rata-rata (%)")
    st.plotly_chart(fig3, width="stretch")
    st.dataframe(pr.rename(columns=lambda x: f"Level {x}"), width="stretch")

# ---------------------------------------------------------- Rekomendasi
with tab4:
    st.subheader("Prioritas perbaikan")
    if recs.empty:
        st.success("Seluruh proses telah mencapai level target. 🎉")
    else:
        for proc in result.loc[result["Gap"] > 0, "Proses"]:
            r = result[result["Proses"] == proc].iloc[0]
            with st.expander(f'{proc} – {r["Nama Proses"]}  |  Level {r["Level Saat Ini"]} → '
                             f'{r["Level Target"]}  |  Prioritas {r["Prioritas"]}', expanded=True):
                st.dataframe(recs[recs["Proses"] == proc].drop(columns=["Proses"]),
                             width="stretch", hide_index=True)
        st.download_button("⬇️ Unduh rekomendasi (CSV)", recs.to_csv(index=False).encode("utf-8"),
                           "rekomendasi_cobit.csv", "text/csv")
    st.download_button("⬇️ Unduh hasil penilaian (CSV)", result.to_csv(index=False).encode("utf-8"),
                       "hasil_capability_level.csv", "text/csv")
