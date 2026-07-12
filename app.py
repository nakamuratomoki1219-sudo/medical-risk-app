import os
import time
import streamlit as st
from google import genai

# --- ページ設定（スマホで見やすいレイアウト） ---
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

# --- 1. 基本情報の入力 ---
st.header("1. 患者基本情報")
col_base1, col_base2 = st.columns(2)
with col_base1:
    age = st.number_input("年齢", value=75, step=1)
    sex = st.selectbox("性別", ["男性", "女性"])
with col_base2:
    sys_bp = st.number_input("収縮期血圧 (mmHg)", value=130, step=1)
    dia_bp = st.number_input("拡張期血圧 (mmHg)", value=75, step=1)

hr_val = st.number_input("心拍数 (bpm)", value=68, step=1)
rhythm = st.selectbox("心拍リズム", ["整", "不整 (心房細動など)", "ペースメーカー"])

chief_complaint = st.text_input("主訴・現在の症状 (※ここだけ簡潔に文字入力)", placeholder="例: 労作時の息切れ、ふらつき")
history_list = st.multiselect(
    "既往歴・主疾患 (該当するものをタップで複数選択)",
    ["高血圧", "2型糖尿病", "脂質異常症", "慢性腎臓病(CKD)", "虚血性心疾患(狭心症・心筋梗塞)", "心不全", "脳卒中・TIA", "心房細動", "閉塞性動脈硬化症(ASO)", "B型肝炎", "C型肝炎", "肝硬変"]
)

# --- 2. 検査データの入力 ---
st.header("2. 検査データ (数値＆選択式)")
tab_echo, tab_blood, tab_carotid = st.tabs(["💓 心エコー", "🩸 血液検査", "🩺 頸部エコー"])

