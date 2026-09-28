# v3 收尾验收记录

日期：2026-09-15。环境：Windows，Conda `deepresearch`，Python 3.11。

## 实现范围

- Step B：Web 使用 EvidenceStore 去重并合并元数据；Writer 输入为 JSON；Critic 返回后状态为 `completed`；保留子问题预算重置。
- Step C：Markdown 报告、证据表格、空输入与空证据提示、HTTP/连接/超时/格式错误处理、结果跨页面重运行保留。
- Step D：补齐并固定当前直接依赖版本，重写 README，补充缓存忽略规则。
- Step F：只做 Git 检查，没有暂存、commit 或 push。

## 离线验证

```text
python -m pytest tests -q -p no:cacheprovider --tb=short
123 passed in 17.79s
```

- `tests/conftest.py` 禁用 `.env` 加载、使用假模型凭据，阻止真实 Requests / HTTPX 网络调用。
- 使用 AppTest 验证实际 Streamlit 控件及表格，HTTP 响应由测试替换。
- Windows 沙箱对系统临时目录有访问限制，因此完整测试在沙箱外执行；未修改业务代码绕过该限制。
- `py_compile` 检查 CLI、Web Pipeline、API、前端及状态模型通过。
- `pip check`：`No broken requirements found.`
- 依赖版本来自当前环境；本次未另建全新环境重新安装所有依赖。

## CLI 真实验证

小问题：检索 LightGCN 原始论文（2020），简述核心方法并提供来源，要求最多两个子问题。

- CLI 退出码：0。
- checkpoint：`outputs/state_20260915_105100.json`。
- 状态：`completed`；去重证据：2 条；最终审核：`PASS`。
- 对应报告、审核 JSON、研究记忆均成功保存。
- 再次使用该 checkpoint 执行 `--resume`，退出码为 0。
- 原始输出位于已忽略的 `outputs/`，未加入版本控制。

## Web 验证

- FastAPI 根路径：HTTP 200。
- Swagger `/docs`：HTTP 200。
- Streamlit `/_stcore/health`：HTTP 200。
- 真实浏览器成功展示输入控件并提交研究问题。
- 第一次选择学术检索，两家学术 API 都报告网络错误，最终返回 0 条证据；页面正确显示空证据提示，报告没有据此编造研究结论。
- CLI 成功证据来自网页检索，因此第二次明确要求 `web_search`，未更改供应商实现或绕过工具权限。
- 第二次真实 Web 研究完成：Markdown 报告正常显示，Evidence Count 为 **2**，证据为 LightGCN 论文页面与代码仓库。
- 浏览器 `errors` 命令无错误输出。
- 真实截图：[报告](images/v3-web-report.png)、[证据表格](images/v3-web-evidence.png)。截图来自实际界面，不是模拟数据。
- 本次证明了网页检索路径的真实可用性；**不代表学术 API 网络问题已解决**。

## Git 与审查

- `.env`、`outputs/`、`__pycache__/`、`.pytest_cache/` 均被忽略。
- 暂存区为空；保留此前尚未提交的 v3 工作。
- Git whitespace 检查按 Windows CRLF 规则运行，通过；默认检查会将已有 CRLF 视作行尾空白。
- 独立只读代码复核未发现本轮 B–D 的阻塞问题。
