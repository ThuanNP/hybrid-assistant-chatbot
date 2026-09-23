/**
 * dang-nhap.spec.ts - Kiem thu don vi cho DangNhapComponent.
 *
 * Tuan thu cac quy chuan:
 * - clean_code.md: Ca kiem thu don nhiem, mo ta ro rang.
 * - type_safety.md: Strict typing, khong dung any.
 */

import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DichVuThongBao } from '../../core/thong-bao';
import { AuthService } from '../../core/auth/auth.service';
import { DangNhapComponent } from './dang-nhap';

describe('DangNhapComponent', () => {
  let component: DangNhapComponent;
  let fixture: ComponentFixture<DangNhapComponent>;

  const mockAuthService = {
    dangXuLy: signal(false),
    dangNhap: vi.fn(),
  };

  const mockRouter = {
    navigate: vi.fn().mockResolvedValue(true),
  };

  beforeEach(async () => {
    mockAuthService.dangXuLy.set(false);
    mockAuthService.dangNhap.mockReset();
    mockRouter.navigate.mockReset();

    await TestBed.configureTestingModule({
      imports: [DangNhapComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: mockRouter },
        { provide: DichVuThongBao, useValue: { phienBan: signal('1.0.0-rc.1'), taiLai: vi.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DangNhapComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công với form trống ở trạng thái sẵn sàng', () => {
    expect(component).toBeTruthy();
    expect(component.email()).toBe('');
    expect(component.matKhau()).toBe('');
    expect(component.hienMatKhau()).toBe(false);
    expect(component.thongBaoLoi()).toBeNull();
  });

  it('chuyển đổi trạng thái ẩn/hiện mật khẩu khi bấm nút mắt', () => {
    expect(component.hienMatKhau()).toBe(false);
    component.chuyenDoiHienMatKhau();
    expect(component.hienMatKhau()).toBe(true);
    component.chuyenDoiHienMatKhau();
    expect(component.hienMatKhau()).toBe(false);
  });

  it('hiển thị thông báo yêu cầu nhập nếu để trống mật khẩu', () => {
    component.email.set('nv01@vidu.com');
    component.matKhau.set('');

    component.xuLyDangNhap();

    expect(component.thongBaoLoi()).toBe('Vui lòng nhập đầy đủ email và mật khẩu.');
    expect(mockAuthService.dangNhap).not.toHaveBeenCalled();
  });

  it('gọi AuthService.dangNhap và chuyển hướng về / khi thành công', () => {
    mockAuthService.dangNhap.mockReturnValue(of({ access_token: 'fake-jwt' }));
    component.email.set('nv01@vidu.com');
    component.matKhau.set('MatKhau123@');

    component.xuLyDangNhap();

    expect(mockAuthService.dangNhap).toHaveBeenCalledWith('nv01@vidu.com', 'MatKhau123@');
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/']);
  });

  it('hiển thị lỗi và ma_yeu_cau khi backend từ chối đăng nhập', () => {
    const errorResponse = {
      error: {
        loi: {
          ma: 'XAC_THUC_THAT_BAI',
          thong_diep: 'Email hoặc mật khẩu không chính xác.',
          ma_yeu_cau: 'yc-err-12345',
        },
      },
      status: 401,
    };
    mockAuthService.dangNhap.mockReturnValue(throwError(() => errorResponse));

    component.email.set('nv01@vidu.com');
    component.matKhau.set('SaiMatKhau');

    component.xuLyDangNhap();

    expect(component.thongBaoLoi()).toBe('Email hoặc mật khẩu không chính xác.');
    expect(component.maYeuCau()).toBe('yc-err-12345');
  });
});
