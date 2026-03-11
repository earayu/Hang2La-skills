---
name: make-tierlist
description: 制作"从夯到拉"排行榜锐评视频。当用户想制作排行榜锐评视频、给事物打分排名、或从话题生成带动画的排行榜 MP4 时使用。负责协调 search-images、generate-tts 和 assemble_tierlist 脚本。
---

# make-tierlist

端到端"从夯到拉"排行榜视频生成流水线。

## 环境前置检查

**在开始任何步骤之前，若用户是第一次运行，先确认以下条件满足：**

### 1. Python 依赖
```bash
uv sync          # 推荐，使用 uv（快速）
# 或
pip install moviepy edge-tts pillow pyyaml pydantic requests aiohttp aiofiles openai numpy
```

### 2. ffmpeg（视频合成必须）
```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# 验证安装
ffmpeg -version
```

### 3. config.yaml
```bash
cp config.template.yaml config.yaml
# 最少只需填写（可选）：
#   pexels_api_key — 若要使用 Pexels 搜图
#   openai_api_key — 若要使用 OpenAI TTS
# 默认使用 DuckDuckGo 搜图 + edge-tts 配音，无需任何 API Key
```

> 如果用户报告脚本报错，先对照各 skill 末尾的"常见错误与修复"表排查，再寻求其他解法。

---

## 视频格式说明

这是一种流行的互联网排行榜视频形式：

- **背景**：固定的五档排行榜画面（夯 / 顶级 / 人上人 / NPC / 拉完了），全程可见。
- **流程**：逐一点评每位"选手"——每位选手有一张代表图，大图居中展示；配音旁白评价一番；评价结束后，图片缩小飞入对应档位行（动画约 0.6 秒）。同一档位的后续选手排列在前一位右侧。
- **语言风格**：幽默犀利，能引起共情，口语化。
- **时长**：3–10 分钟；品类 5–20 个。

---

## project.yaml 是项目蓝图

`project.yaml` 是整个项目的**单一事实来源**，支持 agent 自动生成、人工手写、或两者混合：

- **任意字段可手动填写或留空**：agent 执行前先检查字段，已存在则跳过，不会覆盖。
- **`materials/` 是素材来源目录**：每个选手有独立子文件夹，可放图片（`.jpg/.png`）、文字描述（`.txt`）、或 agent 搜图后自动保存的 `search_results.json`。
- **支持从任意步骤重做**：删掉 yaml 中某个字段（如 `text`、`audio`、`image`），让 agent 重跑对应步骤。

---

## 项目目录结构

```
projects/{项目名}/
├── project.yaml          ← 蓝图，人机共同维护
├── materials/            ← 所有原始素材（图片 + 文字描述 + 搜索元数据）
│   ├── intro/
│   │   └── photo_00.jpg
│   ├── contestant_01/    ← 每个选手一个文件夹
│   │   ├── photo_00.jpg          ← 搜到或手动放入的图片
│   │   ├── photo_01.jpg
│   │   ├── desc.txt              ← 可选：人工放入的文字说明
│   │   └── search_results.json   ← 搜图时自动保存的标题/URL 元数据
│   └── outro/
├── audio/                ← TTS 生成的音频文件
│   ├── intro.mp3
│   └── contestant_01.mp3
└── output/               ← 最终合成的视频
```

---

## 工作流

### 第 0 步 — 初始化项目

创建目录和 `project.yaml`：

```bash
mkdir -p projects/{项目名}/materials projects/{项目名}/audio projects/{项目名}/output
```

初始 `project.yaml` 模板：

