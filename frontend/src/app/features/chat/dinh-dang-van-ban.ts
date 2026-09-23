/**
 * dinh-dang-van-ban.ts - Phân tích cú pháp văn bản Markdown sang cấu trúc AST an toàn.
 * Tuân thủ quy chuẩn:
 * - AGENTS.md: Không gán innerHTML bằng chuỗi thô, bảo mật XSS tuyệt đối.
 * - clean_code.md: Hàm dưới 40 dòng, đơn nhiệm, không nuốt ngoại lệ.
 * - type_safety.md: Strict mode, cấm any.
 */

export interface DoanInline {
  loai: 'chu' | 'in_dam' | 'code_ngang';
  noiDung: string;
}

export interface KhoiMa {
  loai: 'ma';
  ngonNgu: string;
  noiDung: string;
}

export interface KhoiDanhSach {
  loai: 'danh_sach';
  coThuTu: boolean;
  cacMuc: DoanInline[][];
}

export interface KhoiBang {
  loai: 'bang';
  tieuDeCot: DoanInline[][];
  cacHang: DoanInline[][][];
}

export interface KhoiDoanVan {
  loai: 'doan_van';
  cacDoan: DoanInline[];
}

export type KhoiVanBan = KhoiMa | KhoiDanhSach | KhoiBang | KhoiDoanVan;

/**
 * Phân tích các định dạng nội dòng: in đậm (**...**) và code ngang (`...`).
 */
export function phanTichInline(vanBan: string): DoanInline[] {
  if (!vanBan) return [];
  const ketQua: DoanInline[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  const cacPhan = vanBan.split(regex);

  for (const phan of cacPhan) {
    if (!phan) continue;
    if (phan.startsWith('**') && phan.endsWith('**') && phan.length >= 4) {
      ketQua.push({ loai: 'in_dam', noiDung: phan.slice(2, -2) });
    } else if (phan.startsWith('`') && phan.endsWith('`') && phan.length >= 2) {
      ketQua.push({ loai: 'code_ngang', noiDung: phan.slice(1, -1) });
    } else {
      ketQua.push({ loai: 'chu', noiDung: phan });
    }
  }
  return ketQua;
}

/**
 * Trích xuất một khối mã (fenced code block) từ danh sách dòng.
 */
function trichXuatKhoiMa(cacDong: string[], viTriBatDau: number): { khoi: KhoiMa; viTriMoi: number } {
  const dongDau = cacDong[viTriBatDau].trim();
  const ngonNgu = dongDau.replace(/^```/, '').trim();
  const noiDungDong: string[] = [];
  let i = viTriBatDau + 1;

  while (i < cacDong.length && !cacDong[i].trim().startsWith('```')) {
    noiDungDong.push(cacDong[i]);
    i++;
  }
  if (i < cacDong.length && cacDong[i].trim().startsWith('```')) {
    i++;
  }

  return {
    khoi: { loai: 'ma', ngonNgu, noiDung: noiDungDong.join('\n') },
    viTriMoi: i,
  };
}

/**
 * Trích xuất một khối bảng Markdown từ danh sách dòng.
 */
function trichXuatBang(cacDong: string[], viTriBatDau: number): { khoi: KhoiBang; viTriMoi: number } {
  let i = viTriBatDau;
  const dongHeaders = cacDong[i].split('|').map((c) => c.trim()).filter(Boolean);
  const tieuDeCot: DoanInline[][] = dongHeaders.map((c) => phanTichInline(c));
  i++;

  // Bỏ qua dòng phân cách |---|---| nếu có
  if (i < cacDong.length && cacDong[i].includes('---')) {
    i++;
  }

  const cacHang: DoanInline[][][] = [];
  while (i < cacDong.length && cacDong[i].trim().startsWith('|')) {
    const oDong = cacDong[i].split('|').map((c) => c.trim()).filter(Boolean);
    if (oDong.length > 0) {
      cacHang.push(oDong.map((c) => phanTichInline(c)));
    }
    i++;
  }

  return { khoi: { loai: 'bang', tieuDeCot, cacHang }, viTriMoi: i };
}

/**
 * Trích xuất một khối danh sách (có thứ tự hoặc không thứ tự) từ danh sách dòng.
 */
function trichXuatDanhSach(
  cacDong: string[],
  viTriBatDau: number,
  coThuTu: boolean,
): { khoi: KhoiDanhSach; viTriMoi: number } {
  const cacMuc: DoanInline[][] = [];
  let i = viTriBatDau;
  const regexItem = coThuTu ? /^\d+\.\s+(.*)$/ : /^[-*]\s+(.*)$/;

  while (i < cacDong.length) {
    const dongTrim = cacDong[i].trim();
    const match = regexItem.exec(dongTrim);
    if (!match) break;
    cacMuc.push(phanTichInline(match[1]));
    i++;
  }

  return { khoi: { loai: 'danh_sach', coThuTu, cacMuc }, viTriMoi: i };
}

/**
 * Phân tích toàn bộ văn bản đầu vào thành các khối AST hiển thị an toàn.
 */
export function phanTichVanBan(vanBanTho: string): KhoiVanBan[] {
  if (!vanBanTho) return [];
  const cacDong = vanBanTho.split(/\r?\n/);
  const danhSachKhoi: KhoiVanBan[] = [];
  let i = 0;

  while (i < cacDong.length) {
    const dong = cacDong[i];
    const dongTrim = dong.trim();

    if (!dongTrim) {
      i++;
      continue;
    }

    if (dongTrim.startsWith('```')) {
      const { khoi, viTriMoi } = trichXuatKhoiMa(cacDong, i);
      danhSachKhoi.push(khoi);
      i = viTriMoi;
    } else if (dongTrim.startsWith('|') && dongTrim.endsWith('|')) {
      const { khoi, viTriMoi } = trichXuatBang(cacDong, i);
      danhSachKhoi.push(khoi);
      i = viTriMoi;
    } else if (/^\d+\.\s+/.test(dongTrim)) {
      const { khoi, viTriMoi } = trichXuatDanhSach(cacDong, i, true);
      danhSachKhoi.push(khoi);
      i = viTriMoi;
    } else if (/^[-*]\s+/.test(dongTrim)) {
      const { khoi, viTriMoi } = trichXuatDanhSach(cacDong, i, false);
      danhSachKhoi.push(khoi);
      i = viTriMoi;
    } else {
      danhSachKhoi.push({ loai: 'doan_van', cacDoan: phanTichInline(dong) });
      i++;
    }
  }

  return danhSachKhoi;
}