# =========================================================
# タブ1：心エコー（全項目数値＆選択化）
# =========================================================
with tab_echo:
    st.subheader("心臓超音波検査 (Echo)")
    st.caption("必要な箇所の数値を入力・選択してください（未計測・不明は0のままで構いません）。")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        ef = st.number_input("EF (% - 駆出率)", value=60.0, step=1.0)
        e_val = st.number_input("Mitral E (cm/s)", value=70.0, step=1.0)
    with col_e2:
        e_prime = st.number_input("E' (cm/s)", value=8.0, step=0.5)
        e_e_prime = st.number_input("E/E'", value=8.8, step=0.1)
    
    with st.expander("➕ 形態計測・収縮機能 (AoD, LVDd/s, FS, SV, CI等)"):
        c1, c2 = st.columns(2)
        with c1:
            aod = st.number_input("AoD (mm)", value=30.0, step=1.0)
            lad = st.number_input("LAD (mm)", value=35.0, step=1.0)
            ivs = st.number_input("IVS Thickness (mm)", value=10.0, step=0.5)
            lvpw = st.number_input("LVPW Thickness (mm)", value=10.0, step=0.5)
            fs = st.number_input("FS (%)", value=35.0, step=1.0)
        with c2:
            lvdd = st.number_input("LVDd (mm)", value=45.0, step=1.0)
            lvds = st.number_input("LVDs (mm)", value=30.0, step=1.0)
            sv = st.number_input("SV - 一回拍出量 (mL)", value=60.0, step=1.0)
            co = st.number_input("Co - 心拍出量 (L/min)", value=4.5, step=0.1)
            ci = st.number_input("CI - 心係数 (L/min/m²)", value=2.5, step=0.1)
    
    with st.expander("➕ 僧帽弁・ドップラー速度 (Mitral A, E/A, D-time, LVOT等)"):
        c3, c4 = st.columns(2)
        with c3:
            mitral_a = st.number_input("Mitral A (cm/s)", value=60.0, step=1.0)
            e_a_ratio = st.number_input("E/A ratio", value=1.1, step=0.05)
            d_time = st.number_input("D-time (ms)", value=180.0, step=5.0)
            lvot = st.number_input("LVOT velocity (m/s)", value=1.0, step=0.1)
        with c4:
            ddr = st.selectbox("Mitral valve DDR", ["正常・良好", "低下", "著明低下", "評価なし"])
            prolapse = st.selectbox("Prolapse (逸脱)", ["なし (-)", "あり (+)"])
            sam = st.selectbox("SAM (収縮期前方運動)", ["なし (-)", "あり (+)"])
            
    with st.expander("➕ 弁膜症評価 (AR, MR, AS/MS弁口面積, PG, PHT等)"):
        c5, c6 = st.columns(2)
        with c5:
            ar = st.selectbox("AR (大動脈弁逆流)", ["なし/極軽度", "軽度 (I度)", "中等度 (II度)", "高度 (III度〜)"])
            mr = st.selectbox("MR (僧帽弁逆流)", ["なし/極軽度", "軽度 (I度)", "中等度 (II度)", "高度 (III度〜)"])
            pr = st.selectbox("PR (肺動脈弁逆流)", ["なし/極軽度", "軽度", "中等度", "高度"])
            tr = st.selectbox("TR (三尖弁逆流)", ["なし/極軽度", "軽度", "中等度", "高度"])
            pht = st.number_input("PHT (ms)", value=0.0, step=10.0)
        with c6:
            as_area = st.number_input("AS弁口面積 (cm²)", value=0.0, step=0.1)
            lv_ao_pg = st.number_input("LV-Ao PG max (mmHg)", value=0.0, step=1.0)
            ms_area = st.number_input("MS弁口面積 (cm²)", value=0.0, step=0.1)
            la_lv_pg = st.number_input("LA-LV PG max (mmHg)", value=0.0, step=1.0)
            mva = st.number_input("MVA (cm²)", value=0.0, step=0.1)
            
    with st.expander("➕ その他心エコー所見 (血栓, 心嚢液, IVC径等)"):
        c7, c8 = st.columns(2)
        with c7:
            thrombus = st.selectbox("心内血栓", ["なし (-)", "あり (+)"])
            pe = st.selectbox("PE (心嚢液/心嚢水腫)", ["なし (-)", "軽度", "中等度〜高度"])
            pleural_eff = st.selectbox("胸水", ["なし (-)", "右のみ", "左のみ", "両側あり"])
        with c8:
            ivc_diam = st.number_input("IVC径 (mm)", value=14.0, step=1.0)
            ivc_resp = st.selectbox("IVC呼吸変動", ["良好 (>50%短縮)", "低下 (≤50%短縮)", "消失 (非変動)"])

