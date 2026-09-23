/**
 * api.service.ts - Dich vu giao tiep voi Backend REST API.
 * Tuan thu cac quy chuan:
 * - AGENTS.md: ma_yeu_cau truyen xuyen suot, co trong moi phan hoi loi de nguoi dung bao ho tro.
 * - Angular CLI MCP Best Practices: Tiêm phụ thuộc bằng `inject(HttpClient)`.
 * - clean_code.md: Ham don nhiem < 40 dong, khong nuot ngoai le.
 * - type_safety.md: Strict mode, khong su dung kieu any.
 */

import { HttpClient, HttpErrorResponse, HttpParams, HttpResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { ENDPOINTS } from './cau-hinh';
import {
  BaoCaoChiPhi,
  BoLocHoiThoai,
  ChiTietHoiThoai,
  DanhSachHoiThoai,
  PhanHoiXoaHoiThoai,
  TrangThaiHangDoi,
  TrangThaiModels,
  TrangThaiSucKhoe,
  TrangThaiBoChay,
} from './mo-hinh';

export interface LoiApiTuyBien extends Error {
  maYeuCau?: string;
  maLoi?: string;
  retryAfter?: number;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly http = inject(HttpClient);
  private maYeuCauGanNhat: string = '';

  /**
   * Tra ve ma yeu cau HTTP gan nhat nhan duoc tu tieu de X-Ma-Yeu-Cau hoac phan hoi loi.
   */
  public layMaYeuCauGanNhat(): string {
    return this.maYeuCauGanNhat;
  }

  /**
   * Kiem tra trang thai song cua may chu Backend (/health).
   */
  public kiemTraSucKhoe(): Observable<TrangThaiSucKhoe> {
    return this.thucThiYeuCau(
      this.http.get<TrangThaiSucKhoe>(ENDPOINTS.HEALTH, { observe: 'response' }),
    );
  }

  /**
   * Lay danh sach hoi thoai cua nguoi dung co phan trang. May chu loc theo tu khoa tieu de,
   * khoang ngay cap nhat (gio Viet Nam) va sap xep; `tong_so` dem theo bo loc.
   */
  public layDanhSachHoiThoai(
    trang: number = 1,
    kichThuoc: number = 20,
    boLoc: BoLocHoiThoai = {},
  ): Observable<DanhSachHoiThoai> {
    let params = new HttpParams()
      .set('trang', trang.toString())
      .set('kich_thuoc', kichThuoc.toString());
    const tuKhoa = boLoc.tuKhoa?.trim();
    if (tuKhoa) params = params.set('tu_khoa', tuKhoa);
    if (boLoc.tuNgay) params = params.set('tu_ngay', boLoc.tuNgay);
    if (boLoc.denNgay) params = params.set('den_ngay', boLoc.denNgay);
    if (boLoc.sapXep && boLoc.sapXep !== 'moi_nhat') params = params.set('sap_xep', boLoc.sapXep);

    return this.thucThiYeuCau(
      this.http.get<DanhSachHoiThoai>(ENDPOINTS.HOI_THOAI, {
        params,
        observe: 'response',
      }),
    );
  }

  /**
   * Lay chi tiet mot cuoc hoi thoai bao gom toan bo lich su cac luot trao doi.
   */
  public layHoiThoai(id: number | string): Observable<ChiTietHoiThoai> {
    return this.thucThiYeuCau(
      this.http.get<ChiTietHoiThoai>(`${ENDPOINTS.HOI_THOAI}/${id}`, {
        observe: 'response',
      }),
    );
  }

  /**
   * Bi danh tuong thich cho layHoiThoai.
   */
  public layChiTietHoiThoai(id: number | string): Observable<ChiTietHoiThoai> {
    return this.layHoiThoai(id);
  }

  /**
   * Xoa mem mot cuoc hoi thoai cua nguoi dung.
   */
  public xoaHoiThoai(id: number | string): Observable<PhanHoiXoaHoiThoai> {
    return this.thucThiYeuCau(
      this.http.delete<PhanHoiXoaHoiThoai>(`${ENDPOINTS.HOI_THOAI}/${id}`, {
        observe: 'response',
      }),
    );
  }

  /**
   * Lay bao cao chi phi va ty le dinh tuyen mo hinh tu Backend.
   */
  public layChiPhi(): Observable<BaoCaoChiPhi> {
    return this.thucThiYeuCau(
      this.http.get<BaoCaoChiPhi>(ENDPOINTS.CHI_PHI, { observe: 'response' }),
    );
  }

  /**
   * Lay thong tin cau hinh mo hinh hien hanh (local va dam may).
   */
  public layModels(): Observable<TrangThaiModels> {
    return this.thucThiYeuCau(
      this.http.get<TrangThaiModels>(ENDPOINTS.MODELS, { observe: 'response' }),
    );
  }

  /**
   * Lay anh chup trang thai van hanh hien tai cua hang doi dieu phoi local.
   */
  public layTrangThaiHangDoi(): Observable<TrangThaiHangDoi> {
    return this.thucThiYeuCau(
      this.http.get<TrangThaiHangDoi>(ENDPOINTS.HANG_DOI_TINH_TRANG, {
        observe: 'response',
      }),
    );
  }

  /**
   * Lay tinh trang hoat dong va chi so tai nguyen cua bo chay local (/giam-sat/bo-chay).
   */
  public layTrangThaiBoChay(): Observable<TrangThaiBoChay> {
    return this.thucThiYeuCau(
      this.http.get<TrangThaiBoChay>(ENDPOINTS.GIAM_SAT_BO_CHAY, {
        observe: 'response',
      }),
    );
  }

  /**
   * Pipeline chung thuc thi yeu cau, trich xuat header X-Ma-Yeu-Cau va xu ly loi co ma yeu cau.
   */
  private thucThiYeuCau<T>(obs: Observable<HttpResponse<T>>): Observable<T> {
    return obs.pipe(
      tap((res) => {
        const maYc = res.headers.get('X-Ma-Yeu-Cau');
        if (maYc) {
          this.maYeuCauGanNhat = maYc;
        }
      }),
      map((res) => res.body as T),
      catchError((err: unknown) => this.xuLyLoi(err)),
    );
  }

  /**
   * Bóc tách mã yêu cầu và thông điệp lỗi để hiển thị cho người dùng báo bộ phận hỗ trợ kỹ thuật.
   */
  private xuLyLoi(err: unknown): Observable<never> {
    let maYc = this.maYeuCauGanNhat;
    let thongDiep = 'Đã xảy ra lỗi không xác định.';
    let maLoi = 'LOI_KHONG_XAC_DINH';

    let retryAfter: number | undefined;

    if (err instanceof HttpErrorResponse) {
      const headerMa = err.headers.get('X-Ma-Yeu-Cau');
      const headerRetry = err.headers.get('Retry-After');
      if (err.status === 429 && headerRetry) {
        const parsed = parseInt(headerRetry, 10);
        if (!Number.isNaN(parsed)) {
          retryAfter = parsed;
        }
      }
      const bodyLoi = err.error as
        { loi?: { ma?: string; thong_diep?: string; ma_yeu_cau?: string } } | undefined;

      if (bodyLoi?.loi?.ma_yeu_cau) {
        maYc = bodyLoi.loi.ma_yeu_cau;
      } else if (headerMa) {
        maYc = headerMa;
      }

      if (bodyLoi?.loi?.thong_diep) {
        thongDiep = bodyLoi.loi.thong_diep;
      } else if (typeof err.error === 'string' && err.error.trim()) {
        thongDiep = err.error;
      } else {
        thongDiep = err.message || `Lỗi máy chủ HTTP ${err.status}`;
      }

      if (bodyLoi?.loi?.ma) {
        maLoi = bodyLoi.loi.ma;
      }
    } else if (err instanceof Error) {
      thongDiep = err.message;
    }

    if (maYc) {
      this.maYeuCauGanNhat = maYc;
    }

    // Dinh dang thong bao co kem ro rang ma yeu cau de nguoi dung bao bo phan ho tro
    const noiDungLoi = maYc ? `${thongDiep} (Mã yêu cầu: ${maYc})` : thongDiep;
    const loiTuyBien: LoiApiTuyBien = new Error(noiDungLoi);
    loiTuyBien.maYeuCau = maYc;
    loiTuyBien.maLoi = maLoi;
    loiTuyBien.retryAfter = retryAfter;

    return throwError(() => loiTuyBien);
  }
}
