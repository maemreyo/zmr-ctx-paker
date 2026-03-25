# So sánh chuyên sâu: `ws-ctx-engine` vs `Repomix`

Cập nhật: 2026-03-25

## 1. Tóm tắt điều hành

Nếu nhìn từ rất xa, hai dự án cùng giải một bài toán giống nhau: đưa codebase vào ngữ cảnh đủ tốt để LLM hoặc AI agent có thể hiểu và làm việc hiệu quả hơn. Nhưng nếu nhìn kỹ vào kiến trúc và workflow, chúng đi theo hai triết lý gần như khác nhau:

- `Repomix` là **packing-first product**: ưu tiên quét repo, lọc file, nén nội dung, rồi đóng gói thành một artifact AI-friendly thật nhanh.
- `ws-ctx-engine` là **retrieval-first engine**: ưu tiên tạo index bền vững, phân tích cấu trúc code, xếp hạng mức liên quan theo ngữ nghĩa + đồ thị phụ thuộc, rồi mới xuất ra artifact ở bước cuối.

Nói ngắn gọn:

- Nếu mục tiêu là **"lấy cả repo hoặc một phần lớn repo thành 1 output dễ đưa cho AI"**, `Repomix` hiện có product fit rõ ràng hơn.
- Nếu mục tiêu là **"chọn đúng những file quan trọng nhất dưới token budget, phục vụ review/agent workflow có truy hồi thông minh"**, `ws-ctx-engine` có kiến trúc tham vọng và khác biệt hơn.

Đây không chỉ là khác biệt về tính năng; nó là khác biệt về **unit of value**:

- `Repomix` tối ưu cho **artifact đầu ra**.
- `ws-ctx-engine` tối ưu cho **quyết định chọn nội dung nào nên vào artifact**.

## 2. Phạm vi và phương pháp

Báo cáo này dựa trên:

1. Khảo sát trực tiếp codebase hiện tại của repo này (`zmr-ctx-paker` / package `ws-ctx-engine`).
2. Đối chiếu với tài liệu công khai của `Repomix` (README + guide chính thức) tại thời điểm viết báo cáo.
3. So sánh theo góc nhìn sản phẩm, kiến trúc, DX, agent workflow, bảo mật, khả năng mở rộng và độ trưởng thành triển khai.

Lưu ý: phần `Repomix` trong báo cáo phản ánh public docs hiện có, không phải reverse-engineer toàn bộ source code nội bộ của họ.

## 3. Định vị sản phẩm: giống ở đâu, khác ở đâu

### 3.1. Điểm giống nhau

Cả hai đều nhắm đến các use case như:

- code review với AI
- bug investigation
- tạo context cho chat với LLM
- chuẩn bị input cho Claude / ChatGPT / Cursor / agent workflows
- tối ưu token so với việc paste repo thủ công

Cả hai cũng đều có:

- CLI
- cấu hình include/exclude
- đếm token / budget awareness
- output thân thiện với AI
- cơ chế tránh đưa toàn bộ rác build/dependency vào output
- lớp bảo mật liên quan đến secrets

### 3.2. Khác biệt cốt lõi

Khác biệt quan trọng nhất là câu hỏi mà mỗi tool ưu tiên trả lời:

- `Repomix`: **"Làm sao đóng gói repo này thành output tốt nhất cho AI?"**
- `ws-ctx-engine`: **"Trong repo này, file nào thực sự đáng được đưa vào context dưới ngân sách token hữu hạn?"**

Điều đó dẫn tới toàn bộ khác biệt phía sau:

- `Repomix` ưu tiên breadth, UX đơn giản, output ecosystem, và packaging ergonomics.
- `ws-ctx-engine` ưu tiên ranking quality, persistent indexing, query-driven retrieval, và agent-native context selection.

## 4. So sánh nhanh theo ma trận

