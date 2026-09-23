import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth/auth.service';
import { TrangThaiBoChay } from '../../core/mo-hinh';
import { QuanTriBoChayComponent } from './quan-tri-bo-chay';

describe('QuanTriBoChayComponent', () => {
  let component: QuanTriBoChayComponent;
  let fixture: ComponentFixture<QuanTriBoChayComponent>;

  const mockTrangThai: TrangThaiBoChay = {
    ho_so_gpu: 'gpu8',
    dung_luong_vram_gb: 8,
    bac_1: { model: 'qwen3.5:4b-q8_0', num_ctx: 16384 },
    bac_2: { model: 'qwen3.5:2b-q8_0', num_ctx: 8192 },
    model_dang_nap: [
      {
        ten: 'qwen3.5:4b-q8_0',
        kich_thuoc_byte: 4725049344,
        kich_thuoc_vram_byte: 4725049344,
        dung_luong_vram_gb: 4.4,
        het_han_luc: '2026-09-24T05:00:00Z',
        so_giay_con_lai: 1800,
      },
    ],
    ngu_canh: [
      {
        bac: 'chinh',
        model: 'qwen3.5:4b-q8_0',
        num_ctx_cau_hinh: 16384,
        num_ctx_thuc_te: 16384,
        co_lech: false,
      },
    ],
    co_lech: false,
    vram: {
      dung_luong_vram_gb: 8,
      tong_vram_da_dung_byte: 4725049344,
      tong_vram_da_dung_gb: 4.4,
      vram_con_trong_gb: 3.6,
      ghi_chu: 'chạy trong container Docker',
    },
  };

  const mockApiService = {
    layTrangThaiBoChay: () => of(mockTrangThai),
  };

  const mockAuthService = {
    laQuanTri: signal(true),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QuanTriBoChayComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: ApiService, useValue: mockApiService },
        { provide: AuthService, useValue: mockAuthService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(QuanTriBoChayComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('khởi tạo thành công và hiển thị dữ liệu bộ chạy', () => {
    expect(component).toBeTruthy();
    expect(component.trangThai()).toEqual(mockTrangThai);
    expect(component.dinhDangVram(4.4)).toBe('4,4 GB');
    expect(component.dinhDangThoiGian(1800)).toBe('Còn 30m 0s');
  });

  it('tự làm mới mặc định tắt, có thanh chọn chu kỳ và dòng thời điểm cập nhật', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(component.chuKyTuLamMoi()).toBe(0);
    const cacTuyChon = [...el.querySelectorAll('.chon-tu-lam-moi option')].map((o) => o.textContent?.trim());
    expect(cacTuyChon).toEqual(['Tắt', '15 giây', '30 giây', '60 giây']);
    expect(el.querySelector('.nhan-cap-nhat')?.textContent).toContain('Cập nhật lúc');
  });

  it('chọn chu kỳ thì gọi lại API theo chu kỳ; keep_alive đếm ngược theo đồng hồ', async () => {
    vi.useFakeTimers();
    try {
      // Tao lai component sau khi bat dong ho gia de dong ho dem nguoc dung thoi gian gia
      fixture = TestBed.createComponent(QuanTriBoChayComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
      const goi = vi.spyOn(mockApiService, 'layTrangThaiBoChay');
      const o = document.createElement('select');
      o.innerHTML = '<option value="15">15</option>';
      o.value = '15';
      component.chonChuKy({ target: o } as unknown as Event);
      fixture.detectChanges();
      await vi.advanceTimersByTimeAsync(15_000);
      expect(goi).toHaveBeenCalled();

      component.taiDuLieu();
      await vi.advanceTimersByTimeAsync(10_000);
      expect(Math.round(component.giayConLai(1800) ?? 0)).toBe(1790);
    } finally {
      vi.useRealTimers();
      localStorage.removeItem('tro-ly.bo-chay.tu-lam-moi-giay');
    }
  });
});
