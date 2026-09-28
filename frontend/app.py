import requests
import streamlit as st


st.set_page_config(
    page_title="DeepResearch AI",
    page_icon="DR",
    layout="wide"
)



# =====================
# CSS
# =====================


st.markdown(
"""
<style>


/* background */

.stApp {

background:
linear-gradient(
180deg,
#1677b8 0%,
#8fc4e8 35%,
#f5f9ff 75%,
#ffffff 100%
);

}



.block-container {

max-width:1000px;

padding-top:50px;

}



header {

visibility:hidden;

}


#MainMenu {

visibility:hidden;

}



/* =================
Hero
================= */


.hero {

text-align:center;

color:white;

margin-bottom:45px;

}



.logo {

font-size:32px;

font-weight:700;

}



.title {

font-size:48px;

font-weight:800;

margin-top:20px;

}



.subtitle {

font-size:22px;

margin-top:15px;

}



.desc {

font-size:18px;

margin-top:15px;

}



/* =================
Input title
================= */


[data-testid="stTextArea"] label {


color:white;


font-size:20px;


font-weight:600;


margin-bottom:4px !important;


}

[data-testid="stTextArea"] label p {
color:white;
font-size:20px;
font-weight:600;
margin:0;
}



/* =================
Streamlit textarea fix
================= */



[data-testid="stTextAreaRootElement"],
[data-baseweb="textarea"] {


background:white !important;


border:none !important;


border-radius:22px !important;

overflow:hidden;

box-shadow:none !important;


}



[data-baseweb="textarea"] > div {


border:none !important;


background:white !important;


border-radius:22px !important;


box-shadow:none !important;


}



[data-testid="stTextArea"] textarea {


background:white !important;


color:#1f2937 !important;


border:none !important;


outline:none !important;


box-shadow:none !important;


border-radius:22px !important;


padding:25px !important;


font-size:16px !important;

resize:none !important;

}



textarea:focus {


border:none !important;


outline:none !important;


box-shadow:none !important;


}




textarea::placeholder {


color:#9ca3af !important;


}



/* =================
Button center
================= */


.stButton {


display:flex;

justify-content:center;

margin-top:0;


}



.stButton button {


width:150px;


height:45px;


border-radius:15px;


background:#1677ff;


color:white;


font-size:16px;


font-weight:600;


border:none;


}





/* =================
Feature
================= */


.feature {


background:white;


padding:25px;


border-radius:20px;


text-align:center;


box-shadow:

0 5px 20px rgba(0,0,0,0.08);


}



.feature-title {


font-size:22px;


font-weight:700;


color:#1f2937;


}



.feature-text {


margin-top:10px;


color:#6b7280;


}


/* =================
Research status and report
================= */

.st-key-research_status,
.st-key-research_result {

background:rgba(255,255,255,0.96);

border:1px solid rgba(255,255,255,0.75);

border-radius:20px;

box-shadow:0 12px 32px rgba(20,67,105,0.18);

padding:8px 14px;

}

.st-key-research_status *,
.st-key-research_result p,
.st-key-research_result li,
.st-key-research_result td,
.st-key-research_result th {

color:#1e293b !important;

}

.st-key-research_result h1,
.st-key-research_result h2,
.st-key-research_result h3 {

color:#0f3d62 !important;

}



</style>

""",
unsafe_allow_html=True
)




# =====================
# Hero
# =====================


st.markdown(
"""
<div class="hero">


<div class="logo">

DeepResearch AI

</div>


<div class="title">

智能科研助手

</div>


<div class="subtitle">

AI-powered Research Assistant

</div>


<div class="desc">

探索知识 · 分析文献 · 生成报告

</div>


</div>

""",
unsafe_allow_html=True
)




# =====================
# Input
# =====================



question = st.text_area(

    "请输入您的科研问题：",

    placeholder=
"""例如：
分析2025年多模态推荐系统研究进展，
并列出代表性论文。""",

    height=160

)



with st.container(horizontal=True, horizontal_alignment="center"):
    run = st.button("开始研究")