| Tiêu chí                | `ws-ctx-engine`                                         | `Repomix`                                                   | Nhận định                                                                 |
| ----------------------- | ------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------- |
| Triết lý sản phẩm       | Retrieval-first                                         | Packing-first                                               | Khác biệt nền tảng                                                        |
| Workflow mặc định       | Index -> Search/Query -> Pack                           | Scan -> Filter -> Pack                                      | `ws-ctx-engine` phức tạp hơn nhưng có chiều sâu hơn                       |
| Cơ chế chọn file        | Semantic + PageRank + lexical/domain boosts             | Chủ yếu dựa vào lọc, token count, compression, đóng gói     | `ws-ctx-engine` mạnh hơn rõ ở relevance selection                         |
| Output formats          | XML, ZIP, JSON, Markdown                                | XML, Markdown, JSON, Plain text, split output               | `Repomix` đầy đủ và polished hơn ở output layer                           |
| Ignore/include          | YAML config + custom matcher + respect `.gitignore`     | `.gitignore` / `.ignore` / `.repomixignore` + CLI glob mạnh | `Repomix` có semantics gần sản phẩm hơn                                   |
| Compression             | Không có compression-first thực thụ                     | Có `--compress` dựa trên Tree-sitter                        | `Repomix` thắng rõ                                                        |
| Remote repo             | Không thấy support trực tiếp                            | Có remote repository support                                | `Repomix` thắng rõ                                                        |
| MCP / agent             | Có MCP read-only, init scripts cho nhiều agent          | Có MCP/integrations/plugins rộng hơn                        | `ws-ctx-engine` mạnh ở chiều sâu retrieval; `Repomix` mạnh ở distribution |
| Security                | Secret scan + RADE delimiters + path guard + rate limit | Secretlint/security checks                                  | `ws-ctx-engine` bảo vệ agent workflow sâu hơn                             |
| Độ trưởng thành product | Alpha, docs/code drift còn đáng kể                      | Ecosystem rộng, nhiều bề mặt sử dụng hơn                    | `Repomix` trưởng thành hơn ở go-to-market                                 |
| Kiến trúc dài hạn       | Có moat kỹ thuật rõ                                     | Tập trung UX/output and ecosystem                           | Tùy mục tiêu cạnh tranh                                                   |

## 5. Phân tích chuyên sâu theo từng lớp

## 5.1. Kiến trúc lõi

### `Repomix`

`Repomix` được thiết kế như một công cụ đóng gói repo thành output AI-friendly nhanh nhất có thể. Trục chính của hệ thống là:

1. đọc repo
2. áp dụng ignore/include
3. thống kê token
4. tùy chọn nén code
5. xuất ra XML / Markdown / JSON / Plain text

Tư duy này làm cho `Repomix` rất mạnh ở các use case:

- lấy snapshot toàn repo
- feed cho LLM một cách đơn giản, predictable
- tích hợp vào extension, website, GitHub workflow
- chạy trên local hoặc remote repo với ít thiết lập

### `ws-ctx-engine`

`ws-ctx-engine` không dừng ở việc đóng gói. Nó xây hẳn một pipeline retrieval:

1. parse code thành chunks
2. tạo semantic index
3. dựng dependency graph và PageRank
4. lưu metadata để phát hiện stale index
5. dựng domain map riêng
6. khi query thì mới xếp hạng và chọn file theo token budget
7. cuối cùng mới emit XML / ZIP / JSON / Markdown

Về bản chất, đây là một **code retrieval system có thêm output packer**, không phải một packer thuần.

### Kết luận lớp kiến trúc

- `Repomix` đơn giản, dễ hiểu, dễ phân phối, dễ adoption.
- `ws-ctx-engine` có chiều sâu thuật toán hơn, nhưng DX nặng hơn vì cần tư duy theo lifecycle của index.

Nếu người dùng muốn “một lệnh là có artifact”, `Repomix` hợp hơn.
Nếu người dùng muốn “truy hồi đúng phần code quan trọng trong repo lớn”, `ws-ctx-engine` thú vị hơn nhiều.

