/**
 * auth.service.ts - Dich vu quan ly xac thuc nguoi dung phia frontend.
 *
 * Tuan thu cac quy chuan:
 * - Quy tac tuyet doi 4 & cam ket bao mat: Luu access token trong Angular Signal (bo nho),
 *   refresh token luu trong HttpOnly Cookie do backend thiet lap qua withCredentials: true.
 *   TUYET DOI KHONG dung kho luu tru cuc bo client.
 * - clean_code.md: Cac ham duoi 40 dong, don nhiem, chu thich day du.
 * - type_safety.md: Strict mode, khong dung any.
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, map, Observable, of, tap } from 'rxjs';
import { ENDPOINTS } from '../cau-hinh';
import { NguoiDung, PhanHoiDangNhap, PhanHoiDangXuat, PhanHoiLamMoiToken, YeuCauDangNhap } from '../mo-hinh';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  // Quan ly trang thai xac thuc hoan toan trong bo nho qua Angular Signals
  readonly accessToken = signal<string | null>(null);
  readonly nguoiDung = signal<NguoiDung | null>(null);
  readonly dangXuLy = signal<boolean>(false);
  readonly daKhoiTao = signal<boolean>(false);

  readonly daDangNhap = computed(() => Boolean(this.accessToken()));
  readonly vaiTro = computed(() => this.nguoiDung()?.vai_tro ?? null);
  readonly laQuanTri = computed(() => this.vaiTro() === 'quan_tri');
  readonly laChiDoc = computed(() => this.vaiTro() === 'chi_doc');

  /**
   * Dang nhap bang email va mat khau.
   */
  public dangNhap(email: string, matKhau: string): Observable<PhanHoiDangNhap> {
    this.dangXuLy.set(true);
    const body: YeuCauDangNhap = { email, mat_khau: matKhau };

    return this.http
      .post<PhanHoiDangNhap>(ENDPOINTS.DANG_NHAP, body, { withCredentials: true })
      .pipe(
        tap((res) => {
          this.accessToken.set(res.access_token);
          this.nguoiDung.set(res.nguoi_dung);
          this.dangXuLy.set(false);
          this.daKhoiTao.set(true);
        }),
        catchError((err) => {
          this.dangXuLy.set(false);
          throw err;
        }),
      );
  }

  /**
   * Lam moi access token thong qua refresh token luu trong HttpOnly cookie.
   */
  public lamMoiToken(): Observable<string | null> {
    return this.http
      .post<PhanHoiLamMoiToken>(ENDPOINTS.LAM_MOI_TOKEN, {}, { withCredentials: true })
      .pipe(
        tap((res) => {
          this.accessToken.set(res.access_token);
        }),
        map((res) => res.access_token),
        catchError(() => {
          this.accessToken.set(null);
          this.nguoiDung.set(null);
          return of(null);
        }),
      );
  }

  /**
   * Lay thong tin nguoi dung hien tai tu may chu backend.
   */
  public layThongTinToi(): Observable<NguoiDung | null> {
    return this.http.get<NguoiDung>(ENDPOINTS.TOI).pipe(
      tap((res) => this.nguoiDung.set(res)),
      catchError(() => of(null)),
    );
  }

  /**
   * Dang xuat khoi he thong, xoa cookie phien va dat lai trang thai ve rong.
   */
  public dangXuat(): Observable<PhanHoiDangXuat> {
    return this.http
      .post<PhanHoiDangXuat>(ENDPOINTS.DANG_XUAT, {}, { withCredentials: true })
      .pipe(
        tap(() => this.xoaTrangPhien()),
        catchError(() => {
          this.xoaTrangPhien();
          return of({ thanh_cong: true, thong_diep: 'Đã xóa phiên làm việc.' });
        }),
      );
  }

  /**
   * Khoi tao phien lam viec khi tai lai trang (F5): thu lam moi token mot lan.
   */
  public khoiTaoPhien(): Observable<boolean> {
    if (this.daDangNhap()) {
      return of(true);
    }

    return this.lamMoiToken().pipe(
      tap((token) => {
        this.daKhoiTao.set(true);
        if (token) {
          this.layThongTinToi().subscribe();
        }
      }),
      map((token) => Boolean(token)),
    );
  }

  /**
   * Xoa trang phien trong bo nho va dieu huong ve trang dang nhap.
   */
  public xoaTrangPhien(): void {
    this.accessToken.set(null);
    this.nguoiDung.set(null);
    this.dangXuLy.set(false);
    void this.router.navigate(['/dang-nhap']);
  }
}