# =====================
# Feature cards
# =====================


st.write("")



c1,c2,c3 = st.columns(3)



with c1:

    st.markdown(
"""
<div class="feature">

<div class="feature-title">
文献检索
</div>

<div class="feature-text">
搜索相关论文与资料
</div>

</div>
""",
unsafe_allow_html=True
)



with c2:

    st.markdown(
"""
<div class="feature">

<div class="feature-title">
智能分析
</div>

<div class="feature-text">
理解研究内容与技术趋势
</div>

</div>
""",
unsafe_allow_html=True
)



with c3:

    st.markdown(
"""
<div class="feature">

<div class="feature-title">
报告生成
</div>

<div class="feature-text">
生成结构化研究报告
</div>

</div>
""",
unsafe_allow_html=True
)




# =====================
# Backend
# =====================


if run:
    question = question.strip()
    if not question:
        st.warning("请输入研究问题")
    else:
        st.session_state.pop("research_result", None)
        status_placeholder = st.empty()
        with status_placeholder.container():
            status_box = st.container(border=True, key="research_status")
            status_box.info("正在生成报告，请稍等…")
        with st.spinner("正在研究中，可能需要数分钟..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/research",
                    json={"question": question},
                    timeout=600,
                )
                if response.status_code != 200:
                    suggestions = {
                        402: "模型账户余额不足，请充值或更换 API 密钥。",
                        422: "问题格式不正确，请检查输入。",
                        429: "请求过于频繁，请稍后重试。",
                        500: "研究服务执行失败，请检查后端日志后重试。",
                        502: "上游服务暂时不可用，请稍后重试。",
                        503: "研究服务暂时不可用，请稍后重试。",
                        504: "上游服务超时，请缩小问题范围后重试。",
                    }
                    st.error(
                        f"研究失败（HTTP {response.status_code}）。"
                        + suggestions.get(response.status_code, "请检查后端服务后重试。")
                    )
                else:
                    result = response.json()
                    if (
                        not isinstance(result, dict)
                        or not isinstance(result.get("report"), str)
                        or not isinstance(result.get("evidence"), list)
                        or not all(isinstance(item, dict) for item in result["evidence"])
                    ):
                        raise ValueError("Invalid research response")
                    st.session_state.research_result = result
            except requests.Timeout:
                st.error("研究请求超时。请缩小问题范围后重试；后端任务可能仍在运行。")
            except requests.ConnectionError:
                st.error("无法连接研究服务，请确认 FastAPI 已启动（127.0.0.1:8000）。")
                st.info("请在项目根目录打开另一个终端，激活 deepresearch 环境并运行以下命令，保持后端运行后重试。")
                st.code("python -m uvicorn api.server:app --host 127.0.0.1 --port 8000", language="bash")
            except ValueError:
                st.error("研究服务返回的数据格式不正确，请检查后端日志后重试。")
            except requests.RequestException:
                st.error("研究请求失败，请检查网络和后端服务后重试。")
            finally:
                status_placeholder.empty()


result = st.session_state.get("research_result")
if result is not None:
    st.divider()
    with st.container(border=True, key="research_result"):
        st.success("研究流程完成")
        st.caption(f"研究问题：{result.get('question', '')}")
        st.subheader("📄 研究报告")
        st.markdown(result["report"])
        evidence = result["evidence"]
        st.metric("证据数量", len(evidence))
        with st.expander("查看研究证据", expanded=True):
            if evidence:
                st.dataframe(
                    [
                        {
                            "Title": item.get("title", ""),
                            "Year": item.get("year"),
                            "Citations": item.get("citations"),
                            "Venue": item.get("venue"),
                            "Source": item.get("source", ""),
                            "Verified": item.get("verified", False),
                        }
                        for item in evidence
                    ],
                    hide_index=True,
                    width="stretch",
                )
                st.caption("Verified 为证据记录中的标记，不代表报告中的每项结论均经过独立核验。")
            else:
                st.info("本次未收集到证据。请缩小范围或调整关键词。")