## 5.2. Cơ chế chọn ngữ cảnh

Đây là nơi `ws-ctx-engine` tạo ra khác biệt lớn nhất.

### `Repomix`

`Repomix` tối ưu chuyện:

- file nào được include/exclude
- tổng token là bao nhiêu
- có nên nén code không
- output nên hiển thị theo format nào

Tức là nó giải rất tốt bài toán **representation và packaging**.

### `ws-ctx-engine`

`ws-ctx-engine` giải bài toán **selection quality**. Hệ thống retrieval hiện tại không chỉ có semantic search, mà còn thêm:

- PageRank từ dependency graph
- exact symbol boost
- path keyword boost
- domain boost
- test penalty
- query classification (`symbol`, `path-dominant`, `semantic-dominant`)

Hệ quả là tool này có thể trả lời câu hỏi kiểu:

- “đâu là code thực sự liên quan đến authentication?”
- “nếu tôi chỉ có 30k token, file nào nên được ưu tiên trước?”
- “giữa file quan trọng theo graph và file khớp semantic, nên trộn thế nào?”

Đây là một năng lực mà `Repomix` không nhắm đến ở mức độ sâu tương tự.

### Nhận định

Nếu `Repomix` là một công cụ **đóng gói repo**, thì `ws-ctx-engine` là một công cụ **xếp hạng repo trước khi đóng gói**.

Với repo lớn, nhiều module, nhiều test, nhiều thư mục hạ tầng, khác biệt này rất đáng giá.

## 5.3. Token budget và tối ưu ngữ cảnh

### `Repomix`

Điểm mạnh của `Repomix` là biến token thành first-class UX:

- có token counting rõ ràng
- có tree/token views
- có top files theo token
- có split output
- có compression để giảm kích thước ngữ cảnh

Nó giúp người dùng kiểm soát artifact cuối cùng rất tốt.

### `ws-ctx-engine`

`ws-ctx-engine` cũng có budget awareness khá tốt:

- dùng `tiktoken`
- reserve khoảng 20% cho metadata / manifest
- chọn file theo greedy knapsack style dưới budget

Nhưng hiện tại lợi thế lớn của nó không nằm ở “nén output”, mà ở “chọn file có giá trị thông tin cao hơn”.

### Kết luận

- `Repomix` thắng ở **compression + output budget ergonomics**.
- `ws-ctx-engine` thắng ở **budget-aware relevance selection**.

Hai thứ này bổ sung cho nhau hơn là thay thế hoàn toàn nhau.

## 5.4. Parsing, chunking và hiểu cấu trúc code

### `Repomix`

Theo tài liệu công khai, `Repomix` tận dụng Tree-sitter mạnh ở lớp compression/structure extraction. Giá trị chính là giữ lại skeleton quan trọng để tiết kiệm token.

### `ws-ctx-engine`

`ws-ctx-engine` dùng Tree-sitter như lớp phân tích để sinh `CodeChunk`, sau đó feed vào retrieval pipeline. Ngoài Tree-sitter còn có:

- regex fallback
- markdown chunker riêng
- file-level embedding từ việc gộp chunk theo file

Tuy nhiên có một điểm quan trọng: phần config/README tạo cảm giác hỗ trợ ngôn ngữ rất rộng, nhưng implementation thực tế hiện rõ nhất mới tập trung vào:

- Python
- JavaScript
- TypeScript
- Rust
- Markdown

Điều này không làm thiết kế yếu đi, nhưng làm cho **perceived capability > actual capability** ở thời điểm hiện tại.

### Nhận định

- `Repomix`: dùng AST/Tree-sitter để phục vụ compression và packaging.
- `ws-ctx-engine`: dùng AST/Tree-sitter để phục vụ retrieval và ranking.

