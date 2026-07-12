import os
import time
import streamlit as st
from google import genai

# --- ページ設定 ---
st.set_page_config(page_title="臨床リスク・統合アセスメントAI", layout="centered")
st.title("🩺 臨床リスク・統合アセスメント")
st.caption("心エコー・血液・頸部エコーと最新ガイドラインから個体的な病態生理を推論します。")

# --- APIキーのセットアップ ---
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = st.sidebar.text_input("🔑 Gemini API Key を入力", type="password")

# --- 便利関数：AIへ送るテキストの整形（空欄時は「未計測」に自動変換） ---
def fmt(val, unit=""):
    if val is None or val == "":
        return "未計測/評価なし"
    return f"{val}{unit}"

# --- 1. 基本情報の入力 ---
st.header("1. 患者基本情報")
col_base1, col_base2 = st.columns(2)
with col_base1:
    age = st.number_input("年齢", value=75, step=1)
    sex = st.selectbox("性別", ["男性", "女性"])
with col_base2:
    sys_bp = st.number_input("収縮期血圧 (mmHg)", value=None, placeholder="例: 130", step=1)
    dia_bp = st.number_input("拡張期血圧 (mmHg)", value=None, placeholder="例: 75", step=1)

hr_val = st.number_input("心拍数 HR (bpm)", value=None, placeholder="例: 68", step=1)
rhythm = st.selectbox("心拍リズム", ["整", "不整 (心房細動など)", "ペースメーカー"], index=0)

chief_complaint = st.text_input("主訴・現在の症状", placeholder="例: 労作時の息切れ、ふらつき")
history_list = st.multiselect(
    "既往歴・主疾患 (該当するものをタップで複数選択)",
    ["高血圧", "2型糖尿病", "脂質異常症", "慢性腎臓病(CKD)", "虚血性心疾患(狭心症・心筋梗塞)", "心不全", "脳卒中・TIA", "心房細動", "閉塞性動脈硬化症(ASO)", "B型肝炎", "C型肝炎", "肝硬変"]
)

# --- 2. 検査データの入力 ---
st.header("2. 検査データ (未計測欄は空欄のままでOK)")
tab_echo, tab_blood, tab_carotid = st.tabs(["💓 心エコー", "🩸 血液検査", "🩺 頸部エコー"])

