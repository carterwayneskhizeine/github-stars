#!/usr/bin/env python3
"""
Classify trending-readme/ projects into category subfolders (copy, not move).

Categories were assigned by hand from each README's title/description.
The original flat files stay in place; each file is copied to
trending-readme/<category>/<filename>. Re-runs are idempotent, and a
分类索引.md index is (re)generated at trending-readme/ root.
"""

import json
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "trending-readme"
MAPPING_PATH = BASE / "data" / "trending_mapping.json"
INDEX_PATH = SRC / "分类索引.md"

CATEGORIES = {
    "Agent-harness": "代理运行时/harness/编码代理/编排框架",
    "Skill-生态": "Agent Skills、插件、上下文工程与工作流方法论",
    "个人AI助手-Claw系列": "OpenClaw/Claw 生态 + 个人 AI 助理/伴侣/第二大脑",
    "决策模型-Jev系": "Jev/Laya 等小型决策模型生态",
    "基础设施层": "推理引擎/编译器/协议/网络/存储/底层库",
    "设计与前端": "UI/设计/前端组件/图标/模板",
    "多媒体与3D": "视频/图像/3D/语音生成",
    "模型与研究": "模型/训练/研究/基准",
    "金融与交易": "交易与金融研究 agent",
    "独立品类": "独立应用与工具（桌面/CLI/硬件/游戏/安全等）",
}

