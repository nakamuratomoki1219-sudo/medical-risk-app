import os
import time
import streamlit as st
from google import genai

# --- ページ設定 ---
st.set_page_config(page_title="臨床リスク・統合アセスメントAI", layout="centered")
st.title("🩺 臨床リスク・統合アセスメント")
st.caption("心エコー・血液・頸部エコーと最新ガイドラインから個体的な病態生理と介入ガイドを推論します。")

# --- APIキーのセットアップ ---
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = st.sidebar.text_input("🔑 Gemini API Key を入力", type="password")

# --- 便利関数 ---
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

# --- 2. 検査データ＆情報の入力 (5タブ構成) ---
st.header("2. 臨床情報・検査データ (未入力欄は空欄でOK)")
tab_echo, tab_blood, tab_carotid, tab_med, tab_rehab = st.tabs([
    "💓 心エコー", "🩸 血液検査", "🩺 頸部エコー", "💊 薬剤情報", "🏃 運動・リハビリ"
])

# =========================================================
# タブ1：心エコー
# =========================================================
with tab_echo:
    st.subheader("心臓超音波検査 (Echo)")
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
# タブ2：血液検査 (現場の検査シート完全準拠・並び替え版)
# =========================================================
with tab_blood:
    st.subheader("🩸 血液・生化学検査")
    with st.expander("➕ 蛋白・腎機能・脂質 (総蛋白, Alb, BUN, Cre, eGFR, 脂質等)", expanded=True):
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            tp = st.number_input("総蛋白 (g/dL)", value=None, placeholder="目安: 7.0", step=0.1)
            ag_ratio = st.number_input("A/G比", value=None, placeholder="目安: 1.5", step=0.05)
            alb = st.number_input("アルブミン Alb (g/dL)", value=None, placeholder="目安: 4.0", step=0.1)
            bun = st.number_input("尿素窒素 BUN (mg/dL)", value=None, placeholder="目安: 15.0", step=1.0)
            cre = st.number_input("クレアチニン (mg/dL)", value=None, placeholder="目安: 0.80", step=0.05)
        with c_b2:
            egfr = st.number_input("推算GFRcreat", value=None, placeholder="目安: 65.0", step=1.0)
            ua = st.number_input("尿酸 (mg/dL)", value=None, placeholder="目安: 5.5", step=0.1)
            ldl = st.number_input("LDLコレステロール (mg/dL)", value=None, placeholder="目安: 110", step=5.0)
            hdl = st.number_input("HDLコレステロール (mg/dL)", value=None, placeholder="目安: 55", step=5.0)
            tg = st.number_input("中性脂肪 (mg/dL)", value=None, placeholder="目安: 120", step=10.0)
            
    with st.expander("➕ 肝機能・酵素・電解質・血糖・炎症 (AST/ALT, 電解質, 血糖, CRP等)"):
        c_b3, c_b4 = st.columns(2)
        with c_b3:
            t_bil = st.number_input("総ビリルビン (mg/dL)", value=None, placeholder="目安: 0.8", step=0.1)
            ast = st.number_input("AST (U/L)", value=None, placeholder="目安: 22", step=1.0)
            alt = st.number_input("ALT (U/L)", value=None, placeholder="目安: 20", step=1.0)
            alp = st.number_input("ALP (U/L)", value=None, placeholder="目安: 180", step=10.0)
            ggt = st.number_input("γ-GT (U/L)", value=None, placeholder="目安: 30", step=5.0)
            ld = st.number_input("LD (U/L)", value=None, placeholder="目安: 180", step=10.0)
            ck = st.number_input("CK (U/L)", value=None, placeholder="目安: 100", step=10.0)
        with c_b4:
            amylase = st.number_input("アミラーゼ (U/L)", value=None, placeholder="目安: 70", step=5.0)
            na = st.number_input("ナトリウム (mEq/L)", value=None, placeholder="目安: 140", step=1.0)
            k = st.number_input("カリウム (mEq/L)", value=None, placeholder="目安: 4.2", step=0.1)
            cl = st.number_input("クロール (mEq/L)", value=None, placeholder="目安: 102", step=1.0)
            ca = st.number_input("カルシウム (mg/dL)", value=None, placeholder="目安: 9.2", step=0.1)
            fbs = st.number_input("血糖 - 空腹時 (mg/dL)", value=None, placeholder="目安: 100", step=5.0)
            crp = st.number_input("CRP定量 / LA (mg/dL)", value=None, placeholder="目安: 0.10", step=0.05)
            
    with st.expander("➕ 血算・白血球像 (WBC, RBC, Hb, Ht, 血小板, 白血球分画)"):
        c_b5, c_b6 = st.columns(2)
        with c_b5:
            wbc = st.number_input("白血球数 (/μL)", value=None, placeholder="目安: 6000", step=100.0)
            rbc = st.number_input("赤血球数 (万/μL)", value=None, placeholder="目安: 430", step=10.0)
            hb = st.number_input("血色素量 Hb (g/dL)", value=None, placeholder="目安: 13.0", step=0.1)
            ht = st.number_input("ヘマトクリット (%)", value=None, placeholder="目安: 40", step=1.0)
            mcv = st.number_input("MCV (fL)", value=None, placeholder="目安: 90", step=1.0)
            mch = st.number_input("MCH (pg)", value=None, placeholder="目安: 30", step=0.5)
            mchc = st.number_input("MCHC (%)", value=None, placeholder="目安: 33", step=0.5)
        with c_b6:
            plt = st.number_input("血小板数 (万/μL)", value=None, placeholder="目安: 22", step=1.0)
            st.markdown("##### 白血球像 (分画 %)")
            baso = st.number_input("好塩基球 (%)", value=None, placeholder="目安: 1.0", step=0.1)
            eosino = st.number_input("好酸球 (%)", value=None, placeholder="目安: 3.0", step=0.5)
            lympho = st.number_input("リンパ球 (%)", value=None, placeholder="目安: 30.0", step=1.0)
            mono = st.number_input("単球 (%)", value=None, placeholder="目安: 6.0", step=0.5)
            neutro = st.number_input("好中球 (%)", value=None, placeholder="目安: 60.0", step=1.0)
            
    with st.expander("➕ 特殊酵素・直接ビリルビン・感染症マーカー (LAP, ChE, 肝炎ウイルス, 梅毒等)"):
        c_b7, c_b8 = st.columns(2)
        with c_b7:
            lap = st.number_input("LAP (U/L)", value=None, placeholder="目安: 40", step=5.0)
            che = st.number_input("ChE (U/L)", value=None, placeholder="目安: 300", step=10.0)
            d_bil = st.number_input("直接ビリルビン (mg/dL)", value=None, placeholder="目安: 0.2", step=0.1)
            rpr = st.selectbox("RPR法 定性", ["陰性 (-)", "陽性 (+)"], index=None, placeholder="選択なし")
            tp_ab = st.selectbox("梅毒TP抗体 定性", ["陰性 (-)", "陽性 (+)"], index=None, placeholder="選択なし")
        with c_b8:
            hbs_ag = st.selectbox("HBs抗原 / CLIA", ["陰性 (-)", "陽性 (+)", "判定保留"], index=None, placeholder="選択なし")
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
# タブ4：薬剤情報 (効果発現時間追加＆「薬→検査」ルート対応)
# =========================================================
with tab_med:
    st.subheader("💊 薬剤情報・リスク管理")
    
    DRUG_GROUPS = [
        "ACE阻害薬 / ARB / ARNI", "β遮断薬", "MRA (ミネラルコルチコイド受容体拮抗薬)",
        "ループ利尿薬 / サイアジド系", "SGLT2阻害薬", "DOAC (直接経口抗凝固薬)",
        "ワルファリン", "抗血小板薬 (アスピリン/クロピドグレル等)", "スタチン / 脂質低下薬", "ジギタリス製剤", "抗不整脈薬", "NSAIDs (解熱鎮痛剤)"
    ]
    if "selected_med_groups" not in st.session_state:
        st.session_state["selected_med_groups"] = []

    with st.expander("🔍 【AI薬剤辞書】複数薬剤のクイック検索 ＆ グループ自動分類", expanded=True):
        st.caption("「、」等で複数の薬名を入力可能。効果発現時間を含むプロファイルを表示し、主要グループへ自動振り分けます。")
        c_srch1, c_srch2 = st.columns([3, 1])
        with c_srch1:
            search_drug_names = st.text_input("検索したい薬剤名を入力 (複数可)", placeholder="例: リクシアナ、ペンライブ、メインテート、ロキソニン等", label_visibility="collapsed")
        with c_srch2:
            btn_drug_search = st.button("🔍 複数検索＆自動分類", use_container_width=True)
            
        if btn_drug_search:
            if not api_key:
                st.error("⚠️ APIキーが設定されていません。")
            elif not search_drug_names:
                st.warning("⚠️ 検索したい薬の名前を入力してください。")
            else:
                with st.spinner(f"🔍 「{search_drug_names}」の薬理プロファイルと発現時間を検索中..."):
                    try:
                        client_search = genai.Client(api_key=api_key)
                        group_list_str = "、".join(DRUG_GROUPS)
                        
                        # 効果発現時間(Tmax等)の出力と、自己補正防止・自動分類プロンプト
                        drug_prompt = f"""
                        あなたは日本国内の医薬品に精通した臨床薬理の専門家および病棟薬剤師です。
                        入力された薬剤リストについて、各薬のプロファイル（効果発現時間を含む）と副作用を簡潔にまとめ、主要薬剤グループへの自動分類を行ってください。

                        入力文字列: 「{search_drug_names}」

                        【🚨 最重要ルール】
                        1. **勝手な名称補正の禁止:** 文字の響きが似ていても別の薬に置き換えないこと。点滴輸液（ペンライブ注等）・注射薬・外用薬も正確に同定すること。
                        2. **効果発現時間の明記:** 「1. 基本プロファイル」の中に、必ず「⏱️ 効果発現・最高血中濃度時間 (内服/投与から効き始める目安・Tmax等)」を明記してください。
                        3. **自動振り分け分類の実行:** 最後に必ず、解説した全薬剤が以下の【分類対象グループ(12選)】のどれに該当するかを判断し、文章の最下部に「【分類結果タグ】: グループ名1, グループ名2...」と出力してください。

                        【分類対象グループ(12選)】
                        {group_list_str}

                        【出力フォーマット例】
                        ### 💊 [入力された薬名 / 一般名]
                        - **基本プロファイル:** [一般名・薬効クラス・主な効能]
                        - **⏱️ 効果発現時間:** [例: 内服後約1〜2時間で最高血中濃度に到達、半減期約10時間]
                        - **主な副作用・警戒点:** [臨床で注意すべき副作用の要点]
                        ---
                        【分類結果タグ】: DOAC (直接経口抗凝固薬), β遮断薬
                        """
                        res_drug = client_search.models.generate_content(model="gemini-3.5-flash", contents=[drug_prompt])
                        response_text = res_drug.text
                        
                        found_groups = []
                        for group in DRUG_GROUPS:
                            if "【分類結果タグ】" in response_text:
                                if group in response_text.split("【分類結果タグ】")[-1]:
                                    found_groups.append(group)
                            elif group in response_text:
                                found_groups.append(group)
                        
                        if found_groups:
                            current_selected = st.session_state.get("selected_med_groups", [])
                            st.session_state["selected_med_groups"] = list(set(current_selected + found_groups))
                            st.success(f"🎯 **自動振り分け成功！** 下部のチェックボックスへ自動登録しました:\n**{', '.join(found_groups)}**")
                        
                        st.markdown(response_text.split("【分類結果タグ】")[0].strip())
                        st.markdown("---")
                    except Exception as e:
                        st.error(f"❌ 検索中でエラーが発生しました: {e}")

    st.markdown("##### 📋 服用中主要薬剤グループの登録")
    meds_list = st.multiselect("服用中の主要薬剤グループ (複数選択可)", options=DRUG_GROUPS, key="selected_med_groups")
    meds_memo = st.text_input("気になる併用薬・用量・直近の変更等があれば記載 (任意)", placeholder="例: 直近でビソプロロール0.625mg開始")
    
    # --- 🚀 【新設：「薬→検査」ルート】ここで直接、薬剤＆リハビリの処方アセスメントを回せる！ ---
    st.markdown("---")
    st.markdown("##### 🚀 薬剤・運動処方アセスメントのダイレクト実行")
    st.caption("※「薬から先に調べたい」方は、ここからボタン1つで現在入力されている検査値（eGFR・K値等）と統合した安全管理・運動ガイドを生成できます！")
    
    if st.button("💊🏃 現在の処方薬・運動情報と検査値を統合して処方・リスクアセスメントを実行", use_container_width=True, type="primary"):
        if not api_key:
            st.error("⚠️ APIキーが設定されていません。")
        elif not meds_list and not meds_memo:
            st.warning("⚠️ 服用薬グループが選択されていないか、メモが空です。薬を検索・選択してください。")
        else:
            with st.spinner("💊🏃 選択された薬剤と現在の検査数値を照合し、リスク管理と運動処方箋を推論中..."):
                try:
                    client_dir = genai.Client(api_key=api_key)
                    # 薬・運動系の必須PDFとCKD・心不全PDFをピックアップして照合
                    dir_pdfs = ["geriatric_meds.pdf", "cardiac_rehab.pdf", "antithrombotic.pdf", "ckd.pdf", "heart_failure.pdf"]
                    up_files_dir = []
                    for fname in dir_pdfs:
                        fpath = os.path.join("guidelines", fname)
                        if os.path.exists(fpath):
                            uf = client_dir.files.upload(file=fpath)
                            while uf.state.name == "PROCESSING":
                                time.sleep(2)
                                uf = client_dir.files.get(name=uf.name)
                            up_files_dir.append(uf)
                    
                    meds_str = "、".join(meds_list) if meds_list else "選択なし"
                    history_str = "、".join(history_list) if history_list else "特記事項なし"
                    
                    prompt_dir = f"""
                    あなたは臨床経験・薬理・リハビリの知識が極めて豊富な医療従事者です。
                    添付ガイドラインを参照し、現在の【服用薬剤・身体機能】と【患者の検査データ（特にeGFRや電解質、心拍数等）】を統合して、安全管理提言と運動処方箋を作成してください。

                    【患者基本・臨床情報】
                    年齢/性別: {age}歳 {sex} / 血圧: {fmt(sys_bp)}/{fmt(dia_bp)} / 心拍数: {fmt(hr_val,'bpm')} ({rhythm}) / 既往歴: {history_str}
                    ・服用薬グループ: {meds_str} / 薬剤メモ: {fmt(meds_memo)}
                    ・ADL: {fmt(adl_status)} / 自覚症状(NYHA): {fmt(nyha)} / フレイル: {fmt(frail_status)} / 歩行・リハビリメモ: {fmt(rehab_memo)}
                    ・重要検査値: eGFR={fmt(egfr)}, K={fmt(k,'mEq/L')}, Na={fmt(na,'mEq/L')}, PLT={fmt(plt,'万/μL')}, Hb={fmt(hb,'g/dL')}, Alb={fmt(alb,'g/dL')}, EF={fmt(ef,'%')}

                    以下の2見出し(Markdown)で実践的に出力してください。
                    ### 1. 💊 薬剤情報からの安全管理・副作用モニタリング提言 (現在の腎機能やK値、用量注意と警戒サイン)
                    ### 2. 🏃 個体別の「運動療法処方箋」と「最警戒・中止基準」
                    """
                    res_dir = client_dir.models.generate_content(model="gemini-3.5-flash", contents=up_files_dir + [prompt_dir])
                    st.success("🎉 薬剤・運動療法のダイレクト統合アセスメント完了！")
                    st.markdown(res_dir.text)
                    for uf in up_files_dir:
                        try: client_dir.files.delete(name=uf.name)
                        except Exception: pass
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {e}")