# =========================================================
# タブ1：心エコー（完全準拠・セクション編成＆単位m/s対応）
# =========================================================
with tab_echo:
    st.subheader("心臓超音波検査 (Echo)")
    st.caption("※検査した項目のみ数値を入力してください。未入力の欄は裏に薄文字の目安が表示されます。")
    
    with st.expander("➕ AoD・LAD", expanded=True):
        c_aod1, c_aod2 = st.columns(2)
        with c_aod1:
            aod = st.number_input("AoD (mm)", value=None, placeholder="目安: 30.0", step=1.0)
        with c_aod2:
            lad = st.number_input("LAD (mm)", value=None, placeholder="目安: 35.0", step=1.0)

    with st.expander("➕ Mitral valve (DDR, Prolapse, SAM)"):
        c_mv1, c_mv2, c_mv3 = st.columns(3)
        with c_mv1:
            ddr = st.selectbox("DDR", ["正常・良好", "低下", "著明低下"], index=None, placeholder="選択なし")
        with c_mv2:
            prolapse = st.selectbox("Prolapse (逸脱)", ["なし (-)", "あり (+)"], index=None, placeholder="選択なし")
        with c_mv3:
            sam = st.selectbox("SAM", ["なし (-)", "あり (+)"], index=None, placeholder="選択なし")

    with st.expander("➕ LV size function (IVS, LVPW, LVDd/s, SV, Co, CI, HR, EF, FS)"):
        c_lv1, c_lv2 = st.columns(2)
        with c_lv1:
            ivs = st.number_input("IVS Thickness (mm)", value=None, placeholder="目安: 10.0", step=0.5)
            lvpw = st.number_input("LVPW Thickness (mm)", value=None, placeholder="目安: 10.0", step=0.5)
            lvdd = st.number_input("LVDd (mm)", value=None, placeholder="目安: 45.0", step=1.0)
            lvds = st.number_input("LVDs (mm)", value=None, placeholder="目安: 30.0", step=1.0)
            sv = st.number_input("SV (mL)", value=None, placeholder="目安: 60.0", step=1.0)
        with c_lv2:
            co = st.number_input("Co (L/min)", value=None, placeholder="目安: 4.5", step=0.1)
            ci = st.number_input("CI (L/min/m²)", value=None, placeholder="目安: 2.5", step=0.1)
            hr_echo = st.number_input("HR - エコー時 (bpm)", value=None, placeholder="目安: 65", step=1)
            ef = st.number_input("EF (%)", value=None, placeholder="目安: 60.0", step=1.0)
            fs = st.number_input("FS (%)", value=None, placeholder="目安: 35.0", step=1.0)

    with st.expander("➕ Doppler Measurements Flow Velocity (E, A, E/A, D-time, E/E', LVOT)"):
        c_dop1, c_dop2 = st.columns(2)
        with c_dop1:
            mitral_e = st.number_input("Mitral E (m/s)", value=None, placeholder="目安: 0.70", step=0.05)
            mitral_a = st.number_input("Mitral A (m/s)", value=None, placeholder="目安: 0.60", step=0.05)
            e_a_ratio = st.number_input("E/A", value=None, placeholder="目安: 1.10", step=0.05)
        with c_dop2:
            d_time = st.number_input("D-time (ms)", value=None, placeholder="目安: 180.0", step=5.0)
            e_e_prime = st.number_input("E/E'", value=None, placeholder="目安: 8.8", step=0.5)
            lvot = st.number_input("LVOT (m/s)", value=None, placeholder="目安: 1.00", step=0.05)

    with st.expander("➕ Regurgitation (逆流・狭窄・弁口面積等)"):
        c_reg1, c_reg2 = st.columns(2)
        with c_reg1:
            ar = st.selectbox("AR", ["なし/極軽度 (-)", "軽度 (+)", "中等度 (++)", "高度 (+++)"], index=None, placeholder="選択なし")
            mr = st.selectbox("MR", ["なし/極軽度 (-)", "軽度 (+)", "中等度 (++)", "高度 (+++)"], index=None, placeholder="選択なし")
            pr = st.selectbox("PR", ["なし/極軽度 (-)", "軽度 (+)", "中等度 (++)", "高度 (+++)"], index=None, placeholder="選択なし")
            tr = st.selectbox("TR", ["なし/極軽度 (-)", "軽度 (+)", "中等度 (++)", "高度 (+++)"], index=None, placeholder="選択なし")
            pht = st.number_input("PHT (ms)", value=None, placeholder="目安: 150", step=10.0)
        with c_reg2:
            as_area = st.number_input("AS弁口面積 (cm²)", value=None, placeholder="目安: 1.5", step=0.1)
            lv_ao_pg = st.number_input("LV-AoPG (mmHg)", value=None, placeholder="目安: 15.0", step=1.0)
            ms_area = st.number_input("MS弁口面積 (cm²)", value=None, placeholder="目安: 2.0", step=0.1)
            la_lv_pg = st.number_input("LA-LVPG (mmHg)", value=None, placeholder="目安: 5.0", step=1.0)
            mva = st.number_input("MVA (cm²)", value=None, placeholder="目安: 4.0", step=0.1)

    with st.expander("➕ その他 (心内血栓, PE, 呼吸変動, 胸水, IVC径)"):
        c_oth1, c_oth2 = st.columns(2)
        with c_oth1:
            thrombus = st.selectbox("心内血栓", ["なし (-)", "あり (+)"], index=None, placeholder="選択なし")
            pe = st.selectbox("PE (心嚢液/水腫)", ["なし (-)", "あり (+)"], index=None, placeholder="選択なし")
            pleural_eff = st.selectbox("胸水", ["なし (-)", "右", "左", "両側"], index=None, placeholder="選択なし")
        with c_oth2:
            ivc_resp = st.selectbox("IVC呼吸変動", ["あり (+ : 変動良好)", "なし (- : 変動消失/低下)"], index=None, placeholder="選択なし")
            ivc_diam = st.number_input("IVC径 (mm)", value=None, placeholder="目安: 14.0", step=1.0)

