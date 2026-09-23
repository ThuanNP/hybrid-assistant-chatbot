/**
 * auth.guard.ts - Guard kiem tra quyen truy cap va dieu huong dang nhap.
 *
 * Tuan thu cac quy chuan:
 * - clean_code.md: Functional guard theo chuan Angular hien dai, ro rang, don nhiem.
 * - type_safety.md: Strict typing, xu ly day du truong hop chua khoi tao.
 */

import { inject } from '@angular/core';
import { CanActivateFn, Router, UrlTree } from '@angular/router';
import { map, Observable, of } from 'rxjs';
import { AuthService } from './auth.service';

/**
 * Guard chan cac route yeu cau xac thuc. Neu chua dang nhap se dieu huong ve /dang-nhap.
 */
export const authGuard: CanActivateFn = (): Observable<boolean | UrlTree> => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.daDangNhap()) {
    return of(true);
  }

  if (authService.daKhoiTao()) {
    return of(router.createUrlTree(['/dang-nhap']));
  }

  return authService.khoiTaoPhien().pipe(
    map((thanhCong) => (thanhCong ? true : router.createUrlTree(['/dang-nhap']))),
  );
};

/**
 * Guard chan nguoi dung da dang nhap khong truy cap lai trang /dang-nhap.
 */
export const dangNhapGuard: CanActivateFn = (): Observable<boolean | UrlTree> => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.daDangNhap()) {
    return of(router.createUrlTree(['/']));
  }

  if (authService.daKhoiTao()) {
    return of(true);
  }

  return authService.khoiTaoPhien().pipe(
    map((thanhCong) => (thanhCong ? router.createUrlTree(['/']) : true)),
  );
};
