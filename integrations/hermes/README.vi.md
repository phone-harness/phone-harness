# phone-harness cho Hermes Agent

![phone-harness](assets/banner.png)

Một plugin cho [Hermes Agent](https://github.com/NousResearch/hermes-agent) cho phép
Hermes điều khiển một chiếc điện thoại thật bằng một công cụ duy nhất, `phone_exec`. Mô hình viết
một script Python ngắn với các helper của phone-harness được nhập sẵn, và plugin chạy
nó trên điện thoại rồi trả về những gì nó in ra.

```text
phone_exec(code='''
ensure_device()
open_app("Weather")
wait_stable()
print([o["text"] for o in screen()][:12])
''')
```

Khi gói `phone_harness` đã cài chứa `SKILL.md`, plugin
đăng ký file đó làm skill `phone-harness:phone-harness`, và truyền
cho Hermes phần mô tả cùng frontmatter từ file (Hermes không đọc lại
chúng cho danh sách skill). Nếu gói không kèm `SKILL.md`, không có skill nào
được đăng ký. Agent đọc các helper từ skill đó.

## Cài đặt

```bash
hermes plugins install phone-harness/phone-harness/integrations/hermes
```

Hermes cài gói `phone-harness` vào môi trường của riêng nó và hỏi
có bật plugin hay không. Các công cụ được nạp theo phiên, nên hãy bắt đầu một cuộc trò chuyện mới. Nếu một
Hermes gateway đang chạy, trước tiên hãy chạy `hermes gateway restart --detach`,
nếu không cuộc trò chuyện mới sẽ không có `phone_exec`. Khởi động lại ứng dụng Hermes desktop sau khi
cài hoặc cập nhật plugin.
Mỗi script chạy dưới dạng `python -m phone_harness.run` trên trình thông dịch của Hermes: bản
sao Hermes đã cài, tách biệt với một lệnh `phone-harness` trên `PATH`.

phone-harness chọn điện thoại (một điện thoại đám mây đã gắn, nếu không thì chiếc
mặc định của nó). Để ép dùng điện thoại trên máy này, hãy export `PHONE_HARNESS_PLATFORM`
là `ios` hoặc `android` trong môi trường Hermes chạy. Điều khiển iPhone cần
Accessibility và Screen Recording cho ứng dụng chạy Hermes (ứng dụng Hermes
desktop, hoặc terminal của bạn cho `hermes` trong shell). Android cần adb; một
điện thoại đám mây cần `phone-harness cloud login`. [install.vi.md](../../install.vi.md)
trình bày từng trường hợp. Một bản cài Hermes tiêu chuẩn không đặt `phone-harness` lên
PATH của bạn, nên ngoài Hermes hãy dùng `uvx phone-harness`.

## Thiết lập

- Mọi lần gọi `phone_exec` đều hỏi trước khi chạy. Xem [Phê duyệt](#phe-duyet).
- Classifier auto-run tắt trừ khi bạn chọn bật. Khi bật, một script
  mà bộ phân loại đánh giá là chỉ dùng điện thoại sẽ bỏ qua bước hỏi. Bộ phân loại là một
  phép suy đoán và có thể bị qua mặt, nên một script vẫn có thể chạm tới máy tính này.
  Hãy để nó tắt trừ khi bạn chấp nhận điều đó.
  - Thiết lập của plugin `classifier_auto_run` (boolean, mặc định false).
  - Hoặc export `PHONE_HARNESS_CLASSIFIER_AUTO_RUN=1` trong môi trường Hermes
    chạy. Khi biến đó được đặt, nó thắng thiết lập của plugin.
- Telemetry tắt dưới Hermes trừ khi bạn chọn bật bằng
  `phone-harness config set telemetry true`. Khi bật, mỗi lần chạy gửi
  script, phần cuối đầu ra của nó, các lần gọi helper cùng đối số, lỗi,
  loại điện thoại và một ID cài đặt tới PostHog. Nếu bạn đã đăng nhập Phone Harness
  Cloud, nó còn gửi ID tài khoản và ID phiên của bạn.
  - Với `DO_NOT_TRACK=1` hoặc `phone-harness config set telemetry false`, không có
    telemetry nào được gửi.
  - `PHONE_HARNESS_TELEMETRY`, khi bạn đã export nó, thắng `config set`.
    `DO_NOT_TRACK=1` thắng cả hai.
  - Một Hermes gateway giữ môi trường nó khởi động cùng, nên một biến
    export trong shell bạn đang trò chuyện không tới được một gateway đang
    chạy. Hãy đặt nó vào `~/.hermes/.env` thay thế. `config set` có hiệu lực từ
    lần chạy tiếp theo.
  - `phone_exec` chạy ở nơi Hermes chạy. Trên một backend terminal Docker hoặc SSH, một
    lệnh `phone-harness` trong terminal chạy trên máy đó, nên hãy đặt các biến này ở đó nữa.
  - Phone Harness Cloud giữ nhật ký hoạt động riêng của các phiên đám mây. Các
    thiết lập này không thay đổi nó.
- `PHONE_HARNESS_PLATFORM`, khi bạn đã export nó, được truyền qua.
- Workspace của agent là một thư mục, `agent-workspace`, trong thư mục
  dữ liệu plugin của Hermes. Nếu `PH_AGENT_WORKSPACE` đã được đặt, đường dẫn đó được dùng
  thay thế. Mỗi script nhận nó dưới dạng `PH_AGENT_WORKSPACE`. Nếu
  `agent_helpers.py` bị thiếu, bản mặc định đóng gói sẵn được sao chép vào; một file
  đã có ở đó được giữ nguyên.

## Cách hoạt động

1. Mô hình gọi `phone_exec(code, timeout_s=300)`.
2. Một hook `pre_tool_call` yêu cầu bạn phê duyệt mọi script trước khi nó chạy.
   Hermes hiển thị một mô tả ngắn của script. Một câu trả lời cho cả phiên,
   hoặc luôn luôn, bao quát các lần gọi sau. Khi classifier auto-run được chọn bật, một script
   chỉ điều khiển điện thoại sẽ chạy mà không hỏi, và mọi thứ khác vẫn hỏi.
3. Các subagent trong tiến trình này thay phiên nhau dùng điện thoại, qua một khóa trong tiến trình.
   Sau 120 giây, công cụ báo điện thoại đang bận.
4. Plugin truyền script qua stdin tới bản phone-harness mà Hermes đã cài,
   với `PH_AGENT_WORKSPACE` và `PH_CLIENT=hermes`. Nó không đặt nền tảng.
   Telemetry tắt trừ khi bạn chọn bật. Xem [Thiết lập](#thiet-lap).
5. Kết quả là những gì script in ra, cộng mã thoát và phần cuối
   của stderr. `screenshot()` in ra đường dẫn nó đã lưu. Đường dẫn tuyệt đối PNG,
   JPEG hoặc WebP cuối cùng trong đầu ra đó mà tồn tại và được ghi trong
   lúc gọi sẽ được đính kèm vào kết quả của công cụ khi mô hình xem được hình ảnh. Một
   hình ảnh lớn được thu nhỏ trước. Nếu mô hình không xem được hình ảnh, hoặc
   việc đính kèm thất bại, kết quả giữ dạng văn bản thuần và đường dẫn nằm trong
   `screenshots` (mở nó bằng `vision_analyze`). Một script vượt quá thời gian chờ
   sẽ bị hủy cùng mọi thứ nó đã khởi động.

## Phê duyệt

Mọi lần gọi `phone_exec` đều hỏi bạn trước khi chạy. Hermes hiển thị một
mô tả ngắn của script. Cho phép nó một lần, cho cả phiên, hoặc luôn luôn; một
câu trả lời theo phiên hoặc luôn luôn bao quát các lần gọi sau. Nếu không ai có thể trả lời (một
công việc theo lịch, hoặc một cuộc trò chuyện không có ai), script không chạy.

Classifier auto-run tắt trừ khi bạn chọn bật (xem [Thiết lập](#thiet-lap)). Khi
bật, các script chỉ dùng các helper của điện thoại sẽ chạy ngay. Việc kiểm tra là một
phép suy đoán và có thể bị qua mặt: một script vẫn có thể chạm tới máy tính này. Hãy
để nó tắt trừ khi bạn chấp nhận điều đó.

Trong khi auto-run đang bật, một script vẫn hỏi khi nó nhập bất cứ thứ gì ngoài
các helper của điện thoại, đọc hoặc ghi file, chạy hoặc đánh giá code, dùng các thành phần
nội bộ của Python, chạy một lệnh adb shell, hoặc gọi `send("raw", ...)`. Việc làm gì
trên chính điện thoại — gửi, đăng, mua, xóa, thay đổi thiết lập — vẫn là
quy tắc đồng ý của skill: agent hỏi bạn trước những việc đó.

## Plugin chạm vào những gì

- Chạy Python do mô hình viết ngay trên máy qua bản phone-harness mà Hermes đã cài.
- Chạm và gõ vào chiếc điện thoại thật của bạn, với các ứng dụng và tài khoản của bạn.
- Ảnh chụp màn hình là các file PNG trong thư mục tạm của hệ thống.
- Một điện thoại đám mây truyền màn hình của nó tới Phone Harness Cloud và dùng cơ chế đăng nhập đám mây riêng của phone-harness.
  Một chiếc cloud Android tính phí theo phút; một chiếc cloud iPhone là thuê bao cố định và không tính theo phút.
- Hermes thêm bộ công cụ của plugin vào mọi nền tảng có lựa chọn công cụ
  đã lưu, kể cả các nền tảng nhắn tin. Tắt nó ở đó bằng
  `hermes tools` trừ khi bạn muốn những người có thể nhắn tin cho bot của bạn điều khiển
  điện thoại của bạn.

## Giới hạn

- Một ảnh chụp màn hình lưu trong lúc gọi được đính kèm khi mô hình xem được
  hình ảnh. Nếu không, đường dẫn nằm trong kết quả văn bản cho `vision_analyze`.
- Không tích hợp kho mật khẩu: agent không bao giờ nhập mật khẩu, PIN hay mã 2FA.
  Hãy trao lại điện thoại cho người dùng trong những trường hợp đó.
- `back()` chỉ dành cho Android; trên iPhone, agent chạm vào mũi tên quay lại của ứng dụng.