```yaml
name: "{项目名}"
type: "tierlist"
topic: "{话题}，从夯到拉排名"
language: zh
resolution: "1920x1080"
fps: 24
# tts_voice 留空即可继承 config.yaml 中的 tts_provider / tts_voices 配置
# 仅当需要覆盖音色时才填写，例如：tts_voice: zh-CN-YunxiNeural

tierlist:
  background: "skills/assemble-video/assets/tierlist_bg.png"
  label_width_ratio: 0.127   # 标签列占视频宽度比例，无需修改

tiers:
  - id: "hang"
    label: "夯"
  - id: "top"
    label: "顶级"
  - id: "rsr"
    label: "人上人"
  - id: "npc"
    label: "NPC"
  - id: "la"
    label: "拉完了"

# 风格提示：几个字到一句话，agent 写文案时参考（可选）
style: "幽默犀利，互联网口语，多用比较和类比"

intro:
  text: "{片头导语，约 20–40 字}"
  audio: "audio/intro.mp3"

contestants: []   # 第 1 步填写

outro:
  text: "你有不同意见吗？咱们下期再见。"
  audio: "audio/outro.mp3"
```

---

### 第 1 步 — 规划选手与文案

**对每个选手，执行以下决策：**

```
text 字段存在？
  ✅ 已有 → 跳过
  ❌ 缺失 → 查看 materials/contestant_XX/：
      有 desc.txt？→ 读取作为参考
      有 search_results.json？→ 读取图片标题作为参考
      → 结合 name / tier / topic / style，写点评文案（100–400 字）
      → 填写 text 字段
```

文案风格要求：口语化、幽默、有共情，参考 `style` 字段。**参考时长**：约 120 汉字 ≈ 8–10 秒音频。

在 `project.yaml` 中填写 `contestants`：

```yaml
contestants:
  - index: 1
    name: "帝王牧绅一"
    keywords: "灌篮高手 牧绅一"
    tier: "hang"
    text: |
      首先是帝王牧绅一，30分且三双达成。
      整场比赛，阿牧的表现无可挑剔...
  - index: 2
    name: "赤木刚宪"
    keywords: "灌篮高手 赤木刚宪"
    tier: "hang"
    text: |
      接下来是湘北队长赤木...
```

---

### 第 2 步 — 准备素材图片

**对每个选手，执行以下决策：**

```
image 字段存在？
  ✅ 已有 → 跳过
  ❌ 缺失 → 查看 materials/contestant_XX/：
      有图片文件（*.jpg / *.png）？
        ✅ 有 → 读取 search_results.json 中的标题，选最相关的图片路径 → 填写 image
        ❌ 无 → 用 keywords 搜图（见下方命令）→ 选最相关的图片 → 填写 image
```

搜图命令（仅在素材目录无图时使用）：

```bash
python skills/search-images/scripts/search_images.py \
  --keywords "{contestant.keywords}" \
  --output "projects/{name}/materials/contestant_{index:02d}/" \
  --count 5 \
  --config config.yaml
```

脚本会下载多张图片并在目录下保存 `search_results.json`（含标题、URL）。**agent 根据 `title` 选择最相关的一张**，填入 `image` 字段。

> **选手图片将在视频中大图展示（约 720×720）**，建议优先选构图清晰、主体明显的图片。

---

### 第 3 步 — 生成音频

**对每个片段，执行以下决策：**

```
audio + duration 字段均存在？
  ✅ 均有 → 跳过
  ❌ 任一缺失 → 用 text 字段跑 TTS → 填写 audio 和 duration
```

**音色优先级**（高 → 低）：片段级 `tts_voice` → 项目级 `tts_voice` → `config.yaml` 中的 `tts_voices[language]`。
通常只需传 `--config`，provider 和音色均由 config.yaml 决定，**不要额外加 `--voice` 或 `--provider` 参数**。

```bash
python skills/generate-tts/scripts/tts.py \
  --text "{text}" \
  --output "projects/{name}/audio/{segment}.mp3" \
  --config config.yaml
```

> 若文案含换行（多行 YAML block scalar），请将文本写入临时文件再传入，避免 shell 截断：
> ```bash
> echo '{text}' > /tmp/seg.txt
> python skills/generate-tts/scripts/tts.py --text "$(cat /tmp/seg.txt)" --output ... --config config.yaml
> ```

对 `intro`、每位 `contestant`、`outro` 分别执行，更新 `project.yaml`。

---

### 第 4 步 — 合成排行榜视频

