# Cài đặt phone-harness

phone-harness điều khiển một chiếc điện thoại thật. Quy trình chạy lần đầu dành cho agent:
https://github.com/phone-harness/phone-harness/blob/main/onboarding.vi.md.
Việc sử dụng hằng ngày là `phone-harness skill`. Nó hoạt động với một chiếc **iPhone**
qua ứng dụng iPhone Mirroring của macOS, một chiếc **Android** qua adb (USB hoặc
Wi‑Fi), hoặc một điện thoại từ Phone Harness Cloud — một chiếc Android qua adb, hoặc một
chiếc iPhone mà các helper điều khiển qua HTTPS (`phone-harness cloud start` với tên
của điện thoại đó lấy từ `cloud ls`). Dù cách nào cũng dùng cùng một bộ helper; bạn chọn một
mặc định và có thể chuyển đổi theo từng lần gọi. Đọc văn bản trên màn hình là `screen()`;
tên và chữ ký của các helper nằm trong skill (`SKILL.md`, được in ra bởi
`phone-harness skill`).

## Máy này chạy được chế độ nào?

| Chế độ | Cần có | Chi tiết |
| --- | --- | --- |
| iPhone cá nhân | macOS 15+, iPhone Mirroring đã ghép nối (iOS 18+), Accessibility + Screen Recording cho ứng dụng chạy Python | [setup/ios.md](https://github.com/phone-harness/phone-harness/blob/main/setup/ios.md) |
| Android trên bàn | macOS, Linux hoặc Windows; adb; USB hoặc Wireless debugging | [setup/android.md](https://github.com/phone-harness/phone-harness/blob/main/setup/android.md) |
| Cloud iPhone | Chỉ HTTPS; một tài khoản đã đăng nhập | [setup/cloud.md](https://github.com/phone-harness/phone-harness/blob/main/setup/cloud.md) |
| Cloud Android | HTTPS, adb, và kết nối TCP ra tới cổng adb của điện thoại | [setup/cloud.md](https://github.com/phone-harness/phone-harness/blob/main/setup/cloud.md) |
| Không cài được gì cả | một HTTP client | [setup/api.md](https://github.com/phone-harness/phone-harness/blob/main/setup/api.md) |

Không có Mac và không có điện thoại không phải là ngõ cụt: đám mây không cần phần cứng.

## Cài đặt nhanh

```bash
uv tool install --python 3.12 --upgrade --force phone-harness
```

Cần [uv](https://docs.astral.sh/uv/) và Python 3.12. Bản thân gói chấp nhận
Python 3.10 trở lên. **iPhone Mirroring cần một máy Mac.** Một chiếc cloud
iPhone (mục iOS trong danh mục của `cloud start`) được điều khiển qua HTTPS từ
bất kỳ hệ điều hành nào. **Android hoạt động trên macOS, Linux và Windows** và là mặc định
khi không dùng Mac.

Đăng ký skill để agent tìm đến nó:

```bash
# Codex
mkdir -p ${CODEX_HOME:-$HOME/.codex}/skills/phone-harness && phone-harness skill > ${CODEX_HOME:-$HOME/.codex}/skills/phone-harness/SKILL.md
```

Claude Code và các agent khác: đăng ký một skill tên phone-harness với
`phone-harness skill` làm nội dung, cộng một câu kích hoạt ngắn (ví
dụ: "Use this when the task needs the user's phone.").

Kiểm tra nhanh:

```bash
phone-harness <<'PY'
ensure_device()
PY
```

Lệnh đó kết nối tới điện thoại mặc định. Nếu thất bại, hãy dùng các mục bên dưới.

- Các helper bạn thêm vào nằm trong `~/.phone-harness/agent-workspace`, bên ngoài
  bản cài đặt, nên nâng cấp không xóa chúng. Khi `~/.phone-harness` là một
  bản git checkout, chúng nằm trong
  `~/.local/share/phone-harness/agent-workspace` (`XDG_DATA_HOME` nếu biến đó
  được đặt). Các đường dẫn này giống nhau trên mọi hệ điều hành. `PH_AGENT_WORKSPACE`
  ghi đè các đường dẫn này. Lần chạy đầu tiên sao chép các mặc định đóng gói sẵn khi
  thư mục đó chưa tồn tại. Một workspace đã có sẽ được giữ nguyên,
  kể cả một `agent_helpers.py` tùy chỉnh. Muốn có lại mặc định mới, hãy xóa
  thư mục workspace; nó sẽ được tạo lại ở lần chạy tiếp theo.
- Điện thoại mặc định được đặt bằng `phone-harness config set platform ios|android`;
  `phone-harness config` hiển thị mọi thiết lập và nguồn gốc của chúng;
  `PHONE_HARNESS_PLATFORM=android phone-harness …` ghi đè cho một lần gọi.
- `phone-harness --doctor` kiểm tra điện thoại mặc định; `--doctor ios` hoặc
  `--doctor android` kiểm tra chiếc còn lại.
- Chạy lại việc đăng ký skill sau `phone-harness update` để
  bản sao của agent khớp với code. `phone-harness update` thực hiện việc nâng cấp:
  `uv tool upgrade phone-harness` khi đây là một uv tool, `git pull
  --ff-only` trong một bản checkout, nếu không nó in ra `pip install -U
  phone-harness` và không chạy lệnh đó. Nó không bao giờ tự cập nhật. Một
  bản phát hành PyPI mới hơn được thông báo bằng một dòng stderr, tối đa mỗi ngày một lần, và chỉ trên
  một terminal; `PHONE_HARNESS_NO_UPDATE_CHECK=1` bỏ qua việc kiểm tra.
- **Không có điện thoại trên bàn?** `phone-harness cloud login`, rồi
  `phone-harness cloud ls` và `phone-harness cloud start` (mặc định của tài khoản)
  hoặc `phone-harness cloud start PHONE` với một id trong danh mục, một nhãn, hoặc
  `ios` / `android` khi nó chỉ đúng một điện thoại. Một chiếc Android cần adb, xem bên dưới.
  Một chiếc iPhone không cần adb và không cần Mac; việc điều khiển nó là **Cloud iPhone** trong
  skill. Một lần khởi động kéo dài 15 phút trừ khi bạn truyền `--for` (`90s`, `15m`,
  hoặc một số phút). Tài khoản mới nhận $5 credit (100 phút Android).
  Một giả lập cloud Android tính phí 5¢ mỗi phút từ credit đó. Một chiếc cloud iPhone là
  điện thoại thật theo gói thuê bao cố định, từ $80 mỗi tháng: nó không tính phí theo phút. Một tài khoản
  chưa có chiếc nào thì đặt trước một chiếc bằng `phone-harness cloud
  reserve`, với khoản đặt cọc hoàn lại $20 cho mỗi điện thoại: nó in ra một báo giá — báo giá
  đó là chính thức — và một liên kết nơi người dùng thanh toán
  ([setup/cloud.md](https://github.com/phone-harness/phone-harness/blob/main/setup/cloud.md)).
  Đặt trước chỉ dành cho iPhone (có hoặc không có eSIM). Các giả lập Cloud Android
  thuộc gói $20 và không cần đặt trước.

Không có uv? `pip install phone-harness` cũng được. Nâng cấp bản cài đó bằng
`pip install -U phone-harness` (chính là lệnh mà `phone-harness update` in ra cho trường hợp này).

## Làm việc từ bản checkout (dành cho người đóng góp)

```bash
git clone https://github.com/phone-harness/phone-harness ~/.phone-harness
cd ~/.phone-harness
pip install -e .
```

`pip install -e .` chỉ kéo pyobjc trên macOS. Đăng ký skill giống
như ở mục Cài đặt nhanh. Một bản checkout dùng `agent-workspace/` của riêng nó. Vì
bản clone đó nằm ở `~/.phone-harness`, một bản cài pip hoặc uv riêng sẽ lưu
helper trong `~/.local/share/phone-harness/agent-workspace` thay vì
ghi vào bản checkout.

## iPhone

Xem [setup/ios.md](https://github.com/phone-harness/phone-harness/blob/main/setup/ios.md), rồi chạy `phone-harness doctor ios`.

## Android

Xem [setup/android.md](https://github.com/phone-harness/phone-harness/blob/main/setup/android.md), rồi chạy `phone-harness doctor android`.
`phone-harness android` hiển thị các điện thoại đã biết; `phone-harness android awake --bg`
giữ một chiếc mở khóa cho một tác vụ dài và `phone-harness android rest` kết thúc việc đó.

## Cả hai

Thiết lập từng chiếc như trên; `phone-harness config set platform …` chọn mặc định,
`PHONE_HARNESS_PLATFORM=…` chọn theo từng lần gọi. Hai điện thoại trên bàn không bao giờ cản trở nhau —
iPhone được điều khiển qua cửa sổ mirroring, Android qua adb. Một
cloud iPhone là con đường thứ ba: các thao tác qua HTTPS, được trình bày trong skill.

`phone-harness config set telemetry false` tắt telemetry sử dụng, và
`DO_NOT_TRACK=1` hoặc `PHONE_HARNESS_TELEMETRY=0` trong môi trường cũng vậy. Dưới Hermes, telemetry
tắt trừ khi bạn chọn bật bằng `phone-harness config set telemetry true`. Khi bạn
đăng nhập vào Phone Harness Cloud, telemetry được liên kết với tài khoản của bạn.

## Khi gặp lỗi

`phone-harness doctor` đi qua từng bậc theo thứ tự và chỉ ra bước còn thiếu. Khi một
kiểm tra cục bộ thất bại, nó cũng chỉ hướng sang đám mây. Các lỗi thường gặp:

- **iPhone — ảnh chụp trống/đen**: Screen Recording đã được cấp nhưng
  ứng dụng chạy lệnh của bạn chưa được khởi động lại; hoặc Mirroring đang hiển thị một màn hình trung gian (iPhone in Use /
  Connect / Mac Locked) — hãy xử lý nó trên Mac, khóa iPhone nếu nó báo đang được sử dụng.
- **iPhone — chạm không có tác dụng**: thiếu Accessibility, hoặc một cửa sổ khác đã cướp
  tiêu điểm (các helper sẽ kích hoạt lại cửa sổ; kiểm tra xem có hộp thoại macOS nào không).
- **iPhone — `--doctor` báo thiếu pyobjc trên một bản cài đang hoạt động**: nó đang
  chạy một Python khác với Python có pyobjc. Chạy lại lệnh ở mục
  Cài đặt nhanh, hoặc dùng đúng trình thông dịch mà `pip install -e .` đã dùng trong một bản checkout.
  Hoặc `pip install pyobjc-framework-Quartz pyobjc-framework-Vision
  pyobjc-framework-Cocoa` cho trình thông dịch đó.
- **Android — `unauthorized`**: mở khóa điện thoại và chạm Allow trên hộp thoại "Allow
  USB debugging?" (rút ra cắm lại nếu hộp thoại không xuất hiện).
- **Android — `no-device`**: USB debugging đang tắt, vấn đề ở cáp/cổng, hoặc với Wi‑Fi:
  Wireless debugging đã tự tắt (nó tự tắt sau khi khởi động lại) hoặc điện thoại ở mạng khác
  với Mac. `adb devices` cho thấy adb nhìn thấy gì.
- **Android — `locked`**: mở khóa điện thoại; `phone-harness android awake` giữ
  nó thức trong suốt phiên. Harness không bao giờ nhập PIN.
- **Cloud iPhone — `the cloud iPhone is locked or asleep`**: nó bị bỏ không
  và đã ngủ. `wake()` đánh thức nó và bước đó có thể chạy lại. Một chiếc cloud
  iPhone được thiết lập không có mật mã, nên không có gì để nhập và không
  có gì phải hỏi người dùng.
- **Android — cây giao diện không khả dụng trên một số màn hình**: màn hình đó không bao giờ
  đứng yên (có thứ gì đó đang chuyển động), nên `uiautomator` từ chối; hãy đọc `screenshot()`
  thay thế hoặc chuyển sang một màn hình ổn định.
