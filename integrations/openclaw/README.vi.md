# Phone Harness cho OpenClaw

Một plugin cho [OpenClaw](https://docs.openclaw.ai) cho phép agent của bạn điều khiển một chiếc điện thoại thật
bằng một công cụ duy nhất, `phone_exec`. Mô hình viết một script Python ngắn với
các helper của Phone Harness được nhập sẵn, bạn phê duyệt nó, và plugin chạy nó trên
điện thoại rồi trả về những gì nó in ra.

```text
phone_exec(code='''
ensure_device()
open_app("Settings")
wait_stable()
print([o["text"] for o in screen()][:12])
''')
```

Plugin kèm theo skill `phone-harness`, skill này dạy agent các helper.

## Cài đặt

Bạn cần OpenClaw 2026.10.9 trở lên và [uv](https://docs.astral.sh/uv/) trên
máy chạy Gateway.

```bash
openclaw plugins install clawhub:phone-harness
```

OpenClaw cho thấy plugin có thể làm gì và yêu cầu bạn chấp nhận nó. Ở nơi nó không
hỏi được, chẳng hạn trong một script hoặc với `/plugins install` trong một cuộc trò chuyện, hãy chạy
lại lệnh với `--accept-capabilities` sau khi bạn đã xem xét plugin. Một Gateway đang
chạy sẽ nhận plugin ngay lập tức, nên không cần khởi động lại gì. Script đầu tiên
tải Phone Harness qua uv, việc này mất một lúc cho lần đầu.

Để cài từ một bản checkout thay vào đó:

```bash
git clone https://github.com/phone-harness/phone-harness
cd phone-harness/integrations/openclaw
npm install --ignore-scripts && npm pack
openclaw plugins install npm-pack:./phone-harness-0.1.2.tgz
```

Để dùng một điện thoại đám mây, đăng nhập một lần trên máy Gateway:

```bash
uvx --from phone-harness==0.3.3 phone-harness cloud login
```

Phone Harness chọn điện thoại: một điện thoại đám mây đã gắn, nếu không thì chiếc mặc định của nó.
Để ép dùng điện thoại trên máy này, hãy export `PHONE_HARNESS_PLATFORM` là `ios` hoặc
`android` trong môi trường Gateway chạy. Điều khiển iPhone cần
Accessibility và Screen Recording cho ứng dụng chạy Gateway. Android
cần adb. [install.vi.md](../../install.vi.md) trình bày từng trường hợp.

## Agent nào được dùng công cụ

- Các hồ sơ công cụ `coding` và `full` bao gồm `phone_exec`, và một cấu hình
  không có hồ sơ cũng vậy.
- Các hồ sơ `messaging` và `minimal` thì không, nên một bot trò chuyện mặc định không
  đem điện thoại của bạn ra mời. Để thêm nó, đặt `tools.alsoAllow` thành `["phone_exec"]`.
- Các phiên trong sandbox không bao giờ nhận được công cụ này. Một plugin chạy bên trong Gateway, nên một
  script sẽ chạy trên máy Gateway, bên ngoài sandbox.

## Phê duyệt

Mọi lần gọi `phone_exec` đều hỏi bạn trước khi chạy. Hộp thoại hiển thị toàn bộ
script, với mỗi dãy khoảng trắng và ngắt dòng được hiển thị thành một khoảng trắng và mọi
ký tự vô hình được viết ra rõ ràng, và bạn chọn:

- **Allow once** chạy script này.
- **Always allow** chạy script này và mọi script sau đó trong cùng phiên.
  Nó kết thúc cùng phiên, và một cuộc trò chuyện mới, một lần nạp lại plugin hoặc một lần khởi động lại Gateway
  sẽ hỏi lại.
- **Deny** dừng nó.

Phê duyệt từ Control UI, hoặc trong một cuộc trò chuyện bằng `/approve`. Nếu không ai có thể trả lời,
script không chạy. Điều đó bao gồm `openclaw agent` từ một terminal và
các công việc theo lịch. Một hộp thoại không ai trả lời sẽ hết hạn sau năm phút.

OpenClaw giữ 512 ký tự trong một hộp thoại, nên một script dài hơn 500 ký tự khi hiển thị
sẽ không được đưa ra phê duyệt chút nào. Agent được bảo chia nó thành các script ngắn hơn,
và điện thoại giữ trạng thái của nó giữa các script. Khi classifier auto-run bật,
phần lý do chiếm một phần của hộp thoại, nên một script cần hỏi sẽ có ít chỗ hơn.

Chỉ chủ sở hữu mới điều khiển được điện thoại. OpenClaw cho phép một cuộc trò chuyện trả lời
các hộp thoại phê duyệt của chính nó, nên một người gửi mà nó biết không phải chủ sở hữu sẽ bị từ chối trước mọi hộp thoại.

## Thiết lập

- Classifier auto-run tắt trừ khi bạn chọn bật. Khi bật, một script
  mà bộ phân loại đánh giá là chỉ dùng điện thoại sẽ chạy mà không hỏi. Bộ phân loại là một
  phép suy đoán và có thể bị qua mặt, nên một script vẫn có thể chạm tới máy tính này. Hãy
  để nó tắt trừ khi bạn chấp nhận điều đó. `openclaw security audit` báo cáo nó khi nó đang bật.
  - Thiết lập của plugin `plugins.entries.phone-harness.config.classifierAutoRun`
    (boolean, mặc định false).
  - Hoặc export `PHONE_HARNESS_CLASSIFIER_AUTO_RUN=1` trong môi trường Gateway
    chạy. Khi biến đó được đặt, nó thắng thiết lập của plugin.

  Trong khi auto-run đang bật, một script vẫn hỏi khi nó nhập bất cứ thứ gì ngoài các helper
  của điện thoại, đọc hoặc ghi file, chạy hoặc đánh giá code, dùng các thành phần nội bộ của Python, chạy một lệnh adb
  shell, hoặc gọi `send("raw", ...)`. Việc làm gì trên chính điện thoại (gửi, đăng, mua, xóa, thay đổi thiết lập) vẫn là
  quy tắc đồng ý của skill: agent hỏi bạn trước.
- `PHONE_HARNESS_PLATFORM`, khi bạn đã export nó, được truyền qua.
- Workspace của agent là `phone-harness/agent-workspace` trong thư mục
  trạng thái của OpenClaw, hoặc `PH_AGENT_WORKSPACE` nếu biến đó được đặt.

## Cách hoạt động

1. Mô hình gọi `phone_exec(code, timeout_s=300)`. Giới hạn là 1800 giây.
2. Một hook `before_tool_call` cho bạn xem toàn bộ script và yêu cầu bạn phê duyệt
   nó, hoặc từ chối một script quá dài để hiển thị toàn bộ.
3. Các subagent thay phiên nhau dùng điện thoại. Sau 120 giây, công cụ báo nó đang bận.
4. Plugin truyền script tới bản Phone Harness đã ghim qua `uvx`, với
   `PH_AGENT_WORKSPACE` và `PH_CLIENT=openclaw`. Môi trường của script loại bỏ
   `OPENCLAW_*` và bất cứ thứ gì có tên giống thông tin xác thực (khóa API, token,
   bí mật, mật khẩu), nhưng giữ mọi `PHONE_HARNESS_*` bạn đã export.
5. Kết quả là những gì script in ra, cộng mã thoát và phần cuối của
   stderr. Một ảnh chụp màn hình lưu trong lúc gọi được đính kèm để mô hình xem.
   Nếu file không phải hình ảnh thật, kết quả nói rõ điều đó và không có gì được đính kèm.
6. Một script vượt quá thời gian chờ, hoặc một lần gọi bị hủy, sẽ bị dừng cùng mọi tiến trình
   nó đã khởi động. Mỗi lần chạy gắn thẻ các tiến trình của nó bằng một biến môi trường, và
   plugin ghi lại những tiến trình nó thấy dưới script. Việc dừng sẽ hủy cây tiến trình của script,
   bao gồm các tiến trình trong phiên hoặc nhóm tiến trình riêng của chúng, mọi tiến trình mang thẻ hoặc đã được ghi lại, kể cả
   sau khi tiến trình cha của chúng kết thúc, và các nhóm tiến trình của chúng, và lặp lại cho đến khi không còn tiến trình nào, trong tối đa
   năm giây. Chỉ khi đó điện thoại mới trống trở lại. Trên Windows, plugin liệt kê
   cây tiến trình của script, chạy `taskkill` trên nó, chờ nó kết thúc, và kiểm tra
   rằng script cùng mọi tiến trình từng ở dưới nó đã biến mất. Nếu việc dừng không thể
   xác nhận, kết quả nói rõ điều đó và điện thoại vẫn bị giữ cho đến khi xác nhận được. Một
   tiến trình tách ra trước khi plugin ghi lại nó có thể sống lâu hơn lần gọi nếu nó
   bỏ thẻ, hoặc trên macOS nếu nó là một trong các chương trình của chính Apple, mà môi trường
   của chúng bị macOS ẩn đi. Trên Windows, một tiến trình mà tiến trình cha của nó đã kết thúc
   thì không còn trong cây nữa.

## Plugin chạm vào những gì

- Chạy Python do mô hình viết trên máy Gateway, với tư cách người dùng đang chạy OpenClaw.
- Chạm và gõ vào chiếc điện thoại thật của bạn, với các ứng dụng và tài khoản của bạn.
- Ảnh chụp màn hình là các file PNG trong thư mục tạm của hệ thống.
- Một điện thoại đám mây truyền màn hình của nó tới Phone Harness Cloud và dùng cơ chế đăng nhập đám mây riêng của Phone Harness.
  Một chiếc cloud Android thuê tính phí theo phút.

## Giới hạn

- Việc phê duyệt bao quát `phone_exec`. Một agent cũng có công cụ `exec` của OpenClaw
  và một lệnh `phone-harness` có thể chạm tới điện thoại qua shell, thay vào đó dưới
  các phê duyệt exec của bạn. Hãy từ chối `exec` cho agent đó nếu bạn muốn mọi script điện thoại
  đều đi qua cổng này.
- Không tích hợp kho mật khẩu: agent không bao giờ nhập mật khẩu, PIN hay mã 2FA.
  Hãy trao lại điện thoại cho người dùng trong những trường hợp đó.
- `back()` chỉ dành cho Android; trên iPhone, agent chạm vào mũi tên quay lại của ứng dụng.

## Phát triển

```bash
npm install
npm run build   # dist/ and skills/, built from the repo's SKILL.md
npm test
```

Bản phát hành Phone Harness được ghim trên một dòng: `PHONE_HARNESS_VERSION` ở
đầu `src/phone-exec.ts`. Các lệnh `uvx` trong README này nêu cùng
bản phát hành đó, và `tests/test_openclaw_plugin.py` kiểm tra điều đó. `classifier.py`
là bộ phân loại của plugin Hermes, và cùng các kiểm tra đó giữ hai bản giống hệt nhau.

Phone Harness gửi dữ liệu sử dụng, bao gồm các script và những gì chúng in ra, tới PostHog.
Để tắt, đặt `DO_NOT_TRACK=1` trong môi trường của Gateway, hoặc chạy
`uvx --from phone-harness==0.3.3 phone-harness config set telemetry false` với tư cách
người dùng mà Gateway chạy dưới đó.
