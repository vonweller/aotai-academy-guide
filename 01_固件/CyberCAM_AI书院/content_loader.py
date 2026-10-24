# -*- coding: utf-8 -*-
"""朗读文案与关卡数据：本地 content.json 优先，缺失时用内置兜底。"""
import json
import os

try:
    from . import config
except Exception:
    import config

_FALLBACK = {
    "project": "鳌台书院 AI 数字导览",
    "prompts": [
        {"id": "p_relic_task_v2", "zh": "候选清单（关联与地域待核）：厚街粤绣、厚街双手洪拳、鳌鱼砖；莞草编织、清溪麒麟扎作。图片和模型待核实，暂不识别或计分。", "yue": "候選清單（關聯同地域待核）：厚街粵繡、厚街雙手洪拳、鰲魚磚；莞草編織、清溪麒麟紮作。相片同模型仍待核實，暫不識別或計分。"},
        {"id": "p_lang_zh", "zh": "好的，改用普通话为你讲解。", "yue": "好，改用普通話同你講。"},
        {"id": "p_lang_yue", "zh": "好，我改用粤语同你讲。", "yue": "好，我改用粵語同你講。"},
        {"id": "p_relic_candidate_v2", "zh": "这是当前候选展项，类别、来源与实物关系仍待核实。", "yue": "呢個係目前嘅候選展項，類別、來源同實物關係仍待核實。"},
        {"id": "p_content_review_done_v2", "zh": "候选内容清单已列出；五类来源、实物和模型仍待核实，自动识别尚未启用。", "yue": "候選內容清單已列出；五類來源、實物同模型仍待核實，自動識別仲未啟用。"},
        {"id": "p_relic_order_v2", "zh": "火眼金睛先列鳌台书院优先展示候选（具体关联待核），再列东莞技艺候选（地域与项目名待核）；所有类别暂不自动识别或计分。", "yue": "火眼金睛先列鰲台書院優先展示候選（具體關聯待核），再列東莞技藝候選（地域同項目名待核）；所有類別暫不自動識別或計分。"},
        {"id": "p_relic_model_pending_v2", "zh": "当前识别模型仍是旧类别版本，已安全停用。五个新类别的实物图片和训练数据尚待核实补齐，暂不执行自动识别，也不计识别积分。", "yue": "目前識別模型仍然係舊類別版本，已安全停用。五個新類別嘅實物相片同訓練資料仍要核實補齊，暫時唔會自動識別，亦唔會計識別積分。"},
        {"id": "p_relic_next_v2", "zh": "请按顺序查看下一件候选展项；相关图片和模型完成核实后，再启用自动识别。", "yue": "請按次序睇下一件候選展項；相關相片同模型完成核實後，先會啟用自動識別。"},
        {"id": "p_relic_bring_v2", "zh": "请查看相应候选类别的代表图片；图片来源与授权仍待核实，当前不用于自动识别或计分。", "yue": "請睇相應候選類別嘅代表相片；相片來源同授權仍待核實，目前唔會用作自動識別或計分。"},
        {"id": "p_relic_pass_v2", "zh": "候选清单结构已整理；各项来源、实物和模型仍待核实，自动识别尚未启用。", "yue": "候選清單結構已整理；各項來源、實物同模型仍待核實，自動識別仲未啟用。"},
        {"id": "p_relic_intro_v2", "zh": "当前旧类别模型已停用；新类别来源、授权示范图片、训练数据和验证模型尚待核实。自动识别与识别积分均未启用。", "yue": "目前舊類別模型已停用；新類別來源、授權示範相片、訓練資料同驗證模型仍待核實。自動識別同識別積分都未啟用。"},
        {"id": "p_relic_intro_active_v2", "zh": "本次图像识别流程已启动，请按顺序展示对应类别的已核验授权图片。", "yue": "今次圖像識別流程已啟動，請按次序展示相應類別已核實授權嘅相片。"},
        {"id": "p_congrats_v2", "zh": "本次数字导览已完成，多谢参与。", "yue": "今次數字導覽已完成，多謝參與。"},
        {"id": "p_summary_v2", "zh": "今天我们听了书院故事，也查看了本项目拟展示的候选内容。各项目关联、地域、正式名称与实物来源仍待核实，谢谢你陪小鳌走完这一程。", "yue": "今日我哋聽咗書院故事，亦睇咗本項目擬展示嘅候選內容。各項目關聯、地域、正式名稱同實物來源仍待核實，多謝你陪小鰲行完呢一程。"},
        {"id": "p_relic_next_active_v2", "zh": "请展示下一项候选类别对应的已核验授权图片。", "yue": "請展示下一項候選類別相應嘅已核實授權相片。"},
        {"id": "p_relic_bring_active_v2", "zh": "请把相应类别的已核验授权示范图片对准镜头；拳架类别仅对应静态姿势示范图。", "yue": "請將相應類別已核實授權嘅示範相片對準鏡頭；拳架類別只對應靜態姿勢示範圖。"},
        {"id": "p_relic_pass_active_v2", "zh": "本次图像匹配确认完成；这不代表项目来源或历史关系已核实。", "yue": "今次圖像匹配確認完成；呢個唔代表項目來源或歷史關係已核實。"},
        {"id": "p_relic_confirm_v2", "zh": "讲解结束后，请移开图片，再展示同一类别的已核验授权示范图片完成确认。", "yue": "講解結束後，請移開相片，再展示同一類別已核實授權嘅示範相片完成確認。"},
    ],
    "stages": [
        {
            "id": 1, "key": "gate",
            "name": {"zh": "第一关 · 门口迎宾", "yue": "第一關 · 門口迎賓"},
            "lines": [
                {"id": "s1_prompt", "zh": "请正对摄像头，让我先认一认你。", "yue": "請正對鏡頭，等我先認一認你。"},
                {"id": "s1_welcome_ok_v2", "zh": "预约访客，欢迎您来到鳌台书院 AI 导览。认出您了，跟好小鳌，一起查看本项目拟展示的候选内容。",
                 "yue": "預約訪客，歡迎您嚟到鰲台書院 AI 導覽。認得您喇，跟實小鰲，一齊睇本項目擬展示嘅候選內容。"},
                {"id": "s1_welcome_new_v2", "zh": "欢迎光临鳌台书院，我是你的智能导览员小鳌。今天我们会听书院故事，并查看本项目拟展示的候选内容；具体关联、地域与项目名称仍待核实。",
                 "yue": "歡迎光臨鰲台書院，我係你嘅智能導覽員小鰲。今日我哋會聽書院故事，亦會睇本項目擬展示嘅候選內容；具體關聯、地域同項目名稱仍待核實。"},
            ],
            "quiz": [],
        },
        {
            "id": 2, "key": "front_yard",
            "name": {"zh": "第二关 · 书院资料待核", "yue": "第二關 · 書院資料待核"},
            "lines": [
                {"id": "s2_source_pending_v2", "zh": "本项目现有文稿记录了书院创建、迁建及重建等信息，但目前缺少可供展陈引用的权威出处。本次数字导览暂不陈述具体年代和规模，待核对地方志、档案或官方资料后再更新。",
                 "yue": "本項目現有文稿記錄咗書院創建、遷建同重建等資料，但目前欠缺可以用作展陳引用嘅權威出處。今次數字導覽暫時唔講具體年代同規模，待核對地方志、檔案或官方資料後再更新。"},
            ],
            "quiz": [],
        },
        {"id": 3, "key": "hall", "name": {"zh": "第三关 · 题刻待核", "yue": "第三關 · 題刻待核"},
         "lines": [
            {"id": "s3_virtual_hall_scope_v2", "zh": "本项目把这里设置为数字讲堂场景；实际历史用途、题刻内容和原物出处仍待现场资料或档案核实。",
             "yue": "本項目將呢度設置為數字講堂場景；實際歷史用途、題刻內容同原物出處仍待現場資料或檔案核實。"},
            {"id": "s3_inscription_source_pending_v2", "zh": "讲堂楹联、匾额内容、题写者与科名等信息，需由现场原物、地方志或官方资料逐项核实；在来源确认前，本项目不作确定陈述。",
             "yue": "講堂楹聯、匾額內容、題寫者同科名等資料，要由現場原物、地方志或官方資料逐項核實；來源確認之前，本項目唔作確定陳述。"}
         ], "quiz": []},
        {"id": 4, "key": "workshop", "name": {"zh": "第四关 · 数字展陈", "yue": "第四關 · 數字展陳"},
         "lines": [{"id": "s4_virtual_scope_v2", "zh": "这里是本项目设计的虚拟技艺展陈场景，不代表鳌台书院现场已有相同工坊或展品。火眼金睛先介绍拟展示的鳌台书院主题数字展项，再进入东莞技艺候选（地域与项目名待核）；各项目关系、正式名称和实物来源仍待核实。",
                    "yue": "呢度係本項目設計嘅虛擬技藝展陳場景，唔代表鰲台書院現場已有相同工坊或展品。火眼金睛會先介紹擬展示嘅鰲台書院主題數字展項，再介紹東莞技藝候選（地域同項目名待核）；各項目關係、正式名稱同實物來源仍待核實。"}], "quiz": []},
        {"id": 5, "key": "pavilion", "name": {"zh": "第五关 · 留墨寄愿", "yue": "第五關 · 留墨寄願"},
         "lines": [
            {"id": "s5_closing_v2", "zh": "今天我们听了书院故事，也查看了本项目拟展示的候选内容。项目关联、地域、正式名称和实物来源仍待核实，谢谢你陪小鳌走完这一程。",
             "yue": "今日我哋聽咗書院故事，亦睇咗本項目擬展示嘅候選內容。項目關聯、地域、正式名稱同實物來源仍待核實，多謝你陪小鰲行完呢一程。"},
            {"id": "s5_ink_v2", "zh": "你也可以在数字展陈里留下自己的心愿。书院题刻与原物出处仍以核实后的资料为准。",
             "yue": "你都可以喺數字展陳入面留低自己嘅心願。書院題刻同原物出處仍以核實後嘅資料為準。"},
            {"id": "s5_virtual_route_v2", "zh": "本项目中的数字参观路线依次经过门楼、前院、讲堂、东侧虚拟展陈场景和后园，属于交互设计，不代表现场开放路线或实际展项布局。",
             "yue": "本項目嘅數字參觀路線依次經過門樓、前院、講堂、東側虛擬展陳場景同後園，屬於互動設計，唔代表現場開放路線或實際展項布局。"},
            {"id": "s5_bye_v2", "zh": "数字导览到这里结束。谢谢你参与，也欢迎继续查看项目中明确标注为候选或待核的内容。",
             "yue": "數字導覽到呢度結束。多謝你參與，亦歡迎繼續睇項目入面明確標註為候選或待核嘅內容。"}
         ], "quiz": []},
    ],
}