FILE_MAP = {
    # --- Agent harness ---
    "AndyMik90-Auto-Claude.md": "Agent-harness",
    "ApodexAI-FrontierAgent.md": "Agent-harness",
    "AutoMaker-Org-automaker.md": "Agent-harness",
    "ComposioHQ-agent-orchestrator.md": "Agent-harness",
    "Conway-Research-automaton.md": "Agent-harness",
    "CopilotKit-OpenBot.md": "Agent-harness",
    "CopilotKit-openmuse.md": "Agent-harness",
    "Doorman11991-smallcode.md": "Agent-harness",
    "Forsy-AI-agent-apprenticeship.md": "Agent-harness",
    "Fullive-AI-Anima.md": "Agent-harness",
    "Gitlawb-openclaude.md": "Agent-harness",
    "HKUDS-FastCode.md": "Agent-harness",
    "HKUDS-OpenHarness.md": "Agent-harness",
    "Intuition-Lab-personal-model.md": "Agent-harness",
    "JackChen-me-open-multi-agent.md": "Agent-harness",
    "JuliusBrussee-caveman.md": "Agent-harness",
    "Louis-CFM-coucou.md": "Agent-harness",
    "NVlabs-SoL-Pi.md": "Agent-harness",
    "RightNow-AI-openfang.md": "Agent-harness",
    "SawyerHood-dev-browser.md": "Agent-harness",
    "ShawnPana-phone-harness.md": "Agent-harness",
    "StartupHakk-OpenMonoAgent.ai.md": "Agent-harness",
    "TestSprite-testsprite-cli.md": "Agent-harness",
    "VibiumDev-vibium.md": "Agent-harness",
    "Waishnav-devspace.md": "Agent-harness",
    "XiaomiMiMo-MiMo-Code.md": "Agent-harness",
    "aattaran-deepclaude.md": "Agent-harness",
    "andrewyng-openworker.md": "Agent-harness",
    "anthropics-commerce-agents.md": "Agent-harness",
    "browser-use-browser-harness.md": "Agent-harness",
    "deeplethe-forkd.md": "Agent-harness",
    "deepseek-ai-deepseek-harness.md": "Agent-harness",
    "firecrawl-open-agent-builder.md": "Agent-harness",
    "fuxicodex-Fuxi.md": "Agent-harness",
    "gi-dellav-zerostack.md": "Agent-harness",
    "google-research-harness2.md": "Agent-harness",
    "h4ckf0r0day-obscura.md": "Agent-harness",
    "kevinrgu-autoagent.md": "Agent-harness",
    "kvcache-ai-AgentENV.md": "Agent-harness",
    "lexmount-moli.md": "Agent-harness",
    "lopopolo-harness-engineering.md": "Agent-harness",
    "mistralai-mistral-vibe.md": "Agent-harness",
    "omnigent-ai-omnigent.md": "Agent-harness",
    "opensquilla-opensquilla.md": "Agent-harness",
    "rebel0789-codexpro.md": "Agent-harness",
    "safishamsi-graphify.md": "Agent-harness",
    "sapientinc-PRAXIST.md": "Agent-harness",
    "spacedriveapp-spacebot.md": "Agent-harness",
    "steveyegge-beads.md": "Agent-harness",
    "strukto-ai-mirage.md": "Agent-harness",
    "synthetic-sciences-openscience.md": "Agent-harness",
    "tigerless-labs-agent-memory.md": "Agent-harness",
    "unreallabsai-unreal-agent.md": "Agent-harness",
    "vercel-eve.md": "Agent-harness",
    "vercel-labs-fx.md": "Agent-harness",
    "yorgai-ORG2.md": "Agent-harness",
    # --- Skill 生态 ---
    "AgriciDaniel-claude-obsidian.md": "Skill-生态",
    "BuilderIO-skills.md": "Skill-生态",
    "DenisSergeevitch-agents-best-practices.md": "Skill-生态",
    "Forward-Future-loopy.md": "Skill-生态",
    "GitFrog1111-OpenWhip.md": "Skill-生态",
    "Jakeschincariol-day-trader-skill.md": "Skill-生态",
    "Jakeschincariol-replica-skill.md": "Skill-生态",
    "Leonxlnx-unlazy.md": "Skill-生态",
    "LiamGvchi-gc-minimal-zine-poster.md": "Skill-生态",
    "DannyMac180-sol-advisor.md": "Skill-生态",
    "microsoft-SkillOpt.md": "Skill-生态",
    "muratcankoylan-Agent-Skills-for-Context-Engineering.md": "Skill-生态",
    "mksglu-claude-context-mode.md": "Skill-生态",
    "agent0ai-dox.md": "Skill-生态",
    "agenticnotetaking-arscontexta.md": "Skill-生态",
    "agentskills-agentskills.md": "Skill-生态",
    "amElnagdy-guard-skills.md": "Skill-生态",
    "anysearch-ai-anysearch-skill.md": "Skill-生态",
    "achimala-dream-loop.md": "Skill-生态",
    "cathrynlavery-diagram-design.md": "Skill-生态",
    "cloudflare-security-audit-skill.md": "Skill-生态",
    "cobusgreyling-loop-engineering.md": "Skill-生态",
    "diffusionstudio-lottie.md": "Skill-生态",
    "donvito-codex-astra-luna-orchestrator.md": "Skill-生态",
    "dmmulroy-anti-slop.md": "Skill-生态",
    "excalidraw-excalidraw-mcp.md": "Skill-生态",
    "gemini-cli-extensions-conductor.md": "Skill-生态",
    "google-skills.md": "Skill-生态",
    "aicodeking-leanrea.md": "Skill-生态",
    "gvzdv-claudish-to-english.md": "Skill-生态",
    "jakubkrehel-skills.md": "Skill-生态",
    "mattpocock-dictionary-of-ai-coding.md": "Skill-生态",
    "nateherkai-scroll-craft.md": "Skill-生态",
    "nicobailon-visual-explainer.md": "Skill-生态",
    "nolangz-pixel2motion.md": "Skill-生态",
    "oil-oil-beautify-github-readme.md": "Skill-生态",
    "open-gsd-get-shit-done-redux.md": "Skill-生态",
    "openTrinity-mycontext.md": "Skill-生态",
    "openai-codex-security.md": "Skill-生态",
    "obra-superpowers.md": "Skill-生态",
    "oso95-scroll-world.md": "Skill-生态",
    "petergyang-no-ai-slop.md": "Skill-生态",
    "plannotator-effective-html.md": "Skill-生态",
    "Sahir619-fable-method.md": "Skill-生态",
    "s1dashu-ip-as-logo-skill.md": "Skill-生态",
    "shadcn-improve.md": "Skill-生态",
    "shadcn-ui-lint.md": "Skill-生态",
    "t3dotgg-tstack.md": "Skill-生态",
    "thananon-9arm-skills.md": "Skill-生态",
    "tw93-Kami.md": "Skill-生态",
    "unclebob-ub-mode.md": "Skill-生态",
    "vibeforge1111-keep-codex-fast.md": "Skill-生态",
    "vinhhien112-Three.js-Object-Sculptor-Codex-Plugin.md": "Skill-生态",
    "virgiliojr94-book-to-skill.md": "Skill-生态",
    "wheresryan22-anatomy.md": "Skill-生态",
    "yusufkaraaslan-Skill_Seekers.md": "Skill-生态",
    # --- 个人AI助手-Claw系列 ---
    "BlockRunAI-ClawRouter.md": "个人AI助手-Claw系列",
    "HKUDS-ClawWork.md": "个人AI助手-Claw系列",
    "HKUDS-nanobot.md": "个人AI助手-Claw系列",
    "TinyAGI-tinyclaw.md": "个人AI助手-Claw系列",
    "agentscope-ai-CoPaw.md": "个人AI助手-Claw系列",
    "hesamsheikh-awesome-openclaw-usecases.md": "个人AI助手-Claw系列",
    "nearai-ironclaw.md": "个人AI助手-Claw系列",
    "kevinho-clawfeed.md": "个人AI助手-Claw系列",
    "sipeed-picoclaw.md": "个人AI助手-Claw系列",
    "zeroclaw-labs-zeroclaw.md": "个人AI助手-Claw系列",
    "netease-youdao-LobsterAI.md": "个人AI助手-Claw系列",
    "pinchtab-pinchtab.md": "个人AI助手-Claw系列",
    "The-Vibe-Company-companion.md": "个人AI助手-Claw系列",
    "Fei2411-DS-Bot.md": "个人AI助手-Claw系列",
    "farzaa-clicky.md": "个人AI助手-Claw系列",
    "deta-surf.md": "个人AI助手-Claw系列",
    "CaviraOSS-OpenMemory.md": "个人AI助手-Claw系列",
    "garrytan-gbrain.md": "个人AI助手-Claw系列",
    "hydra-db-open-glean.md": "个人AI助手-Claw系列",
    "inkeep-open-knowledge.md": "个人AI助手-Claw系列",
    "nashsu-llm_wiki.md": "个人AI助手-Claw系列",
    "karpathy-llm-council.md": "个人AI助手-Claw系列",
    # --- 决策模型-Jev系 ---
    "TheoLeeCJ-SemIf-OpenJev.md": "决策模型-Jev系",
    "TianyuCodings-NanoJev.md": "决策模型-Jev系",
    "bespokelabsai-nimble.md": "决策模型-Jev系",
    "browser-use-jev-ultrafast.md": "决策模型-Jev系",
    "dzhng-jevgrep.md": "决策模型-Jev系",
    "jaredpalmer-kev.md": "决策模型-Jev系",
    "mizorewww-laya-mlx.md": "决策模型-Jev系",
    "NandhaKishorM-laya.md": "决策模型-Jev系",
    "tamaratran-fast-jev-compaction.md": "决策模型-Jev系",
    # --- 基础设施层 ---
    "AlexsJones-llmfit.md": "基础设施层",
    "Edge0-AI-Edge0.md": "基础设施层",
    "FareedKhan-dev-kimi-k3-in-c.md": "基础设施层",
    "JustVugg-colibri.md": "基础设施层",
    "LaurieWired-tailslayer.md": "基础设施层",
    "Lulzx-tinypdf.md": "基础设施层",
    "Lulzx-zpdf.md": "基础设施层",
    "QuipNetwork-xq-rs.md": "基础设施层",
    "TencentCloud-CubeSandbox.md": "基础设施层",
    "ZSvirt-zsvirt.md": "基础设施层",
    "Zagitta-gpu-unlock.md": "基础设施层",
    "anthropics-claudes-c-compiler.md": "基础设施层",
    "antirez-ds4.md": "基础设施层",
    "antirez-h3.c.md": "基础设施层",
    "bellard-mquickjs.md": "基础设施层",
    "deepseek-ai-DeepInfer.md": "基础设施层",
    "deepseek-ai-DeepSpec.md": "基础设施层",
    "drumih-turbo-fieldfare.md": "基础设施层",
    "durable-streams-durable-streams.md": "基础设施层",
    "feder-cr-git-ai.md": "基础设施层",
    "firecrawl-anydoc.md": "基础设施层",
    "haydenbleasel-files-sdk.md": "基础设施层",
    "hexagonal-sun-moss-kernel.md": "基础设施层",
    "jamesob-local-llm.md": "基础设施层",
    "johannschopplich-toon.md": "基础设施层",
    "lightseekorg-tokenspeed.md": "基础设施层",
    "net-merge-net-merge.md": "基础设施层",
    "nubjs-nub.md": "基础设施层",
    "obsidianmd-pele.md": "基础设施层",
    "oxc-project-tsrs.md": "基础设施层",
    "slvDev-esp32-ai.md": "基础设施层",
    "thu-ml-TurboDiffusion.md": "基础设施层",
    "tobi-walgit.md": "基础设施层",
    "tonl-dev-tonl.md": "基础设施层",
    "vercel-labs-portless.md": "基础设施层",
    "vercel-labs-scriptc.md": "基础设施层",
    "vercel-labs-wterm.md": "基础设施层",
    "vercel-labs-zero-native.md": "基础设施层",
    "vercel-labs-zerolang.md": "基础设施层",
    "xevrion-hatchzip.md": "基础设施层",
    "yetone-magpie.md": "基础设施层",
    # --- 设计与前端 ---
    "0xGF-boneyard.md": "设计与前端",
    "AnmolSaini16-mapcn.md": "设计与前端",
    "Danilaa1-slot-text.md": "设计与前端",
    "DavidHDev-canvas-ui.md": "设计与前端",
    "Jakubantalik-thinking-orbs.md": "设计与前端",
    "Mantitup-Org-vista.md": "设计与前端",
    "MengTo-threeui.md": "设计与前端",
    "Subhan-code-Amicro--Micro-transitions-.md": "设计与前端",
    "VoltAgent-awesome-design-md.md": "设计与前端",
    "aidenybai-cnfast.md": "设计与前端",
    "aidenybai-react-grab.md": "设计与前端",
    "cloudflare-vinext.md": "设计与前端",
    "crafter-station-petdex.md": "设计与前端",
    "gaearon-rscexplorer.md": "设计与前端",
    "google-labs-code-design.md.md": "设计与前端",
    "guillermolg00-morphicons.md": "设计与前端",
    "itshover-itshover.md": "设计与前端",
    "lnkiai-m3e-canvas.md": "设计与前端",
    "lucasmarkes-hairline.md": "设计与前端",
    "mmarinovic-tailwindsql.md": "设计与前端",
    "millionco-react-doctor.md": "设计与前端",
    "nexu-io-open-design.md": "设计与前端",
    "pablodelucca-pixel-agents.md": "设计与前端",
    "pixel-point-aval.md": "设计与前端",
    "Snapchat-Valdi.md": "设计与前端",
    "thebuggeddev-anatomy.md": "设计与前端",
    "yizhiyanhua-ai-fireworks-tech-graph.md": "设计与前端",
    "zarazhangrui-beautiful-html-templates.md": "设计与前端",
    # --- 多媒体与3D ---
    "ByteDance-Seed-Depth-Anything-3.md": "多媒体与3D",
    "HKUDS-Paper2Slides.md": "多媒体与3D",
    "LTH14-JiT.md": "多媒体与3D",
    "MengTo-kage.md": "多媒体与3D",
    "NO6KIKO-gorest-2d-animation-spritesheet-generator.md": "多媒体与3D",
    "Robbyant-lingbot-map.md": "多媒体与3D",
    "Robbyant-lingbot-world-v2.md": "多媒体与3D",
    "TencentARC-Pixal3D.md": "多媒体与3D",
    "Tongyi-MAI-Z-Image.md": "多媒体与3D",
    "Vincentwei1021-video-shotcraft.md": "多媒体与3D",
    "academa-labs-manimgx.md": "多媒体与3D",
    "amagine-ai-Amagine3D.md": "多媒体与3D",
    "apple-ml-sharp.md": "多媒体与3D",
    "ashemag-human-atlas.md": "多媒体与3D",
    "black-forest-labs-flux2.md": "多媒体与3D",
    "browser-use-video-use.md": "多媒体与3D",
    "facebookresearch-vggt-omega.md": "多媒体与3D",
    "huangserva-3DCellForge.md": "多媒体与3D",
    "img2threejs-img2threejs.md": "多媒体与3D",
    "jd-opensource-JoyAI-Echo.md": "多媒体与3D",
    "jd-opensource-JoyAI-Video-Edit.md": "多媒体与3D",
    "Leonxlnx-earshot.md": "多媒体与3D",
    "microsoft-TRELLIS.2.md": "多媒体与3D",
    "neuphonic-neutts-air.md": "多媒体与3D",
    "nexu-io-html-anything.md": "多媒体与3D",
    "openfilm-openfilm.md": "多媒体与3D",
    "showlab-Paper2Video.md": "多媒体与3D",
    "supertone-oss-archive-supertonic.md": "多媒体与3D",
    "wesbos-3d-model-anything.md": "多媒体与3D",
    "xzf-thu-Mega-ASR.md": "多媒体与3D",
    "yorkeccak-history.md": "多媒体与3D",
    "YouMind-OpenLab-awesome-nano-banana-pro-prompts.md": "多媒体与3D",
    # --- 模型与研究 ---
    "Contrastive-LM-CLM.md": "模型与研究",
    "DGoettlich-history-llms.md": "模型与研究",
    "MineDojo-NitroGen.md": "模型与研究",
    "Niko1221-Strata.md": "模型与研究",
    "Pokee-AI-PokeeResearchOSS.md": "模型与研究",
    "SoMarkAI-OXR.md": "模型与研究",
    "anthropics-jacobian-lens.md": "模型与研究",
    "apple-coreai-models.md": "模型与研究",
    "baidu-Unlimited-OCR.md": "模型与研究",
    "deepseek-ai-DeepSeek-OCR.md": "模型与研究",
    "karpathy-nanochat.md": "模型与研究",
    "kyegomez-OpenMythos.md": "模型与研究",
    "openai-math.md": "模型与研究",
    "pathwaycom-arc-task-gen.md": "模型与研究",
    "sapientinc-HRM-Text.md": "模型与研究",
    # --- 金融与交易 ---
    "HKUDS-AI-Trader.md": "金融与交易",
    "NoFxAiOS-nofx.md": "金融与交易",
    "virattt-dexter.md": "金融与交易",
    "jarrodwatts-jev-trader.md": "金融与交易",
    # --- 独立品类 ---
    "ARahim3-DigUp.md": "独立品类",
    "Albert-Weasker-niubi_guard.md": "独立品类",
    "Albert-Weasker-niubigeo.md": "独立品类",
    "CodeOne45-vex-tui.md": "独立品类",
    "DietrichGebert-ponytail.md": "独立品类",
    "DuarteSantos8-openGym.md": "独立品类",
    "Facepunch-sbox-public.md": "独立品类",
    "Gathin23-cleanyourtv.md": "独立品类",
    "Gururagavendra-gmail-cleaner.md": "独立品类",
    "HermannBjorgvin-Clawdmeter.md": "独立品类",
    "HeyPuter-everything.md": "独立品类",
    "Helvesec-rmux.md": "独立品类",
    "Keychron-Keychron-Keyboards-Hardware-Design.md": "独立品类",
    "Lissy93-networking-toolbox.md": "独立品类",
    "MaximeRivest-riddle.md": "独立品类",
    "Maxteabag-sqlit.md": "独立品类",
    "Nutlope-hallmark.md": "独立品类",
    "RohanAdwankar-oxdraw.md": "独立品类",
    "Rohithgilla12-data-peek.md": "独立品类",
    "Shpigford-knockoff.md": "独立品类",
    "Veirt-weathr.md": "独立品类",
    "abusoww-tuxmate.md": "独立品类",
    "ahwootech-BRUTAL.md": "独立品类",
    "alam00000-bentopdf.md": "独立品类",
    "alejandrobujan-tendedero.md": "独立品类",
    "ammaarreshi-Generals-Mac-iOS-iPad.md": "独立品类",
    "antonmedv-textarea.md": "独立品类",
    "bgreenwell-xleak.md": "独立品类",
    "buyukakyuz-install-nothing.md": "独立品类",
    "darrylmorley-whatcable.md": "独立品类",
    "digimata-quill.md": "独立品类",
    "driceroland-Search.md": "独立品类",
    "emdash-cms-emdash.md": "独立品类",
    "f-textream.md": "独立品类",
    "facebookincubator-muse-gadget-sdk.md": "独立品类",
    "francescopace-espectre.md": "独立品类",
    "gamosoft-NoteDiscovery.md": "独立品类",
    "gavrielc-Nano-PDF.md": "独立品类",
    "getagentseal-codeburn.md": "独立品类",
    "google-gemma-gemma-translator.md": "独立品类",
    "guhcostan-mac-cleaner-cli.md": "独立品类",
    "harry0703-MangoDisk.md": "独立品类",
    "horizon-rust-horizon.md": "独立品类",
    "interplains-Zero-Breach-Toolkit.md": "独立品类",
    "karpathy-reader3.md": "独立品类",
    "lenucksi-aur-malware-check.md": "独立品类",
    "liseami-CCBaga.md": "独立品类",
    "maaslalani-sheets.md": "独立品类",
    "makerspet-oomwoo.md": "独立品类",
    "medusalix-FreeMDU.md": "独立品类",
    "mitchellh-vouch.md": "独立品类",
    "mixedbread-ai-mgrep.md": "独立品类",
    "momenbasel-PureMac.md": "独立品类",
    "motiful-cc-gateway.md": "独立品类",
    "mshumer-Claude-of-Duty.md": "独立品类",
    "mysk-research-loupe.md": "独立品类",
    "nfzerox-VirtualMacOniPad.md": "独立品类",
    "nguyenphutrong-quotio.md": "独立品类",
    "nyblnet-bento.md": "独立品类",
    "onehumanbeing-esp32-iphone-agent.md": "独立品类",
    "penecho-penecho.md": "独立品类",
    "perplexityai-bumblebee.md": "独立品类",
    "pranshuparmar-witr.md": "独立品类",
    "productdevbook-port-killer.md": "独立品类",
    "psalias2006-gpu-hot.md": "独立品类",
    "rehan-remade-universal-modder.md": "独立品类",
    "robbietilton-Compositor.md": "独立品类",
    "santifer-career-ops.md": "独立品类",
    "sheeki03-tirith.md": "独立品类",
    "simbasjungles-free-my-tv.md": "独立品类",
    "steipete-summarize.md": "独立品类",
    "storytold-wordcraft.md": "独立品类",
    "t4t5-owly.md": "独立品类",
    "tamnd-kage.md": "独立品类",
    "tandpfun-wardrobe.md": "独立品类",
    "tobi-disktree.md": "独立品类",
    "tonyantony300-dashbeam.md": "独立品类",
    "trycompai-crm.md": "独立品类",
    "tw93-Kaku.md": "独立品类",
    "unhappychoice-gitlogue.md": "独立品类",
    "vercel-labs-deepsec.md": "独立品类",
    "vinzdg-codenotch.md": "独立品类",
    "vorssaint-vorssaint-utils.md": "独立品类",
    "withmarbleapp-os-taxonomy.md": "独立品类",
    "yetone-cumora.md": "独立品类",
    "zenbu-labs-terminal-code.md": "独立品类",
}