所有 `image`、`audio`、`duration` 就绪后：

```bash
python skills/assemble-video/scripts/assemble_tierlist.py \
  --project "projects/{name}/project.yaml" \
  --output  "projects/{name}/output/{name}.mp4" \
  --config  config.yaml
```

输出 JSON：
```json
{"path": "projects/myvideo/output/myvideo.mp4", "duration_seconds": 245.7}
```

---

## 人机协作：常见重做场景

| 场景 | 操作 |
|------|------|
| 对某段文案不满意 | 删除该选手的 `text`、`audio`、`duration` → 让 agent 重跑步骤 1→3→4 |
| 对某段图片不满意 | 删除 `image`，修改 `keywords`（可选）→ 让 agent 重跑步骤 2→4；或手动将新图放入 `materials/contestant_XX/` 并更新 `image` 后重跑步骤 4 |
| 自己提供图片 | 把图片放入 `materials/contestant_XX/`，填写 `image` 字段路径 → 直接运行步骤 4 |
| 自己提供文案资料 | 把说明写入 `materials/contestant_XX/desc.txt` → 删除 `text` 让 agent 读取后重写 |
| 重新录制配音 | 替换 `audio/` 下对应 mp3，删除 `duration` 字段 → 让 agent 重新探测时长后重跑步骤 4 |
| 全部重做 | 保留 `name`/`tier`/`keywords`，清空其他字段 → 让 agent 从步骤 1 开始 |

---

## project.yaml 完整字段说明

| 字段 | 说明 |
|------|------|
| `type` | 必须为 `"tierlist"` |
| `style` | 文案风格提示，几个字到一句话，agent 写文案时参考（可选） |
| `tierlist.background` | 排行榜背景图路径（使用内置资产即可） |
| `tierlist.label_width_ratio` | 左侧标签列宽比例，默认 `0.127` |
| `tiers[].id` | 档位 ID（程序内部使用） |
| `tiers[].label` | 档位显示名称（仅供参考，背景图已含标签） |
| `intro.text` / `outro.text` | 片头片尾旁白文案 |
| `contestants[].tier` | 选手档位 ID，必须匹配 `tiers[].id` |
| `contestants[].keywords` | 搜图关键词，**优先使用中文**（如 `"灌篮高手 流川枫"`） |
| `contestants[].text` | 点评旁白文案；缺失时 agent 参考 `materials/` 下的素材重新生成 |
| `contestants[].image` | 图片路径（相对于项目目录）；缺失时 agent 先查 `materials/`，无图才搜索 |
| `contestants[].audio` | 音频路径（相对于项目目录）；缺失时重跑 TTS |
| `contestants[].duration` | 音频时长（秒）；由 TTS 脚本自动填入 |

---

## 执行清单

```
- [ ] 第 0 步：project.yaml 已创建，type = "tierlist"，materials/ 目录已建
- [ ] 第 1 步：所有选手均有 text（keywords 中文优先）、tier；intro/outro 有 text
- [ ] 第 2 步：所有选手均有 image（优先使用 materials/ 已有图片，无图才搜索）
- [ ] 第 3 步：intro、contestants、outro 均有 audio 和 duration
- [ ] 第 4 步：视频合成完毕，路径已告知用户
```

---

## 注意事项

- 档位顺序决定背景图行顺序：`hang` 对应第一行（最顶），`la` 对应第五行（最底）。
- 每档位最多容纳约 8 个缩略图（1920px 宽度）；超过时缩略图会超出画面，建议控制每档在 6 个以内。
- 若某步骤脚本返回非零退出码，读取 stderr，修复后重试。
- 每步完成后立即保存 `project.yaml`，防止进度丢失。

---

## 参考脚本：湘北对海南，从夯到拉排名

> 出处：原创内容，作者猫叔。以下为格式化参考版本。

### 片头导语

湘北对海南，从"夯"到"拉"排名。
本次排名将结合比赛表现，以及井上手稿综合判定。
没看过的朋友请自行暂停观看。

