/**
 * mo-hinh.ts - Khai bao cac kieu du lieu va interface su dung trong frontend.
 * Tuan thu cac quy chuan:
 * - AGENTS.md: Tran tu chu L2, khop chinh xac cac su kien tu Backend.
 * - type_safety.md: Strict mode, tuyet doi khong dung kieu any.
 * - naming.md: PascalCase cho interface/type, snake_case cho cac truong khop backend DTO.
 */

// ---------------------------------------------------------------------------
// 1. Cac su kien Server-Sent Events (SSE) tu Backend
// ---------------------------------------------------------------------------

export interface SuKienHangDoi {
  readonly loai: 'hang_doi';
  vi_tri: number;
  uoc_luong_giay?: number | null;
}

export interface SuKienBatDau {
  readonly loai: 'bat_dau';
  hoi_thoai_id?: number | null;
  nguon: string;
  tang: number;
  model: string;
  da_cat_ngu_canh: boolean;
  so_luot_bi_cat: number;
}

export interface SuKienManh {
  readonly loai: 'manh';
  noi_dung: string;
}

export interface SuKienXong {
  readonly loai: 'xong';
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
  readonly loai: 'loi';
  ma: string;
  thong_diep: string;
  ma_yeu_cau: string;
  phan_da_nhan?: string;
}

/**
 * Union type dai dien cho moi su kien SSE voi truong phan biet (discriminant field) la `loai`.
 */
export type SuKien = SuKienHangDoi | SuKienBatDau | SuKienManh | SuKienXong | SuKienLoi;

// ---------------------------------------------------------------------------
// 2. Cac kieu du lieu nghiep vu Hoi thoai va Luot tin nhan
// ---------------------------------------------------------------------------

export interface HoiThoai {
  id: number;
  tieu_de: string;
  tao_luc: string;
  cap_nhat_luc: string;
  da_xoa?: boolean;
}

export interface Luot {
  id: number;
  vai_tro: 'nguoi_dung' | 'tro_ly' | 'he_thong' | string;
  noi_dung: string;
  nguon?: string | null;
  tang?: number | null;
  bac_local?: string | null;
  model_da_dung?: string | null;
  token_vao?: number;
  token_ra?: number;
  chi_phi_usd?: number;
  tao_luc: string;
}

// Giu bi danh phu hop tuong thich nguoc
export type LuotTinNhan = Luot;

export interface DanhSachHoiThoai {
  danh_sach: HoiThoai[];
  tong_so: number;
  trang: number;
  kich_thuoc: number;
}

// Bi danh cho danh sach hoi thoai phan trang
export type DanhSachHoiThoaiPhanTrang = DanhSachHoiThoai;

export interface ChiTietHoiThoai {
  id: number;
  tieu_de: string;
  tao_luc: string;
  cap_nhat_luc: string;
  cac_luot: Luot[];
}

export interface PhanHoiXoaHoiThoai {
  thanh_cong: boolean;
  thong_diep: string;
}

export interface YeuCauChat {
  noi_dung: string;
  hoi_thoai_id?: number | null;
}

// ---------------------------------------------------------------------------
// 3. Chi phi va Trang thai Models, Hang doi
// ---------------------------------------------------------------------------

export interface PhanRaTheoTang {
  so_luot: number;
  token: number;
  chi_phi: number;
}

export interface BaoCaoChiPhi {
  chi_phi_hom_nay_usd: number;
  ngan_sach_ngay_usd: number;
  phan_tram_da_dung: number;
  phan_ra_theo_tang: Record<string | number, PhanRaTheoTang>;
  ty_le_local: number;
  ty_le_roi_tang: number;
}

export interface CauHinhBacLocal {
  bac: string;
  model: string;
  num_ctx: number;
  keep_alive: string;
}

export interface ThongTinTangDamMay {
  tang: number;
  ten: string;
  model: string;
  gia_vao_usd_moi_trieu: number;
  gia_ra_usd_moi_trieu: number;
  cua_so_ngu_canh: number;
  kha_dung: boolean;
}

export interface TrangThaiModels {
  che_do_dinh_tuyen: string;
  ho_so_gpu: string;
  bac_local: CauHinhBacLocal[];
  chuoi_dam_may: ThongTinTangDamMay[];
}

export interface TrangThaiHangDoi {
  dang_chay: number;
  dang_cho: number;
  thoi_gian_cho_trung_vi: number;
  so_bi_tu_choi_1_gio: number;
}

// ---------------------------------------------------------------------------
// 4. Cac kieu du lieu he thong bo tro
// ---------------------------------------------------------------------------

export interface ChiTietLoi {
  ma: string;
  thong_diep: string;
  ma_yeu_cau: string;
}

export interface PhanHoiLoi {
  loi: ChiTietLoi;
}

export interface TrangThaiSucKhoe {
  trang_thai: string;
  phien_ban: string;
}
