/**
 * mo-hinh.ts - Khai bao cac kieu du lieu va interface su dung trong frontend.
 * Tuan thu quy chuan type_safety.md: strict mode, khong su dung kieu any.
 */

export interface ChiTietLoi {
  ma: string;
  thong_diep: string;
  ma_yeu_cau: string;
}

export interface PhanHoiLoi {
  loi: ChiTietLoi;
}

export type VaiTroTinNhan = 'user' | 'assistant';

export interface LuotTinNhan {
  id?: number;
  hoi_thoai_id?: number;
  vai_tro: VaiTroTinNhan;
  noi_dung: string;
  model?: string;
  nguon?: string;
  tang?: number;
  bac_local?: string;
  ma_yeu_cau?: string;
  tao_luc?: string;
  nhan_ai?: string;
}

export interface HoiThoai {
  id: number;
  tieu_de: string;
  tao_luc: string;
  cap_nhat_luc: string;
  da_xoa?: boolean;
}

export interface DanhSachHoiThoaiPhanTrang {
  items: HoiThoai[];
  tong_so: number;
  trang: number;
  kich_thuoc: number;
}

export interface YeuCauChat {
  noi_dung: string;
  hoi_thoai_id?: number | null;
}

export interface SuKienHangDoi {
  vi_tri: number;
  uoc_luong_giay?: number | null;
}

export interface SuKienBatDau {
  hoi_thoai_id?: number | null;
  nguon: string;
  tang: number;
  model: string;
  da_cat_ngu_canh: boolean;
  so_luot_bi_cat: number;
}

export interface SuKienManh {
  noi_dung: string;
}

export interface SuKienXong {
  token_vao: number;
  token_ra: number;
  chi_phi_usd: number;
  toc_do_tok_s: number;
  do_tre_ms: number;
  nguon: string;
  tang: number;
  bac_local?: string | null;
  model: string;
  nhan_ai: string;
}

export interface SuKienLoi {
  ma: string;
  thong_diep: string;
  ma_yeu_cau: string;
  phan_da_nhan?: string;
}

export interface ThongTinMoHinh {
  ten: string;
  nguon: string;
  tang: number;
  bac_local?: string;
  ho_so_gpu?: string;
}

export interface TrangThaiSucKhoe {
  trang_thai: string;
  phien_ban: string;
}
