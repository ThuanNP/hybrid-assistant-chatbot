/**
 * api.service.ts - Dich vu giao tiep voi Backend REST API.
 * Tuan thu quy chuan clean_code.md, naming.md va type_safety.md.
 */

import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ENDPOINTS } from './cau-hinh';
import {
  DanhSachHoiThoaiPhanTrang,
  HoiThoai,
  LuotTinNhan,
  TrangThaiSucKhoe,
} from './mo-hinh';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly http = inject(HttpClient);

  public kiemTraSucKhoe(): Observable<TrangThaiSucKhoe> {
    return this.http.get<TrangThaiSucKhoe>(ENDPOINTS.HEALTH);
  }

  public layDanhSachHoiThoai(
    trang: number = 1,
    kichThuoc: number = 20
  ): Observable<DanhSachHoiThoaiPhanTrang> {
    const params = new HttpParams()
      .set('trang', trang.toString())
      .set('kich_thuoc', kichThuoc.toString());
    return this.http.get<DanhSachHoiThoaiPhanTrang>(ENDPOINTS.HOI_THOAI, {
      params,
    });
  }

  public layChiTietHoiThoai(hoiThoaiId: number): Observable<{
    hoi_thoai: HoiThoai;
    luots: LuotTinNhan[];
  }> {
    return this.http.get<{
      hoi_thoai: HoiThoai;
      luots: LuotTinNhan[];
    }>(`${ENDPOINTS.HOI_THOAI}/${hoiThoaiId}`);
  }

  public xoaHoiThoai(hoiThoaiId: number): Observable<{ da_xoa: boolean }> {
    return this.http.delete<{ da_xoa: boolean }>(
      `${ENDPOINTS.HOI_THOAI}/${hoiThoaiId}`
    );
  }
}
