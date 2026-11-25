<div align="center">
  <a href="https://phone-harness.com?utm_source=github&utm_medium=readme&utm_campaign=header">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/logo-animated-dark.svg?v=6f742c0">
      <img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/logo-animated.svg?v=6f742c0" alt="phone-harness" width="560">
    </picture>
  </a>
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/tagline-dark.svg?v=6f742c0">
    <img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/tagline.svg?v=6f742c0" width="600" height="48" alt="Let your agent use your phone.">
  </picture>
</div>

---

<p>
  <a href="https://phone-harness.com/docs?utm_source=github&utm_medium=readme&utm_campaign=button-docs"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/button-docs-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/button-docs.svg?v=6f742c0" width="98" height="40" align="top" alt="Docs"></picture></a>
  <a href="https://phone-harness.com/dashboard?utm_source=github&utm_medium=readme&utm_campaign=button-cloud"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/button-cloud-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/button-cloud.svg?v=6f742c0" width="104" height="40" align="top" alt="Phone Harness Cloud"></picture></a>
  <a href="https://phone-harness.com/dashboard?utm_source=github&utm_medium=readme&utm_campaign=callout"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/callout-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/callout.svg?v=6f742c0" width="230" height="40" align="top" alt="Try your own cloud Android phone for free!"></picture></a>
  <a href="https://discord.gg/7FwGsjvjS"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-discord-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-discord.svg?v=6f742c0" width="32" height="40" align="right" alt="Discord"></picture></a><a href="https://www.linkedin.com/company/phone-harness"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-linkedin-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-linkedin.svg?v=6f742c0" width="32" height="40" align="right" alt="LinkedIn"></picture></a><a href="https://github.com/phone-harness/phone-harness"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-github-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-github.svg?v=6f742c0" width="32" height="40" align="right" alt="GitHub"></picture></a><a href="https://x.com/phone_harness"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-x-dark.svg?v=6f742c0"><img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/icon-x.svg?v=6f742c0" width="32" height="40" align="right" alt="X"></picture></a>
</p>

---

[English](README.md) | Tiếng Việt

Cho phép Claude Code, Codex, hoặc bất kỳ agent nào dùng chiếc điện thoại thật
của bạn. Agent có thể cuộn, chạm, gõ và đọc điện thoại của bạn mà không cần
jailbreak, không cần Xcode, và không cài gì lên điện thoại.

> **iPhone** qua cửa sổ iPhone Mirroring của Mac <br/>
> **Android** qua adb từ macOS, Linux hoặc Windows <br/>
> Điện thoại **Phone Harness Cloud**: một chiếc Android qua adb, hoặc một chiếc iPhone qua HTTPS

```
  ● agent: wants to open Weather
  │
  ● find_text("Weather") → (400, 468)
  │
  ● tap(400, 468) → reads the screen → forecast is up
  ✓ done
```

