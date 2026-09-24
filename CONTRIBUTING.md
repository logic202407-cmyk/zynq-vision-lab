# 贡献与验收

本仓库当前是开发起点，不是已验收作品。先阅读 [规划](docs/project_plan.md)、[状态](report/status.json) 和 [实验边界](docs/safety.md)。

## 任务与提交

从 `main` 新建 `work/<task>` 分支；每个任务写清输入、输出、测试、负责人和复核人。小步提交，不混入工具版本升级和无关重构。初始化阶段不自动创建或邀请协作者。

每个模块提交源码、接口说明、测试、依赖与运行命令；保留能发现故意引入错误的测试。第三方代码先查许可并登记到 `THIRD_PARTY.md`。

## 基础检查

```bash
python tools/check_repository.py
python -m unittest discover -s tests -v
```

这只是仓库层检查。涉及 FPGA 的修改仍需按范围补齐仿真、实现后时序、板级输出及独立复现记录。CI 不会替代这些工作。

## 证据和状态

提升 `report/status.json` 的状态时，证据须对应审查提交、工具版本、输入与配置。没有硬件就写“未板测”；不能把软件输出或 HLS 估计当作板上实测。证据模板位于 `report/templates/`。

## 公开内容

所有路径使用英文字符。个人信息、凭据、许可证与原始报名资料只留在被忽略的 `private/`，不要出现在 commit、Issue 或日志中。只公开经过授权和脱敏的数据与板卡照片。

`publish.ps1` 仅用于未修改的初始化包和同一次失败发布的重试，不是日常提交工具。正常开发使用 Git 分支与 Pull Request，不重新生成初始化清单绕过审查。
