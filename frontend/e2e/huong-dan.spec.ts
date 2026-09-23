import { test, expect, type Page } from '@playwright/test';

/**
 * Thực hiện đăng nhập vào hệ thống trước khi thực hiện các kịch bản kiểm thử.
 * Tài khoản lấy từ biến môi trường E2E_EMAIL, E2E_MAT_KHAU; không ghi mật khẩu vào mã.
 */
async function dangNhap(
  page: Page,
  email = process.env['E2E_EMAIL'] ?? 'nv01@vidu.com',
  matKhau = process.env['E2E_MAT_KHAU'] ?? '',
): Promise<void> {
  if (!matKhau) {
    throw new Error('Đặt biến môi trường E2E_MAT_KHAU (mật khẩu của E2E_EMAIL) trước khi chạy.');
  }
  await page.goto('/dang-nhap');
  await page.waitForLoadState('domcontentloaded');
  if (page.url().includes('/dang-nhap')) {
    await page.locator('input[type="email"]').fill(email);
    await page.locator('input[type="password"]').fill(matKhau);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL((url) => !url.pathname.includes('/dang-nhap'), { timeout: 15_000 });
  }
}

test.describe('Kiểm thử đầu cuối màn hình Hướng dẫn sử dụng & FAQ', () => {
  test.beforeEach(async ({ page }) => {
    await dangNhap(page);
  });

  test('1. Bấm biểu tượng cuốn sách trên thanh đầu trang điều hướng vào /huong-dan', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const nutHuongDan = page.locator('a[aria-label="Hướng dẫn sử dụng"]');
    await expect(nutHuongDan).toBeVisible();
    await nutHuongDan.click();

    await expect(page).toHaveURL(/\/huong-dan$/);
    await expect(page.locator('h1.tieu-de-trang')).toHaveText('Hướng dẫn sử dụng');
    await expect(nutHuongDan).toHaveClass(/dang-chon|active/);
  });

  test('2. Năm nhóm câu hỏi thường gặp, mặc định Bắt đầu và câu đầu mở sẵn; accordion đóng mở', async ({ page }) => {
    await page.goto('/huong-dan');
    await page.waitForLoadState('domcontentloaded');

    const chips = page.locator('.hang-chip .chip-nhom');
    await expect(chips).toHaveCount(5);
    await expect(page.locator('.chip-nhom.dang-chon')).toHaveText('Bắt đầu');

    const theFaqDauTien = page.locator('.the-faq').first();
    await expect(theFaqDauTien.locator('.than-the-faq')).toBeVisible();
    await expect(theFaqDauTien.locator('.nut-hoi-tro-ly')).toBeVisible();

    await theFaqDauTien.locator('.dau-the-faq').click();
    await expect(theFaqDauTien.locator('.than-the-faq')).toHaveCount(0);
  });

  test('3. Bấm Hỏi trợ lý ở một mục thì chuyển sang màn trò chuyện với đúng câu hỏi', async ({ page }) => {
    await page.goto('/huong-dan');
    await page.waitForLoadState('domcontentloaded');

    const theFaq = page.locator('.the-faq').first();
    const cauHoi = (await theFaq.locator('.cau-hoi').innerText()).trim();
    await theFaq.locator('.nut-hoi-tro-ly').click();

    await expect(page).toHaveURL(/\/tro-chuyen\//);
    await expect(page.locator('.danh-sach-tin-nhan')).toContainText(cauHoi);
  });

  test('4. Mục lục bắt đầu bằng Câu hỏi thường gặp; bấm mục thì cuộn tới và đánh dấu mục đó', async ({ page }) => {
    await page.goto('/huong-dan');
    await page.waitForLoadState('domcontentloaded');

    const mucLuc = page.locator('.danh-sach-muc-luc .nut-muc-luc');
    // Mục lục dựng sau khi /api/v1/huong-dan trả về: chờ mục thứ hai xuất hiện rồi mới kiểm tra
    await expect(mucLuc.nth(1)).toBeVisible();
    await expect(mucLuc.first()).toHaveText('Câu hỏi thường gặp');

    await mucLuc.nth(2).click();
    await expect(mucLuc.nth(2)).toHaveClass(/dang-chon/);
    await expect(page.locator('#ba-buoc-bat-dau')).toBeInViewport();
  });
});
