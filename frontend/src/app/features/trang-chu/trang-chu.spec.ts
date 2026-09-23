import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import { DANH_SACH_TAC_VU_NHANH } from '../../core/tac-vu-nhanh';
import { TrangChuComponent } from './trang-chu';

describe('TrangChuComponent', () => {
  let component: TrangChuComponent;
  let fixture: ComponentFixture<TrangChuComponent>;

  const mockApiService = {
    layDanhSachHoiThoai: () => of({ danh_sach: [], tong_so: 0, trang: 1, kich_thuoc: 100 }),
    layChiPhi: () =>
      of({
        chi_phi_hom_nay_usd: 0.25,
        ngan_sach_ngay_usd: 10,
        phan_tram_da_dung: 2.5,
        phan_ra_theo_tang: {
          0: { so_luot: 30, token: 1000, chi_phi: 0 },
          1: { so_luot: 10, token: 800, chi_phi: 0.25 },
        },
        ty_le_local: 0.75,
        ty_le_roi_tang: 0.125,
        so_cau_hoi_hom_nay: 40,
        so_cau_hoi_noi_bo: 30,
        so_cau_hoi_dam_may: 10,
        nguong_canh_bao_ngan_sach: 0.8,
        nguong_ty_le_roi_tang: 0.2,
      }),
    layTrangThaiHangDoi: () =>
      of({
        dang_chay: 1,
        dang_cho: 2,
        thoi_gian_cho_trung_vi: 3.4,
        so_bi_tu_choi_1_gio: 0,
        do_dai_toi_da: 20,
      }),
    layModels: () =>
      of({ che_do_dinh_tuyen: 'local_truoc', ho_so_gpu: 'gpu8', bac_local: [], chuoi_dam_may: [] }),
    kiemTraSucKhoe: () => of({ trang_thai: 'song', phien_ban: '0.3.0' }),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TrangChuComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: ApiService, useValue: mockApiService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TrangChuComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('tính chỉ số từ báo cáo của máy chủ, không tự suy diễn', () => {
    expect(component.tongLuotHomNay()).toBe(40);
    expect(component.luotDamMay()).toBe(10);
    expect(component.dinhDangPhanTram(component.tyLeLocal() ?? 0)).toBe('75%');
  });

  it('lượt hỏi dạng tổng/đám mây kèm biểu đồ tròn; hàng đợi dạng thanh ngang theo sức chứa', () => {
    expect(component.luotNoiBo()).toBe(30);
    expect(component.phanTramLuotNoiBo()).toBe(75);
    expect(component.phanTramHangDoi()).toBe(10);

    const el = fixture.nativeElement as HTMLElement;
    const cacThe = el.querySelectorAll('.the-kpi');
    expect(cacThe[0].querySelector('.gia-tri-kpi')?.textContent?.replace(/\s/g, '')).toBe('40/10');
    expect(cacThe[0].querySelector('.vong-luot-hoi')).not.toBeNull();
    expect(cacThe[3].querySelector('.gia-tri-kpi')?.textContent).toContain('/20 đang chờ');
    const thanh = cacThe[3].querySelector('[role="progressbar"]');
    expect(thanh?.getAttribute('aria-valuenow')).toBe('2');
    expect(thanh?.getAttribute('aria-valuemax')).toBe('20');
  });

  it('hiển thị đủ 4 thẻ chỉ số và 4 tác vụ nhanh', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.the-kpi').length).toBe(4);
    expect(el.querySelectorAll('.o-tac-vu').length).toBe(DANH_SACH_TAC_VU_NHANH.length);
  });

  it('chọn tác vụ nhanh sẽ mở cuộc trò chuyện mới kèm câu hỏi mẫu', () => {
    const kho = TestBed.inject(KhoHoiThoai);
    const spy = vi.spyOn(kho, 'moHoiThoaiMoi').mockImplementation(() => {});
    component.chonTacVu(DANH_SACH_TAC_VU_NHANH[0]);
    expect(spy).toHaveBeenCalledWith(DANH_SACH_TAC_VU_NHANH[0].cauHoi);
  });

  it('gửi câu hỏi ở ô hỏi nhanh chuyển sang màn Trò chuyện, không trò chuyện tại Trang chủ', () => {
    const kho = TestBed.inject(KhoHoiThoai);
    const spy = vi.spyOn(kho, 'moHoiThoaiMoi').mockImplementation(() => {});
    component.batDauHoi('Quy trình cấp điện mới?');
    expect(spy).toHaveBeenCalledWith('Quy trình cấp điện mới?');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.danh-sach-tin-nhan')).toBeNull();
  });
});
