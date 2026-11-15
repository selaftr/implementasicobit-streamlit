"""
cobit_core.py
Logika inti penilaian Capability Level COBIT 2019 (dipakai oleh Jupyter & Streamlit).

Skala rating pencapaian aktivitas (mengacu pada skala NPLF ISO/IEC 33020):
    N = Not achieved        (0  - 15 %)
    P = Partially achieved  (>15 - 50 %)
    L = Largely achieved    (>50 - 85 %)
    F = Fully achieved      (>85 - 100 %)
"""
import pandas as pd

PROCESS_NAMES = {
    "EDM05": "Managed Stakeholder Engagement",
    "APO13": "Managed Security",
    "BAI09": "Managed Assets",
    "DSS05": "Managed Security Services",
    "MEA03": "Managed Compliance With External Requirements",
}
DEFAULT_TARGETS = {"EDM05": 3, "APO13": 4, "BAI09": 3, "DSS05": 3, "MEA03": 3}
LEVEL_NAMES = {0: "Incomplete", 1: "Performed", 2: "Managed",
               3: "Established", 4: "Predictable", 5: "Optimizing"}


def nplf(score: float) -> str:
    """Ubah persentase pencapaian (0-100) menjadi rating N/P/L/F."""
    if score <= 15:
        return "N"
    if score <= 50:
        return "P"
    if score <= 85:
        return "L"
    return "F"


def level_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """Rata-rata skor per proses & level, lalu konversi ke rating NPLF."""
    r = df.groupby(["process", "level"], as_index=False)["score"].mean()
    r["rating"] = r["score"].apply(nplf)
    return r


def capability_level(ratings: dict) -> int:
    """
    Aturan penentuan capability level:
    level n tercapai jika rating level n = L atau F, dan seluruh level di
    bawahnya (1..n-1) berating F.
    """
    achieved = 0
    for n in range(1, 6):
        rt = ratings.get(n, "N")
        if rt in ("L", "F"):
            achieved = n
            if rt != "F":
                break
        else:
            break
    return achieved


def assess(df: pd.DataFrame, targets: dict) -> pd.DataFrame:
    """Hasilkan tabel hasil: level saat ini, target, gap, prioritas."""
    lr = level_ratings(df)
    rows = []
    for proc, g in lr.groupby("process"):
        rt = dict(zip(g["level"], g["rating"]))
        cur = capability_level(rt)
        tgt = int(targets.get(proc, 3))
        gap = max(tgt - cur, 0)
        prio = "Tinggi" if gap >= 2 else "Sedang" if gap == 1 else "Tercapai"
        rows.append({
            "Proses": proc,
            "Nama Proses": PROCESS_NAMES.get(proc, proc),
            "Level Saat Ini": cur,
            "Status": LEVEL_NAMES[cur],
            "Level Target": tgt,
            "Gap": gap,
            "Prioritas": prio,
        })
    return pd.DataFrame(rows).sort_values(["Gap", "Proses"], ascending=[False, True]).reset_index(drop=True)


def recommendations(df: pd.DataFrame, result: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """
    Rekomendasi otomatis: pada level berikutnya (cur+1, maks. target) ambil
    aktivitas dengan skor terendah (< 85 %) sebagai fokus perbaikan.
    """
    out = []
    for _, r in result.iterrows():
        if r["Gap"] == 0:
            continue
        sub = df[df["process"] == r["Proses"]]
        # konsolidasi level saat ini bila belum F, lalu naik ke level berikutnya
        levels = sorted({max(r["Level Saat Ini"], 1), r["Level Saat Ini"] + 1})
        levels = [l for l in levels if 1 <= l <= r["Level Target"]]
        cand = sub[(sub["level"].isin(levels)) & (sub["score"] <= 85)]
        cand = cand.sort_values("score").head(top_n)
        for _, a in cand.iterrows():
            out.append({
                "Proses": r["Proses"],
                "Prioritas": r["Prioritas"],
                "Level": int(a["level"]),
                "Aktivitas yang perlu ditingkatkan": a["activity"],
                "Skor (%)": round(float(a["score"]), 1),
            })
    return pd.DataFrame(out)


def summary(result: pd.DataFrame) -> dict:
    """Ringkasan: rata-rata capability level, rata-rata target, % target tercapai."""
    return {
        "rata_level": float(round(result["Level Saat Ini"].mean(), 2)),
        "rata_target": float(round(result["Level Target"].mean(), 2)),
        "pct_tercapai": float(round((result["Gap"] == 0).mean() * 100, 1)),
        "total_gap": int(result["Gap"].sum()),
    }