---

### 选手 1：帝王牧绅一（档位：夯）

首先是帝王牧绅一，30分且三双达成。

整场比赛，阿牧的表现无可挑剔，进攻端所向披靡，单防根本没人拦得住他。
即使湘北派出赤木樱木两大内线，肌肉牧照样能将球打进。
不仅自己能得分，还能带动队友拿分，10次以上的助攻数据就是最好的证明。
逼得安西只好使出整部漫画里最夸张的四盯一大法，全力压制帝王牧。

而阿牧在防守端的贡献，完全不亚于进攻端。
他能从一号位防到五号位，湘北五虎都受到过他的"关照"。
协防也非常积极，哪里有漏洞他就堵哪里。
10个篮板以上的数据，甚至可能超过了队里的中锋高砂。

凭借攻防两端的完美表现，阿牧给个"夯"，一点毛病没有。

---

### 选手 2：赤木刚宪（档位：夯）

接下来是湘北队长赤木，33分、15板、2助攻、4盖帽。海南战是其个人生涯最高光的一战。

可以说这一战将赤木积压多年的情绪彻底宣泄了出来。
哪怕是在受伤下场的情况下，赤木依然拿到了全场最高分。
不敢想象要是赤木正常打满全场，他能拿到多少分。

而在受伤后赤木所展现出来的斗志，更是令人肃然起敬。
比赛最后时刻，赤木吃阿牧假动作起跳，在忍受剧烈疼痛的情况下，
他竟然能连续起跳，成功干扰阿牧的射篮，紧接着还能抢下防守篮板。
这份意志力，让场边的晴子掩面痛哭，鱼住更是忍不住呐喊助威。

其实安西早在下半场还有18分钟的时候，看出赤木可能撑不下去，让木暮去热身。
结果他愣是撑到了最后一秒。
就像安西说的，赤木的精神已经超越肉体极限了。

就凭这份意志和完美的数据，赤木当之无愧给到一个"夯"。

---

### 选手 3：高砂（档位：NPC）

说完赤木，接下来聊聊和他对位的高砂。数据6分。

相比起斗志高昂的大猩猩，这只小猩猩就显得有些唯唯诺诺了。
面对脚伤严重的赤木，高砂防不住就算了，教练高头让他硬闯，
他却连跟赤木正面PK的勇气都没有，气得高头破口大骂。
阿牧无奈只能让他去盯樱木，自己这个控卫来防赤木。

作为海南的正选中锋，高砂的篮板也被爆得不要不要的，整场比赛几乎毫无存在感。
也就是最后几秒，有个还算亮眼的卡位，以及靠着长相莫名其妙拿到了关键球。

勉勉强强给个NPC吧。

最后强调一点，垫脚赤木的是阿牧不是他。
注意看鞋子和腿的肤色，觉得是高砂的，是因为动画中间给他切了个镜头所造成的误导，别再冤枉他了。

---

### 选手 4：流川枫（档位：顶级）

再来是新人王流川，31分、5板、5助攻、3盖帽。

本场比赛，流川枫展现了强大的攻防能力，
尤其是赤木受伤下场期间，流川仿佛化身"神明"，
硬是靠着个人能力，帮助湘北抹平了11分的分差。
海南几乎倾尽所有，就是没法挡住他。
光上半场流川就拿了25分，气得高头把他的宝贝扇子都折断了。

如果只看半场球，流川肯定夯爆了。
只可惜这种爆种打法，没有超人般的体力根本没法延续。
下半场流川仅得到6分，在湘北最需要他的时候倒下了。
赛后他也承认，比赛失利自己有一定责任。

综合来看可以给到顶级到夯之间。

---

### 选手 5：清田信长（档位：人上人）

接着聊和他对位的清田。数据18分。

比赛刚开始的隔扣，清田给了不少人惊喜。
然而随着流川爆发，清田被各种吊打，两人间的差距显而易见。

好在他身上有股不服输的劲，加上其耐力惊人，
下半场限制流川枫，清田功不可没。
最后时刻敏锐察觉湘北战术，对三井进行的关键封盖，也是海南制胜的重要原因之一。