`ws-ctx-engine` có hướng đi kỹ thuật sâu hơn, nhưng hiện chưa có breadth ngôn ngữ hoặc polish tương xứng với cách nó tự mô tả.

## 5.5. Ignore semantics và kiểm soát biên repo

### `Repomix`

`Repomix` hiện mạnh ở mặt này vì có:

- `.gitignore`
- `.ignore`
- `.repomixignore`
- CLI include/ignore patterns
- semantics quen thuộc với người dùng tooling hiện đại

Đây là kiểu behavior rất “productized”: dễ dự đoán, dễ giải thích, ít bất ngờ.

### `ws-ctx-engine`

`ws-ctx-engine` có:

- `include_patterns`
- `exclude_patterns`
- `respect_gitignore`
- merge một phần `.gitignore` vào exclude runtime

Nhưng lớp matcher hiện dùng cách khớp pattern tương đối custom. Điều đó tạo ra một số rủi ro:

- semantics không đầy đủ như engine gitignore chuẩn
- xử lý negation như `!important.py` chưa hoàn chỉnh
- khả năng người dùng kỳ vọng theo chuẩn git nhưng runtime xử lý khác

### Kết luận

Đây là một khoảng cách sản phẩm rõ ràng. Nếu mục tiêu là cạnh tranh trực diện với `Repomix`, `ws-ctx-engine` nên nâng cấp ignore engine lên mức chuẩn hơn, vì đây là tính năng người dùng cảm nhận trực tiếp.

## 5.6. Output layer và workflow tiêu thụ kết quả

### `Repomix`

`Repomix` mạnh ở lớp artifact cuối cùng:

- XML mặc định rõ ràng
- Markdown / JSON / Plain text
- split output
- copy vào clipboard
- stdout mode
- remote packing
- ecosystem extension / web / editor

Nghĩa là đường đi từ “repo” sang “thứ AI có thể dùng ngay” được tối ưu rất kỹ.

### `ws-ctx-engine`

`ws-ctx-engine` có một output layer khá đáng chú ý:

- XML kiểu Repomix
- ZIP với preserved structure
- `REVIEW_CONTEXT.md` có score / reading order / lý do include
- JSON / Markdown cho agent-friendly consumption

Điểm đặc biệt là output của `ws-ctx-engine` mang tính **review package** hơn là chỉ “flattened repository dump”. Nó cố trả lời thêm:

- tại sao file này được chọn
- nên đọc theo thứ tự nào
- file nào phụ thuộc file nào

Đó là một hướng rất đúng nếu đích đến là code review hoặc AI agent reasoning nhiều bước.

### Nhận định

- `Repomix` mạnh hơn ở **breadth của output workflows**.
- `ws-ctx-engine` mạnh hơn ở **semantic meaning của package**.

Nếu phải so sánh bằng một câu:

- `Repomix` xuất ra “ảnh chụp repo cho AI”.
- `ws-ctx-engine` xuất ra “briefing packet cho AI”.

## 5.7. MCP, agent tooling và workflow cho coding assistants

Đây là một khu vực cả hai bên đều có câu chuyện, nhưng độ nhấn khác nhau.

### `Repomix`

`Repomix` có lợi thế về phân phối:

- MCP / integrations được public rõ
- extension trình duyệt
- VSCode ecosystem
- website dùng trực tiếp
- nhiều entry point cho người dùng cuối

Đây là lợi thế cực lớn ở adoption.

### `ws-ctx-engine`

`ws-ctx-engine` lại rất mạnh ở chiều sâu cho agent workflow:

- MCP server read-only, workspace-bound
- `search_codebase`, `get_file_context`, `get_domain_map`, `get_index_status`
- RADE delimiters để giảm prompt injection risk từ nội dung repo
- path guard và rate limiting
- script `wsctx-init` để bootstrap cho Claude Code, Cursor, Windsurf, Codex, Copilot, `AGENTS.md`

