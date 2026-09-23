/**
 * Phan tich config/huong_dan_su_dung.md (qua GET /api/v1/huong-dan) thanh cac muc co kieu,
 * de man Huong dan su dung dung dung ban Stitch bang template Angular, khong chen HTML tho.
 *
 * Quy uoc noi dung Markdown:
 * - `## Tieu de`: mot muc, hien trong muc luc.
 * - `### Lam duoc` / `### Chua lam duoc` kem danh sach: the xanh / the do dat canh nhau.
 * - `1. **Tieu de**: mo ta`: the buoc danh so.
 * - `- **Noi bo**: ...`, `- **Dam may**: ...`: huy hieu tang tra loi.
 * - `> **Vi du:** ...`: khung vi du; `> ...` khac: khung canh bao.
 * - Doan chi gom mot `ma`: chip ma kem nut sao chep.
 */

export interface PhanChu {
  readonly chu: string;
  readonly dam: boolean;
  readonly ma: boolean;
}

export interface BuocHuongDan {
  readonly tieuDe: string;
  readonly moTa: string;
}

export interface TheDanhSach {
  readonly tieuDe: string;
  readonly kieu: 'dat' | 'chua-dat';
  readonly cacMuc: PhanChu[][];
}

export interface HuyHieuTang {
  readonly nhan: string;
  readonly moTa: string;
  readonly kieu: 'noi-bo' | 'dam-may';
}

export type KhoiHuongDan =
  | { readonly loai: 'doan'; readonly noiDung: PhanChu[] }
  | { readonly loai: 'danh-sach'; readonly cacMuc: PhanChu[][] }
  | { readonly loai: 'cac-buoc'; readonly cacBuoc: BuocHuongDan[] }
  | { readonly loai: 'nhom-the'; readonly cacThe: TheDanhSach[] }
  | { readonly loai: 'huy-hieu'; readonly cacHuyHieu: HuyHieuTang[] }
  | { readonly loai: 'vi-du'; readonly noiDung: PhanChu[] }
  | { readonly loai: 'canh-bao'; readonly noiDung: PhanChu[] }
  | { readonly loai: 'ma'; readonly ma: string };

export interface MucHuongDan {
  readonly id: string;
  readonly tieuDe: string;
  readonly cacKhoi: KhoiHuongDan[];
}

const MAU_BUOC = /^\d+\.\s+\*\*(.+?)\*\*\s*:?\s*(.*)$/;
const MAU_HUY_HIEU = /^\*\*(Nội bộ|Đám mây)\*\*\s*:?\s*(.*)$/;
const TIEN_TO_VI_DU = /^\*\*Ví dụ:?\*\*\s*/;

