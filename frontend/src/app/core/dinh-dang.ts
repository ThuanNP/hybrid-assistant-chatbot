/**
 * dinh-dang.ts - Ham dinh dang du lieu hien thi theo DESIGN.md muc 11.
 */

const MS_MOT_NGAY = 24 * 60 * 60 * 1000;

function hai(so: number): string {
  return String(so).padStart(2, '0');
}

/** Dinh dang `dd/mm/yyyy - HH:mm`; tra ve chuoi goc neu khong phan tich duoc. */
export function dinhDangNgayGio(chuoiIso: string): string {
  const d = new Date(chuoiIso);
  if (!chuoiIso || Number.isNaN(d.getTime())) return chuoiIso;
  return `${hai(d.getDate())}/${hai(d.getMonth() + 1)}/${d.getFullYear()} - ${hai(d.getHours())}:${hai(d.getMinutes())}`;
}

/** Dinh dang ngay dai cho loi chao, vi du `Thứ Tư, 23/09/2026`. */
export function dinhDangNgayDai(d: Date): string {
  const thu = d.getDay() === 0 ? 'Chủ Nhật' : `Thứ ${['Hai', 'Ba', 'Tư', 'Năm', 'Sáu', 'Bảy'][d.getDay() - 1]}`;
  return `${thu}, ${hai(d.getDate())}/${hai(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/**
 * Moc thoi gian gon cho dong lich su (tieu de nhom da cho biet ngay): hom nay, hom qua ghi `HH:mm`;
 * cung nam ghi `dd/mm`; nam khac ghi `dd/mm/yyyy`.
 */
export function dinhDangMocGon(chuoiIso: string, bayGio: Date): string {
  const d = new Date(chuoiIso);
  if (!chuoiIso || Number.isNaN(d.getTime())) return chuoiIso;
  const nhom = xepNhomThoiGian(chuoiIso, bayGio);
  if (nhom === 'Hôm nay' || nhom === 'Hôm qua') return `${hai(d.getHours())}:${hai(d.getMinutes())}`;
  const ngayThang = `${hai(d.getDate())}/${hai(d.getMonth() + 1)}`;
  return d.getFullYear() === bayGio.getFullYear() ? ngayThang : `${ngayThang}/${d.getFullYear()}`;
}

export type NhomThoiGian = 'Hôm nay' | 'Hôm qua' | 'Cũ hơn';

/** Xep mot moc thoi gian vao nhom hien thi cua danh sach lich su: hom nay, hom qua, cu hon. */
export function xepNhomThoiGian(chuoiIso: string, bayGio: Date): NhomThoiGian {
  const d = new Date(chuoiIso);
  const dauHomNay = new Date(bayGio.getFullYear(), bayGio.getMonth(), bayGio.getDate()).getTime();
  const moc = d.getTime();
  if (Number.isNaN(moc)) return 'Cũ hơn';
  if (moc >= dauHomNay) return 'Hôm nay';
  if (moc >= dauHomNay - MS_MOT_NGAY) return 'Hôm qua';
  return 'Cũ hơn';
}
