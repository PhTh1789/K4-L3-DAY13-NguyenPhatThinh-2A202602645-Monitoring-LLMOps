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

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

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