# =========================================================
# タブ5：運動・リハビリ情報
# =========================================================
with tab_rehab:
    st.subheader("🏃 身体機能・活動耐容能アセスメント")
    c_reh1, c_reh2 = st.columns(2)
    with c_reh1:
        adl_status = st.selectbox("日常生活動作 (ADL)", ["自立", "屋内自立 / 屋外見守り", "歩行見守り・介助要", "車椅子・ベッド上離床中心"], index=None, placeholder="選択してください")
        nyha = st.selectbox("自覚症状 (NYHA分類目安)", ["I度 (身体活動に制限なし)", "II度 (通常の労作で息切れ・疲労)", "III度 (軽労作・平地歩行で息切れ)", "IV度 (安静時にも症状あり)"], index=None, placeholder="選択してください")
    with c_reh2:
        frail_status = st.selectbox("フレイル・サルコペニア評価", ["明らかな低下なし", "プレフレイル疑い", "フレイル / 著明な筋力低下あり"], index=None, placeholder="選択してください")
        rehab_memo = st.text_input("歩行の目安・活動時の症状等 (任意)", placeholder="例: 連続歩行50m程度で下肢疲労と軽度息切れ出現")

# =========================================================
# --- 3. 参照ガイドラインの選択 (トークン超過自動ガード付き！) ---
# =========================================================
st.header("3. 参照・照合するガイドライン")
st.caption("※トークン超過(100万の壁)を防ぐため、一度に照合するPDFは自動的に上限6冊以内に調整されます。")

