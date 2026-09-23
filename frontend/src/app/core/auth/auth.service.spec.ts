/**
 * auth.service.spec.ts - Kiem thu don vi cho AuthService.
 *
 * Tuan thu cac quy chuan:
 * - Quy tac tuyet doi 4 & cam ket bao mat: Khong dung kho luu tru cuc bo client, quan ly token trong Signal.
 * - clean_code.md: Cac ca kiem thu ro rang, ngan gon, khong lap ma.
 * - type_safety.md: Strict typing, khong dung any.
 */

import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ENDPOINTS } from '../cau-hinh';
import { NguoiDung, PhanHoiDangNhap, PhanHoiDangXuat, PhanHoiLamMoiToken } from '../mo-hinh';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  const mockRouter = {
    navigate: vi.fn().mockResolvedValue(true),
  };

  const nguoiDungMau: NguoiDung = {
    id: 1,
    email: 'nv01@vidu.com',
    vai_tro: 'nguoi_dung',
    phong_ban: 'KINH_DOANH',
    che_do_dinh_tuyen: 'tu_dong',
    ho_ten: 'Nguyễn Văn 01',
    kich_hoat: true,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: mockRouter },
        AuthService,
      ],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    vi.clearAllMocks();
  });

  it('khởi tạo với trạng thái chưa đăng nhập', () => {
    expect(service.accessToken()).toBeNull();
    expect(service.nguoiDung()).toBeNull();
    expect(service.daDangNhap()).toBe(false);
    expect(service.vaiTro()).toBeNull();
    expect(service.laQuanTri()).toBe(false);
    expect(service.laChiDoc()).toBe(false);
  });

  it('đăng nhập thành công cập nhật tín hiệu accessToken và nguoiDung', () => {
    const phanHoiMau: PhanHoiDangNhap = {
      access_token: 'jwt-access-token-123',
      token_type: 'bearer',
      expires_in: 900,
      nguoi_dung: nguoiDungMau,
    };

    service.dangNhap('nv01@vidu.com', 'MatKhau123@').subscribe((res) => {
      expect(res.access_token).toBe('jwt-access-token-123');
    });

    const req = httpMock.expectOne(ENDPOINTS.DANG_NHAP);
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body).toEqual({
      email: 'nv01@vidu.com',
      mat_khau: 'MatKhau123@',
    });

    req.flush(phanHoiMau);

    expect(service.accessToken()).toBe('jwt-access-token-123');
    expect(service.nguoiDung()).toEqual(nguoiDungMau);
    expect(service.daDangNhap()).toBe(true);
    expect(service.vaiTro()).toBe('nguoi_dung');
    expect(service.laQuanTri()).toBe(false);
  });

  it('làm mới token thành công cập nhật accessToken mới', () => {
    const phanHoiLamMoi: PhanHoiLamMoiToken = {
      access_token: 'jwt-new-token-456',
      token_type: 'bearer',
      expires_in: 900,
    };

    service.lamMoiToken().subscribe((token) => {
      expect(token).toBe('jwt-new-token-456');
    });

    const req = httpMock.expectOne(ENDPOINTS.LAM_MOI_TOKEN);
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);

    req.flush(phanHoiLamMoi);

    expect(service.accessToken()).toBe('jwt-new-token-456');
  });

  it('đăng xuất xóa trắng phiên làm việc và điều hướng về /dang-nhap', () => {
    // Giả lập trạng thái đã đăng nhập trước đó
    service.accessToken.set('token-cu');
    service.nguoiDung.set(nguoiDungMau);

    const phanHoiDangXuat: PhanHoiDangXuat = {
      thanh_cong: true,
      thong_diep: 'Đã xóa phiên làm việc.',
    };

    service.dangXuat().subscribe();

    const req = httpMock.expectOne(ENDPOINTS.DANG_XUAT);
    expect(req.request.method).toBe('POST');
    expect(req.request.withCredentials).toBe(true);

    req.flush(phanHoiDangXuat);

    expect(service.accessToken()).toBeNull();
    expect(service.nguoiDung()).toBeNull();
    expect(service.daDangNhap()).toBe(false);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/dang-nhap']);
  });
});
