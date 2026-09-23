/**
 * auth.guard.spec.ts - Kiem thu don vi cho authGuard va dangNhapGuard.
 *
 * Tuan thu cac quy chuan:
 * - clean_code.md: Cac ca kiem thu ro rang, don nhiem.
 * - type_safety.md: Strict typing, khong dung any.
 */

import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree } from '@angular/router';
import { Observable, of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { authGuard, dangNhapGuard } from './auth.guard';
import { AuthService } from './auth.service';

describe('Auth Guards', () => {
  let mockAuthService: {
    daDangNhap: ReturnType<typeof signal<boolean>>;
    daKhoiTao: ReturnType<typeof signal<boolean>>;
    khoiTaoPhien: ReturnType<typeof vi.fn>;
  };
  let mockRouter: {
    createUrlTree: ReturnType<typeof vi.fn>;
  };

  const dummyRoute = {} as ActivatedRouteSnapshot;
  const dummyState = {} as RouterStateSnapshot;

  beforeEach(() => {
    mockAuthService = {
      daDangNhap: signal(false),
      daKhoiTao: signal(false),
      khoiTaoPhien: vi.fn(),
    };
    mockRouter = {
      createUrlTree: vi.fn().mockImplementation((commands: string[]) => ({
        toString: () => commands.join('/'),
      } as unknown as UrlTree)),
    };

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: mockRouter },
      ],
    });
  });

  describe('authGuard', () => {
    it('cho phép truy cập nếu người dùng đã đăng nhập', () => {
      mockAuthService.daDangNhap.set(true);

      const res = TestBed.runInInjectionContext(() =>
        authGuard(dummyRoute, dummyState),
      ) as Observable<boolean | UrlTree>;

      res.subscribe((result) => {
        expect(result).toBe(true);
      });
    });

    it('điều hướng về /dang-nhap nếu đã khởi tạo và chưa đăng nhập', () => {
      mockAuthService.daDangNhap.set(false);
      mockAuthService.daKhoiTao.set(true);

      const res = TestBed.runInInjectionContext(() =>
        authGuard(dummyRoute, dummyState),
      ) as Observable<boolean | UrlTree>;

      res.subscribe((result) => {
        expect(mockRouter.createUrlTree).toHaveBeenCalledWith(['/dang-nhap']);
        expect(result).toEqual(expect.objectContaining({ toString: expect.any(Function) }));
      });
    });

    it('gọi khoiTaoPhien nếu chưa khởi tạo và cho phép vào nếu khôi phục thành công', () => {
      mockAuthService.daDangNhap.set(false);
      mockAuthService.daKhoiTao.set(false);
      mockAuthService.khoiTaoPhien.mockReturnValue(of(true));

      const res = TestBed.runInInjectionContext(() =>
        authGuard(dummyRoute, dummyState),
      ) as Observable<boolean | UrlTree>;

      res.subscribe((result) => {
        expect(mockAuthService.khoiTaoPhien).toHaveBeenCalled();
        expect(result).toBe(true);
      });
    });
  });

  describe('dangNhapGuard', () => {
    it('điều hướng về / nếu người dùng đã đăng nhập từ trước', () => {
      mockAuthService.daDangNhap.set(true);

      const res = TestBed.runInInjectionContext(() =>
        dangNhapGuard(dummyRoute, dummyState),
      ) as Observable<boolean | UrlTree>;

      res.subscribe(() => {
        expect(mockRouter.createUrlTree).toHaveBeenCalledWith(['/']);
      });
    });

    it('cho phép vào trang /dang-nhap nếu chưa đăng nhập và đã khởi tạo', () => {
      mockAuthService.daDangNhap.set(false);
      mockAuthService.daKhoiTao.set(true);

      const res = TestBed.runInInjectionContext(() =>
        dangNhapGuard(dummyRoute, dummyState),
      ) as Observable<boolean | UrlTree>;

      res.subscribe((result) => {
        expect(result).toBe(true);
      });
    });
  });
});
