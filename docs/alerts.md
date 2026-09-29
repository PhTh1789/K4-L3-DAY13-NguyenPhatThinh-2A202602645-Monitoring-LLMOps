# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `high_latency_p95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack (`#alerts-llmops`)
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (SLI: latency <= 3000ms, mục tiêu 99.5%)
- Điều kiện và thời gian duy trì: P95 Latency > 3000ms liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Người dùng trải nghiệm tốc độ phản hồi rất chậm, nguy cơ timeout trên client.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard Panel 1 (Latency) xác định thời điểm bắt đầu tăng vọt và xem TTFT P95 có tăng đồng thời hay không.
  2. Lọc `data/logs.jsonl` tìm các log `response_sent` có `latency_ms > 3000`, trích xuất `correlation_id`.
  3. Mở Langfuse tìm trace theo `correlation_id`: so sánh thời gian của span `retrieval` và generation để xem nghẽn ở vector store hay mô hình LLM.
- Mitigation tạm thời: Bật cache kết quả RAG, giảm top_k document hoặc tạm thời hạ độ ưu tiên của các batch query; nếu do RAG chậm thì fallback sang câu trả lời trực tiếp từ model.
- Owner: `team-oncall-llmops`

## Alert 2

- Tên: `high_error_rate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack (`#alerts-llmops`, `#oncall-urgent`)
- SLI/SLO liên quan: Guardrail `error_rate_pct_max: 2` và `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: Tỉ lệ lỗi request > 2% hoặc tỉ lệ retrieval thành công < 90% trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận phản hồi lỗi HTTP 500 ("Vector store timeout" hoặc model failure), gián đoạn dịch vụ.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra Dashboard Panel 3 (Errors) để xem phân bố `error_type` (RuntimeError, TimeoutError,...) và kiểm tra `tool_success_rate_pct`.
  2. Mở `data/logs.jsonl` lọc event `request_failed`, xem `payload.detail` và lấy `correlation_id`.
  3. Mở Langfuse trace để xác định component bị crash (ví dụ: span `retrieval` bị exception).
- Mitigation tạm thời: Kích hoạt circuit breaker cho vector store; chuyển RAG sang chế độ degraded mode (trả về generic domain knowledge hoặc cache tĩnh) thay vì ném lỗi 500 ra người dùng.
- Owner: `team-oncall-llmops`

## Alert 3

- Tên: `daily_cost_spike`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack (`#alerts-finops`)
- SLI/SLO liên quan: Guardrail `daily_cost_usd_max: 2.5`
- Điều kiện và thời gian duy trì: Tốc độ tiêu tốn chi phí > $0.05/phút hoặc tổng chi phí tích lũy trong ngày vượt ngưỡng $2.5 USD.
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp đến người dùng cuối nhưng đe dọa ngân sách vận hành của doanh nghiệp.
- Ba bước kiểm tra đầu tiên:
  1. Mở Dashboard Panel 4 (Cost) và Panel 5 (Tokens) để xem chi phí tăng do input token hay output token bùng nổ.
  2. Lọc `data/logs.jsonl` tìm các log `response_sent` có `tokens_out > 500` hoặc `cost_usd` cao bất thường.
  3. Mở Langfuse trace: kiểm tra prompt version hiện tại (`prompt_version`), kiểm tra model output tokens và xem có hiện tượng loop sinh text vô hạn hay không.
- Mitigation tạm thời: Giới hạn `max_tokens` cho LLM generation; điều chỉnh rate limit request; nếu sự cố do prompt v2 sinh quá dài thì rollback prompt về version trước ngay lập tức.
- Owner: `team-finops`