# =========================================================
# タブ2：血液検査
# =========================================================
with tab_blood:
    st.subheader("血液・生化学検査")
    st.caption("※検査項目のみ数値を入力してください。空欄は「未計測」としてAIが認識します。")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        egfr = st.number_input("推算GFRcreat", value=None, placeholder="目安: 65.0", step=1.0)
        alb = st.number_input("アルブミン Alb (g/dL)", value=None, placeholder="目安: 4.0", step=0.1)
    with col_b2:
        hb = st.number_input("血色素量 Hb (g/dL)", value=None, placeholder="目安: 13.0", step=0.1)
        crp = st.number_input("CRP定量 / LA (mg/dL)", value=None, placeholder="目安: 0.10", step=0.05)
        
    with st.expander("➕ 腎機能・代謝・脂質 (BUN, Cre, 尿酸, 血糖, LDL, HDL, TG等)"):
        c9, c10 = st.columns(2)
        with c9:
            tp = st.number_input("総蛋白 (g/dL)", value=None, placeholder="目安: 7.0", step=0.1)
            ag_ratio = st.number_input("A/G比", value=None, placeholder="目安: 1.5", step=0.05)
            bun = st.number_input("尿素窒素 BUN (mg/dL)", value=None, placeholder="目安: 15.0", step=1.0)
            cre = st.number_input("クレアチニン (mg/dL)", value=None, placeholder="目安: 0.80", step=0.05)
            ua = st.number_input("尿酸 (mg/dL)", value=None, placeholder="目安: 5.5", step=0.1)
        with c10:
            fbs = st.number_input("血糖 - 空腹時 (mg/dL)", value=None, placeholder="目安: 100", step=5.0)
            ldl = st.number_input("LDLコレステロール (mg/dL)", value=None, placeholder="目安: 110", step=5.0)
            hdl = st.number_input("HDLコレステロール (mg/dL)", value=None, placeholder="目安: 55", step=5.0)
            tg = st.number_input("中性脂肪 (mg/dL)", value=None, placeholder="目安: 120", step=10.0)
            
    with st.expander("➕ 肝胆道・膵・酵素 (AST, ALT, γ-GT, ビリルビン等)"):
        c11, c12 = st.columns(2)
        with c11:
            t_bil = st.number_input("総ビリルビン (mg/dL)", value=None, placeholder="目安: 0.8", step=0.1)
            d_bil = st.number_input("直接ビリルビン (mg/dL)", value=None, placeholder="目安: 0.2", step=0.1)
            ast = st.number_input("AST (U/L)", value=None, placeholder="目安: 22", step=1.0)
            alt = st.number_input("ALT (U/L)", value=None, placeholder="目安: 20", step=1.0)
            alp = st.number_input("ALP (U/L)", value=None, placeholder="目安: 180", step=10.0)
            ggt = st.number_input("γ-GT (U/L)", value=None, placeholder="目安: 30", step=5.0)
        with c12:
            ld = st.number_input("LD (U/L)", value=None, placeholder="目安: 180", step=10.0)
            ck = st.number_input("CK (U/L)", value=None, placeholder="目安: 100", step=10.0)
            amylase = st.number_input("アミラーゼ (U/L)", value=None, placeholder="目安: 70", step=5.0)
            lap = st.number_input("LAP (U/L)", value=None, placeholder="目安: 40", step=5.0)
            che = st.number_input("ChE (U/L)", value=None, placeholder="目安: 300", step=10.0)
            
    with st.expander("➕ 血算・電解質・白血球分画 (RBC, WBC, 電解質, 好中球/リンパ等)"):
        c13, c14 = st.columns(2)
        with c13:
            na = st.number_input("ナトリウム (mEq/L)", value=None, placeholder="目安: 140", step=1.0)
            k = st.number_input("カリウム (mEq/L)", value=None, placeholder="目安: 4.2", step=0.1)
            cl = st.number_input("クロール (mEq/L)", value=None, placeholder="目安: 102", step=1.0)
            ca = st.number_input("カルシウム (mg/dL)", value=None, placeholder="目安: 9.2", step=0.1)
            wbc = st.number_input("白血球数 (/μL)", value=None, placeholder="目安: 6000", step=100.0)
            rbc = st.number_input("赤血球数 (万/μL)", value=None, placeholder="目安: 430", step=10.0)
            ht = st.number_input("ヘマトクリット (%)", value=None, placeholder="目安: 40", step=1.0)
            plt = st.number_input("血小板数 (万/μL)", value=None, placeholder="目安: 22", step=1.0)
        with c14:
            mcv = st.number_input("MCV (fL)", value=None, placeholder="目安: 90", step=1.0)
            mch = st.number_input("MCH (pg)", value=None, placeholder="目安: 30", step=0.5)
            mchc = st.number_input("MCHC (%)", value=None, placeholder="目安: 33", step=0.5)
            neutro = st.number_input("好中球 (%)", value=None, placeholder="目安: 60", step=1.0)
            lympho = st.number_input("リンパ球 (%)", value=None, placeholder="目安: 30", step=1.0)
            mono = st.number_input("単球 (%)", value=None, placeholder="目安: 6", step=0.5)
            eosino = st.number_input("好酸球 (%)", value=None, placeholder="目安: 3", step=0.5)
            baso = st.number_input("好塩基球 (%)", value=None, placeholder="目安: 1", step=0.1)
            
    with st.expander("➕ 感染症・血清学・ウイルスマーカー (HBs, HCV, 梅毒等)"):
        c15, c16 = st.columns(2)
        with c15:
            rpr = st.selectbox("RPR法 定性", ["陰性 (-)", "陽性 (+)"], index=None, placeholder="選択なし")
            tp_ab = st.selectbox("梅毒TP抗体 定性", ["陰性 (-)", "陽性 (+)"], index=None, placeholder="選択なし")
            hbs_ag = st.selectbox("HBs抗原 / CLIA", ["陰性 (-)", "陽性 (+)", "判定保留"], index=None, placeholder="選択なし")
        with c16:
            hbs_val = st.number_input("HBs抗原 定量値 (IU/mL)", value=None, placeholder="目安: 0.00", step=0.01)
            hcv_ab = st.selectbox("HCV抗体 3rd", ["陰性 (-)", "陽性 (+)", "判定保留"], index=None, placeholder="選択なし")
            hcv_idx = st.number_input("HCV抗体 インデックス/ユニット", value=None, placeholder="目安: 0.1", step=0.1)

