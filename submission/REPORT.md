# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Phát Thịnh
- **MSSV:** 2A202602645
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/PhTh1789/K4-L3-DAY13-NguyenPhatThinh-2A202602645-Monitoring-LLMOps
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602645`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence            | Đường dẫn                             |
| ------------------- | ------------------------------------- |
| Pytest cuối         | `evidence/01-pytest.png`              |
| Log validator       | `evidence/02-log-validator.png`       |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log      | `evidence/04-structured-log.png`      |
| PII redaction       | `evidence/05-pii-redaction.png`       |
| Trace list          | `evidence/06-trace-list.png`          |
| Trace waterfall     | `evidence/07-trace-waterfall.png`     |
| Trace metadata      | `evidence/08-trace-metadata.png`      |
| Prompt versions     | `evidence/09-prompt-versions.png`     |
| Prompt rollback     | `evidence/10-prompt-rollback.png`     |
| Dashboard runtime   | `evidence/11-dashboard-overview.png`  |
| Incident metric     | `evidence/12-incident-metric.png`     |
| Incident log        | `evidence/13-incident-log.png`        |
| Incident trace      | `evidence/14-incident-trace.png`      |

## 3. Kết quả kỹ thuật

| Nội dung                | Baseline    | Kết quả cuối | Nhận xét |
| ----------------------- | ----------- | ------------ | -------- |
| `validate_logs.py`      | 30/100      | 100/100      | Đạt điểm tuyệt đối sau khi hoàn thiện CP1 |
| `validate_dashboard.py` | 6/6 panel   |              |          |
| `pytest`                | 22 passed   |              |          |
| Số traces hợp lệ        | 10          |              |          |
| Số PII leak             | 0           |              |          |
| Latency P95 / TTFT P95  | 1455ms/50ms |              |          |
| Retrieval success rate  | 100%        |              |          |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), trước tiên gọi `clear_contextvars()` để xóa context cũ tránh rò rỉ giữa các request. Sau đó kiểm tra header `x-request-id`: nếu client truyền lên thì tái sử dụng, nếu không có thì tự sinh chuỗi định dạng `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). Gán ID vào `request.state.correlation_id`, bind vào structlog qua `bind_contextvars(correlation_id=correlation_id)`, và đính kèm vào response headers: `x-request-id` cùng `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Trong endpoint `POST /chat` (`app/main.py`), gọi `bind_contextvars` để enrich trước khi log: `user_id_hash` (băm SHA-256 12 ký tự), `session_id`, `feature`, `model`, `env`. Các log sau đó tự động đính kèm `ts`, `level`, `service`, `event`, `correlation_id` và các chỉ số hiệu năng (`latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`).
- **Cách bảo đảm PII được scrub trước khi ghi:** Đăng ký processor `scrub_event` trong `structlog.configure()` (`app/logging_config.py`) đứng trước `JsonlFileProcessor` và `JSONRenderer`. Hàm `scrub_event` duyệt đệ quy các trường trong `payload` và `event`, áp dụng regex trong `app/pii.py` để thay thế thông tin nhạy cảm (Email, SĐT Việt Nam, CCCD 12 số, Thẻ thanh toán) thành `[REDACTED_<TYPE>]` trước khi dữ liệu được ghi xuống file `data/logs.jsonl` hoặc xuất ra console.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt điểm tuyệt đối 100/100 (0 missing required fields, 0 missing enrichment, 0 PII leak); gửi request thử nghiệm chứa email, SĐT, CCCD, thẻ và kiểm tra trực tiếp trong file `data/logs.jsonl` xác nhận dữ liệu đã được thay thế sạch sẽ; chạy toàn bộ test unit pass 22/22.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Project Langfuse cá nhân mang tên `day13-k4-l3a-2A202602645` được cấu hình độc lập qua key cá nhân trong `.env`. Mọi trace đều đính kèm metadata `correlation_id`, `user_id_hash`, `env: dev` và danh sách tags `["lab", feature, "claude-sonnet-4-5"]`.
- **Cấu trúc root/retrieval/generation observations:**
  - *Root observation:* `lab-agent-run` (type: `agent`) bao bọc toàn bộ chu trình xử lý, lưu trữ ngữ cảnh request và metadata `correlation_id`.
  - *Child observation 1:* `retrieval` (type: `retriever`) đo lường thời gian truy xuất từ RAG corpus, metadata có `query_preview` và `doc_count`.
  - *Child observation 2:* `generation` (type: `generation`) bọc quá trình suy luận của LLM, liên kết với managed prompt, lưu trữ `model`, chi tiết `usage_details` (`input`, `output`, `total` tokens) và `cost_details` (`total` USD).
- **Cách nối trace với log:** Chuỗi `correlation_id` định dạng `req-<8-hex>` do `CorrelationIdMiddleware` sinh ra được lưu đồng bộ vào trường `correlation_id` của structured log (`data/logs.jsonl`) và trường `metadata.correlation_id` của Langfuse trace. Khi có sự cố, ta chỉ cần copy `correlation_id` từ log dán vào ô tìm kiếm của Langfuse là định vị được trace ngay lập tức.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, labels: `baseline`, `production`. Template: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`.
- **Version/label candidate:** Version 2, label: `candidate`. Template: `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nPlease keep answers concise and professional.`.
- **Trace ID của mỗi version:**
  - Version 1 (Baseline / Initial Production): Correlation ID `req-0c608c9c` (Session `s_v1`)
  - Version 2 (Candidate / Promoted Production): Correlation ID `req-a2f7e7cc` (Session `s_v2`)
  - Sau khi Rollback về Version 1: Correlation ID `req-1f8580b2` (Session `s_rollback`)
