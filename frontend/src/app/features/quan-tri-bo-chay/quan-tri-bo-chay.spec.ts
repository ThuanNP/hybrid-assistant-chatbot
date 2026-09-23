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
});
