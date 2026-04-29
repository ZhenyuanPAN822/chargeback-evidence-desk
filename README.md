# Chargeback Evidence Desk

[English](README.md) | 中文

一个本地优先的支付争议证据整理台，帮助小商家在 Stripe、Shopify、PayPal、Square 的 chargeback / dispute 截止日前整理证据和下一步动作。

- 把混乱的争议 CSV、复制出来的后台文字、手动输入案件统一成可检查的争议记录。
- 按截止日期、涉案金额、证据缺口、争议原因自动排序。
- 生成 Markdown / JSON 证据包草稿，明确每个案件下一步该补什么材料。

上线前补充截图或 GIF。

快速体验：

```bash
python server.py
# 打开 http://127.0.0.1:8784
```

## Hero Section

Chargeback Evidence Desk 面向小型电商、工作室、服务商和自由职业业务。它解决的不是“知道有一笔争议”这个问题，而是争议发生后最紧张的操作问题：哪个案件最急、哪笔金额风险最高、缺什么证据、不同争议原因应该准备哪些材料、证据包应该怎么组织。

## Problem

很多小商家收到 chargeback 通知时，钱已经先从账户里扣走了。接下来他们需要在很短时间内找到订单、确认截止日期、判断争议原因、收集物流或交付证明、整理客户沟通记录，再把这些内容写成简洁的提交材料。这个过程靠脑子记、靠表格排、靠临时翻后台，很容易漏掉关键证据或错过截止日期。

## Why Existing Approaches Are Not Enough

支付平台后台通常提供上传证据的位置，但不会替商家跨平台统一排序。普通表格可以记录案件，但通常不会把 reason code 转成缺失证据、截止日期风险和证据包结构。网上的 chargeback 教程也有帮助，但商家仍然需要自己把泛泛建议映射到每个具体案件。

## What This Project Does

CSV 导出、后台文字粘贴或手动录入 -> 字段映射 -> 人工 review 表 -> 证据要求评分 -> 截止日与金额优先级 -> Markdown / JSON 证据包报告。

## Why this is useful

这个项目不是通用的上传文件出报告页面。它聚焦在提交证据前的操作决策：先处理哪一笔、缺哪些证据、哪个平台和争议原因需要什么材料、证据包应该包含哪些段落、哪些结论因为信息不足必须降低置信度。

## Key Features

- 支持 Stripe-like、Shopify-like、PayPal-like、Square-like 和通用表格导出的灵活 CSV 字段映射。
- 支持粘贴争议邮件、后台页面、PDF 复制文本或 OCR 文本。
- 支持单个案件手动录入。
- 分析前必须经过 normalized review table。
- 按截止日期、涉案金额、证据完整度、缺失字段计算优先级。
- 针对 fraud、product_not_received、not_as_described、duplicate、refund、service 等原因给出证据清单。
- 按处理平台生成 processor board。
- 提供内部 deadline buffer 和缺失 tracking evidence 的 what-if 提示。
- 本地保存 Markdown 和 JSON 报告。
- 不需要账号、不需要 API key、不上传数据。

## Demo / Screenshots

上线前补充截图或 GIF。

内置样例包含 24 条争议记录，覆盖 Stripe、Shopify、PayPal、Square，包括过期截止日、紧急截止日、缺 tracking、缺 due date、数字商品、服务争议、高金额争议、低金额争议、退款、重复扣款、欺诈、未收到商品等情况。

## Quick Start

```bash
python server.py
```

打开 `http://127.0.0.1:8784`，点击 `Load 24-case sample`，再点击 `Analyze evidence queue`。

运行测试：

```bash
python -m unittest discover -s tests
python scripts/smoke_test.py
```

## Example Input / Output

输入示例：

- `samples/chargebacks_24_cases.csv`
- `samples/stripe_like_disputes.csv`
- `samples/pasted_dispute_examples.txt`

输出文件：

- `outputs/chargeback-evidence-report.md`
- `outputs/chargeback-evidence-report.json`
- `examples/` 中包含已生成的样例报告

报告会包含 executive summary、processor summary、按截止日排序的优先队列、缺失证据、置信度、建议下一步动作和每个案件的证据包段落。

## Use Cases

- Shopify 商家同时遇到多笔 chargeback，需要先判断哪笔最急。
- Stripe 卖家需要检查 fraud / product_not_received 案件是否缺 AVS、device、tracking 或沟通记录。
- PayPal 卖家想在上传 seller protection 材料前先整理本地清单。
- Square 商家需要在后台提交前准备一份简洁证据包。
- 小型 agency 想在不上传客户数据到 SaaS 的情况下整理服务争议。

## How It Works

应用会把常见列名映射成统一的 dispute model，然后根据争议原因应用证据要求，结合 due date、内部 review buffer、金额、证据缺口和字段置信度生成优先级。粘贴文本解析使用保守正则，不假装是 OCR；低置信度字段会提示人工 review。

## Project Structure

```text
chargeback_evidence_desk/analyzer.py   导入、解析、评分、报告生成
server.py                              本地 web server 和 API
web/                                   浏览器工作台
samples/                               真实感 CSV 和粘贴文本样例
tests/                                 单元测试
scripts/smoke_test.py                  用户视角 smoke test
examples/                              生成的样例报告
```

## Roadmap

- Stripe、Shopify、PayPal、Square 的 source-specific export preset。
- PDF / 图片 OCR 导入。
- 本地附件 checklist。
- 不同处理平台的证据包格式。
- 给代理商批量处理争议用的 CLI / CI 模式。
- GitHub 发布用截图或 GIF。

## Limitations

Chargeback Evidence Desk 是操作准备工具，不是法律建议，也不能保证争议结果。它不会自动提交证据到支付平台，不连接 Stripe / Shopify / PayPal / Square API，也不做 PDF 或图片 OCR。粘贴文本解析是保守规则，正式使用前必须人工检查。支付平台规则可能变化，最终提交前仍应以对应平台后台和官方文档为准。

## License

MIT

## Language

- English: `README.md`
- Chinese: `README.zh-CN.md`