因此野猴子可以给到个人上人。

---

### 选手 6：樱木花道（档位：顶级）

下面是红毛猴樱木，6分、17板、2助攻、2封盖。

相比起翔阳战靠宫城助攻的2分，这次打海南樱木几乎凭自己，
足足翻了3倍，已经跟高砂一样分数了，成长速度有目共睹。

当然最厉害的还得是篮板球。
17个篮板全场封王，其中还有好几次关键的前场篮板，逼得帝王牧只能亲自出手。
全场三次犯规，全都犯在了樱木身上。

只是莫名其妙被宫益限制，以及最后的误传失误，让樱木的评级有所下降。
整体可以给到一个顶级。

---

### 选手 7：武藤（档位：拉完了）

同样是大前锋，武藤的表现可就差远了，数据只有5分，比菜鸟樱木还少。
要知道这还是给了他放投机会的情况下，整场比赛几乎隐形，不是被盖就是传球失误。

有人说武藤完美限制了三井，被误导了。
他只有阿神不在的9分钟左右，才是跟三井对位，其它时候防三井的都是阿神。
而且这几分钟，三井本就没什么球权，防守压力并不大。

无论攻防两端，武藤的贡献微乎其微，只能给到一个拉完了。

---

### 选手 8：三井寿（档位：NPC）

接下来是社会我三哥，8分、2板、6助攻。

本场比赛三井的得分排在湘北正选倒数第二，仅比樱木多了两分，这个数据显然非常不理想。
归根结底是被阿神算计了。
在之前几次的观察中，阿神就发现三井跟他很像，属于越投越有的类型。
因此他的防守策略主要就是防投。
你突破不要紧，反正内线有其它人协防，但初期一定不能让你找到投篮节奏。
这也就是为什么比赛中后段，三井好几次空位都投不进的原因。

鉴于个人情怀，我勉强给到三哥一个NPC，当然你给他拉我也觉得没什么大毛病。

---

### 选手 9：神（档位：顶级）

相较而言，阿神的表现就好多了。数据22分，海南第二，其中绝大部分都来自下半场。

凭借对射手深刻的理解能力，阿神给三井制定的防守策略非常奏效。
而在进攻端他时常给出妙传，并且没有浪费任何一次出手机会，这一点确实很"神"。

可惜运动能力不及樱木，即便形成突破，还是遭到了逆天大帽。

整体可以给到一个顶级。

---

### 选手 10：宫城良田（档位：顶级）

下面是五虎最后一位宫城，10分，16次助攻，湘北唯二拿到两双的球员。

不仅助攻数据非常亮眼，能在跟阿牧的对位中拿到10分，已经超越了平日水准。
另外井上没有统计抢断数据，本场比赛宫城有好几次精彩抢断，
抢断高砂，更是强行为湘北续命。

把这些都算上的话，宫城的数据可不比樱木差，他值得一个顶级。

---

### 选手 11：宫益义范（档位：人上人）

最后是两队替补。宫益义范，数据9分。

不管符不符合现实，至少在漫画里，宫益的确克制了樱木。
他的三分球同样弹无虚发，属于绝对不能放空的存在。
偶尔灵光一闪，还能贡献几记妙传。

尽管本身的缺陷很明显——长得矮，运动能力差，
但就凭他1米6的个头，敢给樱木放狠话的勇气，他就够得上一个"人上人"。

---

### 选手 12：木暮公延（档位：拉完了）

眼镜兄木暮相较而言，就显得黯淡太多了。

上半场上场9分多钟，除了给清田贡献一个盖帽数据，对球队毫无建树。
最后时刻临危受命，接替体能不济的流川。
结果面对阿牧的霸王色霸气，只能勉强站稳，连动作都不敢做。
唯一亮点也就一个飞身救球。

但依旧无法掩盖本场拉胯的表现。

---

### 片尾

你有不同意见吗？我是猫叔，咱们下期视频再见。
