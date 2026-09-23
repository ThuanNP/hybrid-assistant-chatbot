/**
 * nhan-hien-thi.ts - Doi ma cau hinh cua may chu sang nhan tieng Viet de hien thi,
 * khong de lo ma ky thuat (`local_truoc`, `gpu6`, `chinh`) tren giao dien.
 */

const NHAN_CHE_DO_DINH_TUYEN: Readonly<Record<string, string>> = {
  chi_local: 'Chỉ mô hình nội bộ',
  local_truoc: 'Ưu tiên mô hình nội bộ',
  dam_may_truoc: 'Ưu tiên đám mây',
};

const NHAN_BAC_LOCAL: Readonly<Record<string, string>> = {
  chinh: 'Bậc chính',
  nho: 'Bậc nhỏ',
};

/** Ma che do la ma moi (chua co nhan) thi giu nguyen de khong mat thong tin. */
export function nhanCheDoDinhTuyen(ma: string | null | undefined): string {
  if (!ma) return '—';
  return NHAN_CHE_DO_DINH_TUYEN[ma] ?? ma;
}

/** `gpu6` -> `GPU 6 GB`; ho so khong theo mau thi giu nguyen. */
export function nhanHoSoGpu(ma: string | null | undefined): string {
  if (!ma) return '—';
  const khop = /^gpu(\d+)$/i.exec(ma);
  return khop ? `GPU ${khop[1]} GB` : ma;
}

export function nhanBacLocal(ma: string): string {
  return NHAN_BAC_LOCAL[ma] ?? ma;
}