# =========================================================
# タブ3：頸部エコー
# =========================================================
with tab_carotid:
    st.subheader("頸動脈超音波検査")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cca_ed_ratio = st.number_input("CCA ED ratio", value=None, placeholder="目安: 1.0", step=0.05)
        plaque_score = st.number_input("Plaque Score", value=None, placeholder="目安: 1.5", step=0.5)
    with col_c2:
        plaque_echo = st.selectbox("プラーク性状・動脈硬化所見", ["明らかなプラークなし", "等輝度・均質 (安定)", "低輝度・不均質 (不安定疑い)", "石灰化・高輝度プラーク"], index=None, placeholder="選択なし")
        stenosis = st.selectbox("狭窄度評価", ["明らかな狭窄なし (<30%)", "軽度狭窄 (30-49%)", "中等度狭窄 (50-69%)", "高度狭窄 (≥70%)"], index=None, placeholder="選択なし")

    with st.expander("➕ CCA IMT (内中膜複合体厚) 平均・最大"):
        c17, c18 = st.columns(2)
        with c17:
            rt_imt_mean = st.number_input("Rt-CCA IMT 平均 (mm)", value=None, placeholder="目安: 0.7", step=0.05)
            rt_imt_max = st.number_input("Rt-CCA IMT 最大 (mm)", value=None, placeholder="目安: 0.8", step=0.05)
        with c18:
            lt_imt_mean = st.number_input("Lt-CCA IMT 平均 (mm)", value=None, placeholder="目安: 0.7", step=0.05)
            lt_imt_max = st.number_input("Lt-CCA IMT 最大 (mm)", value=None, placeholder="目安: 0.8", step=0.05)

    with st.expander("➕ Rt-CCA (右総頸動脈) パラメータ"):
        c19, c20 = st.columns(2)
        with c19:
            rt_cca_diam = st.number_input("Rt-CCA 血管径 (mm)", value=None, placeholder="目安: 7.0", step=0.1)
            rt_cca_vmax = st.number_input("Rt-CCA Vmax (cm/s)", value=None, placeholder="目安: 65", step=1.0)
            rt_cca_vmin = st.number_input("Rt-CCA Vmin (cm/s)", value=None, placeholder="目安: 20", step=1.0)
        with c20:
            rt_cca_vmean = st.number_input("Rt-CCA Vmean (cm/s)", value=None, placeholder="目安: 35", step=1.0)
            rt_cca_pi = st.number_input("Rt-CCA PI", value=None, placeholder="目安: 1.25", step=0.05)
            rt_cca_ri = st.number_input("Rt-CCA RI", value=None, placeholder="目安: 0.68", step=0.02)

    with st.expander("➕ Lt-CCA (左総頸動脈) パラメータ"):
        c21, c22 = st.columns(2)
        with c21:
            lt_cca_diam = st.number_input("Lt-CCA 血管径 (mm)", value=None, placeholder="目安: 6.8", step=0.1)
            lt_cca_vmax = st.number_input("Lt-CCA Vmax (cm/s)", value=None, placeholder="目安: 62", step=1.0)
            lt_cca_vmin = st.number_input("Lt-CCA Vmin (cm/s)", value=None, placeholder="目安: 18", step=1.0)
        with c22:
            lt_cca_vmean = st.number_input("Lt-CCA Vmean (cm/s)", value=None, placeholder="目安: 33", step=1.0)
            lt_cca_pi = st.number_input("Lt-CCA PI", value=None, placeholder="目安: 1.30", step=0.05)
            lt_cca_ri = st.number_input("Lt-CCA RI", value=None, placeholder="目安: 0.70", step=0.02)

    with st.expander("➕ Rt-ICA / Lt-ICA (右/左内頸動脈) パラメータ"):
        c23, c24 = st.columns(2)
        with c23:
            st.markdown("##### Rt-ICA (右内頸動脈)")
            rt_ica_diam = st.number_input("Rt-ICA 血管径 (mm)", value=None, placeholder="目安: 4.8", step=0.1)
            rt_ica_vmax = st.number_input("Rt-ICA Vmax (cm/s)", value=None, placeholder="目安: 80", step=1.0)
            rt_ica_vmin = st.number_input("Rt-ICA Vmin (cm/s)", value=None, placeholder="目安: 28", step=1.0)
            rt_ica_vmean = st.number_input("Rt-ICA Vmean (cm/s)", value=None, placeholder="目安: 45", step=1.0)
            rt_ica_pi = st.number_input("Rt-ICA PI", value=None, placeholder="目安: 1.15", step=0.05)
            rt_ica_ri = st.number_input("Rt-ICA RI", value=None, placeholder="目安: 0.65", step=0.02)
        with c24:
            st.markdown("##### Lt-ICA (左内頸動脈)")
            lt_ica_diam = st.number_input("Lt-ICA 血管径 (mm)", value=None, placeholder="目安: 4.6", step=0.1)
            lt_ica_vmax = st.number_input("Lt-ICA Vmax (cm/s)", value=None, placeholder="目安: 78", step=1.0)
            lt_ica_vmin = st.number_input("Lt-ICA Vmin (cm/s)", value=None, placeholder="目安: 26", step=1.0)
            lt_ica_vmean = st.number_input("Lt-ICA Vmean (cm/s)", value=None, placeholder="目安: 43", step=1.0)
            lt_ica_pi = st.number_input("Lt-ICA PI", value=None, placeholder="目安: 1.16", step=0.05)
            lt_ica_ri = st.number_input("Lt-ICA RI", value=None, placeholder="目安: 0.66", step=0.02)