Dùng thử [Phone Harness Cloud](https://phone-harness.com/dashboard?utm_source=github&utm_medium=readme&utm_campaign=cloud) → iPhone và Android được lưu trữ sẵn với tính năng tàng hình, số điện thoại thật, 2FA và số lượng thiết bị không giới hạn

Bắt đầu bằng cách gửi [lời nhắc cài đặt](https://phone-harness.com?utm_source=github&utm_medium=readme&utm_campaign=setup-prompt) cho
coding agent của bạn.

## Demo

**Task:** "Buy me a Waymo to Delah Coffee from my current location."

<img src="https://raw.githubusercontent.com/phone-harness/media/main/phone-harness/demo-waymo.gif?v=6f742c0" width="100%" alt="An agent orders a Waymo to Delah Coffee on a real iPhone through phone-harness">

## Cài đặt

Đối với CLI, hãy gửi lời nhắc cài đặt này cho agent của bạn (Claude Code, Codex, Grok Bot và nhiều nữa):

```text
Install or upgrade phone-harness to the latest stable version with uv using Python 3.12, register the skill from `phone-harness skill`, then read https://github.com/phone-harness/phone-harness/blob/main/onboarding.md and walk me through it. Follow https://github.com/phone-harness/phone-harness/blob/main/install.md if setup or connection fails.
```

Agent sẽ cài CLI, hỏi bạn muốn dùng điện thoại nào, và hướng dẫn bạn qua các
bước cần đến tay bạn. Mỗi loại điện thoại cần:

| Điện thoại | Cần có |
| --- | --- |
| **iPhone** | macOS 15+, iPhone Mirroring đã ghép nối với iPhone chạy iOS 18+, quyền Accessibility và Screen Recording |
| **Android** | adb và USB debugging, trên macOS, Linux hoặc Windows |
| **Cloud Android / iPhone** | Tài khoản [Phone Harness Cloud](https://phone-harness.com/dashboard?utm_source=github&utm_medium=readme&utm_campaign=setup-table); cloud Android còn cần thêm adb |

`phone-harness doctor` kiểm tra việc cài đặt. Chi tiết đầy đủ: [install.vi.md](install.vi.md) và [setup/](setup/).

**MCP:** thêm `https://mcp.phone-harness.com/mcp` vào bất kỳ MCP client nào ([hướng dẫn cài đặt](https://github.com/phone-harness/mcp)). Hiện chỉ hỗ trợ Cloud Android và iPhone.

**Hermes Agent:** `hermes plugins install phone-harness/phone-harness/integrations/hermes`. Xem [integrations/hermes](integrations/hermes/README.vi.md).

**OpenClaw:** `openclaw plugins install clawhub:phone-harness`. Xem [integrations/openclaw](integrations/openclaw/README.vi.md).

## Cách dùng

```bash
phone-harness <<'PY'
open_app("Notes")
tap_text("New Note")
type_text("hello from the harness")
print([o["text"] for o in screen()][:10])
PY
```

Các helper được nhập sẵn; [helpers.py](src/phone_harness/helpers.py) có danh sách đầy đủ. Agent lưu các helper của riêng nó trong `~/.phone-harness/agent-workspace`.

## Phone Harness Cloud

Không có điện thoại trên bàn, hoặc cần nhiều hơn một chiếc? [Phone Harness Cloud](https://phone-harness.com/dashboard?utm_source=github&utm_medium=readme&utm_campaign=cloud-section) lưu trữ chúng cho bạn:

- **Điện thoại Android** theo yêu cầu: một chiếc mới cho mỗi phiên, hoặc một chiếc đã lưu giữ nguyên ứng dụng và thông tin đăng nhập.
- **iPhone thật chuyên dụng**, điều khiển qua HTTPS từ bất kỳ hệ điều hành nào.
- **Xem trực tiếp** điện thoại trong trình duyệt trong khi agent làm việc.

```bash
phone-harness cloud login            # once: approve in your browser
phone-harness cloud ls               # phones on the account, and any live session
phone-harness cloud start            # cloud.phone if set, else a temporary Android; 15 min (--for 90s, 15m)
phone-harness cloud start ios        # the account's iPhone, when only one is listed
phone-harness <<'PY'
print(screenshot())
PY
phone-harness cloud stop             # ends the session; a saved Android is written back
```

Cùng những helper đó điều khiển một chiếc điện thoại đám mây: Android qua adb,
iPhone qua HTTPS. `cloud start` nhận tên hoặc id của điện thoại từ `cloud ls`,
hoặc `ios` / `android`; nếu không chỉ định, nó khởi động một chiếc Android tạm
thời. `phone-harness cloud` liệt kê mọi lệnh.

Tài khoản chưa có cloud iPhone nào, hoặc cần thêm? Hãy đặt trước với khoản đặt
cọc hoàn lại $20 cho mỗi điện thoại. Lệnh sẽ in ra một báo giá — con số đó là
con số chính thức — và một liên kết Stripe Checkout. Bạn thanh toán trong trình
duyệt, và chính khoản thanh toán đó giữ chỗ của bạn trong hàng đợi, theo thứ tự
đặt cọc; CLI không bao giờ thanh toán thay bạn.

```bash
phone-harness cloud reserve --type iphone --plan monthly --qty 2 \
  --use-case "Testing our app on real iPhones" --open
phone-harness cloud reservations             # status, place in the queue, deposit, when it was paid
phone-harness cloud reservations cancel ID   # leave the queue; the deposit still held goes back to the card that paid
```

`--type` là `iphone` hoặc `iphone-esim`, và `--plan` là `monthly` hoặc `annual`. Đặt trước chỉ dành cho iPhone (có hoặc không có eSIM). Các giả lập Cloud Android thuộc gói $20 và không cần đặt trước. Gói bắt đầu khi điện thoại được bàn giao; khoản đặt cọc được trừ vào hóa đơn đầu tiên và từ đó không còn được hoàn lại. Một tài khoản có thể có năm lượt đặt trước chưa thanh toán mỗi giờ, và hủy một lượt không giải phóng một chỗ.

## Cách hoạt động

Mọi điện thoại đều đứng sau cùng một bộ helper, nên một script viết cho chiếc này chạy được trên các chiếc khác.

- **iPhone:** chụp cửa sổ iPhone Mirroring, đọc bằng Vision OCR của Apple, và gửi các thao tác chạm, vuốt và gõ dưới dạng sự kiện đầu vào.
- **Android:** adb cho ảnh chụp màn hình và thao tác nhập, cây accessibility cho văn bản. USB hoặc Wi-Fi.
- **Cloud Android:** giống Android, qua adb tới một điện thoại được lưu trữ.
- **Cloud iPhone:** các thao tác qua HTTPS.

`phone-harness config set platform ios|android` chọn điện thoại mặc định. `phone-harness update` nâng cấp CLI, và in một dòng khi có phiên bản mới (`PHONE_HARNESS_NO_UPDATE_CHECK=1` tắt thông báo đó).

## Giới hạn

- Mở khóa iPhone sẽ tạm dừng mirroring; một chiếc Android khóa bằng PIN cần người dùng xử lý.
- OCR chỉ thấy văn bản, không thấy biểu tượng. Các nút điều khiển không có nhãn cần ảnh chụp màn hình và một
  mô hình có khả năng nhìn.
- Không hỗ trợ đa điểm chạm, không hỗ trợ các luồng camera hay Face ID. Video có DRM sẽ hiển thị màu đen.
- Kết nối điện thoại luôn là việc của người dùng.

## Tài trợ

phone-harness miễn phí và được duy trì trong thời gian rảnh của tôi.
[Tài trợ](https://github.com/sponsors/ShawnPana) giúp nó tiếp tục như vậy.
