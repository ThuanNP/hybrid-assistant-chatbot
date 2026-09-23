/**
 * bo-cuc-trang.ts - Thong tin hien thi o thanh dau trang (breadcrumb) va hang tieu de trang
 * (DESIGN.md muc 6.2, 6.3). Moi man hinh tu khai bao; khung ung dung chi doc de hien thi.
 */

import { Service, computed, signal } from '@angular/core';

export interface MucDuongDan {
  readonly nhan: string;
  /** Duong dan dieu huong; `null` voi muc hien tai (cuoi breadcrumb). */
  readonly lienKet: string | null;
}

export const TRANG_CHU: MucDuongDan = { nhan: 'Trang chủ', lienKet: '/' };

@Service()
export class BoCucTrang {
  public readonly tieuDe = signal('Trang chủ');
  /** Dong mo ta ngan duoi tieu de trang. */
  public readonly moTa = signal<string | null>(null);
  /** Nhan trang thai ngan canh tieu de, vi du che do dinh tuyen o man Tro chuyen. */
  public readonly nhanPhu = signal<string | null>(null);
  /** Cac muc sau `Trang chủ`; rong nghia la dang o Trang chu. */
  public readonly duongDan = signal<readonly MucDuongDan[]>([]);

  public readonly laTrangChu = computed(() => this.duongDan().length === 0);

  public datTieuDe(
    tieuDe: string,
    duongDan: readonly MucDuongDan[] = [],
    nhanPhu: string | null = null,
    moTa: string | null = null,
  ): void {
    this.tieuDe.set(tieuDe);
    this.duongDan.set(duongDan);
    this.nhanPhu.set(nhanPhu);
    this.moTa.set(moTa);
  }
}