# =========================================================
# --- 3. 参照ガイドラインの選択 (日本語表示＆自動推奨機能つき！) ---
# =========================================================
st.header("3. 参照・照合するガイドライン")
st.caption("※患者さんの既往歴や入力された検査数値に基づき、AIが最適なガイドラインを自動推奨（チェック）しています。必要に応じてタップで調整してください。")

# 1. ユーザー指定の10ファイル完全対応！日本語表示マッピング辞書
GUIDELINE_MAP = {
    "echo.pdf": "💓 心エコー",
    "valvular_heart.pdf": "🫀 弁膜症",
    "heart_failure.pdf": "📕 心不全",
    "atherosclerosis.pdf": "📙 動脈硬化",
    "carotid_echo.pdf": "🩺 頸部エコー",
    "stroke.pdf": "🧠 脳卒中",
    "ckd.pdf": "📗 CKD (慢性腎臓病)",
    "liver_cirrhosis.pdf": "🟤 肝硬変",
    "hbv.pdf": "🦠 B型肝炎",
    "hcv.pdf": "🦠 C型肝炎"
}

available_pdfs = []
guidelines_dir = "guidelines"
if os.path.exists(guidelines_dir):
    available_pdfs = [f for f in os.listdir(guidelines_dir) if f.endswith(".pdf")]