# =========================================================
# タブ2：血液検査（全項目数値＆選択化）
# =========================================================
with tab_blood:
    st.subheader("血液・生化学検査")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        egfr = st.number_input("推算GFRcreat", value=65.0, step=1.0)
        alb = st.number_input("アルブミン (Alb - g/dL)", value=4.0, step=0.1)
    with col_b2:
        hb = st.number_input("血色素量 (Hb - g/dL)", value=13.0, step=0.1)
        crp = st.number_input("CRP定量 / LA (mg/dL)", value=0.10, step=0.05)
        
    with st.expander("➕ 腎機能・代謝・脂質 (BUN, Cre, 尿酸, 血糖, LDL, HDL, TG等)"):
        c9, c10 = st.columns(2)
        with c9:
            tp = st.number_input("総蛋白 (g/dL)", value=7.0, step=0.1)
            ag_ratio = st.number_input("A/G比", value=1.5, step=0.05)
            bun = st.number_input("尿素窒素 (BUN - mg/dL)", value=15.0, step=1.0)
            cre = st.number_input("クレアチニン (mg/dL)", value=0.80, step=0.05)
            ua = st.number_input("尿酸 (mg/dL)", value=5.5, step=0.1)
        with c10:
            fbs = st.number_input("血糖 (空腹時 - mg/dL)", value=100.0, step=5.0)
            ldl = st.number_input("LDLコレステロール (mg/dL)", value=110.0, step=5.0)
            hdl = st.number_input("HDLコレステロール (mg/dL)", value=55.0, step=5.0)
            tg = st.number_input("中性脂肪 (mg/dL)", value=120.0, step=10.0)
            
    with st.expander("➕ 肝胆道・膵・酵素 (AST, ALT, γ-GT, ビリルビン等)"):
        c11, c12 = st.columns(2)
        with c11:
            t_bil = st.number_input("総ビリルビン (mg/dL)", value=0.8, step=0.1)
            d_bil = st.number_input("直接ビリルビン (mg/dL)", value=0.2, step=0.1)
            ast = st.number_input("AST (U/L)", value=22.0, step=1.0)
            alt = st.number_input("ALT (U/L)", value=20.0, step=1.0)
            alp = st.number_input("ALP (U/L)", value=180.0, step=10.0)
            ggt = st.number_input("γ-GT (U/L)", value=30.0, step=5.0)
        with c12:
            ld = st.number_input("LD (U/L)", value=180.0, step=10.0)
            ck = st.number_input("CK (U/L)", value=100.0, step=10.0)
            amylase = st.number_input("アミラーゼ (U/L)", value=70.0, step=5.0)
            lap = st.number_input("LAP (U/L)", value=40.0, step=5.0)
            che = st.number_input("ChE (U/L)", value=300.0, step=10.0)
            
    with st.expander("➕ 血算・電解質・白血球分画 (RBC, WBC, 電解質, 好中球/リンパ等)"):
        c13, c14 = st.columns(2)
        with c13:
            na = st.number_input("ナトリウム (mEq/L)", value=140.0, step=1.0)
            k = st.number_input("カリウム (mEq/L)", value=4.2, step=0.1)
            cl = st.number_input("クロール (mEq/L)", value=102.0, step=1.0)
            ca = st.number_input("カルシウム (mg/dL)", value=9.2, step=0.1)
            wbc = st.number_input("白血球数 (/μL)", value=6000.0, step=100.0)
            rbc = st.number_input("赤血球数 (万/μL)", value=430.0, step=10.0)
            ht = st.number_input("ヘマトクリット (%)", value=40.0, step=1.0)
            plt = st.number_input("血小板数 (万/μL)", value=22.0, step=1.0)
        with c14:
            mcv = st.number_input("MCV (fL)", value=90.0, step=1.0)
            mch = st.number_input("MCH (pg)", value=30.0, step=0.5)
            mchc = st.number_input("MCHC (%)", value=33.0, step=0.5)
            neutro = st.number_input("好中球 (%)", value=60.0, step=1.0)
            lympho = st.number_input("リンパ球 (%)", value=30.0, step=1.0)
            mono = st.number_input("単球 (%)", value=6.0, step=0.5)
            eosino = st.number_input("好酸球 (%)", value=3.0, step=0.5)
            baso = st.number_input("好塩基球 (%)", value=1.0, step=0.1)
            
    with st.expander("➕ 感染症・血清学・ウイルスマーカー (HBs, HCV, 梅毒等)"):
        c15, c16 = st.columns(2)
        with c15:
            rpr = st.selectbox("RPR法 定性", ["陰性 (-)", "陽性 (+)"])
            tp_ab = st.selectbox("梅毒TP抗体 定性", ["陰性 (-)", "陽性 (+)"])
            hbs_ag = st.selectbox("HBs抗原 / CLIA", ["陰性 (-)", "陽性 (+)", "判定保留"])
        with c16:
            hbs_val = st.number_input("HBs抗原 定量値 (IU/mL ※陽性時等)", value=0.00, step=0.01)
            hcv_ab = st.selectbox("HCV抗体 3rd", ["陰性 (-)", "陽性 (+)", "判定保留"])
            hcv_idx = st.number_input("HCV抗体 インデックス/ユニット", value=0.1, step=0.1)

