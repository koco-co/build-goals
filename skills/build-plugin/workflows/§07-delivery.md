# Plugin 交付

使用 `templates/plugin-delivery-report.template.md`。

交付内容必须让用户能够回答：

- 最终交付了什么；
- 哪些内容没有做；
- Plugin 在 Claude Code 与 Codex 中如何发现、安装和调用；
- 哪些文件是规范源，哪些是平台适配；
- 哪些路径是软链接以及指向哪里；
- Plugin 中的 Skills 是否通过 `build-skill` 规范；
- 实际运行了哪些命令；
- 哪些结论来自真实客户端，哪些只是静态检查；
- 当前版本是否已提交、推送、发布或仅在本地；
- 存在哪些未验证项或阻塞项。

交付完成后停止。不要自动开始另一个 Plugin、发布到 Marketplace、创建 Release 或适配其他 Coding Agent。