GUIDELINE_MAP = {
    "echo.pdf": "💓 心エコー", "valvular_heart.pdf": "🫀 弁膜症", "heart_failure.pdf": "📕 心不全",
    "atherosclerosis.pdf": "📙 動脈硬化", "carotid_echo.pdf": "🩺 頸部エコー", "stroke.pdf": "🧠 脳卒中",
    "ckd.pdf": "📗 CKD (慢性腎臓病)", "liver_cirrhosis.pdf": "🟤 肝硬変", "hbv.pdf": "🦠 B型肝炎",
    "hcv.pdf": "🦠 C型肝炎", "cardiac_rehab.pdf": "🏃 心血管疾患リハビリ", "geriatric_meds.pdf": "💊 高齢者薬物療法", "antithrombotic.pdf": "💊 抗血栓療法"
}

available_pdfs = []
if os.path.exists("guidelines"):
    available_pdfs = [f for f in os.listdir("guidelines") if f.endswith(".pdf")]

if available_pdfs:
    recommended_pdfs = []
    for pdf in available_pdfs:
        if pdf == "heart_failure.pdf" and (any(h in history_list for h in ["心不全", "虚血性心疾患(狭心症・心筋梗塞)", "心房細動"]) or (ef is not None and ef < 50.0)): recommended_pdfs.append(pdf)
        elif pdf == "echo.pdf" and any(v is not None for v in [ef, aod, lad, ivs, lvpw, lvdd, lvds, sv, co, ci]): recommended_pdfs.append(pdf)
        elif pdf == "valvular_heart.pdf" and any(r in ["中等度 (++)", "高度 (+++)"] for r in [ar, mr, pr, tr]): recommended_pdfs.append(pdf)
        elif pdf == "atherosclerosis.pdf" and any(h in history_list for h in ["脂質異常症", "高血圧", "2型糖尿病"]): recommended_pdfs.append(pdf)
        elif pdf == "carotid_echo.pdf" and (any(v is not None for v in [cca_ed_ratio, plaque_score]) or stenosis is not None): recommended_pdfs.append(pdf)
        elif pdf == "stroke.pdf" and any(h in history_list for h in ["脳卒中・TIA", "心房細動"]): recommended_pdfs.append(pdf)
        elif pdf == "ckd.pdf" and (any(h in history_list for h in ["慢性腎臓病(CKD)", "高血圧", "2型糖尿病"]) or (egfr is not None and egfr < 60.0)): recommended_pdfs.append(pdf)
        elif pdf == "liver_cirrhosis.pdf" and any(h in history_list for h in ["肝硬変", "B型肝炎", "C型肝炎"]): recommended_pdfs.append(pdf)
        elif pdf == "cardiac_rehab.pdf" and (adl_status is not None or nyha is not None): recommended_pdfs.append(pdf)
        elif pdf == "geriatric_meds.pdf" and (age >= 65 or len(meds_list) > 0): recommended_pdfs.append(pdf)
        elif pdf == "antithrombotic.pdf" and any(m in meds_list for m in ["DOAC (直接経口抗凝固薬)", "ワルファリン"]): recommended_pdfs.append(pdf)

    if not recommended_pdfs: recommended_pdfs = available_pdfs[:3]
    # トークン超過を防ぐため推奨自体も最大5冊に絞る
    recommended_pdfs = list(set(recommended_pdfs))[:5]

    selected_pdfs = st.multiselect("📚 照合させるガイドラインを選択 (最大6冊推奨)", options=available_pdfs, default=recommended_pdfs, format_func=lambda x: GUIDELINE_MAP.get(x, x))