- **Cách promote và rollback `production`:**
  - *Promote:* Trên giao diện Langfuse (hoặc qua API `update_prompt`), gán label `production` cho Version 2. Ứng dụng tự động tải Version 2 cho các lượt request tiếp theo.
  - *Rollback:* Khi cần phục hồi, chuyển lại label `production` sang Version 1 (`baseline`). Hệ thống ngay lập tức quay lại sử dụng Version 1 mà không cần sửa code hay khởi động lại ứng dụng.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard được dựng tại route `/dashboard` (hoạt động trực tiếp trên server FastAPI) tuân thủ 100% contract `config/dashboard.yaml` đọc từ nguồn chuẩn `data/logs.jsonl`, time range 60 phút, tự động làm mới mỗi 30 giây gồm 6 panel:
  1. `Latency percentiles and TTFT` (ms): Hiển thị P50, P95, P99 và TTFT P95 kèm đường ngưỡng `P95 <= 3000ms`.
  2. `Request traffic` (requests/min): Biểu đồ lưu lượng request nhận được theo phút và tốc độ trung bình, ngưỡng `Rate >= 1 req/min`.
  3. `Error rate and retrieval success` (%): Biểu đồ tròn tỉ lệ lỗi (ngưỡng `<= 2.0%`) và tỉ lệ retrieval thành công từ vector store.
  4. `Cost over time` (USD): Biểu đồ chi phí tích lũy theo phút và số dư ngân sách còn lại, ngưỡng `Total <= $2.5 USD`.
  5. `Input and output tokens` (tokens): Phân tách lượng token đầu vào (input) và token sinh ra (output), ngưỡng `<= 50,000`.
  6. `Quality proxy` (score 0.0 - 1.0): Điểm chất lượng trung bình dựa trên heuristic (độ dài, sự hiện diện context, tính liên quan câu hỏi), ngưỡng `>= 0.75`.
- **SLO và lý do chọn:** Primary SLO là `fast_successful_requests`: Tỉ lệ request thành công có độ trễ `<= 3000ms` phải đạt tối thiểu `99.5%` trong chu kỳ rolling window 28 ngày (`target_percent: 99.5%`). Lý do chọn: Ngưỡng 3 giây là giới hạn tâm lý phản hồi tối ưu của người dùng khi hỏi đáp với AI chatbot; mục tiêu 99.5% vừa bảo đảm trải nghiệm ổn định cho đa số người dùng vừa chừa biên độ an toàn cho các cập nhật mô hình.
- **Cách tính error budget:** Error budget = `100% - Target% = 100% - 99.5% = 0.5%`. Nghĩa là trong toàn bộ request nhận được trong 28 ngày, tối đa 0.5% request được phép chậm hơn 3 giây hoặc bị lỗi HTTP 500. Ví dụ: Với 10,000 requests/tháng, ngân sách lỗi cho phép tối đa 50 requests không đạt chuẩn. Khi error budget bị cạn kiệt (> 0.5%), đội ngũ phải tạm hoãn phát hành prompt/tính năng mới để ưu tiên khắc phục hiệu năng.
- **Ba alert và runbook tương ứng:** Cấu hình trong `config/alert_rules.yaml` và chi tiết runbook tại `docs/alerts.md`:
  1. `high_latency_p95` (Warning, duration 5m): P95 latency > 3000ms liên tục trong 5 phút. Runbook: Kiểm tra panel 1 xem TTFT có tăng không, lọc `data/logs.jsonl` tìm correlation ID có latency cao, mở Langfuse waterfall xem span `retrieval` hay `generation` bị chậm; tạm thời bật cache RAG hoặc giảm top_k document.
  2. `high_error_rate` (Critical, duration 3m): Error rate > 2% hoặc retrieval success < 90% trong 3 phút. Runbook: Kiểm tra panel 3 xác định loại lỗi, lọc log `request_failed`, mở trace định vị exception ở vector store; bật circuit breaker chuyển sang degraded mode (trả về fallback tĩnh) thay vì ném lỗi 500.
  3. `daily_cost_spike` (Warning, duration 5m): Tốc độ chi phí > $0.05/phút hoặc tổng chi phí vượt $2.5 USD. Runbook: Kiểm tra panel 4 & 5 xem output token có tăng đột biến không, lọc log tìm `tokens_out > 500`, mở trace xem prompt version nào đang chạy; áp đặt max_tokens hoặc rollback prompt v2 về v1 nếu câu trả lời bị lặp từ.

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
