# 环境配置与避坑指南：CodexPilot 启动与 Clash Verge 校园网冲突解决方案

本篇文档用于记录在 Windows 11 环境下，配置 CodexPilot 以及解决 Clash Verge（TUN 模式）与学校内部实验服务器（4090 集群内网域名）路由冲突的完整排查过程与终极解决方案。

---

## 🛠️ 问题一：CodexPilot 无法启动 Codex App

### 1. 现象与报错
在 Win11 平台上使用 CodexPilot 启动 Codex App 时失败，程序退出并返回 `exit code: 1`。
报错日志中显示的路径结尾呈现如下异常拼接：
```text
...\app\Codex.exe\codex.exe
```
2. 原因分析
CodexPilot 在读取或拼接路径时发生了逻辑错误，将正常的执行文件 Codex.exe 误判为了一个文件夹，并在其后自动追加了额外的 \codex.exe，导致最终生成的绝对路径在系统中并不存在。

3. 解决方案
调整 CodexPilot 的设置或配置文件中的路径定义：

若设置项要求填入「应用程序目录」：将路径末尾的 .exe 删去，只保留到所在的父级文件夹：
C:\Program Files\WindowsApps\OpenAI.Codex_26.608.1337.0_x64__2p2nqsd0c76g0\app

若设置项要求填入「执行文件路径」：确保路径中只出现单次 Codex.exe，且末尾不要携带多余的斜杠。

💡 权限小贴士：由于 WindowsApps 是系统的隐藏且受高权限保护的目录，若改对路径后仍无法启动，需彻底退出 CodexPilot 并选择以管理员身份运行再试。

🌐 问题二：开启 Clash Verge TUN 模式后无法连接学校服务器
1. 现象与报错
为了满足手机远程连接等需求，必须开启 Clash Verge 的 TUN 模式。但开启后，连接学校实验服务器（内网域名如 *.xidian-ai-intranet.top）时失效，SSH 工具输出如下握手前断开的日志：

Plaintext
Local ident: 'SSH-2.0-ssh2js1.17.0'
Client: Trying 4090x8_8.xidian-ai-intranet.top on port 38022 ...
Socket connected
Socket ended
Connection lost before handshake
注：关闭 TUN 模式后，校园网连接即刻恢复正常。

2. 原因分析
网络接管冲突：TUN 模式创建了虚拟网卡并接管了系统的全局流量。当尝试连接校园网域名时，流量被强行拦截并打包发送给了外部代理节点，而外部节点在公网上无法触达学校的内网环境。

Fake-IP 拦截陷阱：在 Clash 核心开启时，其 DNS 模块会优先抢占域名解析请求，并向 SSH 客户端返回一个虚假的内部 IP（如 198.18.x.x）。即使在规则中配置了 DIRECT（直连），Clash 核心在尝试建立物理连接时，依然会因为使用外部 DNS 或自身解析逻辑缺陷，无法正确识别高校内网域名的真实去向，最终导致在 SSH 握手前连接被强行挂断（Socket ended）。

3. 终极解决方案（使用配置合并 Merge）
通过修改 Clash Verge 的配置合并（Merge）功能，同时引入 fake-ip-filter（假 IP 过滤器）和直连分流规则，明确告知 Clash 核心不对学校内网域名进行 DNS 劫持，转而交付给系统原生校园网 DNS 进行直连解析。

Step 1: 编写 Merge 扩展配置
打开 Clash Verge，点击左侧导航栏的 配置 (Profiles)。

点击顶部 新建 (New)，类型选择 Merge，命名为例如 校园网直连白名单。

右键该配置选择编辑，填入以下优化后的 YAML 代码：

```YAML
# Profile Enhancement Merge Template for Clash Verge

dns:
  fake-ip-filter:
    - '+.xidian-ai-intranet.top'  # 放行该主域名及其所有子域名，不分配假IP

prepend-rules:
  - DOMAIN-SUFFIX,xidian-ai-intranet.top,DIRECT  # 匹配该域名的流量全部走直连
  - IP-CIDR,10.0.0.0/8,DIRECT                    # 高校常见的内网10.x.x.x网段全部走直连
```

保存并右键该 Merge 项，点击 启用 (Enable)。

重新激活（Active）你日常使用的机场订阅配置，使合并规则生效。

Step 2: 刷新系统缓存
规则应用后，由于 Windows 本地可能仍残留有此前 Clash 分配的 Fake-IP 缓存，需要手动清理：

暂时关闭 Clash 的 TUN 模式。

按 Win + R 输入 cmd 打开命令行。

执行以下命令清空本地 DNS 缓存：

DOS
ipconfig /flushdns
重新开启 TUN 模式。

4. 预期效果
经过上述配置后，发往学校 4090 服务器域名的网络请求将完美绕过代理，直接走原生的校园网物理网卡建立连接；而其他外网请求则继续受到 Clash Verge TUN 模式的代理加速，两者互不干扰，完美共存。