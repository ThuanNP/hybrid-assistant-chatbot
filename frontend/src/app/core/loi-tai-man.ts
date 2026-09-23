import { NavigationError } from '@angular/router';

/** Thong diep trinh duyet dua ra khi khong tai duoc mot chunk JavaScript tai theo nhu cau. */
const MAU_LOI_TAI_CHUNK = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|ChunkLoadError/i;

/**
 * Sau moi lan trien khai ban moi, tab dang mo van giu ten chunk cu nen dieu huong toi man
 * tai theo nhu cau se loi. Khi do tai lai toan trang toi dung dia chi dich de nhan ban moi,
 * thay vi dung im o man hien tai (vi du bam Dang nhap xong khong chuyen trang).
 */
export function xuLyLoiDieuHuong(loi: NavigationError): void {
  const thongDiep = loi.error instanceof Error ? loi.error.message : String(loi.error);
  if (MAU_LOI_TAI_CHUNK.test(thongDiep)) {
    window.location.assign(loi.url);
  }
}