def main() -> int:
    mapping = {
        k: v
        for k, v in json.loads(MAPPING_PATH.read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }
    files = sorted(
        f.name for f in SRC.iterdir() if f.is_file() and not f.name.startswith("分类索引")
    )

    unclassified = [f for f in files if f not in FILE_MAP]
    stale = [f for f in FILE_MAP if f not in set(files)]
    if unclassified:
        print("未分类文件（请补充 FILE_MAP）:")
        for f in unclassified:
            print(f"  {f}")
        return 1
    if stale:
        print("FILE_MAP 里多余（磁盘上不存在）:")
        for f in stale:
            print(f"  {f}")
        return 1

    copied = 0
    for fname, cat in FILE_MAP.items():
        dest_dir = SRC / cat
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / fname
        if not dest.exists():
            shutil.copy2(SRC / fname, dest)
            copied += 1

    # 分类索引.md
    lines = [
        "# trending-readme 分类索引",
        "",
        "按类型分类的 GitHub Trending 合集 README（原文件仍保留在本目录根部，",
        "子文件夹里是复制副本）。分类由 `scripts/classify_trending.py` 生成。",
        "",
    ]
    for cat, desc in CATEGORIES.items():
        members = sorted(f for f, c in FILE_MAP.items() if c == cat)
        lines.append(f"## {cat}（{len(members)}）")
        lines.append(f"> {desc}")
        lines.append("")
        for m in members:
            url = mapping.get(m, "")
            name = m.rsplit(".", 1)[0]
            lines.append(f"- [{name}]({cat}/{m}) — {url}" if url else f"- {name}")
        lines.append("")
    lines.append(f"共 {len(FILE_MAP)} 个项目 / {len(CATEGORIES)} 类。")
    INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"分类完成：{len(FILE_MAP)} 个文件，新复制 {copied} 个")
    for cat in CATEGORIES:
        n = sum(1 for c in FILE_MAP.values() if c == cat)
        print(f"  {cat}: {n}")
    print(f"索引已写入 {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
