import requests
import streamlit as st


st.set_page_config(page_title="DeepResearch Agent", page_icon="🔎", layout="wide")
st.title("🔎 DeepResearch Agent")
st.caption("将研究问题拆解为检索任务，汇总证据并生成研究报告。")
st.info("Web Demo 执行检索、写作与审核；报告仍需结合原始来源核对。")

question = st.text_area("请输入研究问题：", placeholder="例如：查找 LightGCN 原始论文，简述它的核心方法。")

if st.button("开始研究", type="primary"):
    question = question.strip()
    if not question:
        st.warning("请输入问题")
    else:
        st.session_state.pop("research_result", None)
        with st.spinner("Agent 正在研究，可能需要数分钟..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/research",
                    json={"question": question},
                    timeout=600,
                )
                if response.status_code != 200:
                    suggestions = {
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
            except ValueError:
                st.error("研究服务返回的数据格式不正确，请检查后端日志后重试。")
            except requests.RequestException:
                st.error("研究请求失败，请检查网络和后端服务后重试。")

result = st.session_state.get("research_result")
if result is not None:
    st.success("研究流程完成")
    st.caption(f"研究问题：{result.get('question', '')}")
    st.subheader("Research Report")
    st.markdown(result["report"])
    evidence = result["evidence"]
    st.metric("Evidence Count", len(evidence))
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
            st.info("本次未收集到证据。请缩小范围或调整关键词，勿将无来源的报告视为已验证结论。")
