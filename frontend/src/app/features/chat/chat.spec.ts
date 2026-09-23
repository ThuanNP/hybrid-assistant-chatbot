import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { Observable, Subject, of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import { DANH_SACH_TAC_VU_NHANH } from '../../core/tac-vu-nhanh';
import { ChiTietHoiThoai, SuKien } from '../../core/mo-hinh';
import { SseService } from '../../core/sse.service';
import { ChatComponent } from './chat';

describe('ChatComponent', () => {
  let component: ChatComponent;
  let fixture: ComponentFixture<ChatComponent>;
  let streamSubject: Subject<SuKien>;

  const mockApiService = {
    layModels: () =>
      of({
        che_do_dinh_tuyen: 'local_truoc',
        ho_so_gpu: 'gpu8',
        bac_local: [],
        chuoi_dam_may: [],
      }),
    layChiPhi: () =>
      of({
        chi_phi_hom_nay_usd: 0.05,
        ngan_sach_ngay_usd: 10,
        phan_tram_da_dung: 0.5,
        phan_ra_theo_tang: {},
        ty_le_local: 0.8,
        ty_le_roi_tang: 0.2,
        so_cau_hoi_hom_nay: 0,
        so_cau_hoi_noi_bo: 0,
        so_cau_hoi_dam_may: 0,
        nguong_canh_bao_ngan_sach: 0.8,
        nguong_ty_le_roi_tang: 0.2,
      }),
    layDanhSachHoiThoai: () => of({ danh_sach: [], tong_so: 0, trang: 1, kich_thuoc: 20 }),
    layHoiThoai: (): Observable<ChiTietHoiThoai> =>
      of({ id: 1, tieu_de: 'Test', tao_luc: '', cap_nhat_luc: '', cac_luot: [] }),
    xoaHoiThoai: () => of({ thanh_cong: true, thong_diep: 'Đã xoá' }),
  };

  const mockSseService = {
    guiTinNhan: (
      _noiDung: string,
      _hoiThoaiId?: number | null,
      _signal?: AbortSignal,
    ) => streamSubject.asObservable(),
  };

  beforeEach(async () => {
    streamSubject = new Subject<SuKien>();

    await TestBed.configureTestingModule({
      imports: [ChatComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([{ path: 'tro-chuyen/:id', children: [] }]),
        { provide: ApiService, useValue: mockApiService },
        { provide: SseService, useValue: mockSseService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('cuộc trò chuyện trống hiển thị màn chào và 4 chip gợi ý', () => {
    expect(component).toBeTruthy();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.man-hinh-chao')).not.toBeNull();
    const chips = el.querySelectorAll('.the-goi-y');
    expect(chips.length).toBe(4);
    expect(chips[0].textContent).toContain('Tra cứu quy trình');
  });

  it('khi máy chủ cấp mã hội thoại, địa chỉ đổi sang /tro-chuyen/:id và ẩn màn chào', async () => {
    const router = TestBed.inject(Router);
    const spy = vi.spyOn(router, 'navigate');

    component.guiTinNhan('Quy trình cấp điện mới');
    streamSubject.next({
      loai: 'bat_dau',
      hoi_thoai_id: 42,
      nguon: 'local',
      tang: 0,
      model: 'qwen3.5:9b-q4_K_M',
      da_cat_ngu_canh: false,
      so_luot_bi_cat: 0,
    });
    await fixture.whenStable();

    expect(spy).toHaveBeenCalledWith(['/tro-chuyen', 42], { replaceUrl: true });
    expect(component.hoiThoaiHienTaiId()).toBe(42);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.man-hinh-chao')).toBeNull();
  });

  it('câu hỏi gửi từ Trang chủ qua kho hội thoại được gửi ngay khi mở khung trò chuyện', async () => {
    const spy = vi.spyOn(mockSseService, 'guiTinNhan');
    const kho = TestBed.inject(KhoHoiThoai);
    kho.yeuCauMoi.set({ lan: 1, cauHoi: 'Diễn giải biểu giá bậc thang' });
    await fixture.whenStable();

    expect(spy).toHaveBeenCalledWith('Diễn giải biểu giá bậc thang', null, expect.anything());
    expect(kho.yeuCauMoi()).toBeNull();
    expect(component.danhSachTinNhan()[0].noiDung).toBe('Diễn giải biểu giá bậc thang');
  });

  it('lỗi giữa chừng: giữ nguyên phần chữ đã nhận và hiển thị dòng lỗi màu đỏ kèm ma_yeu_cau', async () => {
    component.noiDungNhap.set('Quy trình kiểm tra công tơ');
    component.guiTinNhan();

    // 1. Nhận sự kiện bat_dau
    streamSubject.next({
      loai: 'bat_dau',
      hoi_thoai_id: 10,
      nguon: 'local',
      tang: 0,
      model: 'qwen3.5:9b-q4_K_M',
      da_cat_ngu_canh: false,
      so_luot_bi_cat: 0,
    });

    // 2. Nhận các mảnh văn bản (manh)
    streamSubject.next({
      loai: 'manh',
      noi_dung: 'Bước 1: Tiếp nhận hồ sơ khách hàng. ',
    });
    streamSubject.next({
      loai: 'manh',
      noi_dung: 'Bước 2: Cán bộ kỹ thuật kiểm tra tại chỗ.',
    });

    // 3. Đứt kết nối giữa chừng với sự kiện loi
    streamSubject.next({
      loai: 'loi',
      ma: 'MAT_KET_NOI',
      thong_diep: 'Mất kết nối với mô hình Ollama',
      ma_yeu_cau: 'yc-test-999',
      phan_da_nhan: '',
    });
    streamSubject.complete();

    await fixture.whenStable();

    // Kiểm tra tin nhắn trợ lý: Chữ đã nhận phải được giữ nguyên
    const danhSach = component.danhSachTinNhan();
    const tinTroLy = danhSach.find((t) => t.vaiTro === 'tro_ly');
    expect(tinTroLy).toBeDefined();
    expect(tinTroLy?.noiDung).toBe(
      'Bước 1: Tiếp nhận hồ sơ khách hàng. Bước 2: Cán bộ kỹ thuật kiểm tra tại chỗ.',
    );
    expect(tinTroLy?.coLoi).toBe(true);
    expect(tinTroLy?.maYeuCau).toBe('yc-test-999');

    // Kiểm tra hiển thị DOM
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Bước 1: Tiếp nhận hồ sơ khách hàng.');
    expect(el.textContent).toContain('Bước 2: Cán bộ kỹ thuật kiểm tra tại chỗ.');
    const dongLoi = el.querySelector('.dong-loi-red');
    expect(dongLoi).not.toBeNull();
    expect(dongLoi?.textContent).toContain('Mất kết nối với mô hình Ollama');
    expect(dongLoi?.textContent).toContain('yc-test-999');
  });

  it('da_cat_ngu_canh = true: hiện dòng chữ xám thông báo lược bớt lượt', async () => {
    component.noiDungNhap.set('Hỏi tiếp bước 3');
    component.guiTinNhan();

    streamSubject.next({
      loai: 'bat_dau',
      hoi_thoai_id: 11,
      nguon: 'local',
      tang: 0,
      model: 'qwen3.5:9b-q4_K_M',
      da_cat_ngu_canh: true,
      so_luot_bi_cat: 4,
    });
    streamSubject.next({ loai: 'manh', noi_dung: 'Bước 3 là lập biên bản.' });
    streamSubject.complete();

    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    const dongCat = el.querySelector('.dong-cat-ngu-canh');
    expect(dongCat).not.toBeNull();
    expect(dongCat?.textContent).toContain('Đã lược bớt 4 lượt đầu để vừa cửa sổ ngữ cảnh');
  });

  it('huy hiệu viền vàng khi tang khác 0 hoặc bac_local = 2', async () => {
    component.noiDungNhap.set('Câu hỏi hạ cấp');
    component.guiTinNhan();

    // Rơi tầng đám mây (tang = 1)
    streamSubject.next({
      loai: 'bat_dau',
      hoi_thoai_id: 12,
      nguon: 'gemini',
      tang: 1,
      model: 'gemini-2.5-flash',
      da_cat_ngu_canh: false,
      so_luot_bi_cat: 0,
    });
    streamSubject.next({ loai: 'manh', noi_dung: 'Trả lời từ tầng đám mây.' });
    streamSubject.next({
      loai: 'xong',
      token_vao: 150,
      token_ra: 80,
      chi_phi_usd: 0.0005,
      toc_do_tok_s: 45,
      do_tre_ms: 1200,
      nguon: 'gemini',
      tang: 1,
      bac_local: null,
      model: 'gemini-2.5-flash',
      nhan_ai: 'Nội dung do AI tạo',
    });
    streamSubject.complete();

    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    const huyHieu = el.querySelector('.huy-hieu-container');
    expect(huyHieu?.classList.contains('canh-bao-roi-tang')).toBe(true);
  });

  it('chuỗi có thẻ script trong manh không được thực thi', async () => {
    const windowObj = window as unknown as Record<string, unknown>;
    windowObj['__xss_kiem_thu_chay'] = false;

    component.noiDungNhap.set('Kiểm tra XSS');
    component.guiTinNhan();

    // Model sinh chuỗi chứa thẻ script nguy hiểm
    streamSubject.next({
      loai: 'manh',
      noi_dung: 'Đoạn mã: <script>window.__xss_kiem_thu_chay = true;</script>',
    });
    streamSubject.complete();

    await fixture.whenStable();

    // Xác nhận script tuyệt đối không được thực thi
    expect(windowObj['__xss_kiem_thu_chay']).toBe(false);

    // Xác nhận văn bản được hiển thị an toàn
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('<script>window.__xss_kiem_thu_chay = true;</script>');
  });

  it('câu hỏi dài được thu gọn và bấm "Xem thêm" để mở rộng, bấm lại để thu gọn', async () => {
    const cauHoiDai = Array.from({ length: 10 }, (_, i) => `Dòng thứ ${i + 1} của câu hỏi.`).join('\n');
    component.guiTinNhan(cauHoiDai);
    component.guiTinNhan('Ngắn');
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    const doanVan = el.querySelector('.noi-dung-nguoi-dung');
    const nut = el.querySelector<HTMLButtonElement>('.nut-mo-rong');
    expect(doanVan?.classList.contains('thu-gon')).toBe(true);
    expect(nut?.textContent).toContain('Xem thêm');
    expect(nut?.getAttribute('aria-expanded')).toBe('false');

    nut?.click();
    await fixture.whenStable();
    expect(doanVan?.classList.contains('thu-gon')).toBe(false);
    expect(nut?.textContent).toContain('Thu gọn');
    expect(nut?.getAttribute('aria-expanded')).toBe('true');

    nut?.click();
    await fixture.whenStable();
    expect(doanVan?.classList.contains('thu-gon')).toBe(true);
    expect(el.querySelectorAll('.nut-mo-rong').length).toBe(1);
  });

  it('bấm chip gợi ý nhanh sẽ gửi ngay câu hỏi đó', () => {
    let textDaGui = '';
    const spy = vi.spyOn(mockSseService, 'guiTinNhan').mockImplementation((cauHoi: string) => {
      textDaGui = cauHoi;
      return streamSubject.asObservable();
    });

    component.bamGoiY(DANH_SACH_TAC_VU_NHANH[2]);

    expect(spy).toHaveBeenCalled();
    expect(textDaGui).toBe(DANH_SACH_TAC_VU_NHANH[2].cauHoi);
  });

  it('mở lại hội thoại vẫn đủ nhãn AI, dòng lược bớt và huy hiệu theo cờ ha_cap của máy chủ', async () => {
    vi.spyOn(mockApiService, 'layHoiThoai').mockReturnValue(
      of({
        id: 7,
        tieu_de: 'Mở lại',
        tao_luc: '',
        cap_nhat_luc: '',
        cac_luot: [
          { id: 1, vai_tro: 'nguoi_dung', noi_dung: 'Câu hỏi', tao_luc: '' },
          {
            id: 2,
            vai_tro: 'tro_ly',
            noi_dung: 'Câu trả lời',
            nguon: 'dam_may',
            tang: 1,
            model_da_dung: 'nha-cung-cap/model',
            toc_do_tok_s: 40,
            do_tre_ms: 900,
            da_cat_ngu_canh: true,
            so_luot_bi_cat: 2,
            ma_yeu_cau: 'abc123def456',
            nhan_ai: 'Nội dung do AI tạo - nha-cung-cap/model - 23/09/2026 - 10:00',
            ha_cap: false,
            tao_luc: '',
          },
        ],
      }),
    );

    fixture.componentRef.setInput('id', '7');
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Nội dung do AI tạo - nha-cung-cap/model');
    expect(el.textContent).toContain('Đã lược bớt 2 lượt đầu');
    const huyHieu = el.querySelector('.huy-hieu-container');
    expect(huyHieu?.classList.contains('canh-bao-roi-tang')).toBe(false);
    expect(huyHieu?.getAttribute('title')).toContain('Tốc độ: 40 tok/s');
  });
});