if available_pdfs:
    # 2. 既往歴・検査数値から推奨PDFを自動セレクトする臨床ロジック
    recommended_pdfs = []
    
    for pdf in available_pdfs:
        # ① 心不全・心エコー
        if pdf == "heart_failure.pdf":
            if any(h in history_list for h in ["心不全", "虚血性心疾患(狭心症・心筋梗塞)", "心房細動", "高血圧"]) or (ef is not None and ef < 50.0):
                recommended_pdfs.append(pdf)
        elif pdf == "echo.pdf":
            # 心エコーの数値や項目が何か1つでも入力されていれば推奨
            if any(v is not None for v in [ef, aod, lad, ivs, lvpw, lvdd, lvds, sv, co, ci, mitral_e, mitral_a, lvot, d_time, e_e_prime]) or any(h in history_list for h in ["心不全", "虚血性心疾患(狭心症・心筋梗塞)", "心房細動", "高血圧"]):
                recommended_pdfs.append(pdf)
        
        # ② 弁膜症
        elif pdf == "valvular_heart.pdf":
            # 逆流が中等度以上、または弁口面積・圧較差に入力がある場合、逸脱ありの場合
            if any(r in ["中等度 (++)", "高度 (+++)"] for r in [ar, mr, pr, tr]) or any(v is not None for v in [as_area, lv_ao_pg, ms_area, la_lv_pg, mva, pht]) or prolapse == "あり (+)":
                recommended_pdfs.append(pdf)
                
        # ③ 動脈硬化・頸部エコー
        elif pdf == "atherosclerosis.pdf":
            if any(h in history_list for h in ["脂質異常症", "高血圧", "2型糖尿病", "閉塞性動脈硬化症(ASO)", "虚血性心疾患(狭心症・心筋梗塞)", "脳卒中・TIA"]) or (ldl is not None and ldl >= 140) or (sys_bp is not None and sys_bp >= 140):
                recommended_pdfs.append(pdf)
        elif pdf == "carotid_echo.pdf":
            # 頸動脈の数値や狭窄評価が入力されている場合
            if any(v is not None for v in [cca_ed_ratio, plaque_score, rt_imt_max, lt_imt_max, rt_cca_vmax, lt_cca_vmax, rt_ica_vmax, lt_ica_vmax]) or stenosis is not None or plaque_echo is not None or any(h in history_list for h in ["脳卒中・TIA", "閉塞性動脈硬化症(ASO)"]):
                recommended_pdfs.append(pdf)
                
        # ④ 脳卒中
        elif pdf == "stroke.pdf":
            if any(h in history_list for h in ["脳卒中・TIA", "心房細動", "高血圧"]) or (stenosis in ["中等度狭窄 (50-69%)", "高度狭窄 (≥70%)"]):
                recommended_pdfs.append(pdf)
                
        # ⑤ CKD (慢性腎臓病)
        elif pdf == "ckd.pdf":
            if any(h in history_list for h in ["慢性腎臓病(CKD)", "高血圧", "2型糖尿病"]) or (egfr is not None and egfr < 60.0) or (cre is not None and cre >= 1.0) or (bun is not None and bun >= 20.0):
                recommended_pdfs.append(pdf)
                
        # ⑥ 肝疾患 (肝硬変・B型肝炎・C型肝炎)
        elif pdf == "liver_cirrhosis.pdf":
            if any(h in history_list for h in ["肝硬変", "B型肝炎", "C型肝炎"]) or (plt is not None and plt <= 15.0) or (alb is not None and alb <= 3.5) or (t_bil is not None and t_bil >= 1.5) or pleural_eff is not None or pe is not None:
                recommended_pdfs.append(pdf)
        elif pdf == "hbv.pdf":
            if "B型肝炎" in history_list or "肝硬変" in history_list or hbs_ag in ["陽性 (+)", "判定保留"] or (hbs_val is not None and hbs_val > 0):
                recommended_pdfs.append(pdf)
        elif pdf == "hcv.pdf":
            if "C型肝炎" in history_list or "肝硬変" in history_list or hcv_ab in ["陽性 (+)", "判定保留"] or (hcv_idx is not None and hcv_idx >= 1.0):
                recommended_pdfs.append(pdf)

    # 該当ルールが一つもない（またはまだ何も入力していない）場合は、デフォルトで最初の3個を選択
    if not recommended_pdfs:
        recommended_pdfs = available_pdfs[:3] if len(available_pdfs) >= 3 else available_pdfs

    # 3. 日本語化＆自動推奨付きのセレクトボックス
    selected_pdfs = st.multiselect(
        "📚 AIに照合させるガイドラインを選択 (複数タップ可能)",
        options=available_pdfs,
        default=list(set(recommended_pdfs)), # 重複を除いてデフォルト設定
        format_func=lambda x: GUIDELINE_MAP.get(x, x) # ←【神機能】ここで英語を日本語に変換！
    )
    
    if recommended_pdfs:
        st.info(f"💡 **AI自動推奨システム稼働中**: ご入力いただいた既往歴や検査数値に基づいて、最適なガイドライン **{len(set(recommended_pdfs))}個** を自動選択しました。")
else:
    selected_pdfs = []
    st.warning("⚠️ guidelinesフォルダ内にPDFファイルが見つかりません。")

