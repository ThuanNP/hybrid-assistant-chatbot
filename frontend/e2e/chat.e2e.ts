import { test, expect, type Page } from '@playwright/test';

/** Gửi lần lượt các câu hỏi trong một hội thoại mới, chờ từng câu trả lời xong; trả về mã hội thoại. */
async function taoHoiThoai(page: Page, cauHoi: string[]): Promise<number> {
  await page.goto('/tro-chuyen/moi');
  await page.waitForLoadState('domcontentloaded');

  const vungNhap = page.locator('textarea.vung-nhap');
  const nutGui = page.locator('button[aria-label="Gửi câu hỏi"]');
  for (const [i, noiDung] of cauHoi.entries()) {
    await vungNhap.fill(noiDung);
    await nutGui.click();
    // Câu trả lời xong khi dòng huy hiệu của lượt trợ lý thứ i xuất hiện
    await expect(page.locator('.hang-tro-ly').nth(i).locator('app-huy-hieu-mo-hinh')).toBeVisible({
      timeout: 90_000,
    });
  }

  await expect(page).toHaveURL(/\/tro-chuyen\/\d+$/);
  return Number(new URL(page.url()).pathname.split('/').pop());
}

test.describe('Kiểm thử đầu cuối hệ thống Trợ lý AI (E2E Playwright)', () => {
  test('1. Gửi câu hỏi, thấy chữ hiện dần (ít nhất 2 lần cập nhật), có huy hiệu và nhãn AI', async ({
    page,
  }) => {
    // Điều hướng vào màn hình trò chuyện mới
    await page.goto('/tro-chuyen/moi');
    await page.waitForLoadState('domcontentloaded');

    const vungNhap = page.locator('textarea.vung-nhap');
    await expect(vungNhap).toBeVisible();

    // Nhập câu hỏi nghiệp vụ
    await vungNhap.fill('Xin chào, giới thiệu ngắn gọn về chức năng của bạn trong 2 câu.');

    const nutGui = page.locator('button[aria-label="Gửi câu hỏi"]');
    await expect(nutGui).toBeEnabled();
    await nutGui.click();

    // Theo dõi phản hồi trợ lý xuất hiện
    const hangTroLy = page.locator('.hang-tro-ly').first();
    await expect(hangTroLy).toBeVisible({ timeout: 45_000 });

    const noiDungTroLy = hangTroLy.locator('.noi-dung-tro-ly');

    // Kiểm tra chữ hiện dần qua ít nhất 2 lần cập nhật nội dung trước khi luồng hoàn tất
    let soLanCapNhat = 0;
    let doDaiTruoc = 0;
    const thoiGianKetThuc = Date.now() + 60_000;

    while (Date.now() < thoiGianKetThuc) {
      const noiDungHienTai = (await noiDungTroLy.textContent()) || '';
      const doDaiHienTai = noiDungHienTai.trim().length;

      if (doDaiHienTai > doDaiTruoc) {
        soLanCapNhat++;
        doDaiTruoc = doDaiHienTai;
      }

      // Nếu nút Dừng đã biến mất và xuất hiện huy hiệu thì quá trình phát dòng đã xong
      const nutDung = page.locator('button[aria-label="Dừng tạo câu trả lời"]');
      const dangDung = await nutDung.isVisible();
      const coHuyHieu = await hangTroLy.locator('app-huy-hieu-mo-hinh').isVisible();

      if (!dangDung && coHuyHieu && soLanCapNhat >= 2) {
        break;
      }

      await page.waitForTimeout(300);
    }

    expect(soLanCapNhat).toBeGreaterThanOrEqual(2);

    // Xác minh huy hiệu mô hình hiển thị đầy đủ
    const huyHieu = hangTroLy.locator('app-huy-hieu-mo-hinh');
    await expect(huyHieu).toBeVisible({ timeout: 15_000 });

    // Xác minh nhãn AI hiển thị
    const nhanAi = hangTroLy.locator('.nhan-ai-tao');
    await expect(nhanAi).toBeVisible({ timeout: 10_000 });
    const vanBanNhanAi = (await nhanAi.textContent()) || '';
    expect(vanBanNhanAi.toLowerCase()).toContain('ai');
  });

  test('2. Bấm Dừng giữa chừng, phần chữ đã hiện giữ nguyên', async ({ page }) => {
    await page.goto('/tro-chuyen/moi');
    await page.waitForLoadState('domcontentloaded');

    const vungNhap = page.locator('textarea.vung-nhap');
    await expect(vungNhap).toBeVisible();

    // Gửi câu hỏi dài yêu cầu mô hình phản hồi nhiều đoạn
    await vungNhap.fill(
      'Hãy phân tích chi tiết quy trình thí nghiệm định kỳ máy biến áp phân phối và các tiêu chuẩn kiểm tra dầu cách điện.',
    );

    const nutGui = page.locator('button[aria-label="Gửi câu hỏi"]');
    await nutGui.click();

    // Chờ nút Dừng xuất hiện
    const nutDung = page.locator('button[aria-label="Dừng tạo câu trả lời"]');
    await expect(nutDung).toBeVisible({ timeout: 45_000 });

    const hangTroLy = page.locator('.hang-tro-ly').first();
    const noiDungTroLy = hangTroLy.locator('.noi-dung-tro-ly');

    // Chờ có ít nhất một đoạn văn bản trả lời thật sự xuất hiện (.doan-van)
    await expect(hangTroLy.locator('.doan-van').first()).toBeVisible({ timeout: 45_000 });

    // Đợi thêm một chút để dòng có ít nhất 20 ký tự
    await expect
      .poll(async () => ((await noiDungTroLy.textContent()) || '').trim().length, {
        timeout: 20_000,
        intervals: [300],
      })
      .toBeGreaterThan(20);

    // Bấm Dừng giữa chừng
    await nutDung.click();

    // Lấy nội dung ngay khi bấm Dừng
    const noiDungSauKhiDung = (await noiDungTroLy.textContent()) || '';
    expect(noiDungSauKhiDung.trim().length).toBeGreaterThan(0);

    // Chờ 2 giây để xác minh không có thêm dữ liệu phát tiếp
    await page.waitForTimeout(2000);

    const noiDungKiemChung = (await noiDungTroLy.textContent()) || '';
    expect(noiDungKiemChung.trim()).toBe(noiDungSauKhiDung.trim());

    // Nút dừng biến mất, nút gửi được khôi phục
    await expect(nutDung).not.toBeVisible();
    await expect(page.locator('button[aria-label="Gửi câu hỏi"]')).toBeVisible();
  });

  test('3. Tải lại trang, hội thoại vẫn có trong nhóm GẦN ĐÂY và màn Lịch sử hội thoại, mở lại thấy đủ lượt', async ({
    page,
  }) => {
    // Tự tạo hội thoại hai lượt, không dựa vào dữ liệu của kịch bản khác
    const id = await taoHoiThoai(page, [
      'Kiểm thử E2E lịch sử: trả lời đúng một câu ngắn.',
      'Kiểm thử E2E lịch sử: nhắc lại câu trả lời trước trong một câu.',
    ]);

    try {
      // Tải lại trang
      await page.reload();
      await page.waitForLoadState('networkidle');

      // Hội thoại vừa tạo có trong nhóm GẦN ĐÂY ở thanh điều hướng bên
      await expect(page.locator(`.muc-gan-day[href="/tro-chuyen/${id}"]`)).toBeVisible({
        timeout: 15_000,
      });

      // Điều hướng tới màn Lịch sử hội thoại
      const menuLichSu = page.locator('.sidebar a[title="Lịch sử hội thoại"]');
      await menuLichSu.click();
      await expect(page).toHaveURL(/\/lich-su/);

      // Hội thoại vừa tạo có trong danh sách lịch sử; mở lại
      const lienKetMo = page.locator(`.muc-hoi-thoai .lien-ket-muc[href="/tro-chuyen/${id}"]`);
      await expect(lienKetMo).toBeVisible({ timeout: 15_000 });
      await lienKetMo.click();
      await expect(page).toHaveURL(new RegExp(`/tro-chuyen/${id}$`));

      // Mở lại thấy đủ hai lượt người dùng và hai lượt trợ lý
      await expect(page.locator('.hang-nguoi-dung')).toHaveCount(2, { timeout: 10_000 });
      await expect(page.locator('.hang-tro-ly')).toHaveCount(2);
    } finally {
      await page.request.delete(`/api/v1/hoi-thoai/${id}`);
    }
  });

  test('4. Xoá hội thoại ở màn Lịch sử hội thoại qua hộp thoại xác nhận của ứng dụng', async ({
    page,
  }) => {
    // Tự tạo hội thoại để xoá, không đụng tới hội thoại có sẵn trong CSDL
    const id = await taoHoiThoai(page, ['Kiểm thử E2E xoá hội thoại: trả lời đúng một câu ngắn.']);

    // Điều hướng tới màn Lịch sử hội thoại
    await page.goto('/lich-su');
    await page.waitForLoadState('networkidle');

    const mucCanXoa = page.locator('.muc-hoi-thoai', {
      has: page.locator(`.lien-ket-muc[href="/tro-chuyen/${id}"]`),
    });
    await expect(mucCanXoa).toBeVisible({ timeout: 15_000 });

    // Bấm nút xoá (thùng rác) của đúng hội thoại vừa tạo
    const nutXoa = mucCanXoa.locator('button.nut-xoa-muc');
    await expect(nutXoa).toBeVisible();
    await nutXoa.click();

    // Hộp thoại xác nhận xoá của ứng dụng phải xuất hiện
    const hopThoai = page.locator('div[role="dialog"]');
    await expect(hopThoai).toBeVisible();
    await expect(hopThoai.locator('.hop-thoai-tieu-de')).toHaveText('Xác nhận xoá hội thoại');

    // Bấm nút Xoá nguy hiểm trong hộp thoại
    const nutXacNhanXoa = hopThoai.locator('button.nut-nguy-hiem');
    await expect(nutXacNhanXoa).toBeVisible();
    await nutXacNhanXoa.click();

    // Chờ hộp thoại đóng lại
    await expect(hopThoai).not.toBeVisible({ timeout: 10_000 });

    // Hội thoại vừa tạo không còn trong danh sách
    await expect(mucCanXoa).toHaveCount(0);
  });

  test('5. Khung nhìn 375x812 dùng được: drawer mở được, ô nhập không bị che', async ({ page }) => {
    // Đặt kích thước khung nhìn chuẩn di động 375x812 (iPhone X/13/14)
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/tro-chuyen/moi');
    await page.waitForLoadState('domcontentloaded');

    // Bấm nút mở ngăn kéo thanh điều hướng trên thanh đầu trang
    const nutMoSidebar = page.locator('header.thanh-dau-trang button.nut-ghost').first();
    await expect(nutMoSidebar).toBeVisible();
    await nutMoSidebar.click();

    // Ngăn kéo drawer phải mở ra
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toHaveClass(/ngan-keo-mo/);

    // Đóng drawer bằng cách bấm vào nền mờ backdrop
    const nenMo = page.locator('.nen-mo-ngan-keo');
    await expect(nenMo).toBeVisible();
    await nenMo.click();
    await expect(sidebar).not.toHaveClass(/ngan-keo-mo/);

    // Kiểm tra ô soạn câu hỏi không bị che và nằm trọn trong khung nhìn
    const vungNhap = page.locator('textarea.vung-nhap');
    await expect(vungNhap).toBeVisible();
    await expect(vungNhap).toBeEnabled();

    // Xác minh toạ độ của ô soạn thảo nằm hoàn toàn phía trong độ cao 812px của viewport
    const hopBao = await vungNhap.boundingBox();
    expect(hopBao).not.toBeNull();
    if (hopBao) {
      expect(hopBao.y).toBeGreaterThan(0);
      expect(hopBao.y + hopBao.height).toBeLessThanOrEqual(812);
    }

    // Nhập liệu thử nghiệm trên di động
    await vungNhap.fill('Kiểm tra nhập liệu trên di động 375x812');
    expect(await vungNhap.inputValue()).toBe('Kiểm tra nhập liệu trên di động 375x812');
  });

  test('6. Không có yêu cầu mạng nào tới máy chủ khác localhost và console không có lỗi vi phạm CSP', async ({
    page,
  }) => {
    const yeuCauNgoaiLocalhost: string[] = [];
    const loiCspConsole: string[] = [];

    // Bắt toàn bộ sự kiện request của trang
    page.on('request', (request) => {
      try {
        const urlObj = new URL(request.url());
        if (urlObj.hostname !== 'localhost' && urlObj.hostname !== '127.0.0.1') {
          yeuCauNgoaiLocalhost.push(request.url());
        }
      } catch {
        // Bỏ qua url nội bộ dạng data: hoặc blob:
      }
    });

    // Lắng nghe sự kiện console để phát hiện cảnh báo hoặc lỗi vi phạm Content Security Policy
    page.on('console', (msg) => {
      const vanBan = msg.text();
      if (
        vanBan.toLowerCase().includes('content security policy') ||
        vanBan.toLowerCase().includes('violates the following content security policy')
      ) {
        loiCspConsole.push(vanBan);
      }
    });

    // Lắng nghe lỗi trang pageerror
    page.on('pageerror', (error) => {
      const loi = error.message;
      if (loi.toLowerCase().includes('content security policy')) {
        loiCspConsole.push(loi);
      }
    });

    // Điều hướng qua các màn chính của ứng dụng
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.goto('/lich-su');
    await page.waitForLoadState('networkidle');

    await page.goto('/tro-chuyen/moi');
    await page.waitForLoadState('networkidle');

    // Xác minh không có kết nối ra ngoài localhost
    expect(yeuCauNgoaiLocalhost).toEqual([]);

    // Xác minh không có lỗi vi phạm CSP
    expect(loiCspConsole).toEqual([]);
  });
});
