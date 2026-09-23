import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { App } from './app';
import { ApiService } from './core/api.service';
import { BoCucTrang } from './core/bo-cuc-trang';

describe('App (khung ứng dụng)', () => {
  const mockApiService = {
    layDanhSachHoiThoai: () =>
      of({
        danh_sach: [
          { id: 7, tieu_de: 'Soạn công văn', tao_luc: '', cap_nhat_luc: '' },
        ],
        tong_so: 1,
        trang: 1,
        kich_thuoc: 100,
      }),
    kiemTraSucKhoe: () => of({ trang_thai: 'song', phien_ban: '0.3.0' }),
    layModels: () =>
      of({
        che_do_dinh_tuyen: 'local_truoc',
        ho_so_gpu: 'gpu6',
        bac_local: [{ bac: 'chinh', model: 'qwen3.5:4b-q4_K_M', num_ctx: 8192 }],
        chuoi_dam_may: [],
      }),
    layChiPhi: () =>
      of({
        chi_phi_hom_nay_usd: 9,
        ngan_sach_ngay_usd: 10,
        phan_tram_da_dung: 90,
        phan_ra_theo_tang: {},
        ty_le_local: 0.5,
        ty_le_roi_tang: 0,
        so_cau_hoi_hom_nay: 0,
        so_cau_hoi_noi_bo: 0,
        so_cau_hoi_dam_may: 0,
        nguong_canh_bao_ngan_sach: 0.8,
        nguong_ty_le_roi_tang: 0.2,
      }),
    layTrangThaiHangDoi: () =>
      of({
        dang_chay: 0,
        dang_cho: 0,
        thoi_gian_cho_trung_vi: 0,
        so_bi_tu_choi_1_gio: 0,
        do_dai_toi_da: 20,
      }),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([{ path: '**', children: [] }]),
        { provide: ApiService, useValue: mockApiService },
      ],
    }).compileComponents();
  });

  it('hiển thị khối nhận diện "Trợ lý nội bộ"', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.sidebar .chu-nhan-dien')?.textContent).toContain('Trợ lý nội bộ');
  });

  it('sidebar có nút tạo cuộc trò chuyện mới, hai mục chức năng và danh sách gần đây', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.nut-tro-chuyen-moi')?.textContent).toContain('Cuộc trò chuyện mới');
    const cacMuc = Array.from(el.querySelectorAll('.muc-menu')).map((m) => m.textContent?.trim());
    expect(cacMuc).toEqual(['Trang chủ', 'Lịch sử hội thoại']);
    const ganDay = el.querySelector<HTMLAnchorElement>('.muc-gan-day');
    expect(ganDay?.getAttribute('href')).toBe('/tro-chuyen/7');
  });

  it('bấm Cuộc trò chuyện mới sẽ chuyển sang /tro-chuyen/moi', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const router = TestBed.inject(Router);
    const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    fixture.componentInstance.moHoiThoaiMoi();
    expect(spy).toHaveBeenCalledWith(['/tro-chuyen', 'moi']);
  });

  it('thanh đầu trang có chuông thông báo lấy từ số liệu thật và menu tài khoản', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    const chuong = el.querySelector<HTMLButtonElement>('button[title="Thông báo"]');
    expect(chuong?.getAttribute('aria-label')).toBe('Thông báo, 1 mục');
    chuong?.click();
    await fixture.whenStable();
    expect(el.querySelector('.muc-thong-bao')?.textContent).toContain('90% ngân sách ngày');

    el.querySelector<HTMLButtonElement>('.nut-nguoi-dung')?.click();
    await fixture.whenStable();
    const hoSo = el.querySelector('.bang-nguoi-dung .the-ho-so');
    expect(hoSo?.textContent).toContain('Nguyễn Văn A');
    expect(hoSo?.querySelector('.chuc-danh')?.textContent).toBe('Chuyên viên · Phòng Kinh doanh');
    expect(hoSo?.querySelector('.don-vi')?.textContent).toBe('Doanh nghiệp Kinh doanh Điện năng');
    expect(el.querySelector('.muc-thong-bao')).toBeNull();
  });

  it('breadcrumb trên thanh đầu trang tách riêng khỏi tiêu đề trang (h1)', async () => {
    const fixture = TestBed.createComponent(App);
    const boCuc = TestBed.inject(BoCucTrang);
    boCuc.datTieuDe(
      'Soạn công văn',
      [
        { nhan: 'Lịch sử hội thoại', lienKet: '/lich-su' },
        { nhan: 'Soạn công văn', lienKet: null },
      ],
      'Ưu tiên local',
      'Mô tả ngắn',
    );
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    const cacMuc = Array.from(el.querySelectorAll('.duong-dan li')).map((li) =>
      li.textContent?.replace('/', '').trim(),
    );
    expect(cacMuc).toEqual(['Trang chủ', 'Lịch sử hội thoại', 'Soạn công văn']);
    expect(el.querySelector('.duong-dan a[href="/lich-su"]')).not.toBeNull();
    expect(el.querySelector('.duong-dan [aria-current="page"]')?.textContent).toContain('Soạn công văn');

    expect(el.querySelector('.duong-dan h1')).toBeNull();
    expect(el.querySelector('.hang-tieu-de-trang h1')?.textContent).toContain('Soạn công văn');
    expect(el.querySelector('.hang-tieu-de-trang .mo-ta-trang')?.textContent).toContain('Mô tả ngắn');
  });

  it('breadcrumb quá dài: mục giữa gộp thành "…", giữ Trang chủ và mục hiện tại; có tiêu đề cho di động', async () => {
    const fixture = TestBed.createComponent(App);
    const boCuc = TestBed.inject(BoCucTrang);
    boCuc.datTieuDe('Quy trình cấp điện mới cho hộ gia đình', [
      { nhan: 'Lịch sử hội thoại', lienKet: '/lich-su' },
      { nhan: 'Quy trình cấp điện mới cho hộ gia đình', lienKet: null },
    ]);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const thanh = fixture.debugElement.query((de) => de.name === 'app-thanh-dau-trang')
      .componentInstance as { rutGonDuongDan: { set(v: boolean): void } };

    thanh.rutGonDuongDan.set(true);
    await fixture.whenStable();
    const cacMuc = Array.from(el.querySelectorAll('.duong-dan li')).map((li) =>
      li.textContent?.replace('/', '').trim(),
    );
    expect(cacMuc).toEqual(['Trang chủ', '…', 'Quy trình cấp điện mới cho hộ gia đình']);
    const rutGon = el.querySelector<HTMLAnchorElement>('.duong-dan .muc-rut-gon');
    expect(rutGon?.getAttribute('href')).toBe('/lich-su');
    expect(rutGon?.getAttribute('aria-label')).toBe('Lịch sử hội thoại');

    expect(el.querySelector('.tieu-de-di-dong')?.textContent).toContain('Quy trình cấp điện mới');
  });

  it('nút đóng mở menu đổi biểu tượng và nhãn theo trạng thái sidebar', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const nut = () => el.querySelector<HTMLButtonElement>('app-thanh-dau-trang button[aria-expanded]');
    const dangMo = fixture.componentInstance.sidebarDangMo();

    expect(nut()?.getAttribute('aria-expanded')).toBe(String(dangMo));
    nut()?.click();
    await fixture.whenStable();
    expect(nut()?.getAttribute('aria-expanded')).toBe(String(!dangMo));
    expect(nut()?.getAttribute('aria-label')).toBe(
      dangMo ? 'Mở thanh điều hướng' : 'Thu gọn thanh điều hướng',
    );
  });

  it('trạng thái hệ thống ở thanh đầu trang dùng nhãn tiếng Việt, footer hiện phiên bản', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    const nhan = el.querySelector<HTMLButtonElement>('.nut-trang-thai');
    expect(nhan?.textContent).toContain('Đang hoạt động');
    nhan?.click();
    await fixture.whenStable();
    const bang = el.querySelector('.bang-he-thong')?.textContent ?? '';
    expect(bang).toContain('Ưu tiên mô hình nội bộ');
    expect(bang).toContain('GPU 6 GB');
    expect(bang).not.toContain('local_truoc');

    const chanTrang = el.querySelector('.chan-trang')?.textContent ?? '';
    expect(chanTrang).toContain('Phiên bản 0.3.0');
    expect(chanTrang).toContain(`© ${new Date().getFullYear()} Nguyễn Phước Thuận. Bảo lưu mọi quyền.`);
  });

  it('thu gọn sidebar trên màn hình rộng', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    const truoc = app.sidebarThuGon();
    app.chuyenDoiSidebar();
    expect(app.sidebarThuGon()).toBe(window.innerWidth >= 768 ? !truoc : truoc);
  });
});
