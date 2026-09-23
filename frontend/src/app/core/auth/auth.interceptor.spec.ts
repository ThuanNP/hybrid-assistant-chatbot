/**
 * auth.interceptor.spec.ts - Kiem thu don vi cho authInterceptor.
 *
 * Tuan thu cac quy chuan:
 * - Quy tac ky thuat 10: Gan ma_yeu_cau vao header cua moi request.
 * - clean_code.md: Cac ca kiem thu ro rang, ngan gon.
 * - type_safety.md: Strict typing, khong dung any.
 */

import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ENDPOINTS } from '../cau-hinh';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  const mockAuthService = {
    accessToken: signal<string | null>(null),
    lamMoiToken: vi.fn(),
    xoaTrangPhien: vi.fn(),
  };

  beforeEach(() => {
    mockAuthService.accessToken.set(null);
    mockAuthService.lamMoiToken.mockReset();
    mockAuthService.xoaTrangPhien.mockReset();

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: mockAuthService },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('tự động gắn X-Ma-Yeu-Cau và Authorization khi có token', () => {
    mockAuthService.accessToken.set('test-jwt-token');

    http.get('/api/v1/hoi-thoai').subscribe();

    const req = httpMock.expectOne('/api/v1/hoi-thoai');
    expect(req.request.headers.get('Authorization')).toBe('Bearer test-jwt-token');
    expect(req.request.headers.has('X-Ma-Yeu-Cau')).toBe(true);
    expect(req.request.headers.get('X-Ma-Yeu-Cau')).toBeTruthy();

    req.flush([]);
  });

  it('tự động làm mới token và thử lại yêu cầu khi nhận lỗi 401', () => {
    mockAuthService.accessToken.set('token-het-han');
    mockAuthService.lamMoiToken.mockReturnValue(of('token-moi-tinh'));

    http.get('/api/v1/hoi-thoai').subscribe((res) => {
      expect(res).toEqual([{ id: 1 }]);
    });

    // Lần gọi đầu tiên bị 401
    const req1 = httpMock.expectOne('/api/v1/hoi-thoai');
    expect(req1.request.headers.get('Authorization')).toBe('Bearer token-het-han');
    req1.flush({ detail: 'Token het han' }, { status: 401, statusText: 'Unauthorized' });

    expect(mockAuthService.lamMoiToken).toHaveBeenCalled();

    // Thử lại lần thứ hai với token mới
    const req2 = httpMock.expectOne('/api/v1/hoi-thoai');
    expect(req2.request.headers.get('Authorization')).toBe('Bearer token-moi-tinh');
    req2.flush([{ id: 1 }]);
  });

  it('không thử làm mới khi endpoint chính là đăng nhập hoặc làm mới', () => {
    mockAuthService.lamMoiToken.mockReturnValue(of('new-token'));

    let errResult: HttpErrorResponse | undefined;
    http.post(ENDPOINTS.DANG_NHAP, { email: 'a@v.c', mat_khau: '123' }).subscribe({
      error: (e: HttpErrorResponse) => {
        errResult = e;
      },
    });

    const req = httpMock.expectOne(ENDPOINTS.DANG_NHAP);
    req.flush({ detail: 'Sai mat khau' }, { status: 401, statusText: 'Unauthorized' });

    expect(mockAuthService.lamMoiToken).not.toHaveBeenCalled();
    expect(errResult?.status).toBe(401);
  });
});