# Offline fallback preserves candidate order and fail-closed readiness.
_FALLBACK_KEYS = ("houjie_yuexiu", "houjie_shuangshou_hongquan",
                  "aotai_aoyu_brick", "guancao", "qingxi_qilin_zhazuo")
_FALLBACK_GROUPS = [
    {"id": "aotai_priority_candidates", "label": {"zh": "鳌台书院优先展示候选（关联待核）", "yue": "鰲台書院優先展示候選（關聯待核）"}, "keys": list(_FALLBACK_KEYS[:3])},
    {"id": "dongguan_local_candidates", "label": {"zh": "东莞技艺候选（地域与项目名待核）", "yue": "東莞技藝候選（地域同項目名待核）"}, "keys": list(_FALLBACK_KEYS[3:])},
]
_FALLBACK_NAMES = [
    ("厚街粤绣", "厚街粵繡"), ("厚街双手洪拳", "厚街雙手洪拳"),
    ("鳌鱼砖", "鰲魚磚"), ("莞草编织", "莞草編織"),
    ("清溪麒麟扎作", "清溪麒麟紮作"),
]
_FALLBACK["fireEyes"] = {"status": "planned_pending_curated_media", "order": list(_FALLBACK_KEYS), "groups": _FALLBACK_GROUPS}
_FALLBACK["candidate_sources_status"] = "no_item_level_authoritative_sources_verified"
_FALLBACK["relics"] = [
    {"id": "relic_%s_v2" % key, "key": key, "name": {"zh": name[0], "yue": name[1]},
     "proposal_status": "proposed_candidate", "group": _FALLBACK_GROUPS[0 if i < 3 else 1]["id"],
     "source_status": "pending_authoritative_verification", "source_refs": [],
     "media_rights_status": "pending_permission_review", "media_rights_refs": [],
     "recognition": {"status": "needs_curated_photos_and_retraining", "enabled": False},
     "model_validation": {"status": "not_run", "independent_test_report": None,
        "deployment_validation": "not_run", "deployment_report": None},
     "required_evidence": ["权威来源记录", "图像授权凭证", "独立模型测试报告", "设备部署回归报告"],
     "zh": "本项目拟展示的候选类别；正式名称、地域/书院关系、实物来源与授权仍待核实。",
     "yue": "本項目擬展示嘅候選類別；正式名稱、地域/書院關係、實物來源同授權仍待核實。", "quiz": None}
    for i, (key, name) in enumerate(zip(_FALLBACK_KEYS, _FALLBACK_NAMES))
]

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class Content(object):
    def __init__(self, path=None):
        self.path = path or config.CONTENT_PATH
        self.data = _load_json(self.path)
        if not self.data:
            # IDE 调试：脚本同级或 ../../02_数据/content.json
            here = os.path.dirname(os.path.abspath(__file__))
            for cand in (
                os.path.join(here, "content.json"),
                os.path.join(here, "..", "..", "02_数据", "content.json"),
                os.path.join(here, "..", "..", "02_数据", "content.json".lower()),
            ):
                self.data = _load_json(os.path.abspath(cand))
                if self.data:
                    self.path = os.path.abspath(cand)
                    break
        self.data = self.data or _FALLBACK
        self.stages = {}
        for st in self.data.get("stages", []):
            try:
                self.stages[int(st.get("id", 0))] = st
            except Exception:
                continue
        # 兼容：content.json 放在 APP 目录（IDE 调试时）
        if not self.stages:
            self.data = _FALLBACK
            self.stages = {int(s["id"]): s for s in _FALLBACK["stages"]}

    # ---------- 查询 ----------
    def stage(self, stage):
        return self.stages.get(int(stage)) or {}

    def entry_id(self, stage):
        st = self.stage(stage)
        if st.get("entry"):
            return st["entry"]
        lines = st.get("lines") or []
        return lines[0].get("id") if lines else None

    def stage_name(self, stage, lang):
        st = self.stage(stage)
        n = st.get("name") or {}
        return n.get(lang) or n.get("zh") or config.STAGE_NAMES.get(stage, {}).get(lang, "第%d关" % stage)

    def lines(self, stage):
        return self.stage(stage).get("lines", [])

    def line(self, line_id):
        for st in self.stages.values():
            for ln in st.get("lines", []):
                if ln.get("id") == line_id:
                    return ln
            # 题目的 q / a / wrong 也当成可朗读条目
            for q in st.get("quiz") or []:
                qid = q.get("qid") or ""
                if line_id == qid + "_q":
                    return {"id": line_id, "zh": (q.get("q") or {}).get("zh"),
                            "yue": (q.get("q") or {}).get("yue")}
                if line_id == qid + "_a":
                    return {"id": line_id, "zh": (q.get("explain") or {}).get("zh"),
                            "yue": (q.get("explain") or {}).get("yue")}
                if line_id == qid + "_wrong":
                    w = q.get("explain_wrong") or {}
                    return {"id": line_id, "zh": w.get("zh"), "yue": w.get("yue")}
        for rel in self.data.get("relics") or []:
            if rel.get("id") == line_id:
                return rel
        for prompt in self.data.get("prompts") or []:
            if prompt.get("id") == line_id:
                return prompt
        return None

    def text(self, line_id, lang):
        """返回 (朗读文本, 字幕文本)。粤语缺字时回退普通话。"""
        ln = self.line(line_id)
        if not ln:
            return "", ""
        t = ln.get(lang) or ln.get("zh") or ""
        return t, t

    def relics(self):
        return list(self.data.get("relics") or [])

    def quiz(self, stage):
        qs = self.stage(stage).get("quiz") or []
        return qs[0] if qs else None

    def quiz_text(self, quiz, lang):
        q = quiz or {}
        return (q.get("q") or {}).get(lang) or (q.get("q") or {}).get("zh", "")

    def quiz_options(self, quiz, lang):
        out = []
        for op in (quiz or {}).get("options", []):
            out.append({"key": op.get("key"), "text": op.get(lang) or op.get("zh", "")})
        return out

    def quiz_explain(self, quiz, lang):
        e = (quiz or {}).get("explain") or {}
        return e.get(lang) or e.get("zh", "")