Điều này cho thấy dự án không chỉ muốn “tạo artifact cho AI”, mà muốn trở thành **một runtime phụ trợ cho AI coding agents**.

### Kết luận

- `Repomix` thắng ở ecosystem reach.
- `ws-ctx-engine` có thiết kế agent-security và retrieval tooling sâu hơn.

Nếu roadmap tiếp tục đúng hướng, đây có thể là moat khác biệt thật sự của dự án.

## 5.8. Bảo mật

### `Repomix`

Điểm mạnh chính là security check/Secretlint: ngăn vô tình đóng gói secrets vào artifact.

### `ws-ctx-engine`

Ngoài secret scanning/redaction, `ws-ctx-engine` còn có lớp bảo vệ dành riêng cho agent serving:

- workspace isolation
- path guard
- RADE delimiter wrapping
- read-only MCP design
- rate limiting

Nói cách khác, `ws-ctx-engine` nghĩ về bảo mật không chỉ ở mức “đừng xuất secret”, mà còn ở mức “đừng để AI tool bị lạm dụng qua nội dung repo hoặc truy cập ngoài workspace”.

### Kết luận

Nếu xét riêng cho **agent-facing runtime security**, `ws-ctx-engine` có tư duy sâu hơn `Repomix`.

## 5.9. Hiệu năng, mở rộng và đặc tính vận hành

### `Repomix`

Ưu điểm vận hành:

- không đòi hỏi lifecycle index dài hạn
- hợp tác tốt với repo local lẫn remote
- dễ chạy trong CI/CD hoặc extension
- mental model đơn giản

Nhược điểm tự nhiên:

- với repo rất lớn, nếu không split/compress thì artifact có thể vẫn rất nặng
- mọi lần chạy đều thiên về packaging pass mới

### `ws-ctx-engine`

Ưu điểm vận hành:

- index persistent, tái sử dụng được
- có `status`, `vacuum`, `reindex-domain`
- thích hợp với workflow nhiều truy vấn trên cùng một codebase
- càng dùng lặp lại, lợi ích của index càng rõ

Nhược điểm:

- setup và statefulness phức tạp hơn
- stale handling hiện thiên về rebuild hơn là incremental reindex thật sự
- chi phí nhận thức của người dùng cao hơn một tool pack đơn giản

### Kết luận

- `Repomix` hợp với **stateless packaging**.
- `ws-ctx-engine` hợp với **stateful codebase intelligence**.

## 5.10. Maturity, DX và độ nhất quán sản phẩm

Đây là phần rất quan trọng nếu so sánh như một sản phẩm thực chiến.

### `Repomix`

Nhìn từ bề mặt sử dụng, `Repomix` đang đi theo hướng product rất rõ:

- feature surface dễ hiểu
- integrations nhiều
- output workflows đầy đủ
- thông điệp sản phẩm nhất quán

### `ws-ctx-engine`

`ws-ctx-engine` có codebase giàu ý tưởng, nhưng hiện lộ một số dấu hiệu “thiết kế đi trước đóng gói sản phẩm”:

1. **Docs/code drift**
   - README vẫn nhắc `--changed-files`, nhưng CLI hiện không expose option này rõ ràng như tài liệu mô tả.
   - README chưa phản ánh đầy đủ các format output mới như JSON/Markdown.

2. **Config/runtime drift**
   - file example config mô tả nhiều section/field hơn những gì runtime thực sự parse hoặc dùng.
   - một số field như `max_workers`, `cache_embeddings`, `incremental_index` xuất hiện nhưng chưa có dấu hiệu được wiring đầy đủ.

3. **Version drift**
   - version trong package và version trong `pyproject.toml` không đồng nhất.

4. **Positioning drift**
   - README nói về breadth fallback và support rộng, nhưng implementation hiện thực tế hẹp hơn ở vài điểm.

5. **Maturity signal**
   - project classifier vẫn là `Alpha`.

### Kết luận