/** Tao id neo tu tieu de tieng Viet: bo dau, chu thuong, noi bang gach ngang. */
export function taoIdSlug(van_ban: string): string {
  return van_ban
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/** Tach dong chu thanh cac doan thuong, **dam** va `ma`. */
export function tachPhanChu(dong: string): PhanChu[] {
  const ketQua: PhanChu[] = [];
  const mau = /\*\*(.+?)\*\*|`([^`]+)`/g;
  let viTri = 0;
  for (const khop of dong.matchAll(mau)) {
    const batDau = khop.index ?? 0;
    if (batDau > viTri) ketQua.push({ chu: dong.slice(viTri, batDau), dam: false, ma: false });
    if (khop[1] !== undefined) ketQua.push({ chu: khop[1], dam: true, ma: false });
    else ketQua.push({ chu: khop[2] ?? '', dam: false, ma: true });
    viTri = batDau + khop[0].length;
  }
  if (viTri < dong.length) ketQua.push({ chu: dong.slice(viTri), dam: false, ma: false });
  return ketQua;
}

/** Bo tich luy khoi cua mot muc: gom dong lien tiep cung loai thanh mot khoi. */
class BoGomKhoi {
  public readonly cacKhoi: KhoiHuongDan[] = [];
  private doan: string[] = [];
  private danhSach: PhanChu[][] = [];
  private cacBuoc: BuocHuongDan[] = [];
  private cacHuyHieu: HuyHieuTang[] = [];
  private trichDan: string[] = [];
  private cacThe: TheDanhSach[] = [];
  private theHienTai: { tieuDe: string; cacMuc: PhanChu[][] } | null = null;

  public them(dong: string): void {
    const dongGon = dong.trim();
    if (dongGon === '' || dongGon === '---') {
      this.dongDoanVaTrichDan();
      return;
    }
    if (dongGon.startsWith('### ')) {
      this.dongTatCa(false);
      this.theHienTai = { tieuDe: dongGon.slice(4).trim(), cacMuc: [] };
      return;
    }
    if (dongGon.startsWith('> ')) {
      this.dongDoan();
      this.trichDan.push(dongGon.slice(2).trim());
      return;
    }
    if (dongGon.startsWith('- ')) {
      this.themMucDanhSach(dongGon.slice(2).trim());
      return;
    }
    const buoc = MAU_BUOC.exec(dongGon);
    if (buoc) {
      this.dongDoanVaTrichDan();
      this.cacBuoc.push({ tieuDe: buoc[1].trim(), moTa: buoc[2].trim() });
      return;
    }
    this.dongTatCa(true);
    this.doan.push(dongGon);
  }

  public ketThuc(): KhoiHuongDan[] {
    this.dongTatCa(true);
    return this.cacKhoi;
  }

  private themMucDanhSach(noiDung: string): void {
    this.dongDoanVaTrichDan();
    if (this.theHienTai) {
      this.theHienTai.cacMuc.push(tachPhanChu(noiDung));
      return;
    }
    const huyHieu = MAU_HUY_HIEU.exec(noiDung);
    if (huyHieu) {
      this.cacHuyHieu.push({
        nhan: huyHieu[1],
        moTa: huyHieu[2].trim(),
        kieu: huyHieu[1] === 'Nội bộ' ? 'noi-bo' : 'dam-may',
      });
      return;
    }
    this.danhSach.push(tachPhanChu(noiDung));
  }

  private dongDoan(): void {
    if (this.doan.length === 0) return;
    const noiDung = this.doan.join(' ');
    this.doan = [];
    const chiMa = /^`([^`]+)`$/.exec(noiDung);
    this.cacKhoi.push(chiMa ? { loai: 'ma', ma: chiMa[1] } : { loai: 'doan', noiDung: tachPhanChu(noiDung) });
  }

  private dongDoanVaTrichDan(): void {
    this.dongDoan();
    if (this.trichDan.length === 0) return;
    const noiDung = this.trichDan.join(' ');
    this.trichDan = [];
    this.cacKhoi.push(
      TIEN_TO_VI_DU.test(noiDung)
        ? { loai: 'vi-du', noiDung: tachPhanChu(noiDung.replace(TIEN_TO_VI_DU, '')) }
        : { loai: 'canh-bao', noiDung: tachPhanChu(noiDung) },
    );
  }

  /** Dong moi khoi dang mo; `dongThe` = false khi bat dau the moi (giu nhom the lien tiep). */
  private dongTatCa(dongThe: boolean): void {
    this.dongDoanVaTrichDan();
    if (this.theHienTai) {
      const tieuDe = this.theHienTai.tieuDe;
      this.cacThe.push({
        tieuDe,
        kieu: /chưa/i.test(tieuDe) ? 'chua-dat' : 'dat',
        cacMuc: this.theHienTai.cacMuc,
      });
      this.theHienTai = null;
    }
    if (dongThe && this.cacThe.length > 0) {
      this.cacKhoi.push({ loai: 'nhom-the', cacThe: this.cacThe });
      this.cacThe = [];
    }
    // Huy hieu dung truoc danh sach thuong cua cung muc (ban Stitch: hai huy hieu roi cac y)
    if (this.cacHuyHieu.length > 0) {
      this.cacKhoi.push({ loai: 'huy-hieu', cacHuyHieu: this.cacHuyHieu });
      this.cacHuyHieu = [];
    }
    if (this.danhSach.length > 0) {
      this.cacKhoi.push({ loai: 'danh-sach', cacMuc: this.danhSach });
      this.danhSach = [];
    }
    if (this.cacBuoc.length > 0) {
      this.cacKhoi.push({ loai: 'cac-buoc', cacBuoc: this.cacBuoc });
      this.cacBuoc = [];
    }
  }
}

/** Phan tich toan bo tai lieu; phan truoc `##` dau tien (tieu de, gioi thieu) bi bo qua. */
export function phanTichHuongDan(markdown: string): MucHuongDan[] {
  const cacMuc: MucHuongDan[] = [];
  let tieuDe: string | null = null;
  let bo = new BoGomKhoi();

  const dongMuc = (): void => {
    if (tieuDe !== null) cacMuc.push({ id: taoIdSlug(tieuDe), tieuDe, cacKhoi: bo.ketThuc() });
  };

  for (const dong of markdown.split(/\r?\n/)) {
    if (dong.startsWith('## ')) {
      dongMuc();
      tieuDe = dong.slice(3).trim();
      bo = new BoGomKhoi();
    } else if (tieuDe !== null) {
      bo.them(dong);
    }
  }
  dongMuc();
  return cacMuc;
}