else:
    selected_pdfs = []

# =========================================================
# --- 4. 統合アセスメント実行 (トークン自動調整・安全ガードつき) ---
# =========================================================
st.markdown("---")
st.header("4. 統合アセスメント実行")

# 【「検査→薬」ルート】従来の病態生理アセスメント
if st.button("🚀 Step 1: 病態生理・リスクアセスメントを実行", use_container_width=True, type="primary"):
    if not api_key: st.error("⚠️ APIキーが設定されていません。")
    elif not chief_complaint and not history_list: st.warning("⚠️ 主訴または既往歴を1つ以上選択してください。")
    elif not selected_pdfs: st.warning("⚠️ 参照PDFを1つ以上選択してください。")
    else:
        # 🚨 【100万トークンの壁・自動防御システム】万が一ユーザーが7冊以上選んでいても勝手に上位6冊に絞ってエラーを100%防ぐ！
        safe_pdfs = selected_pdfs[:6]
        if len(selected_pdfs) > 6:
            st.warning(f"⚠️ 選択されたPDFが {len(selected_pdfs)}冊 と多すぎるため、容量超過(100万トークンエラー)を防ぐ目的で、優先度の高い上位6冊に自動絞り込みして推論を実行します。")
            
        with st.spinner(f"📚 {len(safe_pdfs)}冊のガイドラインを視覚解析し、病態生理を推論中..."):
            try:
                client = genai.Client(api_key=api_key)
                uploaded_files = []
                for fname in safe_pdfs:
                    fpath = os.path.join("guidelines", fname)
                    if os.path.exists(fpath):
                        uf = client.files.upload(file=fpath)
                        while uf.state.name == "PROCESSING":
                            time.sleep(2)
                            uf = client.files.get(name=uf.name)
                        uploaded_files.append(uf)
                
                history_str = "、".join(history_list) if history_list else "特記事項なし"
                prompt_step1 = f"""
                あなたは経験豊富な専門医です。添付PDFを参照し、以下のデータから「個別の病態生理ストーリー」を推論してください。

                【基本情報】年齢/性別: {age}歳 {sex} / 血圧: {fmt(sys_bp)}/{fmt(dia_bp)} / HR: {fmt(hr_val,'bpm')} ({rhythm}) / 主訴: {chief_complaint} / 既往歴: {history_str}
                【心エコー】AoD={fmt(aod,'mm')}, LAD={fmt(lad,'mm')}, DDR={fmt(ddr)}, Mitral E={fmt(mitral_e,'m/s')}, Mitral A={fmt(mitral_a,'m/s')}, E/E'={fmt(e_e_prime)}, LVOT={fmt(lvot,'m/s')}, IVS={fmt(ivs,'mm')}, LVPW={fmt(lvpw,'mm')}, LVDd={fmt(lvdd,'mm')}, LVDs={fmt(lvds,'mm')}, SV={fmt(sv,'mL')}, Co={fmt(co,'L/min')}, CI={fmt(ci)}, EF={fmt(ef,'%')}, AR={fmt(ar)}, MR={fmt(mr)}, TR={fmt(tr)}, AS弁口面積={fmt(as_area,'cm2')}, IVC径={fmt(ivc_diam,'mm')}
                【血液・生化学検査】総蛋白={fmt(tp,'g/dL')}, A/G={fmt(ag_ratio)}, Alb={fmt(alb,'g/dL')}, BUN={fmt(bun,'mg/dL')}, Cre={fmt(cre,'mg/dL')}, eGFR={fmt(egfr)}, 尿酸={fmt(ua,'mg/dL')}, LDL={fmt(ldl,'mg/dL')}, HDL={fmt(hdl,'mg/dL')}, TG={fmt(tg,'mg/dL')}, T-Bil={fmt(t_bil,'mg/dL')}, AST={fmt(ast,'U/L')}, ALT={fmt(alt,'U/L')}, ALP={fmt(alp,'U/L')}, γ-GT={fmt(ggt,'U/L')}, LD={fmt(ld,'U/L')}, CK={fmt(ck,'U/L')}, アミラーゼ={fmt(amylase,'U/L')}, Na={fmt(na,'mEq/L')}, K={fmt(k,'mEq/L')}, Cl={fmt(cl,'mEq/L')}, Ca={fmt(ca,'mg/dL')}, 血糖(空腹時)={fmt(fbs,'mg/dL')}, CRP={fmt(crp,'mg/dL')}, WBC={fmt(wbc,'/μL')}, RBC={fmt(rbc,'万/μL')}, Hb={fmt(hb,'g/dL')}, Ht={fmt(ht,'%')}, MCV={fmt(mcv,'fL')}, MCH={fmt(mch,'pg')}, MCHC={fmt(mchc,'%')}, PLT={fmt(plt,'万/μL')}, 好塩基球={fmt(baso,'%')}, 好酸球={fmt(eosino,'%')}, リンパ球={fmt(lympho,'%')}, 単球={fmt(mono,'%')}, 好中球={fmt(neutro,'%')}, LAP={fmt(lap,'U/L')}, ChE={fmt(che,'U/L')}, D-Bil={fmt(d_bil,'mg/dL')}, RPR={fmt(rpr)}, TP抗体={fmt(tp_ab)}, HBs抗原={fmt(hbs_ag)} (定量値:{fmt(hbs_val,'IU/mL')}), HCV抗体={fmt(hcv_ab)} (IDX/Unit:{fmt(hcv_idx)})
                【頸部エコー】CCA ED ratio={fmt(cca_ed_ratio)}, Plaque Score={fmt(plaque_score)}, 狭窄度={fmt(stenosis)}, Rt-IMT最大={fmt(rt_imt_max)}, Lt-IMT最大={fmt(lt_imt_max)}, Rt-ICA Vmax={fmt(rt_ica_vmax)}, Lt-ICA Vmax={fmt(lt_ica_vmax)}

                以下の3見出し(Markdown)で出力してください。
                ### 1. 総合病態アセスメント（ストーリーとしての病態生理）
                ### 2. ガイドライン基準に照らした重症度・リスク判定
                ### 3. 警戒すべきクリティカルな連鎖・急性増悪リスク
                """
                res1 = client.models.generate_content(model="gemini-3.5-flash", contents=uploaded_files + [prompt_step1])
                st.session_state["step1_result"] = res1.text
                for uf in uploaded_files:
                    try: client.files.delete(name=uf.name)
                    except Exception: pass
            except Exception as e: st.error(f"❌ Step1でエラーが発生しました: {e}")

