# Sports Rehabilitation

## 运行方式

**前置：** Node.js 22 LTS。数据库三选一（Docker / 便携免安装 MySQL / 系统 MySQL）。

### 方式一：便携 MySQL（免 Docker，推荐用于分发）

整套数据库跑在项目内 `.local\` 下，绿色、可整目录拷贝，不需要 Docker，不需要管理员权限。

```powershell
npm run mysql:dev:fetch   # 联网下载 MySQL 免安装版到 vendor\mysql（已有则自动跳过）
npm run app:setup         # 初始化数据库 + 建库建表写初始数据（只需一次）
npm run start:all         # 起数据库 + 起网页服务（http://localhost:3023）
```

详见 [便携版 MySQL 说明](docs/portable-mysql.md)。

> 给最终使用者：从打包根目录双击 `启动-康复网页服务.bat` 即可自动完成以上全部步骤。

### 方式二：Docker（本机开发现状）

```powershell
docker compose up -d      # 启动 MySQL 8.4 容器（端口 3306）
npm run db:init           # 建库建表写初始数据（只需一次）
npm start                 # 起网页服务（http://localhost:3023）
```

> 两种方式共用同一个 `.env`（端口 3306、root123、sports_app），二选一启动即可，不要同时占用 3306。

### 前端开发热更新（仅本地调试）

`npm run dev` 在 `http://localhost:3000` 启停 Vite 热更新；但 UE5 内嵌浏览器指向的是
`http://localhost:3023`，UE5 联调请用上面的 `npm start` / `npm run start:all`（Express 托管已构建的 `dist/`）。

## 媒体素材自动转换（UE5 内置浏览器适配）

UE5 内置浏览器是「阉割版 Chromium(CEF)」，**不能播 MP4/MOV、不能内嵌看 PDF/Word/PPT**。后台上传时系统会**自动转成 UE5 能显示的格式**，无需手动处理：

| 上传 | 自动转成 | 用到的转换器（已内置 `vendor\`，开箱即用） |
|------|----------|--------------------------------------------|
| MP4 / MOV 视频 | WebM (VP9/Opus) | ffmpeg → `vendor\ffmpeg\` |
| PDF | PNG 长图（只存图片） | mupdf（随 `node_modules`） |
| Word `.doc/.docx`、PPT `.ppt/.pptx` | PNG 长图（先转 PDF 再渲染，只存图片） | LibreOffice → `vendor\libreoffice\` |
| JPG / PNG / WEBP、WebM | 直接用 | — |

换新机器部署时，一键备齐全部转换器：

```powershell
npm run setup:converters   # = ffmpeg:fetch + libreoffice:fetch（已就绪的自动跳过）
```

> 改了 `src/` 前端代码后需 `npm run build` 重建 `dist/`；只改 `server/` 后端则重启服务即可。
> 详见 [更新图文和视频资料教程](docs/更新图文和视频资料教程.md)。

## 部署

客户交付以本地 Windows 为主，公网服务器仅用于异地测试。

- [便携版 MySQL 说明](docs/portable-mysql.md)
- [Windows 本地部署手册](docs/windows-local-deployment-guide.md)
- [Local Windows deployment](docs/local-windows-deployment.md)
- [Shared test server deployment](docs/production-deployment.md)

## Project Docs

- [更新图文和视频资料教程（媒体自动转换 / 转换器准备 / 排错）](docs/更新图文和视频资料教程.md)
- [Design system](DESIGN.md)
- [Final functional design](docs/final-functional-design.md)
- [Follow-up todo](docs/follow-up-todo.md)
- [Implementation and test plan](docs/implementation-plan.md)
- [Detailed E2E test plan](docs/detailed-e2e-test-plan.md)
- [M3 learning plan and stage design](docs/m3-learning-plan-stage-design.md)
- [M4 knowledge and learning design](docs/m4-knowledge-learning-design.md)
- [M5 quiz design](docs/m5-quiz-design.md)
- [M6 metrics and stars design](docs/m6-metrics-stars-design.md)
- [M7 UE5 training design](docs/m7-ue5-training-design.md)
- [M8 reports and progress design](docs/m8-reports-design.md)
- [M9 admin console design](docs/m9-admin-design.md)
- [M10 deployment and acceptance](docs/m10-deployment-acceptance.md)
- [2026-04-25 Word extracted plan](docs/20260425-word-extracted.md)
- [Current feature inventory](docs/current-feature-inventory.md)
- [Frontend interaction details](docs/frontend-interaction-details.md)
- [Integrated functional design discussion](docs/integrated-functional-design-discussion.md)
- [Backend and admin design draft](docs/backend-admin-design-draft.md)
- [UE5 integration notes](docs/ue5-integration-notes.md)
- [2026-04-25 design comparison](docs/20260425-design-comparison.md)
- [Database setup](docs/database-setup.md)
- [便携版 MySQL（免 Docker）](docs/portable-mysql.md)
- [Windows 本地部署手册](docs/windows-local-deployment-guide.md)
- [Production deployment](docs/production-deployment.md)
- [Local Windows deployment](docs/local-windows-deployment.md)
- [M0 test record](docs/test-records/m0-test-record.md)
- [M1 test record](docs/test-records/m1-test-record.md)
- [M2 auth test record](docs/test-records/m2-test-record.md)
- [M3 learning plan and stage test record](docs/test-records/m3-test-record.md)
- [M4 knowledge and learning test record](docs/test-records/m4-test-record.md)
- [M5 quiz test record](docs/test-records/m5-test-record.md)
- [M6 metrics and stars test record](docs/test-records/m6-test-record.md)
- [M7 UE5 training test record](docs/test-records/m7-test-record.md)
- [M8 reports and progress test record](docs/test-records/m8-test-record.md)
- [M9 admin console test record](docs/test-records/m9-test-record.md)
- [M10 deployment and acceptance test record](docs/test-records/m10-test-record.md)
