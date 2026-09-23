/**
 * kho-hoi-thoai.ts - Nguon trang thai dung chung cho danh sach hoi thoai.
 * Sidebar, Trang chu, Lich su va Tro chuyen cung doc mot danh sach, tranh moi man hinh
 * tu goi API rieng va lech nhau.
 */

import { Service, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, map, tap } from 'rxjs';
import { ApiService } from './api.service';
import { BoLocHoiThoai, HoiThoai } from './mo-hinh';

/** Yeu cau mo mot cuoc tro chuyen moi, co the kem cau hoi dau tien can gui ngay. */
export interface YeuCauHoiThoaiMoi {
  readonly lan: number;
  readonly cauHoi: string | null;
}

/** So muc moi trang khi cuon vo han; may chu cho phep toi da 100. */
export const KICH_THUOC_TRANG_HOI_THOAI = 30;
const SO_MUC_GAN_DAY = 8;

/**
 * Danh sach hoi thoai phan trang theo mot bo loc. May chu loc, sap xep va dem `tong_so`,
 * nen ket qua dung ngay tu trang dau, khong phai tai het cac trang.
 */
export class DanhSachHoiThoaiPhanTrang {
  private trangDaTai = 0;
  private boLoc: BoLocHoiThoai = {};
  /** Tang moi lan tai lai de bo qua phan hoi cu tra ve muon (tranh ghi de sai thu tu). */
  private theHe = 0;

  public readonly danhSach = signal<HoiThoai[]>([]);
  public readonly tongSo = signal(0);
  public readonly dangTai = signal(false);
  public readonly dangTaiThem = signal(false);
  public readonly thongBaoLoi = signal<string | null>(null);
  public readonly conThem = computed(() => this.danhSach().length < this.tongSo());

  constructor(private readonly api: ApiService) {}

  /** Tai lai trang dau theo bo loc moi (bo trong thi giu bo loc dang dung). */
  public taiLai(boLoc: BoLocHoiThoai = this.boLoc): void {
    this.boLoc = boLoc;
    this.theHe += 1;
    const theHe = this.theHe;
    this.dangTai.set(true);
    this.dangTaiThem.set(false);
    this.thongBaoLoi.set(null);
    this.api.layDanhSachHoiThoai(1, KICH_THUOC_TRANG_HOI_THOAI, boLoc).subscribe({
      next: (kq) => {
        if (theHe !== this.theHe) return;
        this.danhSach.set(kq?.danh_sach ?? []);
        this.tongSo.set(kq?.tong_so ?? 0);
        this.trangDaTai = 1;
        this.dangTai.set(false);
      },
      error: (loi: unknown) => {
        if (theHe !== this.theHe) return;
        this.ghiLoi(loi);
        this.dangTai.set(false);
      },
    });
  }

  /** Tai trang ke tiep va noi vao cuoi danh sach (cuon vo han); bo muc trung theo `id`. */
  public taiThem(): void {
    if (this.dangTai() || this.dangTaiThem() || !this.conThem()) return;
    const theHe = this.theHe;
    this.dangTaiThem.set(true);
    const trang = this.trangDaTai + 1;
    this.api.layDanhSachHoiThoai(trang, KICH_THUOC_TRANG_HOI_THOAI, this.boLoc).subscribe({
      next: (kq) => {
        if (theHe !== this.theHe) return;
        const daCo = new Set(this.danhSach().map((ht) => ht.id));
        const moi = (kq?.danh_sach ?? []).filter((ht) => !daCo.has(ht.id));
        this.danhSach.update((ds) => [...ds, ...moi]);
        this.tongSo.set(kq?.tong_so ?? this.tongSo());
        this.trangDaTai += 1;
        // Trang rong nghia la may chu da het du lieu (vi du do xoa): chot tong so theo thuc te.
        if ((kq?.danh_sach ?? []).length === 0) this.tongSo.set(this.danhSach().length);
        this.dangTaiThem.set(false);
      },
      error: (loi: unknown) => {
        if (theHe !== this.theHe) return;
        this.ghiLoi(loi);
        this.dangTaiThem.set(false);
      },
    });
  }

  private ghiLoi(loi: unknown): void {
    this.thongBaoLoi.set(loi instanceof Error ? loi.message : 'Không thể tải danh sách hội thoại.');
  }

  /** Bo mot muc da xoa khoi danh sach dang hien, khong can tai lai. */
  public boMuc(id: number): void {
    if (!this.danhSach().some((ht) => ht.id === id)) return;
    this.danhSach.update((ds) => ds.filter((ht) => ht.id !== id));
    this.tongSo.update((n) => Math.max(0, n - 1));
  }
}

/**
 * Nguon trang thai dung chung: danh sach khong loc, sap moi nhat truoc, cho sidebar,
 * Trang chu va Tro chuyen. Man Lich su dung DanhSachHoiThoaiPhanTrang rieng co bo loc.
 */
@Service()
export class KhoHoiThoai {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly nguon = new DanhSachHoiThoaiPhanTrang(this.api);
  private soLanYeuCau = 0;

  public readonly danhSach = this.nguon.danhSach;
  public readonly tongSo = this.nguon.tongSo;
  public readonly dangTai = this.nguon.dangTai;
  public readonly dangTaiThem = this.nguon.dangTaiThem;
  public readonly thongBaoLoi = this.nguon.thongBaoLoi;
  public readonly conThem = this.nguon.conThem;
  public readonly yeuCauMoi = signal<YeuCauHoiThoaiMoi | null>(null);

  public readonly ganDay = computed(() => this.danhSach().slice(0, SO_MUC_GAN_DAY));

  /** Tao danh sach phan trang rieng (co bo loc) dung chung ApiService cua kho. */
  public taoDanhSachLoc(): DanhSachHoiThoaiPhanTrang {
    return new DanhSachHoiThoaiPhanTrang(this.api);
  }

  public taiLai(): void {
    this.nguon.taiLai();
  }

  public taiThem(): void {
    this.nguon.taiThem();
  }

  /** Xoa mem mot hoi thoai va bo khoi danh sach khi may chu xac nhan. */
  public xoa(id: number): Observable<void> {
    return this.api.xoaHoiThoai(id).pipe(
      tap(() => this.nguon.boMuc(id)),
      map(() => undefined),
    );
  }

  /** Mo khung tro chuyen moi; neu co cau hoi, khung tro chuyen se gui ngay khi mo. */
  public moHoiThoaiMoi(cauHoi: string | null = null): void {
    this.soLanYeuCau += 1;
    this.yeuCauMoi.set({ lan: this.soLanYeuCau, cauHoi: cauHoi?.trim() || null });
    void this.router.navigate(['/tro-chuyen', 'moi']);
  }

  /** Lay va xoa yeu cau dang cho, bao dam moi yeu cau chi duoc xu ly mot lan. */
  public nhanYeuCauMoi(): YeuCauHoiThoaiMoi | null {
    const yeuCau = this.yeuCauMoi();
    this.yeuCauMoi.set(null);
    return yeuCau;
  }
}