# =========================================================
# タブ3：頸部エコー（全項目数値＆選択化）
# =========================================================
with tab_carotid:
    st.subheader("頸動脈超音波検査")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cca_ed_ratio = st.number_input("CCA ED ratio (拡張末期血流比)", value=1.0, step=0.05)
        plaque_score = st.number_input("Plaque Score (プラークスコア)", value=1.5, step=0.5)
    with col_c2:
        plaque_echo = st.selectbox("プラーク性状・動脈硬化所見", ["明らかなプラークなし", "等輝度・均質 (安定)", "低輝度・不均質 (不安定・可動性疑い)", "石灰化・高輝度プラーク"])
        stenosis = st.selectbox("狭窄度評価", ["明らかな狭窄なし (<30%)", "軽度狭窄 (30-49%)", "中等度狭窄 (50-69%)", "高度狭窄 (≥70%)"])

    with st.expander("➕ CCA IMT (内中膜複合体厚) 平均・最大"):
        c17, c18 = st.columns(2)
        with c17:
            rt_imt_mean = st.number_input("Rt-CCA IMT 平均 (mm)", value=0.7, step=0.05)
            rt_imt_max = st.number_input("Rt-CCA IMT 最大 (mm)", value=0.8, step=0.05)
        with c18:
            lt_imt_mean = st.number_input("Lt-CCA IMT 平均 (mm)", value=0.7, step=0.05)
            lt_imt_max = st.number_input("Lt-CCA IMT 最大 (mm)", value=0.8, step=0.05)

    with st.expander("➕ Rt-CCA (右総頸動脈) パラメータ"):
        c19, c20 = st.columns(2)
        with c19:
            rt_cca_diam = st.number_input("Rt-CCA 血管径 (mm)", value=7.0, step=0.1)
            rt_cca_vmax = st.number_input("Rt-CCA 最高血流速度 Vmax (cm/s)", value=65.0, step=1.0)
            rt_cca_vmin = st.number_input("Rt-CCA 最低血流速度 Vmin (cm/s)", value=20.0, step=1.0)
        with c20:
            rt_cca_vmean = st.number_input("Rt-CCA 平均血流速度 Vmean (cm/s)", value=35.0, step=1.0)
            rt_cca_pi = st.number_input("Rt-CCA PI", value=1.25, step=0.05)
            rt_cca_ri = st.number_input("Rt-CCA RI", value=0.68, step=0.02)

    with st.expander("➕ Lt-CCA (左総頸動脈) パラメータ"):
        c21, c22 = st.columns(2)
        with c21:
            lt_cca_diam = st.number_input("Lt-CCA 血管径 (mm)", value=6.8, step=0.1)
            lt_cca_vmax = st.number_input("Lt-CCA 最高血流速度 Vmax (cm/s)", value=62.0, step=1.0)
            lt_cca_vmin = st.number_input("Lt-CCA 最低血流速度 Vmin (cm/s)", value=18.0, step=1.0)
        with c22:
            lt_cca_vmean = st.number_input("Lt-CCA 平均血流速度 Vmean (cm/s)", value=33.0, step=1.0)
            lt_cca_pi = st.number_input("Lt-CCA PI", value=1.30, step=0.05)
            lt_cca_ri = st.number_input("Lt-CCA RI", value=0.70, step=0.02)

    with st.expander("➕ Rt-ICA / Lt-ICA (右/左内頸動脈) パラメータ"):
        c23, c24 = st.columns(2)
        with c23:
            st.markdown("##### Rt-ICA (右内頸動脈)")
            rt_ica_diam = st.number_input("Rt-ICA 血管径 (mm)", value=4.8, step=0.1)
            rt_ica_vmax = st.number_input("Rt-ICA Vmax (cm/s)", value=80.0, step=1.0)
            rt_ica_vmin = st.number_input("Rt-ICA Vmin (cm/s)", value=28.0, step=1.0)
            rt_ica_vmean = st.number_input("Rt-ICA Vmean (cm/s)", value=45.0, step=1.0)
            rt_ica_pi = st.number_input("Rt-ICA PI", value=1.15, step=0.05)
            rt_ica_ri = st.number_input("Rt-ICA RI", value=0.65, step=0.02)
        with c24:
            st.markdown("##### Lt-ICA (左内頸動脈)")
            lt_ica_diam = st.number_input("Lt-ICA 血管径 (mm)", value=4.6, step=0.1)
            lt_ica_vmax = st.number_input("Lt-ICA Vmax (cm/s)", value=78.0, step=1.0)
            lt_ica_vmin = st.number_input("Lt-ICA Vmin (cm/s)", value=26.0, step=1.0)
            lt_ica_vmean = st.number_input("Lt-ICA Vmean (cm/s)", value=43.0, step=1.0)
            lt_ica_pi = st.number_input("Lt-ICA PI", value=1.16, step=0.05)
            lt_ica_ri = st.number_input("Lt-ICA RI", value=0.66, step=0.02)

