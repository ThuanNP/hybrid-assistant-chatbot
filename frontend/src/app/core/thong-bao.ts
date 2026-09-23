/**
 * thong-bao.ts - Trang thai he thong va thong bao van hanh cho thanh dau trang.
 * Moi thong tin suy ra tu so lieu that cua may chu (suc khoe, mo hinh, chi phi, hang doi),
 * khong co thong bao gia lap.
 */

import { Service, computed, inject, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth/auth.service';
import { BaoCaoChiPhi, TrangThaiHangDoi, TrangThaiModels } from './mo-hinh';

export type MucThongBao = 'loi' | 'canh-bao' | 'thong-tin';
export type TrangThaiDichVu = 'dang-kiem-tra' | 'hoat-dong' | 'mat-ket-noi';

export interface ThongBao {
  readonly ma: string;
  readonly muc: MucThongBao;
  readonly noiDung: string;
}

/** `/health` tra `song` khi tien trinh may chu con chay. */
const TRANG_THAI_SONG = 'song';
const DINH_DANG_SO = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });

const NHAN_TRANG_THAI: Readonly<Record<TrangThaiDichVu, string>> = {
  'dang-kiem-tra': 'Đang kiểm tra',
  'hoat-dong': 'Đang hoạt động',
  'mat-ket-noi': 'Mất kết nối',
};

@Service()
export class DichVuThongBao {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);

  private readonly chiPhi = signal<BaoCaoChiPhi | null>(null);
  private readonly hangDoi = signal<TrangThaiHangDoi | null>(null);

  public readonly trangThai = signal<TrangThaiDichVu>('dang-kiem-tra');
  public readonly moHinh = signal<TrangThaiModels | null>(null);
  /** Phien ban may chu lay tu `/health`, hien o footer. */
  public readonly phienBan = signal<string | null>(null);

  public readonly nhanTrangThai = computed(() => NHAN_TRANG_THAI[this.trangThai()]);

  /** `ty_le_roi_tang` la phan so 0..1; hien thi theo phan tram kieu Viet Nam. */
  public readonly tyLeRoiTang = computed(() => {
    const tyLe = this.chiPhi()?.ty_le_roi_tang;
    return tyLe === undefined ? '—' : `${DINH_DANG_SO.format(tyLe * 100)}%`;
  });

  public readonly danhSach = computed<ThongBao[]>(() => {
    const ketQua: ThongBao[] = [];
    if (this.trangThai() === 'mat-ket-noi') {
      ketQua.push({ ma: 'mat-ket-noi', muc: 'loi', noiDung: 'Không kết nối được máy chủ trợ lý.' });
    }
    // Nguong canh bao lay tu cau hinh may chu (phan so 0-1), khong ghi cung o giao dien
    const chiPhi = this.chiPhi();
    if (chiPhi && chiPhi.phan_tram_da_dung >= chiPhi.nguong_canh_bao_ngan_sach * 100) {
      ketQua.push({
        ma: 'ngan-sach',
        muc: 'canh-bao',
        noiDung: `Chi phí đám mây đã dùng ${DINH_DANG_SO.format(chiPhi.phan_tram_da_dung)}% ngân sách ngày.`,
      });
    }
    if (chiPhi && chiPhi.ty_le_roi_tang > chiPhi.nguong_ty_le_roi_tang) {
      ketQua.push({
        ma: 'roi-tang',
        muc: 'canh-bao',
        noiDung: `Tỷ lệ rơi tầng trong 1 giờ qua là ${this.tyLeRoiTang()}.`,
      });
    }
    const hangDoi = this.hangDoi();
    if (hangDoi && hangDoi.dang_cho > 0) {
      ketQua.push({
        ma: 'hang-doi',
        muc: 'thong-tin',
        noiDung: `${hangDoi.dang_cho} yêu cầu đang chờ ở hàng đợi mô hình nội bộ.`,
      });
    }
    return ketQua;
  });

  public readonly soLuong = computed(() => this.danhSach().length);

  /** Chi goi /health (cong khai, khong cham CSDL): dung cho kiem tra dinh ky cua nut trang thai. */
  public kiemTraSucKhoe(): void {
    this.api.kiemTraSucKhoe().subscribe({
      next: (kq) => {
        this.trangThai.set(kq?.trang_thai === TRANG_THAI_SONG ? 'hoat-dong' : 'mat-ket-noi');
        this.phienBan.set(kq?.phien_ban ?? null);
      },
      error: () => this.trangThai.set('mat-ket-noi'),
    });
  }

  public taiLai(): void {
    this.kiemTraSucKhoe();
    // Cac API con lai can token: chua co phien thi khong goi, tranh 401 va lam moi token thua
    if (!this.auth.daDangNhap()) return;
    this.api.layModels().subscribe({ next: (kq) => this.moHinh.set(kq), error: () => {} });
    this.api.layChiPhi().subscribe({ next: (kq) => this.chiPhi.set(kq), error: () => {} });
    this.api.layTrangThaiHangDoi().subscribe({ next: (kq) => this.hangDoi.set(kq), error: () => {} });
  }
}