# --- 4. アセスメント実行 ---
st.markdown("---")
if st.button("🚀 ガイドラインを照合し病態アセスメントを実行", use_container_width=True, type="primary"):
    if not api_key:
        st.error("⚠️ APIキーが設定されていません。")
    elif not chief_complaint and not history_list:
        st.warning("⚠️ 主訴または既往歴を少なくとも1つ入力・選択してください。")
    elif not selected_pdfs:
        st.warning("⚠️ 参照するガイドラインPDFを少なくとも1つ以上選択してください。")
    elif len(selected_pdfs) > 5:
        st.warning("⚠️ 選択したPDFが多すぎます！容量オーバーを防ぐため、5個以下に絞ることをおすすめします。")
    else:
        with st.spinner(f"📚 選択された {len(selected_pdfs)} 個のガイドラインを視覚解析し、病態生理を推論中..."):
            try:
                client = genai.Client(api_key=api_key)
                
                uploaded_files = []
                for file_name in selected_pdfs:
                    file_path = os.path.join(guidelines_dir, file_name)
                    up_file = client.files.upload(file=file_path)
                    while up_file.state.name == "PROCESSING":
                        time.sleep(2)
                        up_file = client.files.get(name=up_file.name)
                    uploaded_files.append(up_file)
                
                history_str = "、".join(history_list) if history_list else "特記事項なし"
                
                # 未計測項目は fmt() 関数が自動で「未計測/評価なし」の文字に変換します！
                prompt = f"""
                あなたは臨床経験・病態生理の知識が極めて豊富な熟練の医療従事者です。
                添付したPDF（最新の臨床ガイドライン）内の図表・数値・重症度分類・診断基準を正確に参照・照合してください。

                以下の患者の臨床データ（※「未計測/評価なし」となっている項目は今回の検査対象外です。入力された数値を中心に）に基づき、「点と点を結んだ個体性のある総合的な病態生理」を論理的に推論し、詳しく解説してください。

                【患者基本情報】
                ・年齢/性別: {age}歳 {sex} / 血圧: {fmt(sys_bp)}/{fmt(dia_bp)}mmHg / 心拍数: {fmt(hr_val,'bpm')} ({rhythm})
                ・主訴: {chief_complaint}
                ・既往歴・主疾患: {history_str}

                【心臓超音波検査 (Echo)】
                ・AoD・LAD欄: AoD={fmt(aod,'mm')}, LAD={fmt(lad,'mm')}
                ・Mitral valve欄: DDR={fmt(ddr)}, Prolapse={fmt(prolapse)}, SAM={fmt(sam)}
                ・Doppler Measurements Flow Velocity欄: Mitral E={fmt(mitral_e,'m/s')}, Mitral A={fmt(mitral_a,'m/s')}, E/A={fmt(e_a_ratio)}, D-time={fmt(d_time,'ms')}, E/E'={fmt(e_e_prime)}, LVOT={fmt(lvot,'m/s')}
                ・LV size function欄: IVS={fmt(ivs,'mm')}, LVPW={fmt(lvpw,'mm')}, LVDd={fmt(lvdd,'mm')}, LVDs={fmt(lvds,'mm')}, SV={fmt(sv,'mL')}, Co={fmt(co,'L/min')}, CI={fmt(ci)}, HR={fmt(hr_echo,'bpm')}, EF={fmt(ef,'%')}, FS={fmt(fs,'%')}
                ・Regurgitation欄: AR={fmt(ar)}, MR={fmt(mr)}, PR={fmt(pr)}, TR={fmt(tr)}, AS弁口面積={fmt(as_area,'cm2')}, LV-AoPG={fmt(lv_ao_pg,'mmHg')}, MS弁口面積={fmt(ms_area,'cm2')}, LA-LVPG={fmt(la_lv_pg,'mmHg')}, PHT={fmt(pht,'ms')}, MVA={fmt(mva,'cm2')}
                ・その他欄: 心内血栓={fmt(thrombus)}, PE={fmt(pe)}, 呼吸変動={fmt(ivc_resp)}, 胸水={fmt(pleural_eff)}, IVC径={fmt(ivc_diam,'mm')}

                【血液・生化学検査】
                ・推算GFRcreat={fmt(egfr)}, Alb={fmt(alb,'g/dL')}, Hb={fmt(hb,'g/dL')}, CRP={fmt(crp,'mg/dL')}
                ・総蛋白={fmt(tp,'g/dL')}, A/G={fmt(ag_ratio)}, BUN={fmt(bun,'mg/dL')}, Cre={fmt(cre,'mg/dL')}, 尿酸={fmt(ua,'mg/dL')}, 血糖(空腹時)={fmt(fbs,'mg/dL')}, LDL-C={fmt(ldl,'mg/dL')}, HDL-C={fmt(hdl,'mg/dL')}, TG={fmt(tg,'mg/dL')}
                ・総ビリルビン={fmt(t_bil,'mg/dL')}, 直接ビリルビン={fmt(d_bil,'mg/dL')}, AST={fmt(ast,'U/L')}, ALT={fmt(alt,'U/L')}, ALP={fmt(alp,'U/L')}, γ-GT={fmt(ggt,'U/L')}, LD={fmt(ld,'U/L')}, CK={fmt(ck,'U/L')}, アミラーゼ={fmt(amylase,'U/L')}, LAP={fmt(lap,'U/L')}, ChE={fmt(che,'U/L')}
                ・Na={fmt(na,'mEq/L')}, K={fmt(k,'mEq/L')}, Cl={fmt(cl,'mEq/L')}, Ca={fmt(ca,'mg/dL')}, WBC={fmt(wbc,'/μL')}, RBC={fmt(rbc,'万/μL')}, Ht={fmt(ht,'%')}, PLT={fmt(plt,'万/μL')}, MCV={fmt(mcv,'fL')}, MCH={fmt(mch,'pg')}, MCHC={fmt(mchc,'%')}, 好中球={fmt(neutro,'%')}, リンパ球={fmt(lympho,'%')}, 単球={fmt(mono,'%')}, 好酸球={fmt(eosino,'%')}, 好塩基球={fmt(baso,'%')}
                ・RPR={fmt(rpr)}, TP抗体={fmt(tp_ab)}, HBs抗原={fmt(hbs_ag)} (定量値:{fmt(hbs_val,'IU/mL')}), HCV抗体={fmt(hcv_ab)} (IDX:{fmt(hcv_idx)})

                【頸動脈超音波検査 (Carotid Echo)】
                ・CCA ED ratio={fmt(cca_ed_ratio)}, Plaque Score={fmt(plaque_score)}, 所見={fmt(plaque_echo)}, 狭窄度={fmt(stenosis)}
                ・IMT(mm): Rt-CCA平均={fmt(rt_imt_mean)}/最大={fmt(rt_imt_max)}, Lt-CCA平均={fmt(lt_imt_mean)}/最大={lt_imt_max}
                ・Rt-CCA: 径={fmt(rt_cca_diam,'mm')}, Vmax={fmt(rt_cca_vmax)}, Vmin={fmt(rt_cca_vmin)}, Vmean={fmt(rt_cca_vmean)}, PI={fmt(rt_cca_pi)}, RI={fmt(rt_cca_ri)}
                ・Lt-CCA: 径={fmt(lt_cca_diam,'mm')}, Vmax={fmt(lt_cca_vmax)}, Vmin={fmt(lt_cca_vmin)}, Vmean={fmt(lt_cca_vmean)}, PI={fmt(lt_cca_pi)}, RI={fmt(lt_cca_ri)}
                ・Rt-ICA: 径={fmt(rt_ica_diam,'mm')}, Vmax={fmt(rt_ica_vmax)}, Vmin={fmt(rt_ica_vmin)}, Vmean={fmt(rt_ica_vmean)}, PI={fmt(rt_ica_pi)}, RI={fmt(rt_ica_ri)}
                ・Lt-ICA: 径={fmt(lt_ica_diam,'mm')}, Vmax={fmt(lt_ica_vmax)}, Vmin={fmt(lt_ica_vmin)}, Vmean={fmt(lt_ica_vmean)}, PI={fmt(lt_ica_pi)}, RI={fmt(lt_ica_ri)}

                ---
                【出力構成の指示】
                以下の4つの見出し（Markdown）で構成して出力してください。
                ### 1. 総合病態アセスメント（ストーリーとしての病態生理）
                ### 2. ガイドライン基準に照らした重症度・リスク判定
                ### 3. 警戒すべきクリティカルな連鎖・急性増悪リスク
                ### 4. 臨床的介入・観察ケアにおける重点提言
                """
                
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=uploaded_files + [prompt]
                )
                
                st.success("🎉 アセスメント・推論完了！")
                st.markdown(response.text)
                
                for uf in uploaded_files:
                    try:
                        client.files.delete(name=uf.name)
                    except Exception:
                        pass
                
            except Exception as e:
                st.error(f"❌ アセスメント中にエラーが発生しました: {e}")