# --- 3. アセスメント実行 ---
st.markdown("---")
if st.button("🚀 ガイドラインを照合し病態アセスメントを実行", use_container_width=True, type="primary"):
    if not api_key:
        st.error("⚠️ APIキーが設定されていません。画面左側のサイドバーに入力するか、Secretsを設定してください。")
    elif not chief_complaint and not history_list:
        st.warning("⚠️ 主訴または既往歴を少なくとも1つ入力・選択してください。")
    else:
        with st.spinner("📚 10の最新ガイドライン(PDF)を視覚解析し、病態生理を統合推論中... (1〜2分ほどかかります)"):
            try:
                client = genai.Client(api_key=api_key)
                
                # ガイドラインPDFの自動アップロード
                uploaded_files = []
                guidelines_dir = "guidelines"
                
                if os.path.exists(guidelines_dir):
                    pdf_list = [f for f in os.listdir(guidelines_dir) if f.endswith(".pdf")]
                    st.info(f"📂 {len(pdf_list)}個のガイドラインPDFをAIへ送信中...")
                    
                    for file_name in pdf_list:
                        file_path = os.path.join(guidelines_dir, file_name)
                        up_file = client.files.upload(file=file_path)
                        while up_file.state.name == "PROCESSING":
                            time.sleep(2)
                            up_file = client.files.get(name=up_file.name)
                        uploaded_files.append(up_file)
                
                # 既往歴リストを文字列に変換
                history_str = "、".join(history_list) if history_list else "特記事項なし"
                
                # AIへ送信する「全項目網羅プロンプト」
                prompt = f"""
                あなたは臨床経験・病態生理の知識が極めて豊富な熟練の医療従事者（専門医・認定臨床専門職）です。
                添付したPDF（最新の各種臨床ガイドライン等）内の図表・数値・重症度分類・診断基準を画像認識により正確に参照・照合してください。

                以下の患者の完全な臨床検査データに基づき、単なる項目ごとの解説ではなく、「点と点を結んだ個体性のある総合的な病態生理（体内で何が起きているか、複合的な疾患連鎖や将来リスクは何か）」を論理的に推論し、詳しく解説してください。

                【患者基本情報】
                ・年齢/性別: {age}歳 {sex} / 血圧: {sys_bp}/{dia_bp}mmHg / 心拍数: {hr_val}bpm ({rhythm})
                ・主訴: {chief_complaint}
                ・既往歴・主疾患: {history_str}

                【心臓超音波検査 (Echo)】
                ・主要指標: EF={ef}%, Mitral E={e_val}cm/s, E'={e_prime}cm/s, E/E'={e_e_prime}
                ・形態計測/収縮: AoD={aod}mm, LAD={lad}mm, IVS={ivs}mm, LVPW={lvpw}mm, LVDd={lvdd}mm, LVDs={lvds}mm, FS={fs}%, SV={sv}mL, Co={co}L/min, CI={ci}
                ・僧帽弁/ドップラー: Mitral A={mitral_a}cm/s, E/A={e_a_ratio}, D-time={d_time}ms, LVOT={lvot}m/s, DDR={ddr}, Prolapse={prolapse}, SAM={sam}
                ・弁膜症評価: AR={ar}, MR={mr}, PR={pr}, TR={tr}, PHT={pht}ms, AS弁口面積={as_area}cm2, LV-AoPG max={lv_ao_pg}mmHg, MS弁口面積={ms_area}cm2, LA-LVPG max={la_lv_pg}mmHg, MVA={mva}cm2
                ・その他: 心内血栓={thrombus}, PE(心嚢液)={pe}, 胸水={pleural_eff}, IVC径={ivc_diam}mm, IVC呼吸変動={ivc_resp}

                【血液・生化学検査】
                ・主要指標: 推算GFRcreat={egfr}, Alb={alb}g/dL, Hb={hb}g/dL, CRP={crp}mg/dL
                ・腎機能/代謝/脂質: 総蛋白={tp}g/dL, A/G={ag_ratio}, BUN={bun}mg/dL, Cre={cre}mg/dL, 尿酸={ua}mg/dL, 空腹時血糖={fbs}mg/dL, LDL-C={ldl}mg/dL, HDL-C={hdl}mg/dL, TG={tg}mg/dL
                ・肝胆道/酵素: 総ビリルビン={t_bil}mg/dL, 直接ビリルビン={d_bil}mg/dL, AST={ast}U/L, ALT={alt}U/L, ALP={alp}U/L, γ-GT={ggt}U/L, LD={ld}U/L, CK={ck}U/L, アミラーゼ={amylase}U/L, LAP={lap}U/L, ChE={che}U/L
                ・血算/電解質/白血球像: Na={na}mEq/L, K={k}mEq/L, Cl={cl}mEq/L, Ca={ca}mg/dL, WBC={wbc}/μL, RBC={rbc}万/μL, Ht={ht}%, PLT={plt}万/μL, MCV={mcv}fL, MCH={mch}pg, MCHC={mchc}%, 好中球={neutro}%, リンパ球={lympho}%, 単球={mono}%, 好酸球={eosino}%, 好塩基球={baso}%
                ・血清学/ウイルス: RPR={rpr}, TP抗体={tp_ab}, HBs抗原={hbs_ag} (定量値:{hbs_val}IU/mL), HCV抗体={hcv_ab} (IDX:{hcv_idx})

                【頸動脈超音波検査 (Carotid Echo)】
                ・総合指標: CCA ED ratio={cca_ed_ratio}, Plaque Score={plaque_score}, 所見={plaque_echo}, 狭窄度={stenosis}
                ・IMT(mm): Rt-CCA平均={rt_imt_mean}/最大={rt_imt_max}, Lt-CCA平均={lt_imt_mean}/最大={lt_imt_max}
                ・Rt-CCA: 径={rt_cca_diam}mm, Vmax={rt_cca_vmax}, Vmin={rt_cca_vmin}, Vmean={rt_cca_vmean}, PI={rt_cca_pi}, RI={rt_cca_ri}
                ・Lt-CCA: 径={lt_cca_diam}mm, Vmax={lt_cca_vmax}, Vmin={lt_cca_vmin}, Vmean={lt_cca_vmean}, PI={lt_cca_pi}, RI={lt_cca_ri}
                ・Rt-ICA: 径={rt_ica_diam}mm, Vmax={rt_ica_vmax}, Vmin={rt_ica_vmin}, Vmean={rt_ica_vmean}, PI={rt_ica_pi}, RI={rt_ica_ri}
                ・Lt-ICA: 径={lt_ica_diam}mm, Vmax={lt_ica_vmax}, Vmin={lt_ica_vmin}, Vmean={lt_ica_vmean}, PI={lt_ica_pi}, RI={lt_ica_ri}

                ---
                【出力構成の指示】
                以下の4つの見出し（Markdown）で構成して出力してください。
                ### 1. 総合病態アセスメント（ストーリーとしての病態生理）
                ### 2. ガイドライン基準に照らした重症度・リスク判定
                ### 3. 警戒すべきクリティカルな連鎖・急性増悪リスク
                ### 4. 臨床的介入・観察ケアにおける重点提言
                """
                
                # コンテンツ生成
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=uploaded_files + [prompt]
                )
                
                st.success("🎉 アセスメント・推論完了！")
                st.markdown(response.text)
                
                # --- クリーンアップ（Googleのサーバーからファイル削除） ---
                for uf in uploaded_files:
                    try:
                        client.files.delete(name=uf.name)
                    except Exception:
                        pass
                
            except Exception as e:
                st.error(f"❌ アセスメント中にエラーが発生しました: {e}")