Nếu nhìn như một engine nghiên cứu/kỹ thuật, `ws-ctx-engine` rất đáng chú ý.
Nếu nhìn như một sản phẩm cạnh tranh trực diện với `Repomix`, nó vẫn cần thêm một vòng “product hardening” khá lớn.

## 6. `ws-ctx-engine` đang mạnh hơn `Repomix` ở đâu?

Dưới đây là những vùng mà repo này có lợi thế thực chất, không chỉ là khác biệt bề mặt:

### 6.1. Relevance ranking thật sự

Điểm mạnh lớn nhất. `ws-ctx-engine` không chỉ đóng gói cái có sẵn; nó cố quyết định cái gì đáng đọc nhất.

### 6.2. Kết hợp nhiều tín hiệu để truy hồi code

Semantic search + graph centrality + lexical/symbol/path/domain heuristics tạo ra một hướng xếp hạng hợp lý cho code review, triage, hoặc bug investigation.

### 6.3. Domain map

Khả năng ánh xạ keyword -> directory/domain là một ý tưởng hữu ích cho repo lớn, đặc biệt trong tổ chức có bounded context rõ.

### 6.4. Agent-security model

Path guard, RADE delimiters, rate limiting và read-only MCP là những quyết định trưởng thành cho bối cảnh AI agents truy cập codebase.

### 6.5. Review-oriented packaging

`REVIEW_CONTEXT.md`, reading order, lý do include, dependency hints: đây là những thứ rất có giá trị cho AI reasoning nhiều bước.

## 7. `Repomix` đang mạnh hơn repo này ở đâu?

### 7.1. Packaging UX và ecosystem

`Repomix` đã tối ưu bề mặt sử dụng: local CLI, remote repo, web, extension, editor integrations, clipboard, stdout, split output.

### 7.2. Compression như một tính năng hạng nhất

Khả năng giảm token bằng compression là lợi thế sản phẩm rất rõ. `ws-ctx-engine` hiện chưa có lớp tương đương.

### 7.3. Ignore semantics và predictable behavior

`Repomix` gần với kỳ vọng phổ biến của developer tooling hơn.

### 7.4. Breadth of use cases

`Repomix` giải tốt từ cá nhân dùng CLI, đến website, đến browser extension, đến CI packaging. Bề mặt chạm người dùng lớn hơn.

### 7.5. Product polish

Tính nhất quán giữa docs, config, CLI và mental model hiện có vẻ tốt hơn.

## 8. Nếu coi `Repomix` là benchmark, repo này đang thiếu gì?

Nếu mục tiêu là cạnh tranh trực diện hoặc vượt `Repomix` ở lớp sản phẩm, `ws-ctx-engine` nên ưu tiên các khoảng trống sau:

1. **Chuẩn hóa ignore engine**
   - hỗ trợ semantics gần chuẩn gitignore hơn
   - xử lý negation đầy đủ
   - giảm surprise cho người dùng

2. **Bổ sung compression layer**
   - có mode nén AST-aware / signature-only
   - cho phép kết hợp retrieval + compression
   - đây có thể là đòn rất mạnh nếu làm tốt hơn `Repomix`

3. **Remote repository support**
   - pack/query trực tiếp từ GitHub/GitLab
   - có chế độ trust/no-trust config rõ ràng

4. **Output ergonomics**
   - split output
   - stdout mode
   - clipboard integration
   - tree token view / top token files

5. **Docs/code/config consistency sweep**
   - đồng bộ README, CLI help, config example, package version
   - bỏ các field “aspirational” chưa wiring hoặc gắn nhãn experimental

6. **Incremental indexing thật sự**
   - reindex theo changed files thay vì rebuild phần lớn pipeline

7. **Mở rộng language support thực tế**
   - hoặc giảm bớt lời hứa trong docs, hoặc bổ sung parser support tương ứng