if "step1_result" in st.session_state:
    st.success("🎉 Step 1: 病態生理・リスクアセスメント完了！")
    st.markdown(st.session_state["step1_result"])
    st.markdown("---")
    
    st.subheader("💊🏃 Step 2: 上記の病態を引き継いだ『薬剤リスク管理＆運動処方ガイド』")
    if st.button("👉 Step 2: この病態を元に『薬剤＆運動処方ガイド』を追加生成する", use_container_width=True):
        with st.spinner("💊🏃 病態を引き継ぎ、処方薬リスクと運動メニューを推論中..."):
            try:
                client = genai.Client(api_key=api_key)
                # Step2では治療・介入系を中心に安全な5冊に固定！これで容量オーバーゼロ！
                step2_pdfs = ["cardiac_rehab.pdf", "geriatric_meds.pdf", "antithrombotic.pdf", "heart_failure.pdf", "ckd.pdf"]
                up_files2 = []
                for fname in step2_pdfs:
                    fpath = os.path.join("guidelines", fname)
                    if os.path.exists(fpath):
                        uf = client.files.upload(file=fpath)
                        while uf.state.name == "PROCESSING":
                            time.sleep(2)
                            uf = client.files.get(name=uf.name)
                        up_files2.append(uf)
                
                meds_str = "、".join(meds_list) if meds_list else "選択なし"
                prompt2 = f"""
                あなたは臨床専門医および認定リハビリ専門職です。添付ガイドラインを参照し、【Step1の病態アセスメント】と【薬剤・身体情報】を統合して実践的な処方ガイドを作成してください。
                【Step 1 病態生理】\n{st.session_state["step1_result"]}\n---
                【患者の薬剤・身体機能】年齢/性別: {age}歳 {sex} / eGFR: {fmt(egfr)} / K: {fmt(k,'mEq/L')} / PLT: {fmt(plt,'万/μL')} / 服用薬: {meds_str} / 薬メモ: {fmt(meds_memo)} / ADL: {fmt(adl_status)} / NYHA: {fmt(nyha)} / フレイル: {fmt(frail_status)} / リハビリメモ: {fmt(rehab_memo)}

                以下の2見出し(Markdown)で出力してください。
                ### 1. 💊 薬剤情報からの安全管理・副作用モニタリング提言 (用量注意・電解質・ふらつき・出血サイン)
                ### 2. 🏃 個体的な病態に即した「運動療法処方箋」と「最警戒・中止基準」
                """
                res2 = client.models.generate_content(model="gemini-3.5-flash", contents=up_files2 + [prompt2])
                st.success("🎉 Step 2: 薬剤・運動療法の統合処方ガイド完成！")
                st.markdown(res2.text)
                for uf in up_files2:
                    try: client.files.delete(name=uf.name)
                    except Exception: pass
            except Exception as e: st.error(f"❌ Step2でエラーが発生しました: {e}")