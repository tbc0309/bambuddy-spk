# Bambuddy 群晖原生套件

基于 [Bambuddy](https://github.com/maziggy/bambuddy)，为群晖 DSM 制作原生 SPK，不使用 Docker。打包流程参考 [MoviePilot SPK](https://github.com/tbc0309/moviepilot-spk)。本项目不是 Bambuddy 或 Synology 官方项目。

## 支持范围

| 系统 | 最低版本 | 架构 |
| --- | --- | --- |
| DSM 7.2 | 7.2-64570 | x86_64、armv8 |

提供 x86_64、armv8 两种架构的原生套件。已验证真实 DSM 上的安装、普通账户运行、网页和健康检查；实际打印机及虚拟打印机功能仍需按使用场景验证。

## 安装与使用

1. 安装 `ffmpeg8` 套件，用于视频相关功能。
2. 在套件中心手动安装对应系统和架构的 SPK。
3. 打开套件，访问 NAS 的 `8000` 端口，完成 Bambuddy 初始配置。不要直接将未配置认证的服务暴露到公网。

套件使用 `Bambuddy` 用户和用户组运行。数据、数据库和归档位于 `/var/packages/Bambuddy/var/data`；日志位于 `var/logs`。升级保留数据，卸载可选择保留或删除。

默认使用普通套件账户，不申请 capabilities，不修改系统权限策略。（使用虚拟打印机功能需将套件 privilege 中的 run-as 改为 root。）

Tailscale 集成需要用户自行安装并配置 Tailscale；OrcaSlicer/Bambu Studio 切片服务仍需按照上游文档独立部署，本套件不内置这些 sidecar。普通打印机管理不依赖它们。

## 构建与更新

- 主线支持每 6 小时检查上游正式 Release，也支持手动指定版本；当前 schedule 保持关闭。
- 固定上游源码提交，前端使用上游 npm 锁文件；Python 依赖按 DSM 基线解析后固定在构建产物中。
- 仅支持 DSM 7.2。使用 SynoCommunity spksrc 和群晖工具链交叉编译不兼容的原生 wheel；在 manylinux 2.28 环境组装独立 Python 3.14 解释器及运行库。
- 保留上游运行依赖，不安装 pytest/ruff 等开发依赖。NumPy、Pillow、OpenCV 使用满足上游范围的 DSM 兼容版本，见 `scripts/constraints.txt`。
- 执行后端导入、HTTP `/health`、退出、普通账户运行及高端口绑定、glibc 符号检查。低端口功能因 DSM 平台限制不在当前支持范围内。
- 所有归档项统一 root:root、0755（符号链接除外）及本次打包时间；INFO checksum 由实际 package.tgz 计算，不写入 adminport。
- 程序内 Git/pip/npm 自更新被禁用，请通过套件中心升级。

手动构建默认只保存 Actions artifacts，不发布；勾选发布后，上游正式版生成正常 Release 并设为 Latest，上游测试版生成 Pre-release。不再构建 DSM 7.1。

## 许可证与源码

Bambuddy 使用 AGPL-3.0。本项目保留上游许可证，每个 SPK 随附修改后的完整上游源码及依赖锁定清单，可通过页面右下角 `SPK source / 套件源码` 下载。新编写的打包脚本使用 AGPL-3.0。沿用的 MoviePilot 构建辅助脚本保留 MIT 许可证，见 `scripts/LICENSE-MoviePilot-MIT`。安装器与通用生命周期脚本沿用 SynoCommunity 框架，保留其原有声明。第三方 Python/npm 依赖仍遵循各自许可证。
