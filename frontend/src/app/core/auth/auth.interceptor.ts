/**
 * auth.interceptor.ts - Interceptor gan tieu de Authorization, X-Ma-Yeu-Cau va tu dong lam moi token.
 *
 * Tuan thu cac quy chuan:
 * - Quy tac ky thuat 10: ma_yeu_cau truyen xuyen suot trong moi request.
 * - clean_code.md: Functional interceptor theo chuan Angular, xu ly 401 don nhiem.
 * - type_safety.md: Khong dung any, bao toan kieu tra ve HttpEvent.
 */

import { HttpErrorResponse, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { ENDPOINTS } from '../cau-hinh';
import { AuthService } from './auth.service';

function taoMaYeuCauNgauNhien(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `yc-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);
  const token = authService.accessToken();

  let headers = req.headers;
  if (token && !headers.has('Authorization')) {
    headers = headers.set('Authorization', `Bearer ${token}`);
  }
  if (!headers.has('X-Ma-Yeu-Cau')) {
    headers = headers.set('X-Ma-Yeu-Cau', taoMaYeuCauNgauNhien());
  }

  const yeuCauMoi = req.clone({ headers });

  return next(yeuCauMoi).pipe(
    catchError((err: unknown) => {
      if (!(err instanceof HttpErrorResponse) || err.status !== 401) {
        return throwError(() => err);
      }

      // Khong thu lam moi neu chinh yeu cau nay la dang nhap, lam moi hoac dang xuat
      const laEndpointXacThuc =
        req.url.includes(ENDPOINTS.DANG_NHAP) ||
        req.url.includes(ENDPOINTS.LAM_MOI_TOKEN) ||
        req.url.includes(ENDPOINTS.DANG_XUAT);

      if (laEndpointXacThuc) {
        return throwError(() => err);
      }

      // Thu lam moi token mot lan
      return authService.lamMoiToken().pipe(
        switchMap((tokenMoi) => {
          if (!tokenMoi) {
            authService.xoaTrangPhien();
            return throwError(() => err);
          }
          const yeuCauThuLai = req.clone({
            headers: req.headers.set('Authorization', `Bearer ${tokenMoi}`),
          });
          return next(yeuCauThuLai);
        }),
      );
    }),
  );
};