8. **Định vị message rõ ràng hơn**
   - không nên tự bán mình như “Repomix clone thông minh hơn”
   - nên định vị là “retrieval engine cho code agents, có thể xuất pack kiểu Repomix”

## 9. Chiến lược định vị tốt nhất cho repo này

Theo mình, hướng tốt nhất không phải là đánh trực diện `Repomix` ở mọi mặt, mà là khóa chặt một định vị khác biệt hơn:

> `ws-ctx-engine` là lớp intelligence trước khi đóng gói context cho AI.

Cụ thể hơn:

- `Repomix` = excellent universal packer
- `ws-ctx-engine` = intelligent context selector + agent retrieval runtime

Khi đó, roadmap phù hợp sẽ là:

1. củng cố retrieval quality
2. làm MCP/agent workflow thật tốt
3. thêm compression như lớp sau retrieval
4. hỗ trợ xuất artifact tương thích với workflow mà `Repomix` đang phổ biến

Nói cách khác: **đừng cố chỉ thắng ở packaging; hãy thắng ở decision quality.**

## 10. Trường hợp nên chọn tool nào

### Nên chọn `Repomix` khi:

- cần pack repo thật nhanh
- muốn output artifact có thể dùng ngay cho nhiều AI tools
- cần remote repo support
- cần web / extension / editor ecosystem
- không muốn maintain index state
- repo vừa hoặc workflow thiên về snapshot packaging

### Nên chọn `ws-ctx-engine` khi:

- repo lớn, nhiều module, cần chọn lọc mạnh
- làm code review / triage / bug investigation theo query cụ thể
- muốn tận dụng semantic search + structural ranking
- muốn AI agent truy cập codebase qua MCP read-only an toàn hơn
- chấp nhận workflow có index để đổi lấy selection quality tốt hơn

### Nên kết hợp tư duy của cả hai khi:

- muốn truy hồi file thông minh như `ws-ctx-engine`
- nhưng vẫn muốn compression + output ergonomics như `Repomix`

Thực ra đây có thể là hướng sản phẩm mạnh nhất cho repo này trong dài hạn.

## 11. Kết luận cuối cùng

`Repomix` và `ws-ctx-engine` nhìn bề ngoài cùng thuộc nhóm “chuẩn bị code cho AI”, nhưng không phải hai bản sao trực tiếp của nhau.

- `Repomix` là một **sản phẩm packaging hoàn thiện hơn**.
- `ws-ctx-engine` là một **hệ retrieval thông minh hơn về mặt ý tưởng**.

Nếu đặt câu hỏi: **tool nào đang mạnh hơn như một sản phẩm dùng ngay hôm nay?**

> `Repomix` đang nhỉnh hơn.

Nếu đặt câu hỏi: **repo nào có hướng kỹ thuật khác biệt và có thể tạo moat riêng nếu làm tới nơi tới chốn?**

> `ws-ctx-engine` có tiềm năng đáng chú ý hơn.

Điểm quan trọng nhất là repo này không nên tự ép mình thành một bản sao của `Repomix`. Nó nên hoàn thiện thứ mà `Repomix` chưa thật sự nhấn mạnh: **retrieval intelligence, relevance ranking, và agent-native context serving**.

Nếu làm tốt, hai dự án sẽ không còn là quan hệ “thay thế trực tiếp”, mà là hai công cụ ở hai lớp khác nhau của cùng một stack AI coding workflow.

## 12. Tóm tắt hành động đề xuất cho repo này

Ưu tiên cao nhất:

1. Đồng bộ docs/config/runtime/version.
2. Chuẩn hóa ignore semantics.
3. Thêm compression mode sau retrieval.
4. Hoàn thiện incremental indexing thật sự.
5. Củng cố positioning: retrieval-first, agent-native, review-oriented.

Nếu hoàn thành 5 điểm này, repo này sẽ có câu chuyện cạnh tranh rất mạnh: không chỉ “pack repo cho AI”, mà là “chọn đúng ngữ cảnh trước khi pack”.
